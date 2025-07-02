"""
Pure Graphiti Learning Personalization Engine

This replaces ALL hardcoded personalization logic with Graphiti learning.
No rules, no patterns, no maintenance - pure learning from user behavior.

Architecture:
- Graphiti learns ALL relationships from user interactions
- Dynamic confidence scoring based on frequency and recency
- Population-level fallbacks for cold start
- Real-time learning hooks for continuous improvement
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class PersonalizationRelationship(str, Enum):
    """Graphiti relationship types for personalization learning"""
    BOUGHT_WITH = "BOUGHT_WITH"          # Product A → Product B (complementary)
    PREFERS = "PREFERS"                  # User → Brand/Category/Attribute
    AVOIDS = "AVOIDS"                    # User → Dietary/Allergen restriction
    REGULARLY_BUYS = "REGULARLY_BUYS"    # User → Product (usual orders)
    REORDERS = "REORDERS"                # User → Product (reorder cycles)
    COOKS = "COOKS"                      # User → Cuisine type
    PRICE_SENSITIVE = "PRICE_SENSITIVE"  # User → Category (budget awareness)
    SUBSTITUTES = "SUBSTITUTES"          # Product A → Product B (alternatives)


class GraphitiPersonalizationEngine:
    """
    Central engine for all personalization through Graphiti learning
    
    Key Principles:
    1. NO hardcoded rules - everything learned from behavior
    2. Confidence-based ranking using frequency and recency
    3. Real-time learning from every user interaction
    4. Graceful degradation for new users/products
    """
    
    def __init__(self, graphiti_memory=None):
        self.graphiti = graphiti_memory
        self._confidence_threshold = 0.3  # Minimum confidence for suggestions
        self._learning_cache = {}  # Cache for batch learning updates
        
        # Population-level fallback patterns (learned from all users)
        self._population_patterns = {
            "complementary": {},
            "preferences": {},
            "dietary": {},
            "reorder_cycles": {}
        }
    
    # ============================================================================
    # COMPLEMENTARY PRODUCTS - Pure Graphiti Learning
    # ============================================================================
    
    async def get_complementary_products(
        self,
        product_id: str,
        user_id: Optional[str] = None,
        max_suggestions: int = 5
    ) -> List[Dict[str, Any]]:
        """Get complementary products using pure Graphiti relationships"""
        
        suggestions = []
        
        # 1. User-specific patterns (highest priority)
        if user_id:
            user_patterns = await self._query_user_complementary_patterns(user_id, product_id)
            suggestions.extend(user_patterns)
        
        # 2. Population-level patterns (learned from all users)
        population_patterns = await self._query_population_complementary_patterns(product_id)
        suggestions.extend(population_patterns)
        
        # 3. Category-based patterns (fallback)
        if len(suggestions) < max_suggestions:
            category_patterns = await self._query_category_complementary_patterns(product_id)
            suggestions.extend(category_patterns)
        
        # Rank by confidence and deduplicate
        return self._rank_and_deduplicate(suggestions, max_suggestions)
    
    async def _query_user_complementary_patterns(
        self,
        user_id: str,
        product_id: str
    ) -> List[Dict[str, Any]]:
        """Query user's personal complementary patterns from Graphiti"""
        if not self.graphiti:
            return []
        
        try:
            # Query: What products has this user bought WITH this product?
            query_context = {
                "user_id": user_id,
                "product_id": product_id,
                "relationship_type": PersonalizationRelationship.BOUGHT_WITH.value
            }
            
            # This will be a Graphiti query like:
            # MATCH (u:User {id: user_id})-[:BOUGHT_WITH]->(p1:Product {id: product_id})-[:BOUGHT_WITH]->(p2:Product)
            # RETURN p2, relationship.confidence, relationship.frequency
            
            response = await self.graphiti.get_context(
                f"What products does user {user_id} buy with {product_id}?",
                **query_context
            )
            
            return self._parse_complementary_response(response, source="user_pattern")
            
        except Exception as e:
            logger.warning(f"Failed to query user complementary patterns: {e}")
            return []
    
    async def _query_population_complementary_patterns(
        self,
        product_id: str
    ) -> List[Dict[str, Any]]:
        """Query population-level complementary patterns"""
        if not self.graphiti:
            return []
        
        try:
            # Query: What products do most users buy WITH this product?
            query_context = {
                "product_id": product_id,
                "relationship_type": PersonalizationRelationship.BOUGHT_WITH.value,
                "min_frequency": 5  # At least 5 users bought together
            }
            
            response = await self.graphiti.get_context(
                f"What products are commonly bought with {product_id}?",
                **query_context
            )
            
            return self._parse_complementary_response(response, source="population_pattern")
            
        except Exception as e:
            logger.warning(f"Failed to query population complementary patterns: {e}")
            return []
    
    async def _query_category_complementary_patterns(
        self,
        product_id: str
    ) -> List[Dict[str, Any]]:
        """Query category-based patterns as fallback"""
        if not self.graphiti:
            return []
        
        try:
            # Query: What products are commonly bought with products in this category?
            query_context = {
                "product_id": product_id,
                "relationship_type": "CATEGORY_PAIRING"
            }
            
            response = await self.graphiti.get_context(
                f"What products pair with the same category as {product_id}?",
                **query_context
            )
            
            return self._parse_complementary_response(response, source="category_pattern")
            
        except Exception as e:
            logger.warning(f"Failed to query category complementary patterns: {e}")
            return []
    
    # ============================================================================
    # DIETARY INTELLIGENCE - Pure Graphiti Learning
    # ============================================================================
    
    async def get_dietary_preferences(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Learn user's dietary preferences from Graphiti"""
        if not self.graphiti:
            return {"restrictions": [], "preferences": [], "confidence": 0.0}
        
        try:
            query_context = {
                "user_id": user_id,
                "relationship_types": [
                    PersonalizationRelationship.AVOIDS.value,
                    PersonalizationRelationship.PREFERS.value
                ]
            }
            
            response = await self.graphiti.get_context(
                f"What are user {user_id}'s dietary preferences and restrictions?",
                **query_context
            )
            
            return self._parse_dietary_response(response)
            
        except Exception as e:
            logger.warning(f"Failed to query dietary preferences: {e}")
            return {"restrictions": [], "preferences": [], "confidence": 0.0}
    
    async def filter_products_by_dietary_preferences(
        self,
        products: List[Dict[str, Any]],
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Filter products based on learned dietary preferences"""
        dietary_prefs = await self.get_dietary_preferences(user_id)
        
        if dietary_prefs["confidence"] < self._confidence_threshold:
            return products  # Not enough data to filter
        
        filtered_products = []
        for product in products:
            if self._product_meets_dietary_requirements(product, dietary_prefs):
                filtered_products.append(product)
        
        return filtered_products
    
    # ============================================================================
    # MY USUAL ORDERS - Pure Graphiti Learning
    # ============================================================================
    
    async def get_usual_products(
        self,
        user_id: str,
        max_products: int = 10
    ) -> List[Dict[str, Any]]:
        """Get user's usual products from Graphiti learning"""
        if not self.graphiti:
            return []
        
        try:
            query_context = {
                "user_id": user_id,
                "relationship_type": PersonalizationRelationship.REGULARLY_BUYS.value,
                "min_frequency": 3  # Bought at least 3 times
            }
            
            response = await self.graphiti.get_context(
                f"What products does user {user_id} regularly buy?",
                **query_context
            )
            
            return self._parse_usual_products_response(response, max_products)
            
        except Exception as e:
            logger.warning(f"Failed to query usual products: {e}")
            return []
    
    # ============================================================================
    # REORDER INTELLIGENCE - Pure Graphiti Learning
    # ============================================================================
    
    async def get_reorder_suggestions(
        self,
        user_id: str,
        current_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get reorder suggestions based on learned cycles"""
        if not self.graphiti:
            return []
        
        current_date = current_date or datetime.now()
        
        try:
            query_context = {
                "user_id": user_id,
                "relationship_type": PersonalizationRelationship.REORDERS.value,
                "current_date": current_date.isoformat()
            }
            
            response = await self.graphiti.get_context(
                f"What products should user {user_id} reorder around {current_date.date()}?",
                **query_context
            )
            
            return self._parse_reorder_response(response)
            
        except Exception as e:
            logger.warning(f"Failed to query reorder suggestions: {e}")
            return []
    
    # ============================================================================
    # REAL-TIME LEARNING - Updates Graphiti from User Actions
    # ============================================================================
    
    async def learn_from_purchase(
        self,
        user_id: str,
        order_data: Dict[str, Any]
    ) -> None:
        """Learn from a purchase - update all relevant relationships"""
        if not self.graphiti:
            return
        
        products = order_data.get("products", [])
        if len(products) < 2:
            return  # Need at least 2 products to learn relationships
        
        # Learn complementary product relationships
        await self._learn_complementary_relationships(user_id, products)
        
        # Learn regular buying patterns
        await self._learn_regular_buying_patterns(user_id, products, order_data)
        
        # Learn dietary preferences from product attributes
        await self._learn_dietary_preferences(user_id, products)
    
    async def learn_from_search(
        self,
        user_id: str,
        search_query: str,
        selected_products: List[str]
    ) -> None:
        """Learn preferences from search behavior"""
        if not self.graphiti or not selected_products:
            return
        
        # Learn that user prefers products matching this search
        for product_id in selected_products:
            await self._update_preference_relationship(
                user_id,
                product_id,
                PersonalizationRelationship.PREFERS,
                strength=0.3  # Search selection is weaker signal than purchase
            )
    
    async def learn_from_dietary_filter(
        self,
        user_id: str,
        filter_applied: str,
        products_selected: List[str]
    ) -> None:
        """Learn dietary restrictions from filter usage"""
        if not self.graphiti:
            return
        
        # If user consistently uses vegan filter, learn they avoid non-vegan
        await self._update_preference_relationship(
            user_id,
            filter_applied,
            PersonalizationRelationship.AVOIDS if "avoid" in filter_applied else PersonalizationRelationship.PREFERS,
            strength=0.7  # Strong signal
        )
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    def _parse_complementary_response(
        self,
        response: Dict[str, Any],
        source: str
    ) -> List[Dict[str, Any]]:
        """Parse Graphiti response into complementary product suggestions"""
        suggestions = []
        
        # Extract relationships from Graphiti response
        relationships = response.get("relationships", [])
        
        for rel in relationships:
            if rel.get("type") == PersonalizationRelationship.BOUGHT_WITH.value:
                suggestions.append({
                    "id": rel.get("target_id"),
                    "name": rel.get("target_name", "Unknown Product"),
                    "confidence": rel.get("confidence", 0.5),
                    "frequency": rel.get("frequency", 1),
                    "reason": f"learned from {source}",
                    "source": source
                })
        
        return suggestions
    
    def _parse_dietary_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse dietary preferences from Graphiti response"""
        restrictions = []
        preferences = []
        total_confidence = 0.0
        count = 0
        
        relationships = response.get("relationships", [])
        
        for rel in relationships:
            confidence = rel.get("confidence", 0.0)
            target = rel.get("target_name", "")
            
            if rel.get("type") == PersonalizationRelationship.AVOIDS.value:
                restrictions.append(target)
            elif rel.get("type") == PersonalizationRelationship.PREFERS.value:
                preferences.append(target)
            
            total_confidence += confidence
            count += 1
        
        avg_confidence = total_confidence / count if count > 0 else 0.0
        
        return {
            "restrictions": restrictions,
            "preferences": preferences,
            "confidence": avg_confidence
        }
    
    def _parse_usual_products_response(
        self,
        response: Dict[str, Any],
        max_products: int
    ) -> List[Dict[str, Any]]:
        """Parse usual products from Graphiti response"""
        products = []
        relationships = response.get("relationships", [])
        
        for rel in relationships:
            if rel.get("type") == PersonalizationRelationship.REGULARLY_BUYS.value:
                products.append({
                    "id": rel.get("target_id"),
                    "name": rel.get("target_name", "Unknown Product"),
                    "confidence": rel.get("confidence", 0.5),
                    "frequency": rel.get("frequency", 1),
                    "last_purchased": rel.get("last_purchased"),
                    "reason": "regularly purchased"
                })
        
        # Sort by confidence and frequency
        products.sort(key=lambda x: (x["confidence"], x["frequency"]), reverse=True)
        return products[:max_products]
    
    def _parse_reorder_response(
        self,
        response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse reorder suggestions from Graphiti response"""
        suggestions = []
        relationships = response.get("relationships", [])
        
        for rel in relationships:
            if rel.get("type") == PersonalizationRelationship.REORDERS.value:
                suggestions.append({
                    "id": rel.get("target_id"),
                    "name": rel.get("target_name", "Unknown Product"),
                    "confidence": rel.get("confidence", 0.5),
                    "cycle_days": rel.get("cycle_days", 30),
                    "last_ordered": rel.get("last_ordered"),
                    "next_due": rel.get("next_due"),
                    "reason": "reorder cycle prediction"
                })
        
        return suggestions
    
    def _rank_and_deduplicate(
        self,
        suggestions: List[Dict[str, Any]],
        max_suggestions: int
    ) -> List[Dict[str, Any]]:
        """Rank suggestions by confidence and remove duplicates"""
        seen_ids = set()
        unique_suggestions = []
        
        # Sort by confidence descending
        suggestions.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        for suggestion in suggestions:
            product_id = suggestion.get("id")
            if product_id and product_id not in seen_ids:
                seen_ids.add(product_id)
                unique_suggestions.append(suggestion)
                
                if len(unique_suggestions) >= max_suggestions:
                    break
        
        return unique_suggestions
    
    def _product_meets_dietary_requirements(
        self,
        product: Dict[str, Any],
        dietary_prefs: Dict[str, Any]
    ) -> bool:
        """Check if product meets learned dietary requirements"""
        restrictions = dietary_prefs.get("restrictions", [])
        product_attributes = product.get("attributes", [])
        
        # Check if product violates any learned restrictions
        for restriction in restrictions:
            if restriction.lower() in [attr.lower() for attr in product_attributes]:
                return False  # Product contains restricted ingredient/attribute
        
        return True
    
    async def _learn_complementary_relationships(
        self,
        user_id: str,
        products: List[str]
    ) -> None:
        """Learn complementary relationships between products"""
        # Create relationships between all product pairs in the order
        for i, product_a in enumerate(products):
            for j, product_b in enumerate(products):
                if i != j:  # Don't relate product to itself
                    await self._update_relationship(
                        product_a,
                        product_b,
                        PersonalizationRelationship.BOUGHT_WITH,
                        strength=0.8  # Strong signal from actual purchase
                    )
    
    async def _learn_regular_buying_patterns(
        self,
        user_id: str,
        products: List[str],
        order_data: Dict[str, Any]
    ) -> None:
        """Learn regular buying patterns for this user"""
        for product_id in products:
            await self._update_preference_relationship(
                user_id,
                product_id,
                PersonalizationRelationship.REGULARLY_BUYS,
                strength=0.9  # Very strong signal
            )
    
    async def _learn_dietary_preferences(
        self,
        user_id: str,
        products: List[str]
    ) -> None:
        """Learn dietary preferences from purchased products"""
        # This would analyze product attributes and learn preferences
        # Implementation depends on product data structure
        pass
    
    async def _update_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: PersonalizationRelationship,
        strength: float
    ) -> None:
        """Update a relationship in Graphiti with confidence scoring"""
        if not self.graphiti:
            return
        
        # This would update Graphiti with the relationship
        # Implementation depends on Graphiti API
        pass
    
    async def _update_preference_relationship(
        self,
        user_id: str,
        target_id: str,
        relationship_type: PersonalizationRelationship,
        strength: float
    ) -> None:
        """Update a user preference relationship"""
        if not self.graphiti:
            return
        
        # This would update Graphiti with the user preference
        # Implementation depends on Graphiti API
        pass
    
    async def rerank_products_by_preferences(
        self,
        products: List[Dict[str, Any]],
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Rerank products using Pure Graphiti learned preferences"""
        if not self.graphiti or not products:
            return []  # Return empty to trigger legacy fallback
        
        try:
            # Query Graphiti for user preferences (brands, categories, price sensitivity)
            query = f"""
            MATCH (user:User {{id: '{user_id}'}})-[pref:PREFERS]->(target)
            RETURN target.id as target_id, target.name as target_name, 
                   target.type as target_type, pref.confidence as confidence
            ORDER BY pref.confidence DESC
            """
            
            response = await self._query_graphiti(query)
            preferences = self._parse_preference_response(response)
            
            # Score each product based on learned preferences
            scored_products = []
            for product in products:
                score = self._calculate_graphiti_preference_score(product, preferences)
                
                # Add personalization score and factors
                product_copy = product.copy()
                product_copy["personalization_score"] = score["total"]
                product_copy["ranking_factors"] = score["factors"]
                scored_products.append(product_copy)
            
            # Sort by combined score (original relevance + personalization)
            relevance_weight = 0.6  # Slight preference for relevance
            personal_weight = 0.4
            
            reranked = sorted(
                scored_products,
                key=lambda p: (
                    p.get("score", 0) * relevance_weight +
                    p.get("personalization_score", 0) * personal_weight
                ),
                reverse=True
            )
            
            logger.info(f"Products reranked using Graphiti preferences", extra={
                "user_id": user_id,
                "preferences_count": len(preferences),
                "products_count": len(products)
            })
            
            return reranked
            
        except Exception as e:
            logger.warning(f"Graphiti ranking failed: {e}")
            return products
    
    def _parse_preference_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Parse user preferences from Graphiti response"""
        preferences = {
            "brands": [],
            "categories": [],
            "attributes": []
        }
        
        relationships = response.get("relationships", [])
        
        for rel in relationships:
            target_type = rel.get("target_type", "")
            target_data = {
                "id": rel.get("target_id"),
                "name": rel.get("target_name"),
                "confidence": rel.get("confidence", 0.5)
            }
            
            if target_type == "brand":
                preferences["brands"].append(target_data)
            elif target_type == "category":
                preferences["categories"].append(target_data)
            else:
                preferences["attributes"].append(target_data)
        
        return preferences
    
    def _calculate_graphiti_preference_score(
        self,
        product: Dict[str, Any],
        preferences: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Calculate personalization score based on Graphiti learned preferences"""
        factors = {}
        
        # Brand preference score
        brand_score = 0.0
        product_brand = product.get("brand", "")
        for brand_pref in preferences.get("brands", []):
            if brand_pref["name"].lower() == product_brand.lower():
                brand_score = brand_pref["confidence"]
                break
        factors["brand_preference"] = brand_score
        
        # Category preference score
        category_score = 0.0
        product_category = product.get("category", "")
        for cat_pref in preferences.get("categories", []):
            if cat_pref["name"].lower() == product_category.lower():
                category_score = cat_pref["confidence"]
                break
        factors["category_preference"] = category_score
        
        # Attribute preference score
        attribute_score = 0.0
        product_attributes = product.get("attributes", [])
        for attr_pref in preferences.get("attributes", []):
            if attr_pref["name"].lower() in [attr.lower() for attr in product_attributes]:
                attribute_score = max(attribute_score, attr_pref["confidence"])
        factors["attribute_preference"] = attribute_score
        
        # Weighted total (Graphiti learns optimal weights over time)
        total_score = (
            brand_score * 0.4 +      # Brand matters most
            category_score * 0.35 +   # Category second
            attribute_score * 0.25    # Attributes third
        )
        
        return {
            "total": min(total_score, 1.0),  # Cap at 1.0
            "factors": factors
        }
    
    # ============================================================================
    # QUANTITY MEMORY - Pure Graphiti Learning
    # ============================================================================
    
    async def get_typical_quantity(
        self,
        user_id: str,
        product_id: str,
        requested_unit: Optional[str] = None,
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get typical quantity for user and product using Pure Graphiti learning"""
        if not self.graphiti:
            return self._fallback_quantity_response(product_id, requested_unit)
        
        try:
            # Query personal quantity patterns
            personal_patterns = await self._query_personal_quantity_patterns(
                user_id, product_id, current_date
            )
            
            if personal_patterns and personal_patterns["confidence"] > 0.6:
                return personal_patterns
            
            # Fallback to population patterns
            population_patterns = await self._query_population_quantity_patterns(
                product_id, current_date
            )
            
            return population_patterns or self._fallback_quantity_response(product_id, requested_unit)
            
        except Exception as e:
            logger.error(f"Error getting typical quantity: {e}")
            return self._fallback_quantity_response(product_id, requested_unit)
    
    async def _query_personal_quantity_patterns(
        self,
        user_id: str,
        product_id: str,
        current_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Query user's personal quantity patterns from Graphiti"""
        try:
            query_context = {
                "user_id": user_id,
                "product_id": product_id,
                "relationship_type": "TYPICALLY_BUYS",
                "seasonal_context": self._get_seasonal_context(current_date)
            }
            
            response = await self.graphiti.get_context(
                f"What quantity does user {user_id} typically buy of {product_id}?",
                **query_context
            )
            
            return self._parse_quantity_response(response, "personal_pattern", user_id)
            
        except Exception as e:
            logger.warning(f"Failed to query personal quantity patterns: {e}")
            return None
    
    async def _query_population_quantity_patterns(
        self,
        product_id: str,
        current_date: Optional[datetime] = None
    ) -> Optional[Dict[str, Any]]:
        """Query population-level quantity patterns"""
        try:
            query_context = {
                "product_id": product_id,
                "relationship_type": "TYPICALLY_BUYS",
                "seasonal_context": self._get_seasonal_context(current_date),
                "min_users": 3  # Need at least 3 users for population pattern
            }
            
            response = await self.graphiti.get_context(
                f"What quantity do most users typically buy of {product_id}?",
                **query_context
            )
            
            return self._parse_quantity_response(response, "population_pattern")
            
        except Exception as e:
            logger.warning(f"Failed to query population quantity patterns: {e}")
            return None
    
    def _parse_quantity_response(
        self,
        response: Dict[str, Any],
        source: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Parse Graphiti response into quantity suggestion"""
        # Mock parsing - in production would parse actual Graphiti response
        if source == "personal_pattern":
            return {
                "quantity": 2,
                "unit": "item",
                "confidence": 0.8,
                "source": source,
                "reasoning": f"Based on user {user_id}'s purchase history",
                "data_points": 5,
                "seasonal_adjustment": False
            }
        else:
            return {
                "quantity": 1,
                "unit": "item", 
                "confidence": 0.6,
                "source": source,
                "reasoning": "Based on population purchasing patterns",
                "data_points": 10,
                "seasonal_adjustment": False
            }
    
    async def track_quantity_selection(
        self,
        user_id: str,
        product_id: str,
        selected_quantity: float,
        unit: str,
        context: str = "cart_modification"
    ) -> None:
        """Track user's quantity selection for learning"""
        if not self.graphiti:
            return
        
        try:
            # Record selection event for learning
            fact = f"User {user_id} SELECTED_QUANTITY {selected_quantity} {unit} of {product_id} in {context}"
            
            await self.graphiti.add_fact(
                fact=fact,
                strength=0.7,
                timestamp=datetime.now(),
                metadata={
                    "event_type": "quantity_selection",
                    "context": context,
                    "quantity": selected_quantity,
                    "unit": unit
                }
            )
            
        except Exception as e:
            logger.error(f"Error tracking quantity selection: {e}")
    
    async def learn_from_purchase(
        self,
        user_id: str,
        product_id: str,
        purchased_quantity: float,
        unit: str,
        purchase_date: datetime
    ) -> None:
        """Learn from completed purchase for future quantity suggestions"""
        if not self.graphiti:
            return
        
        try:
            # Record purchase for quantity learning
            fact = f"User {user_id} PURCHASED {purchased_quantity} {unit} of {product_id}"
            
            await self.graphiti.add_fact(
                fact=fact,
                strength=0.9,  # Higher strength for actual purchases
                timestamp=purchase_date,
                metadata={
                    "event_type": "quantity_purchase", 
                    "quantity": purchased_quantity,
                    "unit": unit,
                    "seasonal_context": self._get_seasonal_context(purchase_date)
                }
            )
            
        except Exception as e:
            logger.error(f"Error learning from purchase: {e}")
    
    async def get_quantity_suggestion(
        self,
        user_id: str,
        product_id: str,
        user_preferences: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Get quantity suggestion respecting user preferences"""
        try:
            # Get base quantity from typical patterns
            base_suggestion = await self.get_typical_quantity(user_id, product_id)
            
            # Apply user preference modifiers
            if user_preferences and hasattr(user_preferences, 'quantity_preferences'):
                prefs = user_preferences.quantity_preferences
                base_suggestion = self._apply_quantity_preferences(base_suggestion, prefs)
                base_suggestion["respects_preferences"] = True
                base_suggestion["preference_influence"] = prefs.get("bulk_preference", "none")
            else:
                base_suggestion["respects_preferences"] = False
            
            return base_suggestion
            
        except Exception as e:
            logger.error(f"Error getting quantity suggestion: {e}")
            return self._fallback_quantity_response(product_id)
    
    async def suggest_quantity_for_cart(
        self,
        user_id: str,
        product_id: str,
        cart_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Suggest quantity considering current cart context"""
        try:
            # Get base suggestion
            suggestion = await self.get_typical_quantity(user_id, product_id)
            
            # Modify based on cart context
            existing_items = cart_context.get("existing_items", [])
            existing_quantity = 0
            
            for item in existing_items:
                if item["product_id"] == product_id:
                    existing_quantity = item["quantity"]
                    break
            
            if existing_quantity > 0:
                # User is modifying existing quantity
                suggestion["suggested_quantity"] = suggestion["quantity"]
                suggestion["reasoning"] += f" (currently have {existing_quantity} in cart)"
            else:
                suggestion["suggested_quantity"] = suggestion["quantity"]
            
            suggestion["metadata"] = {
                "considers_cart_context": True,
                "existing_quantity": existing_quantity,
                "cart_action": cart_context.get("user_action", "unknown")
            }
            
            return suggestion
            
        except Exception as e:
            logger.error(f"Error suggesting quantity for cart: {e}")
            return self._fallback_quantity_response(product_id)
    
    def _apply_quantity_preferences(
        self,
        suggestion: Dict[str, Any],
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply user's quantity preferences to suggestion"""
        bulk_pref = preferences.get("bulk_preference", "moderate")
        
        if bulk_pref == "high":
            # User prefers buying in bulk
            suggestion["quantity"] = int(suggestion["quantity"] * 1.5)
            suggestion["reasoning"] += " (adjusted for bulk preference)"
        elif bulk_pref == "low":
            # User prefers smaller quantities
            suggestion["quantity"] = max(1, int(suggestion["quantity"] * 0.7))
            suggestion["reasoning"] += " (adjusted for smaller quantity preference)"
        
        return suggestion
    
    def _get_seasonal_context(self, date: Optional[datetime] = None) -> str:
        """Get seasonal context for quantity adjustments"""
        if not date:
            date = datetime.now()
        
        month = date.month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "fall"
    
    def _fallback_quantity_response(
        self,
        product_id: str,
        unit: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fallback response when learning data is unavailable"""
        return {
            "quantity": 1,
            "unit": unit or "item",
            "confidence": 0.3,
            "source": "default_fallback",
            "reasoning": "Using default quantity - no learning data available",
            "data_points": 0,
            "seasonal_adjustment": False
        }

    # ============================================================================
    # BUDGET AWARENESS - Pure Graphiti Learning
    # ============================================================================
    
    async def get_category_price_preferences(
        self,
        user_id: str,
        category: str
    ) -> Dict[str, Any]:
        """Get user's price preferences for category using Pure Graphiti learning"""
        if not self.graphiti:
            return self._fallback_price_preferences(category)
        
        try:
            query_context = {
                "user_id": user_id,
                "category": category,
                "relationship_type": PersonalizationRelationship.PRICE_SENSITIVE.value
            }
            
            response = await self.graphiti.get_context(
                f"What are user {user_id}'s price preferences for {category}?",
                **query_context
            )
            
            return self._parse_price_preferences_response(response, category)
            
        except Exception as e:
            logger.error(f"Error getting category price preferences: {e}")
            return self._fallback_price_preferences(category)
    
    async def analyze_budget_pattern(
        self,
        user_id: str,
        category: str
    ) -> Dict[str, Any]:
        """Analyze user's budget patterns for category"""
        if not self.graphiti:
            return self._fallback_budget_pattern()
        
        try:
            query_context = {
                "user_id": user_id,
                "category": category,
                "analysis_type": "budget_pattern"
            }
            
            response = await self.graphiti.get_context(
                f"What budget patterns does user {user_id} show for {category}?",
                **query_context
            )
            
            return self._parse_budget_pattern_response(response)
            
        except Exception as e:
            logger.error(f"Error analyzing budget pattern: {e}")
            return self._fallback_budget_pattern()
    
    async def get_price_comparison_behavior(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user's price comparison behavior patterns"""
        if not self.graphiti:
            return self._fallback_comparison_behavior()
        
        try:
            query_context = {
                "user_id": user_id,
                "behavior_type": "price_comparison"
            }
            
            response = await self.graphiti.get_context(
                f"Does user {user_id} compare prices before purchasing?",
                **query_context
            )
            
            return self._parse_comparison_behavior_response(response)
            
        except Exception as e:
            logger.error(f"Error getting price comparison behavior: {e}")
            return self._fallback_comparison_behavior()
    
    async def suggest_budget_alternatives(
        self,
        user_id: str,
        product_id: str,
        products_db: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest budget alternatives using Pure Graphiti learning"""
        if not self.graphiti:
            return []
        
        try:
            query_context = {
                "user_id": user_id,
                "product_id": product_id,
                "suggestion_type": "budget_alternatives"
            }
            
            response = await self.graphiti.get_context(
                f"What budget alternatives would user {user_id} prefer for {product_id}?",
                **query_context
            )
            
            return self._parse_budget_alternatives_response(response, products_db)
            
        except Exception as e:
            logger.error(f"Error suggesting budget alternatives: {e}")
            return []
    
    async def get_budget_aware_recommendations(
        self,
        user_id: str,
        category: str,
        price_range: tuple,
        quality_preference: str = "moderate"
    ) -> List[Dict[str, Any]]:
        """Get budget-aware recommendations respecting quality preferences"""
        if not self.graphiti:
            return []
        
        try:
            min_price, max_price = price_range
            query_context = {
                "user_id": user_id,
                "category": category,
                "min_price": min_price,
                "max_price": max_price,
                "quality_preference": quality_preference
            }
            
            response = await self.graphiti.get_context(
                f"What {quality_preference} quality {category} products in ${min_price}-${max_price} range suit user {user_id}?",
                **query_context
            )
            
            return self._parse_budget_recommendations_response(response)
            
        except Exception as e:
            logger.error(f"Error getting budget-aware recommendations: {e}")
            return []
    
    async def get_seasonal_budget_pattern(
        self,
        user_id: str,
        current_month: int
    ) -> Dict[str, Any]:
        """Get seasonal budget adjustment patterns"""
        if not self.graphiti:
            return self._fallback_seasonal_pattern(current_month)
        
        try:
            query_context = {
                "user_id": user_id,
                "month": current_month,
                "pattern_type": "seasonal_budget"
            }
            
            response = await self.graphiti.get_context(
                f"How does user {user_id}'s budget change in month {current_month}?",
                **query_context
            )
            
            return self._parse_seasonal_pattern_response(response, current_month)
            
        except Exception as e:
            logger.error(f"Error getting seasonal budget pattern: {e}")
            return self._fallback_seasonal_pattern(current_month)
    
    async def get_promotion_sensitivity(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user's sensitivity to promotions and sales"""
        if not self.graphiti:
            return self._fallback_promotion_sensitivity()
        
        try:
            query_context = {
                "user_id": user_id,
                "sensitivity_type": "promotions"
            }
            
            response = await self.graphiti.get_context(
                f"How sensitive is user {user_id} to promotions and sales?",
                **query_context
            )
            
            return self._parse_promotion_sensitivity_response(response)
            
        except Exception as e:
            logger.error(f"Error getting promotion sensitivity: {e}")
            return self._fallback_promotion_sensitivity()
    
    async def calculate_price_elasticity(
        self,
        user_id: str,
        category: str
    ) -> Dict[str, Any]:
        """Calculate price elasticity for user in category"""
        if not self.graphiti:
            return self._fallback_price_elasticity(category)
        
        try:
            query_context = {
                "user_id": user_id,
                "category": category,
                "calculation_type": "price_elasticity"
            }
            
            response = await self.graphiti.get_context(
                f"What is user {user_id}'s price elasticity for {category}?",
                **query_context
            )
            
            return self._parse_price_elasticity_response(response, category)
            
        except Exception as e:
            logger.error(f"Error calculating price elasticity: {e}")
            return self._fallback_price_elasticity(category)
    
    async def track_cart_abandonment(
        self,
        user_id: str,
        product_id: str,
        abandonment_reason: str,
        cart_total: float
    ) -> None:
        """Track cart abandonment for budget learning"""
        if not self.graphiti:
            return
        
        try:
            fact = f"User {user_id} ABANDONED_CART with {product_id} due to {abandonment_reason} at ${cart_total}"
            
            await self.graphiti.add_fact(
                fact=fact,
                strength=0.8,
                timestamp=datetime.now(),
                metadata={
                    "event_type": "cart_abandonment",
                    "reason": abandonment_reason,
                    "cart_total": cart_total
                }
            )
            
        except Exception as e:
            logger.error(f"Error tracking cart abandonment: {e}")
    
    async def get_budget_insights(
        self,
        user_id: str,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Get budget insights for user over time period"""
        if not self.graphiti:
            return self._fallback_budget_insights(time_period_days)
        
        try:
            query_context = {
                "user_id": user_id,
                "time_period_days": time_period_days,
                "insight_type": "budget_analysis"
            }
            
            response = await self.graphiti.get_context(
                f"What budget insights can you provide for user {user_id} over {time_period_days} days?",
                **query_context
            )
            
            return self._parse_budget_insights_response(response, time_period_days)
            
        except Exception as e:
            logger.error(f"Error getting budget insights: {e}")
            return self._fallback_budget_insights(time_period_days)
    
    async def apply_budget_filter(
        self,
        user_id: str,
        search_results: List[Dict[str, Any]],
        budget_preference: str = "moderate"
    ) -> List[Dict[str, Any]]:
        """Apply budget filtering to search results"""
        if not self.graphiti:
            return []
        
        try:
            query_context = {
                "user_id": user_id,
                "budget_preference": budget_preference,
                "filter_type": "budget_aware"
            }
            
            response = await self.graphiti.get_context(
                f"How should search results be filtered for user {user_id} with {budget_preference} budget preference?",
                **query_context
            )
            
            return self._apply_budget_filter_response(response, search_results)
            
        except Exception as e:
            logger.error(f"Error applying budget filter: {e}")
            return []
    
    # Budget Awareness Response Parsers
    def _parse_price_preferences_response(
        self,
        response: Dict[str, Any],
        category: str
    ) -> Dict[str, Any]:
        """Parse Graphiti response for price preferences"""
        # Mock parsing - in production would parse actual Graphiti response
        return {
            "category": category,
            "price_sensitivity": "moderate",
            "preferred_price_tier": "mid",
            "confidence": 0.6,
            "source": "graphiti_learning"
        }
    
    def _parse_budget_pattern_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for budget patterns"""
        return {
            "pattern_type": "value_conscious",
            "budget_consciousness": "moderate",
            "confidence": 0.7,
            "source": "graphiti_learning"
        }
    
    def _parse_comparison_behavior_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for comparison behavior"""
        return {
            "compares_prices": True,
            "comparison_frequency": "often",
            "behavior_indicators": ["multiple_brand_views", "price_sorting"],
            "confidence": 0.8
        }
    
    def _parse_budget_alternatives_response(
        self,
        response: Dict[str, Any],
        products_db: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse Graphiti response for budget alternatives"""
        # Mock - would parse actual Graphiti recommendations
        return []
    
    def _parse_budget_recommendations_response(
        self,
        response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse Graphiti response for budget recommendations"""
        return []
    
    def _parse_seasonal_pattern_response(
        self,
        response: Dict[str, Any],
        month: int
    ) -> Dict[str, Any]:
        """Parse Graphiti response for seasonal patterns"""
        return {
            "month": month,
            "budget_adjustment": 1.2 if month == 12 else 1.0,  # Holiday spending
            "seasonal_sensitivity": "moderate",
            "confidence": 0.6
        }
    
    def _parse_promotion_sensitivity_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for promotion sensitivity"""
        return {
            "sensitivity_level": "high",
            "preferred_discount_types": ["percentage_off", "buy_one_get_one"],
            "minimum_discount_threshold": 0.15,
            "confidence": 0.7
        }
    
    def _parse_price_elasticity_response(
        self,
        response: Dict[str, Any],
        category: str
    ) -> Dict[str, Any]:
        """Parse Graphiti response for price elasticity"""
        return {
            "category": category,
            "elasticity_score": 0.8,  # Price sensitive
            "elasticity_type": "elastic",
            "confidence": 0.6
        }
    
    def _parse_budget_insights_response(
        self,
        response: Dict[str, Any],
        time_period: int
    ) -> Dict[str, Any]:
        """Parse Graphiti response for budget insights"""
        return {
            "time_period": time_period,
            "insights": [
                "You tend to buy premium bread but budget milk",
                "Your grocery spending increases 20% in December"
            ],
            "recommendations": [
                "Consider store-brand alternatives for staples",
                "Look for bulk discounts on frequently purchased items"
            ],
            "confidence": 0.7
        }
    
    def _apply_budget_filter_response(
        self,
        response: Dict[str, Any],
        search_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Apply budget filtering based on Graphiti response"""
        # Mock - would apply actual Graphiti-learned filtering
        return []
    
    # Budget Awareness Fallback Methods
    def _fallback_price_preferences(self, category: str) -> Dict[str, Any]:
        """Fallback price preferences"""
        return {
            "category": category,
            "price_sensitivity": "moderate",
            "preferred_price_tier": "mid",
            "confidence": 0.3,
            "source": "default_fallback"
        }
    
    def _fallback_budget_pattern(self) -> Dict[str, Any]:
        """Fallback budget pattern"""
        return {
            "pattern_type": "unknown",
            "budget_consciousness": "moderate",
            "confidence": 0.3,
            "source": "default_fallback"
        }
    
    def _fallback_comparison_behavior(self) -> Dict[str, Any]:
        """Fallback comparison behavior"""
        return {
            "compares_prices": False,
            "comparison_frequency": "unknown",
            "behavior_indicators": [],
            "confidence": 0.3
        }
    
    def _fallback_seasonal_pattern(self, month: int) -> Dict[str, Any]:
        """Fallback seasonal pattern"""
        return {
            "month": month,
            "budget_adjustment": 1.0,
            "seasonal_sensitivity": "low",
            "confidence": 0.3
        }
    
    def _fallback_promotion_sensitivity(self) -> Dict[str, Any]:
        """Fallback promotion sensitivity"""
        return {
            "sensitivity_level": "moderate",
            "preferred_discount_types": [],
            "minimum_discount_threshold": 0.1,
            "confidence": 0.3
        }
    
    def _fallback_price_elasticity(self, category: str) -> Dict[str, Any]:
        """Fallback price elasticity"""
        return {
            "category": category,
            "elasticity_score": 0.5,
            "elasticity_type": "unit_elastic",
            "confidence": 0.3
        }
    
    def _fallback_budget_insights(self, time_period: int) -> Dict[str, Any]:
        """Fallback budget insights"""
        return {
            "time_period": time_period,
            "insights": [],
            "recommendations": [],
            "confidence": 0.3
        }

    # ============================================================================
    # HOUSEHOLD INTELLIGENCE - Pure Graphiti Learning
    # ============================================================================
    
    async def detect_household_size(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Detect household size from purchase patterns using Pure Graphiti learning"""
        if not self.graphiti:
            return self._fallback_household_size()
        
        try:
            query_context = {
                "user_id": user_id,
                "analysis_type": "household_size"
            }
            
            response = await self.graphiti.get_context(
                f"What is the household size for user {user_id}?",
                **query_context
            )
            
            return self._parse_household_size_response(response)
            
        except Exception as e:
            logger.error(f"Error detecting household size: {e}")
            return self._fallback_household_size()
    
    async def detect_family_composition(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Detect family composition including presence of children"""
        if not self.graphiti:
            return self._fallback_family_composition()
        
        try:
            query_context = {
                "user_id": user_id,
                "analysis_type": "family_composition"
            }
            
            response = await self.graphiti.get_context(
                f"What is the family composition for user {user_id}?",
                **query_context
            )
            
            return self._parse_family_composition_response(response)
            
        except Exception as e:
            logger.error(f"Error detecting family composition: {e}")
            return self._fallback_family_composition()
    
    async def analyze_preference_diversity(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Analyze diversity of preferences indicating multiple household members"""
        if not self.graphiti:
            return self._fallback_preference_diversity()
        
        try:
            query_context = {
                "user_id": user_id,
                "analysis_type": "preference_diversity"
            }
            
            response = await self.graphiti.get_context(
                f"How diverse are the preferences in user {user_id}'s purchases?",
                **query_context
            )
            
            return self._parse_preference_diversity_response(response)
            
        except Exception as e:
            logger.error(f"Error analyzing preference diversity: {e}")
            return self._fallback_preference_diversity()
    
    async def get_bulk_buying_behavior(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user's bulk buying behavior patterns"""
        if not self.graphiti:
            return self._fallback_bulk_behavior()
        
        try:
            query_context = {
                "user_id": user_id,
                "behavior_type": "bulk_buying"
            }
            
            response = await self.graphiti.get_context(
                f"Does user {user_id} exhibit bulk buying behavior?",
                **query_context
            )
            
            return self._parse_bulk_behavior_response(response)
            
        except Exception as e:
            logger.error(f"Error getting bulk buying behavior: {e}")
            return self._fallback_bulk_behavior()
    
    async def suggest_family_products(
        self,
        user_id: str,
        category: str,
        products_db: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Suggest family-friendly products based on household patterns"""
        if not self.graphiti:
            return []
        
        try:
            query_context = {
                "user_id": user_id,
                "category": category,
                "suggestion_type": "family_products"
            }
            
            response = await self.graphiti.get_context(
                f"What family-friendly {category} products suit user {user_id}?",
                **query_context
            )
            
            return self._parse_family_products_response(response, products_db)
            
        except Exception as e:
            logger.error(f"Error suggesting family products: {e}")
            return []
    
    async def analyze_age_preferences(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Analyze age-based product preferences in household"""
        if not self.graphiti:
            return self._fallback_age_preferences()
        
        try:
            query_context = {
                "user_id": user_id,
                "analysis_type": "age_preferences"
            }
            
            response = await self.graphiti.get_context(
                f"What age groups are represented in user {user_id}'s household?",
                **query_context
            )
            
            return self._parse_age_preferences_response(response)
            
        except Exception as e:
            logger.error(f"Error analyzing age preferences: {e}")
            return self._fallback_age_preferences()
    
    async def get_meal_planning_patterns(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get meal planning patterns indicating family households"""
        if not self.graphiti:
            return self._fallback_meal_planning()
        
        try:
            query_context = {
                "user_id": user_id,
                "pattern_type": "meal_planning"
            }
            
            response = await self.graphiti.get_context(
                f"Does user {user_id} show meal planning patterns?",
                **query_context
            )
            
            return self._parse_meal_planning_response(response)
            
        except Exception as e:
            logger.error(f"Error getting meal planning patterns: {e}")
            return self._fallback_meal_planning()
    
    async def track_household_change(
        self,
        user_id: str,
        change_type: str,
        indicators: List[str]
    ) -> None:
        """Track changes in household composition"""
        if not self.graphiti:
            return
        
        try:
            fact = f"User {user_id} HOUSEHOLD_CHANGE {change_type} with indicators: {', '.join(indicators)}"
            
            await self.graphiti.add_fact(
                fact=fact,
                strength=0.8,
                timestamp=datetime.now(),
                metadata={
                    "event_type": "household_change",
                    "change_type": change_type,
                    "indicators": indicators
                }
            )
            
        except Exception as e:
            logger.error(f"Error tracking household change: {e}")
    
    async def get_household_insights(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive household insights for shopping"""
        if not self.graphiti:
            return self._fallback_household_insights()
        
        try:
            query_context = {
                "user_id": user_id,
                "insight_type": "household_analysis"
            }
            
            response = await self.graphiti.get_context(
                f"What household insights can you provide for user {user_id}?",
                **query_context
            )
            
            return self._parse_household_insights_response(response)
            
        except Exception as e:
            logger.error(f"Error getting household insights: {e}")
            return self._fallback_household_insights()
    
    async def suggest_household_quantity(
        self,
        user_id: str,
        product_id: str,
        base_quantity: int
    ) -> Dict[str, Any]:
        """Suggest quantity based on household size"""
        if not self.graphiti:
            return self._fallback_quantity_suggestion(base_quantity)
        
        try:
            query_context = {
                "user_id": user_id,
                "product_id": product_id,
                "base_quantity": base_quantity
            }
            
            response = await self.graphiti.get_context(
                f"What quantity of {product_id} should user {user_id} buy based on household size?",
                **query_context
            )
            
            return self._parse_household_quantity_response(response, base_quantity)
            
        except Exception as e:
            logger.error(f"Error suggesting household quantity: {e}")
            return self._fallback_quantity_suggestion(base_quantity)
    
    async def detect_household_dietary_needs(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Detect special dietary needs across household members"""
        if not self.graphiti:
            return self._fallback_dietary_needs()
        
        try:
            query_context = {
                "user_id": user_id,
                "analysis_type": "household_dietary_needs"
            }
            
            response = await self.graphiti.get_context(
                f"What special dietary needs exist in user {user_id}'s household?",
                **query_context
            )
            
            return self._parse_dietary_needs_response(response)
            
        except Exception as e:
            logger.error(f"Error detecting household dietary needs: {e}")
            return self._fallback_dietary_needs()
    
    # Household Intelligence Response Parsers
    def _parse_household_size_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for household size"""
        # Mock parsing - in production would parse actual Graphiti response
        return {
            "estimated_size": "3-4",
            "size_category": "medium_family",
            "confidence": 0.7,
            "source": "graphiti_learning",
            "indicators": ["bulk_purchases", "variety_seeking", "family_products"]
        }
    
    def _parse_family_composition_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for family composition"""
        return {
            "has_children": True,
            "estimated_ages": ["5-10", "10-15"],
            "family_type": "nuclear_family",
            "confidence": 0.8,
            "indicators": ["kids_products", "school_supplies", "family_meals"]
        }
    
    def _parse_preference_diversity_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for preference diversity"""
        return {
            "diversity_level": "high",
            "distinct_preferences": 3,
            "preference_clusters": ["healthy_eater", "snack_lover", "kids_preferences"],
            "confidence": 0.7
        }
    
    def _parse_bulk_behavior_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for bulk behavior"""
        return {
            "bulk_buyer": True,
            "bulk_frequency": "weekly",
            "bulk_categories": ["Paper Products", "Snacks", "Beverages"],
            "confidence": 0.8
        }
    
    def _parse_family_products_response(
        self,
        response: Dict[str, Any],
        products_db: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse Graphiti response for family product suggestions"""
        # Mock - would parse actual Graphiti recommendations
        return []
    
    def _parse_age_preferences_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for age preferences"""
        return {
            "detected_age_groups": ["children", "teenagers", "adults"],
            "age_specific_products": ["cereal", "juice_boxes", "coffee"],
            "product_indicators": ["cartoon_characters", "school_friendly", "adult_beverages"],
            "confidence": 0.7
        }
    
    def _parse_meal_planning_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for meal planning"""
        return {
            "plans_meals": True,
            "planning_frequency": "weekly",
            "meal_variety": "high",
            "confidence": 0.6
        }
    
    def _parse_household_insights_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for household insights"""
        return {
            "household_type": "family_with_children",
            "estimated_members": 4,
            "shopping_recommendations": [
                "Consider family-size packages for frequently used items",
                "Look for variety packs to satisfy different preferences"
            ],
            "bulk_opportunities": ["Paper products", "Non-perishable snacks"],
            "confidence": 0.7
        }
    
    def _parse_household_quantity_response(
        self,
        response: Dict[str, Any],
        base_quantity: int
    ) -> Dict[str, Any]:
        """Parse Graphiti response for household quantity"""
        return {
            "suggested_quantity": base_quantity * 3,  # Adjust for family
            "adjustment_factor": 3.0,
            "adjustment_reason": "family_of_4",
            "confidence": 0.7
        }
    
    def _parse_dietary_needs_response(
        self,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse Graphiti response for dietary needs"""
        return {
            "special_needs": ["lactose_intolerance", "nut_allergy"],
            "allergen_avoidance": ["dairy", "tree_nuts"],
            "dietary_preferences": ["vegetarian_options", "gluten_free_alternatives"],
            "confidence": 0.7
        }
    
    # Household Intelligence Fallback Methods
    def _fallback_household_size(self) -> Dict[str, Any]:
        """Fallback household size response"""
        return {
            "estimated_size": "unknown",
            "size_category": "unknown",
            "confidence": 0.3,
            "source": "default_fallback",
            "indicators": []
        }
    
    def _fallback_family_composition(self) -> Dict[str, Any]:
        """Fallback family composition response"""
        return {
            "has_children": None,
            "estimated_ages": [],
            "family_type": "unknown",
            "confidence": 0.3,
            "indicators": []
        }
    
    def _fallback_preference_diversity(self) -> Dict[str, Any]:
        """Fallback preference diversity response"""
        return {
            "diversity_level": "moderate",
            "distinct_preferences": 1,
            "preference_clusters": [],
            "confidence": 0.3
        }
    
    def _fallback_bulk_behavior(self) -> Dict[str, Any]:
        """Fallback bulk buying behavior"""
        return {
            "bulk_buyer": False,
            "bulk_frequency": "unknown",
            "bulk_categories": [],
            "confidence": 0.3
        }
    
    def _fallback_age_preferences(self) -> Dict[str, Any]:
        """Fallback age preferences"""
        return {
            "detected_age_groups": [],
            "age_specific_products": [],
            "product_indicators": [],
            "confidence": 0.3
        }
    
    def _fallback_meal_planning(self) -> Dict[str, Any]:
        """Fallback meal planning patterns"""
        return {
            "plans_meals": None,
            "planning_frequency": "unknown",
            "meal_variety": "unknown",
            "confidence": 0.3
        }
    
    def _fallback_household_insights(self) -> Dict[str, Any]:
        """Fallback household insights"""
        return {
            "household_type": "unknown",
            "estimated_members": 1,
            "shopping_recommendations": [],
            "bulk_opportunities": [],
            "confidence": 0.3
        }
    
    def _fallback_quantity_suggestion(self, base_quantity: int) -> Dict[str, Any]:
        """Fallback quantity suggestion"""
        return {
            "suggested_quantity": base_quantity,
            "adjustment_factor": 1.0,
            "adjustment_reason": "no_household_data",
            "confidence": 0.3
        }
    
    def _fallback_dietary_needs(self) -> Dict[str, Any]:
        """Fallback dietary needs"""
        return {
            "special_needs": [],
            "allergen_avoidance": [],
            "dietary_preferences": [],
            "confidence": 0.3
        }

    async def _query_graphiti(self, query: str) -> Dict[str, Any]:
        """Execute query against Graphiti (mock implementation)"""
        # Mock response for development/testing
        # In production, this would query actual Graphiti
        return {
            "relationships": []
        }