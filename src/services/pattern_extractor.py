"""
Pattern Extraction Service

Extracts patterns from BigQuery materialized views and prepares them
for synchronization to Graphiti. This is the first step in the feedback loop.
"""

import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import structlog
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger()


class PatternType(Enum):
    """Types of patterns we extract"""
    PREFERENCE = "preference"
    ASSOCIATION = "association" 
    REORDER = "reorder"
    BEHAVIOR = "behavior"
    SESSION = "session"


@dataclass
class ExtractedPattern:
    """Represents an extracted pattern ready for Graphiti"""
    pattern_type: PatternType
    source_node_id: str  # user_id or product_sku
    target_node_id: str  # brand/category/product
    edge_type: str  # PREFERS, BOUGHT_WITH, REORDERS_EVERY, etc.
    confidence: float
    properties: Dict[str, Any]
    extracted_at: datetime
    should_sync: bool = True


class PatternExtractor:
    """Extracts patterns from BigQuery materialized views"""
    
    def __init__(self, project_id: str = "leafloafai", dataset_id: str = "leafloaf_analytics"):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = None
        
        # Confidence thresholds for different pattern types
        self.confidence_thresholds = {
            PatternType.PREFERENCE: 0.7,
            PatternType.ASSOCIATION: 0.6,
            PatternType.REORDER: 0.8,
            PatternType.BEHAVIOR: 0.5,
            PatternType.SESSION: 0.0  # Always sync session patterns
        }
        
        # Limits for each pattern type
        self.pattern_limits = {
            PatternType.PREFERENCE: 20,  # Top 20 preferences per user
            PatternType.ASSOCIATION: 10,  # Top 10 associations per product
            PatternType.REORDER: 50,  # All high-confidence reorder patterns
            PatternType.BEHAVIOR: 1,  # 1 behavior summary per user
            PatternType.SESSION: 5  # Last 5 session patterns
        }
    
    def _get_client(self) -> bigquery.Client:
        """Lazy initialize BigQuery client"""
        if not self.client:
            self.client = bigquery.Client(project=self.project_id)
        return self.client
    
    async def extract_all_patterns(self, 
                                  user_ids: Optional[List[str]] = None,
                                  since: Optional[datetime] = None) -> List[ExtractedPattern]:
        """Extract all pattern types for given users or all users"""
        
        logger.info("Starting pattern extraction", 
                   user_count=len(user_ids) if user_ids else "all",
                   since=since)
        
        # Run extractions in parallel
        tasks = [
            self.extract_preference_patterns(user_ids, since),
            self.extract_association_patterns(since),
            self.extract_reorder_patterns(user_ids, since),
            self.extract_behavior_patterns(user_ids, since),
            self.extract_session_patterns(user_ids)  # Only last 24h
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine all patterns
        all_patterns = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Pattern extraction failed for task {i}", error=str(result))
            else:
                all_patterns.extend(result)
        
        logger.info(f"Extracted {len(all_patterns)} total patterns")
        return all_patterns
    
    async def extract_preference_patterns(self, 
                                        user_ids: Optional[List[str]] = None,
                                        since: Optional[datetime] = None) -> List[ExtractedPattern]:
        """Extract user preference patterns (brands, categories)"""
        
        try:
            client = self._get_client()
            
            # Build query
            query = f"""
            SELECT 
                user_id,
                brand,
                category,
                preference_score,
                confidence,
                total_interactions,
                last_interaction,
                active_days,
                product_variety
            FROM `{self.project_id}.{self.dataset_id}.user_preference_patterns`
            WHERE confidence >= @min_confidence
            """
            
            if user_ids:
                query += " AND user_id IN UNNEST(@user_ids)"
            
            if since:
                query += " AND last_updated >= @since"
            
            query += " ORDER BY user_id, preference_score DESC"
            
            # Set parameters
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("min_confidence", "FLOAT64", 
                                                self.confidence_thresholds[PatternType.PREFERENCE]),
                    bigquery.ArrayQueryParameter("user_ids", "STRING", user_ids or []),
                    bigquery.ScalarQueryParameter("since", "TIMESTAMP", since)
                ]
            )
            
            # Execute query
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()
            
            # Convert to patterns
            patterns = []
            user_pattern_count = {}
            
            for row in results:
                user_id = row["user_id"]
                
                # Limit patterns per user
                if user_pattern_count.get(user_id, 0) >= self.pattern_limits[PatternType.PREFERENCE]:
                    continue
                
                # Brand preference
                if row["brand"] != "Unknown":
                    patterns.append(ExtractedPattern(
                        pattern_type=PatternType.PREFERENCE,
                        source_node_id=user_id,
                        target_node_id=f"brand:{row['brand']}",
                        edge_type="PREFERS_BRAND",
                        confidence=row["confidence"],
                        properties={
                            "preference_score": row["preference_score"],
                            "interactions": row["total_interactions"],
                            "last_interaction": row["last_interaction"].isoformat(),
                            "active_days": row["active_days"],
                            "strength": "strong" if row["preference_score"] > 5.0 else "moderate"
                        },
                        extracted_at=datetime.utcnow()
                    ))
                
                # Category preference
                if row["category"] != "Unknown":
                    patterns.append(ExtractedPattern(
                        pattern_type=PatternType.PREFERENCE,
                        source_node_id=user_id,
                        target_node_id=f"category:{row['category']}",
                        edge_type="PREFERS_CATEGORY",
                        confidence=row["confidence"],
                        properties={
                            "preference_score": row["preference_score"],
                            "interactions": row["total_interactions"],
                            "product_variety": row["product_variety"]
                        },
                        extracted_at=datetime.utcnow()
                    ))
                
                user_pattern_count[user_id] = user_pattern_count.get(user_id, 0) + 2
            
            logger.info(f"Extracted {len(patterns)} preference patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to extract preference patterns: {e}")
            return []
    
    async def extract_association_patterns(self, 
                                         since: Optional[datetime] = None) -> List[ExtractedPattern]:
        """Extract product association patterns (bought together)"""
        
        try:
            client = self._get_client()
            
            query = f"""
            SELECT 
                product_a,
                product_b,
                name_a,
                name_b,
                co_occurrence_count,
                confidence,
                lift,
                unique_users
            FROM `{self.project_id}.{self.dataset_id}.product_association_patterns`
            WHERE confidence >= @min_confidence
                AND lift > 1.0  -- Only positive associations
            """
            
            if since:
                query += " AND last_updated >= @since"
            
            query += " ORDER BY co_occurrence_count DESC LIMIT 1000"
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("min_confidence", "FLOAT64",
                                                self.confidence_thresholds[PatternType.ASSOCIATION]),
                    bigquery.ScalarQueryParameter("since", "TIMESTAMP", since)
                ]
            )
            
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()
            
            patterns = []
            product_associations = {}
            
            for row in results:
                # Limit associations per product
                key = row["product_a"]
                if product_associations.get(key, 0) >= self.pattern_limits[PatternType.ASSOCIATION]:
                    continue
                
                patterns.append(ExtractedPattern(
                    pattern_type=PatternType.ASSOCIATION,
                    source_node_id=f"product:{row['product_a']}",
                    target_node_id=f"product:{row['product_b']}",
                    edge_type="BOUGHT_WITH",
                    confidence=row["confidence"],
                    properties={
                        "co_occurrences": row["co_occurrence_count"],
                        "lift": row["lift"],
                        "unique_users": row["unique_users"],
                        "name_a": row["name_a"],
                        "name_b": row["name_b"],
                        "association_type": "complementary" if row["lift"] > 2.0 else "related"
                    },
                    extracted_at=datetime.utcnow()
                ))
                
                product_associations[key] = product_associations.get(key, 0) + 1
            
            logger.info(f"Extracted {len(patterns)} association patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to extract association patterns: {e}")
            return []
    
    async def extract_reorder_patterns(self,
                                     user_ids: Optional[List[str]] = None,
                                     since: Optional[datetime] = None) -> List[ExtractedPattern]:
        """Extract reorder patterns for predictive restocking"""
        
        try:
            client = self._get_client()
            
            query = f"""
            SELECT 
                user_id,
                product_sku,
                product_name,
                avg_reorder_days,
                reorder_variance,
                avg_quantity,
                order_count,
                reorder_confidence,
                days_since_last_order,
                reorder_due
            FROM `{self.project_id}.{self.dataset_id}.reorder_intelligence_patterns`
            WHERE reorder_confidence >= @min_confidence
            """
            
            if user_ids:
                query += " AND user_id IN UNNEST(@user_ids)"
            
            if since:
                query += " AND last_updated >= @since"
            
            query += " ORDER BY user_id, reorder_confidence DESC"
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("min_confidence", "FLOAT64",
                                                self.confidence_thresholds[PatternType.REORDER]),
                    bigquery.ArrayQueryParameter("user_ids", "STRING", user_ids or []),
                    bigquery.ScalarQueryParameter("since", "TIMESTAMP", since)
                ]
            )
            
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()
            
            patterns = []
            
            for row in results:
                patterns.append(ExtractedPattern(
                    pattern_type=PatternType.REORDER,
                    source_node_id=row["user_id"],
                    target_node_id=f"product:{row['product_sku']}",
                    edge_type="REORDERS_EVERY",
                    confidence=row["reorder_confidence"],
                    properties={
                        "days": int(row["avg_reorder_days"]),
                        "variance": row["reorder_variance"],
                        "usual_quantity": int(row["avg_quantity"]),
                        "order_count": row["order_count"],
                        "days_since_last": row["days_since_last_order"],
                        "due_for_reorder": row["reorder_due"],
                        "product_name": row["product_name"]
                    },
                    extracted_at=datetime.utcnow()
                ))
            
            logger.info(f"Extracted {len(patterns)} reorder patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to extract reorder patterns: {e}")
            return []
    
    async def extract_behavior_patterns(self,
                                      user_ids: Optional[List[str]] = None,
                                      since: Optional[datetime] = None) -> List[ExtractedPattern]:
        """Extract overall shopping behavior patterns"""
        
        try:
            client = self._get_client()
            
            query = f"""
            SELECT 
                user_id,
                total_orders,
                avg_order_value,
                avg_items_per_order,
                preferred_shopping_day,
                preferred_shopping_hour,
                shopping_frequency,
                top_categories
            FROM `{self.project_id}.{self.dataset_id}.user_shopping_behavior_patterns`
            WHERE total_orders >= 5  -- Only established shoppers
            """
            
            if user_ids:
                query += " AND user_id IN UNNEST(@user_ids)"
            
            if since:
                query += " AND last_updated >= @since"
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("user_ids", "STRING", user_ids or []),
                    bigquery.ScalarQueryParameter("since", "TIMESTAMP", since)
                ]
            )
            
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()
            
            patterns = []
            
            for row in results:
                # Extract top categories
                top_categories = []
                if row["top_categories"]:
                    top_categories = [cat["category"] for cat in row["top_categories"][:3]]
                
                patterns.append(ExtractedPattern(
                    pattern_type=PatternType.BEHAVIOR,
                    source_node_id=row["user_id"],
                    target_node_id=f"behavior:{row['shopping_frequency']}",
                    edge_type="HAS_SHOPPING_PATTERN",
                    confidence=min(1.0, row["total_orders"] / 50.0),  # Confidence based on order history
                    properties={
                        "frequency": row["shopping_frequency"],
                        "preferred_day": row["preferred_shopping_day"],
                        "preferred_hour": row["preferred_shopping_hour"],
                        "avg_basket_size": row["avg_items_per_order"],
                        "avg_basket_value": row["avg_order_value"],
                        "top_categories": top_categories
                    },
                    extracted_at=datetime.utcnow()
                ))
            
            logger.info(f"Extracted {len(patterns)} behavior patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to extract behavior patterns: {e}")
            return []
    
    async def extract_session_patterns(self,
                                     user_ids: Optional[List[str]] = None) -> List[ExtractedPattern]:
        """Extract current session patterns for real-time personalization"""
        
        try:
            client = self._get_client()
            
            # Only get sessions from last 4 hours for real-time relevance
            query = f"""
            SELECT 
                session_id,
                user_id,
                session_start,
                session_duration_minutes,
                unique_queries,
                products_viewed,
                cart_adds,
                current_cart_total,
                session_intent,
                recent_products
            FROM `{self.project_id}.{self.dataset_id}.session_context_patterns`
            WHERE session_start >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 4 HOUR)
                AND user_id IS NOT NULL
            """
            
            if user_ids:
                query += " AND user_id IN UNNEST(@user_ids)"
            
            query += " ORDER BY session_start DESC"
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ArrayQueryParameter("user_ids", "STRING", user_ids or [])
                ]
            )
            
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()
            
            patterns = []
            user_sessions = {}
            
            for row in results:
                user_id = row["user_id"]
                
                # Only keep latest session per user
                if user_id in user_sessions:
                    continue
                
                # Extract viewed categories
                viewed_categories = set()
                if row["recent_products"]:
                    for product in row["recent_products"]:
                        if product.get("category"):
                            viewed_categories.add(product["category"])
                
                patterns.append(ExtractedPattern(
                    pattern_type=PatternType.SESSION,
                    source_node_id=user_id,
                    target_node_id=f"session:{row['session_id']}",
                    edge_type="ACTIVE_SESSION",
                    confidence=1.0,  # Current session is always relevant
                    properties={
                        "intent": row["session_intent"],
                        "duration_minutes": row["session_duration_minutes"],
                        "products_viewed": row["products_viewed"],
                        "cart_adds": row["cart_adds"],
                        "cart_value": row["current_cart_total"],
                        "categories_browsed": list(viewed_categories),
                        "search_count": row["unique_queries"]
                    },
                    extracted_at=datetime.utcnow()
                ))
                
                user_sessions[user_id] = True
            
            logger.info(f"Extracted {len(patterns)} session patterns")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to extract session patterns: {e}")
            return []
    
    def filter_patterns_for_sync(self, patterns: List[ExtractedPattern]) -> List[ExtractedPattern]:
        """Filter patterns to determine which should be synced to Graphiti"""
        
        filtered = []
        
        for pattern in patterns:
            # Apply confidence threshold
            min_confidence = self.confidence_thresholds.get(pattern.pattern_type, 0.5)
            
            if pattern.confidence >= min_confidence:
                pattern.should_sync = True
                filtered.append(pattern)
            else:
                logger.debug(f"Filtered out pattern with low confidence",
                           pattern_type=pattern.pattern_type,
                           confidence=pattern.confidence,
                           threshold=min_confidence)
        
        logger.info(f"Filtered {len(patterns)} patterns to {len(filtered)} for sync")
        return filtered
    
    async def extract_patterns_for_user(self, user_id: str) -> List[ExtractedPattern]:
        """Extract all patterns for a specific user"""
        return await self.extract_all_patterns(user_ids=[user_id])


# Global instance
pattern_extractor = PatternExtractor()