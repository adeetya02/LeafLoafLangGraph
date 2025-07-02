"""
Tests for Feature 7: Complementary Products

This feature suggests personalized product pairings based on:
- User's purchase history
- Common pairing patterns
- Dietary preferences
- Cultural context
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from src.personalization.complementary_products import ComplementaryProductSuggester
from src.models.user_preferences import UserPreferences, DietaryRestriction


class TestComplementaryProducts:
    """Test suite for Complementary Products feature"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.suggester = ComplementaryProductSuggester()
        self.user_id = "test_user_123"
        
        # Mock products database
        self.products_db = {
            "milk_001": {
                "id": "milk_001",
                "name": "Oatly Oat Milk",
                "category": "Dairy Alternatives",
                "attributes": ["vegan", "lactose-free"],
                "common_pairings": ["cereal", "coffee", "cookies"],
                "price": 4.99
            },
            "cereal_001": {
                "id": "cereal_001",
                "name": "Granola Cereal",
                "category": "Breakfast",
                "attributes": ["vegan", "whole-grain"],
                "common_pairings": ["milk", "yogurt", "fruit"],
                "price": 5.99
            },
            "pasta_001": {
                "id": "pasta_001",
                "name": "Penne Pasta",
                "category": "Pasta",
                "attributes": ["vegan"],
                "common_pairings": ["tomato_sauce", "parmesan", "olive_oil"],
                "price": 2.99
            },
            "sauce_001": {
                "id": "sauce_001",
                "name": "Marinara Sauce",
                "category": "Sauces",
                "attributes": ["vegan"],
                "common_pairings": ["pasta", "bread", "mozzarella"],
                "price": 3.99
            },
            "chips_001": {
                "id": "chips_001",
                "name": "Tortilla Chips",
                "category": "Snacks",
                "attributes": ["gluten-free", "vegan"],
                "common_pairings": ["salsa", "guacamole", "cheese_dip"],
                "price": 3.49
            },
            "salsa_001": {
                "id": "salsa_001",
                "name": "Medium Salsa",
                "category": "Condiments",
                "attributes": ["vegan", "gluten-free"],
                "common_pairings": ["chips", "tacos", "burritos"],
                "price": 4.49
            }
        }
        
        # Mock purchase history
        self.purchase_history = [
            {
                "order_id": "order_001",
                "date": datetime(2024, 1, 1),
                "products": ["milk_001", "cereal_001"]
            },
            {
                "order_id": "order_002",
                "date": datetime(2024, 1, 8),
                "products": ["pasta_001", "sauce_001"]
            },
            {
                "order_id": "order_003",
                "date": datetime(2024, 1, 15),
                "products": ["milk_001", "cereal_001"]  # Repeat purchase
            }
        ]
    
    @pytest.mark.asyncio
    async def test_suggest_complementary_for_single_product(self):
        """Test suggesting complementary products for a single item"""
        suggestions = await self.suggester.get_complementary_products(
            product_id="milk_001",
            products_db=self.products_db,
            max_suggestions=3
        )
        
        # Should suggest items that pair well with milk
        assert len(suggestions) <= 3
        assert all(s["id"] != "milk_001" for s in suggestions)  # Don't suggest the same product
        assert any(s["id"] == "cereal_001" for s in suggestions)  # Cereal pairs with milk
    
    @pytest.mark.asyncio
    async def test_personalized_complementary_suggestions(self):
        """Test personalized suggestions based on purchase history"""
        suggestions = await self.suggester.get_personalized_complements(
            product_id="milk_001",
            user_id=self.user_id,
            products_db=self.products_db,
            purchase_history=self.purchase_history
        )
        
        # Should prioritize cereal since user frequently buys milk + cereal together
        assert suggestions[0]["id"] == "cereal_001"
        assert suggestions[0]["reason"] == "frequently purchased together"
        assert suggestions[0]["confidence"] > 0.8
    
    @pytest.mark.asyncio
    async def test_cart_based_suggestions(self):
        """Test suggesting items based on current cart contents"""
        current_cart = ["chips_001"]
        
        suggestions = await self.suggester.suggest_for_cart(
            cart_items=current_cart,
            products_db=self.products_db,
            max_suggestions=5
        )
        
        # Should suggest salsa for chips
        assert any(s["id"] == "salsa_001" for s in suggestions)
        suggested_salsa = next(s for s in suggestions if s["id"] == "salsa_001")
        assert suggested_salsa["reason"] == "pairs well with Tortilla Chips"
    
    @pytest.mark.asyncio
    async def test_dietary_aware_suggestions(self):
        """Test that suggestions respect dietary restrictions"""
        preferences = UserPreferences(
            user_id=self.user_id,
            dietary_restrictions=[DietaryRestriction.VEGAN]
        )
        
        # Add non-vegan products to test filtering
        self.products_db["cheese_001"] = {
            "id": "cheese_001",
            "name": "Cheddar Cheese",
            "category": "Dairy",
            "attributes": ["vegetarian"],
            "common_pairings": ["chips", "bread", "wine"],
            "price": 5.99
        }
        
        suggestions = await self.suggester.get_dietary_aware_complements(
            product_id="chips_001",
            products_db=self.products_db,
            preferences=preferences
        )
        
        # Should not suggest cheese for vegan user
        assert not any(s["id"] == "cheese_001" for s in suggestions)
        # Should suggest vegan options
        assert all("vegan" in self.products_db[s["id"]]["attributes"] for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_frequency_based_pairing_detection(self):
        """Test learning pairings from purchase frequency"""
        # Analyze purchase patterns
        patterns = await self.suggester.analyze_pairing_patterns(
            user_id=self.user_id,
            purchase_history=self.purchase_history
        )
        
        # Should detect milk + cereal as frequent pairing (order doesn't matter due to sorting)
        milk_cereal_pair = ("cereal_001", "milk_001")  # Sorted alphabetically
        assert milk_cereal_pair in patterns["frequent_pairs"]
        assert patterns["frequent_pairs"][milk_cereal_pair] == 2  # Bought together twice
        
        # Should detect pasta + sauce pairing
        pasta_sauce_pair = ("pasta_001", "sauce_001")  # Already sorted
        assert pasta_sauce_pair in patterns["frequent_pairs"]
        assert patterns["frequent_pairs"][pasta_sauce_pair] == 1
    
    @pytest.mark.asyncio
    async def test_category_based_suggestions(self):
        """Test fallback to category-based suggestions"""
        # Product not in purchase history
        suggestions = await self.suggester.get_category_complements(
            product_id="pasta_001",
            products_db=self.products_db,
            category_rules={
                "Pasta": ["Sauces", "Cheese", "Vegetables"],
                "Snacks": ["Beverages", "Condiments"]
            }
        )
        
        # Should suggest sauce for pasta
        assert any(s["id"] == "sauce_001" for s in suggestions)
        assert all(s["confidence"] >= 0.5 for s in suggestions)  # Lower confidence for category-based
    
    @pytest.mark.asyncio
    async def test_multi_product_complement_intersection(self):
        """Test finding complements for multiple products"""
        cart_items = ["pasta_001", "chips_001"]
        
        suggestions = await self.suggester.suggest_for_multiple_items(
            product_ids=cart_items,
            products_db=self.products_db
        )
        
        # Should include both pasta and chips complements
        suggested_ids = [s["id"] for s in suggestions]
        assert "sauce_001" in suggested_ids  # For pasta
        assert "salsa_001" in suggested_ids  # For chips
        
        # Should not duplicate if same item complements both
        assert len(suggested_ids) == len(set(suggested_ids))
    
    @pytest.mark.asyncio
    async def test_seasonal_complement_adjustment(self):
        """Test seasonal adjustments to suggestions"""
        # Mock seasonal context
        seasonal_context = {
            "season": "summer",
            "temperature": "hot",
            "holidays": []
        }
        
        # Add seasonal products
        self.products_db["ice_cream_001"] = {
            "id": "ice_cream_001",
            "name": "Vanilla Ice Cream",
            "category": "Frozen",
            "attributes": ["vegetarian"],
            "seasonal_tags": ["summer", "hot_weather"],
            "common_pairings": ["cookies", "fruit", "cake"],
            "price": 6.99
        }
        
        suggestions = await self.suggester.get_seasonal_complements(
            product_id="cookies_001",
            products_db=self.products_db,
            seasonal_context=seasonal_context
        )
        
        # Should prioritize ice cream in summer
        if suggestions:
            summer_items = [s for s in suggestions 
                          if "summer" in self.products_db[s["id"]].get("seasonal_tags", [])]
            assert len(summer_items) > 0
    
    @pytest.mark.asyncio
    async def test_budget_aware_suggestions(self):
        """Test budget-conscious complement suggestions"""
        budget_preference = {
            "max_complement_price": 5.00,
            "prefer_value": True
        }
        
        suggestions = await self.suggester.get_budget_aware_complements(
            product_id="pasta_001",
            products_db=self.products_db,
            budget_preference=budget_preference
        )
        
        # All suggestions should be under budget
        assert all(self.products_db[s["id"]]["price"] <= 5.00 for s in suggestions)
        
        # Should prioritize value items
        if len(suggestions) > 1:
            # Check that cheaper items are ranked higher
            prices = [self.products_db[s["id"]]["price"] for s in suggestions]
            assert prices == sorted(prices)  # Should be in ascending price order
    
    @pytest.mark.asyncio
    async def test_performance_with_large_catalog(self):
        """Test performance with large product catalog"""
        # Create 1000 products
        large_catalog = {}
        for i in range(1000):
            large_catalog[f"prod_{i}"] = {
                "id": f"prod_{i}",
                "name": f"Product {i}",
                "category": f"Category {i % 10}",
                "attributes": ["test"],
                "common_pairings": [f"prod_{(i+1) % 1000}", f"prod_{(i+2) % 1000}"],
                "price": 5.99
            }
        
        import time
        start = time.time()
        
        suggestions = await self.suggester.get_complementary_products(
            product_id="prod_0",
            products_db=large_catalog,
            max_suggestions=5
        )
        
        duration = time.time() - start
        
        # Should complete within 100ms even with large catalog
        assert duration < 0.1
        # Should find at least 2 suggestions (prod_1, prod_2)
        assert len(suggestions) >= 2
        assert len(suggestions) <= 5
    
    @pytest.mark.asyncio
    async def test_explanation_generation(self):
        """Test generating explanations for suggestions"""
        suggestions = await self.suggester.get_explained_complements(
            product_id="milk_001",
            user_id=self.user_id,
            products_db=self.products_db,
            purchase_history=self.purchase_history
        )
        
        # Each suggestion should have an explanation
        assert all("explanation" in s for s in suggestions)
        assert all("confidence_reason" in s for s in suggestions)
        
        # Explanations should be meaningful
        cereal_suggestion = next((s for s in suggestions if s["id"] == "cereal_001"), None)
        if cereal_suggestion:
            assert "frequently bought" in cereal_suggestion["explanation"].lower()
            assert "together" in cereal_suggestion["explanation"].lower()
            assert cereal_suggestion["confidence_reason"] == "based on your purchase history"