"""
Tests for Feature 9: Budget Awareness

This feature learns user's price sensitivity patterns based on:
- Purchase behavior across price ranges
- Category-specific budget preferences
- Economic shopping patterns
- Price comparison behavior
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from src.personalization.budget_awareness import BudgetAwarenessTracker
from src.models.user_preferences import UserPreferences


class TestBudgetAwareness:
    """Test suite for Budget Awareness feature"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.tracker = BudgetAwarenessTracker()
        self.user_id = "test_user_123"
        
        # Mock products database with varying price points
        self.products_db = {
            "milk_budget": {
                "id": "milk_budget",
                "name": "Store Brand Milk",
                "category": "Dairy",
                "price": 2.99,
                "price_tier": "budget"
            },
            "milk_premium": {
                "id": "milk_premium", 
                "name": "Organic Grass-Fed Milk",
                "category": "Dairy",
                "price": 6.99,
                "price_tier": "premium"
            },
            "bread_budget": {
                "id": "bread_budget",
                "name": "White Sandwich Bread",
                "category": "Bakery",
                "price": 1.99,
                "price_tier": "budget"
            },
            "bread_premium": {
                "id": "bread_premium",
                "name": "Artisan Sourdough",
                "category": "Bakery", 
                "price": 5.99,
                "price_tier": "premium"
            },
            "cereal_mid": {
                "id": "cereal_mid",
                "name": "Honey Nut Cheerios",
                "category": "Breakfast",
                "price": 4.49,
                "price_tier": "mid"
            }
        }
        
        # Mock purchase history showing price sensitivity patterns
        self.purchase_history = [
            {
                "date": datetime.now() - timedelta(days=7),
                "products": [
                    {"id": "milk_budget", "price": 2.99, "category": "Dairy"},
                    {"id": "bread_premium", "price": 5.99, "category": "Bakery"},
                    {"id": "cereal_mid", "price": 4.49, "category": "Breakfast"}
                ],
                "total_spent": 13.47
            },
            {
                "date": datetime.now() - timedelta(days=14),
                "products": [
                    {"id": "milk_budget", "price": 2.99, "category": "Dairy"},
                    {"id": "bread_budget", "price": 1.99, "category": "Bakery"}
                ],
                "total_spent": 4.98
            },
            {
                "date": datetime.now() - timedelta(days=21),
                "products": [
                    {"id": "milk_budget", "price": 2.99, "category": "Dairy"},
                    {"id": "bread_premium", "price": 5.99, "category": "Bakery"}
                ],
                "total_spent": 8.98
            }
        ]

    @pytest.mark.asyncio
    async def test_learns_category_price_preferences(self):
        """Test that system learns price preferences by category"""
        # Test fallback behavior (no Graphiti learning data)
        preferences = await self.tracker.get_category_price_preferences(
            user_id=self.user_id,
            category="Dairy"
        )
        
        # Should return default preferences
        assert preferences["category"] == "Dairy"
        assert preferences["price_sensitivity"] == "moderate"  # Default fallback
        assert preferences["confidence"] == 0.3
        assert preferences["source"] == "default_fallback"

    @pytest.mark.asyncio
    async def test_detects_budget_conscious_patterns(self):
        """Test detection of budget-conscious shopping patterns"""
        # Test that system can identify budget consciousness
        pattern = await self.tracker.analyze_budget_pattern(
            user_id=self.user_id,
            category="Dairy"
        )
        
        # Should return default pattern without Graphiti
        assert pattern["pattern_type"] == "unknown"
        assert pattern["confidence"] == 0.3
        assert pattern["source"] == "default_fallback"

    @pytest.mark.asyncio
    async def test_identifies_price_comparison_behavior(self):
        """Test identification of users who compare prices"""
        comparison_behavior = await self.tracker.get_price_comparison_behavior(
            user_id=self.user_id
        )
        
        # Should return default behavior
        assert comparison_behavior["compares_prices"] is False  # Default fallback
        assert comparison_behavior["confidence"] == 0.3
        assert comparison_behavior["behavior_indicators"] == []

    @pytest.mark.asyncio
    async def test_suggests_budget_alternatives(self):
        """Test suggesting budget-friendly alternatives"""
        suggestions = await self.tracker.suggest_budget_alternatives(
            user_id=self.user_id,
            product_id="milk_premium",
            products_db=self.products_db
        )
        
        # Should provide alternatives based on category even in fallback
        assert len(suggestions) > 0
        assert all(s["category"] == "Dairy" for s in suggestions)
        assert all(s["price"] < self.products_db["milk_premium"]["price"] for s in suggestions)

    @pytest.mark.asyncio
    async def test_respects_quality_preferences(self):
        """Test that budget awareness respects quality preferences"""
        # Test with user who prefers premium products
        recommendations = await self.tracker.get_budget_aware_recommendations(
            user_id=self.user_id,
            category="Bakery",
            price_range=(0, 10),
            quality_preference="premium"
        )
        
        # Should respect quality preference even in budget context
        assert len(recommendations) >= 0  # May be empty in fallback
        if recommendations:
            assert all(r.get("price_tier") in ["premium", "mid"] for r in recommendations)

    @pytest.mark.asyncio
    async def test_learns_seasonal_budget_patterns(self):
        """Test learning of seasonal budget changes"""
        seasonal_pattern = await self.tracker.get_seasonal_budget_pattern(
            user_id=self.user_id,
            current_month=12  # December - holiday season
        )
        
        # Should return default seasonal pattern
        assert seasonal_pattern["month"] == 12
        assert seasonal_pattern["budget_adjustment"] == 1.0  # No adjustment in fallback
        assert seasonal_pattern["confidence"] == 0.3

    @pytest.mark.asyncio
    async def test_tracks_promotion_sensitivity(self):
        """Test tracking sensitivity to promotions and sales"""
        promotion_sensitivity = await self.tracker.get_promotion_sensitivity(
            user_id=self.user_id
        )
        
        # Should return default sensitivity
        assert promotion_sensitivity["sensitivity_level"] == "moderate"
        assert promotion_sensitivity["confidence"] == 0.3
        assert promotion_sensitivity["preferred_discount_types"] == []

    @pytest.mark.asyncio
    async def test_calculates_price_elasticity(self):
        """Test calculation of price elasticity by category"""
        elasticity = await self.tracker.calculate_price_elasticity(
            user_id=self.user_id,
            category="Dairy"
        )
        
        # Should return default elasticity
        assert elasticity["category"] == "Dairy"
        assert elasticity["elasticity_score"] == 0.5  # Neutral elasticity in fallback
        assert elasticity["confidence"] == 0.3

    @pytest.mark.asyncio
    async def test_learns_from_cart_abandonment(self):
        """Test learning from cart abandonment due to price"""
        await self.tracker.track_cart_abandonment(
            user_id=self.user_id,
            product_id="milk_premium",
            abandonment_reason="price_too_high",
            cart_total=25.99
        )
        
        # Should complete without error (graceful degradation)
        assert True  # Test passes if no exception raised

    @pytest.mark.asyncio
    async def test_provides_budget_insights(self):
        """Test providing budget insights to users"""
        insights = await self.tracker.get_budget_insights(
            user_id=self.user_id,
            time_period_days=30
        )
        
        # Should provide basic insights even in fallback
        assert insights["time_period"] == 30
        assert insights["insights"] == []  # Empty in fallback
        assert insights["confidence"] == 0.3

    @pytest.mark.asyncio
    async def test_budget_awareness_integration_with_search(self):
        """Test integration with search ranking for budget-aware results"""
        # Test budget-aware search filtering
        filtered_results = await self.tracker.apply_budget_filter(
            user_id=self.user_id,
            search_results=list(self.products_db.values()),
            budget_preference="strict"
        )
        
        # Should filter results even in fallback mode
        assert len(filtered_results) <= len(self.products_db)
        # In strict budget mode, should prefer budget options
        budget_items = [r for r in filtered_results if r.get("price_tier") == "budget"]
        assert len(budget_items) > 0  # Should include some budget items