"""
Feature 9: Budget Awareness

Learns and applies user's price sensitivity patterns using Pure Graphiti Learning.
Delegates all learning to GraphitiPersonalizationEngine following Pure Graphiti approach.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from src.models.user_preferences import UserPreferences
from src.personalization.graphiti_personalization_engine import GraphitiPersonalizationEngine

logger = logging.getLogger(__name__)


class BudgetAwarenessTracker:
    """
    Tracks and applies budget awareness using Pure Graphiti Learning.
    
    Features:
    - Learn category-specific price preferences
    - Detect budget-conscious patterns
    - Track price comparison behavior
    - Suggest budget alternatives
    - Respect quality preferences
    - Learn seasonal budget patterns
    - Track promotion sensitivity
    - Calculate price elasticity
    """
    
    def __init__(self):
        """Initialize with GraphitiPersonalizationEngine"""
        self.engine = GraphitiPersonalizationEngine()
        
    async def get_category_price_preferences(
        self,
        user_id: str,
        category: str
    ) -> Dict[str, Any]:
        """
        Get user's price preferences for a specific category using Pure Graphiti learning.
        
        Args:
            user_id: User identifier
            category: Product category
            
        Returns:
            Dict with price preferences, sensitivity, and confidence
        """
        try:
            # Use GraphitiPersonalizationEngine for price preference learning
            result = await self.engine.get_category_price_preferences(
                user_id=user_id,
                category=category
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting category price preferences: {e}")
            return self._fallback_price_preferences(category)
    
    async def analyze_budget_pattern(
        self,
        user_id: str,
        category: str
    ) -> Dict[str, Any]:
        """
        Analyze user's budget patterns for a category.
        
        Args:
            user_id: User identifier
            category: Product category
            
        Returns:
            Dict with budget pattern analysis
        """
        try:
            return await self.engine.analyze_budget_pattern(
                user_id=user_id,
                category=category
            )
            
        except Exception as e:
            logger.error(f"Error analyzing budget pattern: {e}")
            return self._fallback_budget_pattern()
    
    async def get_price_comparison_behavior(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get user's price comparison behavior patterns.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with price comparison behavior analysis
        """
        try:
            return await self.engine.get_price_comparison_behavior(
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(f"Error getting price comparison behavior: {e}")
            return self._fallback_comparison_behavior()
    
    async def suggest_budget_alternatives(
        self,
        user_id: str,
        product_id: str,
        products_db: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Suggest budget-friendly alternatives to a product.
        
        Args:
            user_id: User identifier
            product_id: Original product identifier
            products_db: Available products database
            
        Returns:
            List of budget alternative products
        """
        try:
            # Get original product
            original_product = products_db.get(product_id)
            if not original_product:
                return []
            
            # Use GraphitiPersonalizationEngine for smart alternatives
            alternatives = await self.engine.suggest_budget_alternatives(
                user_id=user_id,
                product_id=product_id,
                products_db=products_db
            )
            
            # Fallback: Find alternatives in same category with lower price
            if not alternatives:
                alternatives = self._basic_budget_alternatives(original_product, products_db)
            
            return alternatives
            
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
        """
        Get budget-aware recommendations respecting quality preferences.
        
        Args:
            user_id: User identifier
            category: Product category
            price_range: (min_price, max_price) tuple
            quality_preference: Quality preference level
            
        Returns:
            List of budget-aware recommendations
        """
        try:
            return await self.engine.get_budget_aware_recommendations(
                user_id=user_id,
                category=category,
                price_range=price_range,
                quality_preference=quality_preference
            )
            
        except Exception as e:
            logger.error(f"Error getting budget-aware recommendations: {e}")
            return []
    
    async def get_seasonal_budget_pattern(
        self,
        user_id: str,
        current_month: int
    ) -> Dict[str, Any]:
        """
        Get seasonal budget adjustment patterns.
        
        Args:
            user_id: User identifier
            current_month: Current month (1-12)
            
        Returns:
            Dict with seasonal budget pattern
        """
        try:
            return await self.engine.get_seasonal_budget_pattern(
                user_id=user_id,
                current_month=current_month
            )
            
        except Exception as e:
            logger.error(f"Error getting seasonal budget pattern: {e}")
            return self._fallback_seasonal_pattern(current_month)
    
    async def get_promotion_sensitivity(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get user's sensitivity to promotions and sales.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict with promotion sensitivity analysis
        """
        try:
            return await self.engine.get_promotion_sensitivity(
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(f"Error getting promotion sensitivity: {e}")
            return self._fallback_promotion_sensitivity()
    
    async def calculate_price_elasticity(
        self,
        user_id: str,
        category: str
    ) -> Dict[str, Any]:
        """
        Calculate price elasticity for user in specific category.
        
        Args:
            user_id: User identifier
            category: Product category
            
        Returns:
            Dict with price elasticity analysis
        """
        try:
            return await self.engine.calculate_price_elasticity(
                user_id=user_id,
                category=category
            )
            
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
        """
        Track cart abandonment for budget learning.
        
        Args:
            user_id: User identifier
            product_id: Product that caused abandonment
            abandonment_reason: Reason for abandonment
            cart_total: Total cart value when abandoned
        """
        try:
            await self.engine.track_cart_abandonment(
                user_id=user_id,
                product_id=product_id,
                abandonment_reason=abandonment_reason,
                cart_total=cart_total
            )
            
        except Exception as e:
            logger.error(f"Error tracking cart abandonment: {e}")
    
    async def get_budget_insights(
        self,
        user_id: str,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get budget insights for user over time period.
        
        Args:
            user_id: User identifier
            time_period_days: Analysis time period in days
            
        Returns:
            Dict with budget insights and recommendations
        """
        try:
            return await self.engine.get_budget_insights(
                user_id=user_id,
                time_period_days=time_period_days
            )
            
        except Exception as e:
            logger.error(f"Error getting budget insights: {e}")
            return self._fallback_budget_insights(time_period_days)
    
    async def apply_budget_filter(
        self,
        user_id: str,
        search_results: List[Dict[str, Any]],
        budget_preference: str = "moderate"
    ) -> List[Dict[str, Any]]:
        """
        Apply budget filtering to search results.
        
        Args:
            user_id: User identifier
            search_results: List of search results to filter
            budget_preference: Budget preference level
            
        Returns:
            Filtered search results based on budget awareness
        """
        try:
            # Use GraphitiPersonalizationEngine for smart filtering
            filtered = await self.engine.apply_budget_filter(
                user_id=user_id,
                search_results=search_results,
                budget_preference=budget_preference
            )
            
            # Fallback: Basic price-based filtering
            if not filtered:
                filtered = self._basic_budget_filter(search_results, budget_preference)
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error applying budget filter: {e}")
            return search_results  # Return unfiltered on error
    
    def _basic_budget_alternatives(
        self,
        original_product: Dict[str, Any],
        products_db: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Basic budget alternatives fallback"""
        category = original_product.get("category")
        original_price = original_product.get("price", 0)
        
        alternatives = []
        for product in products_db.values():
            if (product.get("category") == category and 
                product.get("price", 0) < original_price and
                product["id"] != original_product["id"]):
                alternatives.append(product)
        
        # Sort by price (cheapest first)
        alternatives.sort(key=lambda x: x.get("price", 0))
        return alternatives[:3]  # Return top 3 alternatives
    
    def _basic_budget_filter(
        self,
        search_results: List[Dict[str, Any]],
        budget_preference: str
    ) -> List[Dict[str, Any]]:
        """Basic budget filtering fallback"""
        if budget_preference == "strict":
            # Only budget tier items
            return [r for r in search_results if r.get("price_tier") == "budget"]
        elif budget_preference == "moderate":
            # Budget and mid-tier items
            return [r for r in search_results if r.get("price_tier") in ["budget", "mid"]]
        else:
            # All items (no filtering)
            return search_results
    
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
            "budget_adjustment": 1.0,  # No adjustment
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
            "elasticity_score": 0.5,  # Neutral elasticity
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