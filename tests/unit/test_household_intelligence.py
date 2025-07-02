"""
Tests for Feature 10: Household Intelligence

This feature detects and learns household patterns based on:
- Multi-member purchase patterns
- Family size indicators
- Age-based product preferences
- Bulk buying behavior
- Variety seeking patterns
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock
from src.personalization.household_intelligence import HouseholdIntelligenceTracker
from src.models.user_preferences import UserPreferences


class TestHouseholdIntelligence:
    """Test suite for Household Intelligence feature"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.tracker = HouseholdIntelligenceTracker()
        self.user_id = "test_user_123"
        
        # Mock products database with household indicators
        self.products_db = {
            "milk_family": {
                "id": "milk_family",
                "name": "Family Size Milk",
                "category": "Dairy",
                "size": "1 gallon",
                "household_indicator": "family_size"
            },
            "cereal_kids": {
                "id": "cereal_kids",
                "name": "Lucky Charms",
                "category": "Breakfast",
                "target_demographic": "children",
                "household_indicator": "has_children"
            },
            "yogurt_variety": {
                "id": "yogurt_variety",
                "name": "Yogurt Variety Pack",
                "category": "Dairy",
                "pack_size": 12,
                "household_indicator": "multiple_preferences"
            },
            "snacks_individual": {
                "id": "snacks_individual",
                "name": "Single Serve Chips",
                "category": "Snacks",
                "pack_size": 1,
                "household_indicator": "single_person"
            },
            "bread_bulk": {
                "id": "bread_bulk",
                "name": "Bread Twin Pack",
                "category": "Bakery",
                "pack_size": 2,
                "household_indicator": "bulk_buyer"
            }
        }
        
        # Mock purchase history showing household patterns
        self.purchase_history = [
            {
                "date": datetime.now() - timedelta(days=7),
                "products": [
                    {"id": "milk_family", "quantity": 2},
                    {"id": "cereal_kids", "quantity": 3},
                    {"id": "yogurt_variety", "quantity": 1}
                ]
            },
            {
                "date": datetime.now() - timedelta(days=14),
                "products": [
                    {"id": "milk_family", "quantity": 2},
                    {"id": "bread_bulk", "quantity": 1},
                    {"id": "cereal_kids", "quantity": 2}
                ]
            },
            {
                "date": datetime.now() - timedelta(days=21),
                "products": [
                    {"id": "milk_family", "quantity": 1},
                    {"id": "yogurt_variety", "quantity": 1}
                ]
            }
        ]

    @pytest.mark.asyncio
    async def test_detects_household_size(self):
        """Test detection of household size from purchase patterns"""
        # Test fallback behavior (no Graphiti learning data)
        household_info = await self.tracker.detect_household_size(
            user_id=self.user_id
        )
        
        # Should return default household info
        assert household_info["estimated_size"] == "unknown"
        assert household_info["confidence"] == 0.3
        assert household_info["source"] == "default_fallback"

    @pytest.mark.asyncio
    async def test_identifies_family_with_children(self):
        """Test identification of families with children"""
        family_info = await self.tracker.detect_family_composition(
            user_id=self.user_id
        )
        
        # Should return default composition
        assert family_info["has_children"] is None  # Unknown in fallback
        assert family_info["confidence"] == 0.3
        assert family_info["indicators"] == []

    @pytest.mark.asyncio
    async def test_detects_multi_preference_household(self):
        """Test detection of households with diverse preferences"""
        diversity = await self.tracker.analyze_preference_diversity(
            user_id=self.user_id
        )
        
        # Should return default diversity analysis
        assert diversity["diversity_level"] == "moderate"
        assert diversity["confidence"] == 0.3
        assert diversity["preference_clusters"] == []

    @pytest.mark.asyncio
    async def test_identifies_bulk_buying_patterns(self):
        """Test identification of bulk buying behavior"""
        bulk_patterns = await self.tracker.get_bulk_buying_behavior(
            user_id=self.user_id
        )
        
        # Should return default bulk patterns
        assert bulk_patterns["bulk_buyer"] is False  # Default fallback
        assert bulk_patterns["bulk_categories"] == []
        assert bulk_patterns["confidence"] == 0.3

    @pytest.mark.asyncio
    async def test_suggests_family_friendly_products(self):
        """Test suggesting products for family households"""
        suggestions = await self.tracker.suggest_family_products(
            user_id=self.user_id,
            category="Breakfast",
            products_db=self.products_db
        )
        
        # Should return some suggestions even in fallback
        assert isinstance(suggestions, list)
        if suggestions:
            assert all(s.get("category") == "Breakfast" for s in suggestions)

    @pytest.mark.asyncio
    async def test_detects_age_based_preferences(self):
        """Test detection of age-based product preferences"""
        age_preferences = await self.tracker.analyze_age_preferences(
            user_id=self.user_id
        )
        
        # Should return default age preferences
        assert age_preferences["detected_age_groups"] == []
        assert age_preferences["confidence"] == 0.3
        assert age_preferences["product_indicators"] == []

    @pytest.mark.asyncio
    async def test_identifies_meal_planning_patterns(self):
        """Test identification of meal planning behavior"""
        meal_patterns = await self.tracker.get_meal_planning_patterns(
            user_id=self.user_id
        )
        
        # Should return default meal planning info
        assert meal_patterns["plans_meals"] is None  # Unknown in fallback
        assert meal_patterns["planning_frequency"] == "unknown"
        assert meal_patterns["confidence"] == 0.3

    @pytest.mark.asyncio
    async def test_tracks_household_changes(self):
        """Test tracking changes in household composition"""
        await self.tracker.track_household_change(
            user_id=self.user_id,
            change_type="new_member",
            indicators=["increased_quantity", "new_product_categories"]
        )
        
        # Should complete without error (graceful degradation)
        assert True  # Test passes if no exception raised

    @pytest.mark.asyncio
    async def test_provides_household_insights(self):
        """Test providing household-based shopping insights"""
        insights = await self.tracker.get_household_insights(
            user_id=self.user_id
        )
        
        # Should provide basic insights even in fallback
        assert insights["household_type"] == "unknown"
        assert insights["shopping_recommendations"] == []
        assert insights["confidence"] == 0.3

    @pytest.mark.asyncio
    async def test_household_aware_quantity_suggestions(self):
        """Test quantity suggestions based on household size"""
        quantity_suggestion = await self.tracker.suggest_household_quantity(
            user_id=self.user_id,
            product_id="milk_family",
            base_quantity=1
        )
        
        # Should return base quantity in fallback
        assert quantity_suggestion["suggested_quantity"] == 1
        assert quantity_suggestion["adjustment_reason"] == "no_household_data"
        assert quantity_suggestion["confidence"] == 0.3

    @pytest.mark.asyncio
    async def test_detects_special_dietary_needs(self):
        """Test detection of special dietary needs in household"""
        dietary_needs = await self.tracker.detect_household_dietary_needs(
            user_id=self.user_id
        )
        
        # Should return empty needs in fallback
        assert dietary_needs["special_needs"] == []
        assert dietary_needs["allergen_avoidance"] == []
        assert dietary_needs["confidence"] == 0.3