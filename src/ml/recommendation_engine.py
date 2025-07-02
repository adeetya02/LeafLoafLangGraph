"""
Async Recommendation Engine
Non-blocking, timeout-safe recommendations
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog
from src.data_capture.capture_strategy import data_capture
from src.cache.redis_feature import redis_feature, smart_redis_manager

logger = structlog.get_logger()

class AsyncRecommendationEngine:
    """
    Recommendation engine that runs asynchronously
    Never blocks the main search flow
    """
    
    def __init__(self):
        self.default_timeout = 1.0  # 1 second max
        self.cache_ttl = 3600  # 1 hour
        self.min_history_for_recs = 3  # Minimum searches for personalization
        
    async def get_recommendations(self, 
                                user_id: str,
                                current_query: str,
                                current_results: List[Dict],
                                timeout: Optional[float] = None) -> Dict:
        """
        Get recommendations with timeout protection
        Returns empty recommendations if timeout or error
        """
        timeout = timeout or self.default_timeout
        
        try:
            # Run with timeout
            recommendations = await asyncio.wait_for(
                self._generate_recommendations(user_id, current_query, current_results),
                timeout=timeout
            )
            return recommendations
            
        except asyncio.TimeoutError:
            logger.warning(f"Recommendation timeout for user {user_id}")
            return self._empty_recommendations()
            
        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            return self._empty_recommendations()
    
    async def _generate_recommendations(self,
                                      user_id: str,
                                      current_query: str,
                                      current_results: List[Dict]) -> Dict:
        """Generate personalized recommendations"""
        
        # Check cache first
        cached = await self._get_cached_recommendations(user_id)
        if cached:
            return cached
        
        # Get user ML features
        user_data = await data_capture.get_user_data_for_ml(user_id)
        
        # If insufficient history, return category-based recs
        if user_data["features"].get("search_count", 0) < self.min_history_for_recs:
            return await self._get_category_recommendations(current_query, current_results)
        
        # Generate personalized recommendations
        recommendations = {
            "type": "personalized",
            "user_id": user_id,
            "generated_at": datetime.utcnow().isoformat(),
            "recommendations": []
        }
        
        # 1. Reorder predictions
        reorder_items = await self._predict_reorders(user_data)
        if reorder_items:
            recommendations["reorder_suggestions"] = reorder_items[:5]
        
        # 2. Complementary products
        complement_items = await self._find_complements(user_data, current_results)
        if complement_items:
            recommendations["you_might_like"] = complement_items[:5]
        
        # 3. Trending in user's preferences
        trending = await self._get_personalized_trending(user_data)
        if trending:
            recommendations["trending_for_you"] = trending[:5]
        
        # Cache recommendations
        await self._cache_recommendations(user_id, recommendations)
        
        return recommendations
    
    async def _predict_reorders(self, user_data: Dict) -> List[Dict]:
        """Predict items user might need to reorder"""
        
        # Simple implementation - would use ML model in production
        history = user_data.get("history_sample", [])
        
        # Find frequently ordered items
        product_frequency = {}
        for search in history:
            for result in search.get("results", []):
                product_id = result.get("product_id")
                if product_id:
                    product_frequency[product_id] = product_frequency.get(product_id, 0) + 1
        
        # Sort by frequency
        frequent_items = sorted(
            product_frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Return top items with reorder prediction
        reorder_predictions = []
        for product_id, frequency in frequent_items[:10]:
            # Estimate days until reorder (mock calculation)
            days_until_reorder = 14 - (frequency * 2)  # More frequent = sooner
            
            reorder_predictions.append({
                "product_id": product_id,
                "confidence": min(0.9, frequency * 0.15),
                "predicted_need_date": (
                    datetime.utcnow() + timedelta(days=max(1, days_until_reorder))
                ).isoformat(),
                "reason": "frequently_ordered"
            })
        
        return reorder_predictions
    
    async def _find_complements(self, 
                               user_data: Dict,
                               current_results: List[Dict]) -> List[Dict]:
        """Find complementary products"""
        
        # Simple rule-based approach (would use association rules in production)
        complements = []
        
        # Get categories from current results
        current_categories = set()
        for result in current_results[:5]:  # Top 5 results
            category = result.get("category", "").lower()
            if category:
                current_categories.add(category)
        
        # Suggest complements based on categories
        complement_rules = {
            "dairy": ["bakery", "breakfast"],
            "produce": ["dairy", "meat"],
            "bakery": ["dairy", "deli"],
            "breakfast": ["dairy", "bakery"]
        }
        
        suggested_categories = set()
        for category in current_categories:
            if category in complement_rules:
                suggested_categories.update(complement_rules[category])
        
        # Return mock products from suggested categories
        for category in suggested_categories:
            complements.append({
                "category": category,
                "reason": f"goes_well_with_{list(current_categories)[0]}",
                "confidence": 0.7
            })
        
        return complements
    
    async def _get_personalized_trending(self, user_data: Dict) -> List[Dict]:
        """Get trending items based on user preferences"""
        
        # Extract user preferences
        preferred_categories = user_data["features"].get("preferred_categories", {})
        
        # Mock trending items (would query from analytics in production)
        trending = []
        for category, preference_score in preferred_categories.items():
            trending.append({
                "category": category,
                "trending_score": preference_score * 0.8,
                "reason": "popular_in_your_preferred_category"
            })
        
        return sorted(trending, key=lambda x: x["trending_score"], reverse=True)
    
    async def _get_category_recommendations(self,
                                          query: str,
                                          current_results: List[Dict]) -> Dict:
        """Get category-based recommendations for new users"""
        
        # Extract category from results
        categories = {}
        for result in current_results:
            cat = result.get("category", "Unknown")
            categories[cat] = categories.get(cat, 0) + 1
        
        top_category = max(categories.items(), key=lambda x: x[1])[0] if categories else "General"
        
        return {
            "type": "category_based",
            "generated_at": datetime.utcnow().isoformat(),
            "recommendations": {
                "popular_in_category": [
                    {
                        "category": top_category,
                        "reason": "popular_choice",
                        "confidence": 0.6
                    }
                ]
            }
        }
    
    async def _get_cached_recommendations(self, user_id: str) -> Optional[Dict]:
        """Get cached recommendations if available"""
        if not redis_feature.enabled:
            return None
            
        try:
            manager = await smart_redis_manager._get_manager()
            cache_key = f"user:{user_id}:recommendations"
            cached = await manager.async_client.get(cache_key)
            
            if cached:
                import json
                return json.loads(cached)
                
        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            
        return None
    
    async def _cache_recommendations(self, user_id: str, recommendations: Dict):
        """Cache recommendations"""
        if not redis_feature.enabled:
            return
            
        try:
            manager = await smart_redis_manager._get_manager()
            cache_key = f"user:{user_id}:recommendations"
            
            import json
            await manager.async_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(recommendations)
            )
            
        except Exception as e:
            logger.error(f"Cache storage error: {e}")
    
    def _empty_recommendations(self) -> Dict:
        """Return empty recommendations structure"""
        return {
            "type": "empty",
            "generated_at": datetime.utcnow().isoformat(),
            "recommendations": {},
            "reason": "timeout_or_error"
        }
    
    async def enrich_search_results(self,
                                  user_id: str,
                                  query: str,
                                  results: List[Dict]) -> List[Dict]:
        """
        Enrich search results with ML scores
        This is fire-and-forget, doesn't block
        """
        
        # Start enrichment task without awaiting
        asyncio.create_task(
            self._async_enrich_results(user_id, query, results)
        )
        
        # Return original results immediately
        return results
    
    async def _async_enrich_results(self,
                                   user_id: str,
                                   query: str,
                                   results: List[Dict]):
        """Async enrichment of results with ML scores"""
        try:
            # Get user preferences
            user_data = await data_capture.get_user_data_for_ml(user_id)
            
            # Calculate personalization scores
            for result in results:
                # Add ML-based scoring
                result["ml_score"] = await self._calculate_ml_score(
                    result,
                    user_data["features"]
                )
                
                # Add reorder probability
                result["reorder_probability"] = await self._calculate_reorder_prob(
                    result.get("product_id"),
                    user_data
                )
            
            # Log enrichment completion
            logger.info(f"Enriched {len(results)} results for user {user_id}")
            
        except Exception as e:
            logger.error(f"Result enrichment failed: {e}")
    
    async def _calculate_ml_score(self, 
                                product: Dict,
                                user_features: Dict) -> float:
        """Calculate personalized score for product"""
        # Simple scoring based on category preference
        category = product.get("category", "").lower()
        preferred_categories = user_features.get("preferred_categories", {})
        
        base_score = product.get("score", 0.5)
        preference_boost = preferred_categories.get(category, 0.0) * 0.3
        
        return min(1.0, base_score + preference_boost)
    
    async def _calculate_reorder_prob(self,
                                    product_id: str,
                                    user_data: Dict) -> float:
        """Calculate reorder probability"""
        # Check if product was ordered before
        history = user_data.get("history_sample", [])
        
        order_count = 0
        for search in history:
            for result in search.get("results", []):
                if result.get("product_id") == product_id:
                    order_count += 1
        
        # Simple probability based on order frequency
        if order_count == 0:
            return 0.0
        elif order_count == 1:
            return 0.3
        elif order_count == 2:
            return 0.6
        else:
            return 0.9

# Global instance
recommendation_engine = AsyncRecommendationEngine()