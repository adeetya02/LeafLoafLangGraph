"""
Tests for Feature 6: Dietary & Cultural Intelligence

This feature automatically filters products based on:
- Dietary restrictions (vegan, gluten-free, kosher, halal)
- Cultural preferences (Indian vegetarian, sambar ingredients)
- Learned patterns from user behavior
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from src.personalization.dietary_cultural_filter import DietaryCulturalFilter
from src.models.user_preferences import UserPreferences, DietaryRestriction


class TestDietaryCulturalIntelligence:
    """Test suite for Dietary & Cultural Intelligence feature"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.filter = DietaryCulturalFilter()
        self.user_id = "test_user_123"
        
        # Mock products with dietary attributes
        self.products = [
            {
                "id": "milk_001",
                "name": "Oatly Oat Milk",
                "category": "Dairy Alternatives",
                "attributes": ["vegan", "lactose-free", "gluten-free"],
                "price": 4.99
            },
            {
                "id": "milk_002", 
                "name": "Whole Milk",
                "category": "Dairy",
                "attributes": ["vegetarian"],
                "price": 3.49
            },
            {
                "id": "bread_001",
                "name": "Gluten-Free Bread",
                "category": "Bakery",
                "attributes": ["gluten-free", "vegan"],
                "price": 5.99
            },
            {
                "id": "meat_001",
                "name": "Organic Chicken",
                "category": "Meat",
                "attributes": ["organic", "halal"],
                "price": 12.99
            },
            {
                "id": "cheese_001",
                "name": "Kosher Cheese",
                "category": "Dairy",
                "attributes": ["kosher", "vegetarian"],
                "price": 6.99
            }
        ]
    
    @pytest.mark.asyncio
    async def test_filter_vegan_products(self):
        """Test filtering for vegan dietary restriction"""
        preferences = UserPreferences(
            user_id=self.user_id,
            dietary_restrictions=[DietaryRestriction.VEGAN]
        )
        
        filtered = await self.filter.apply_dietary_filter(
            products=self.products,
            preferences=preferences
        )
        
        # Should only return vegan products
        assert len(filtered) == 2
        assert all("vegan" in p["attributes"] for p in filtered)
        assert filtered[0]["id"] == "milk_001"
        assert filtered[1]["id"] == "bread_001"
    
    @pytest.mark.asyncio
    async def test_filter_gluten_free_products(self):
        """Test filtering for gluten-free restriction"""
        preferences = UserPreferences(
            user_id=self.user_id,
            dietary_restrictions=[DietaryRestriction.GLUTEN_FREE]
        )
        
        filtered = await self.filter.apply_dietary_filter(
            products=self.products,
            preferences=preferences
        )
        
        # Should return gluten-free products
        assert len(filtered) == 2
        assert all("gluten-free" in p["attributes"] for p in filtered)
    
    @pytest.mark.asyncio
    async def test_multiple_dietary_restrictions(self):
        """Test handling multiple dietary restrictions (AND logic)"""
        preferences = UserPreferences(
            user_id=self.user_id,
            dietary_restrictions=[
                DietaryRestriction.VEGAN,
                DietaryRestriction.GLUTEN_FREE
            ]
        )
        
        filtered = await self.filter.apply_dietary_filter(
            products=self.products,
            preferences=preferences
        )
        
        # Should only return products that are BOTH vegan AND gluten-free
        assert len(filtered) == 2
        for product in filtered:
            assert "vegan" in product["attributes"]
            assert "gluten-free" in product["attributes"]
    
    @pytest.mark.asyncio
    async def test_kosher_halal_filtering(self):
        """Test religious dietary restrictions"""
        # Test Kosher
        preferences_kosher = UserPreferences(
            user_id=self.user_id,
            dietary_restrictions=[DietaryRestriction.KOSHER]
        )
        
        filtered_kosher = await self.filter.apply_dietary_filter(
            products=self.products,
            preferences=preferences_kosher
        )
        
        assert len(filtered_kosher) == 1
        assert filtered_kosher[0]["id"] == "cheese_001"
        
        # Test Halal
        preferences_halal = UserPreferences(
            user_id=self.user_id,
            dietary_restrictions=[DietaryRestriction.HALAL]
        )
        
        filtered_halal = await self.filter.apply_dietary_filter(
            products=self.products,
            preferences=preferences_halal
        )
        
        assert len(filtered_halal) == 1
        assert filtered_halal[0]["id"] == "meat_001"
    
    @pytest.mark.asyncio
    async def test_cultural_preferences_indian_vegetarian(self):
        """Test Indian vegetarian cultural preference"""
        preferences = UserPreferences(
            user_id=self.user_id,
            cultural_preferences=["indian_vegetarian"]
        )
        
        # Add some Indian products
        indian_products = self.products + [
            {
                "id": "dal_001",
                "name": "Toor Dal",
                "category": "Pulses",
                "attributes": ["vegan", "indian", "protein-rich"],
                "cultural_tags": ["indian_staple"],
                "price": 3.99
            },
            {
                "id": "paneer_001",
                "name": "Fresh Paneer",
                "category": "Dairy",
                "attributes": ["vegetarian", "indian"],
                "cultural_tags": ["indian_staple"],
                "price": 5.99
            }
        ]
        
        filtered = await self.filter.apply_cultural_filter(
            products=indian_products,
            preferences=preferences
        )
        
        # Should prioritize Indian vegetarian products
        assert filtered[0]["id"] == "dal_001"  # Vegan Indian
        assert filtered[1]["id"] == "paneer_001"  # Vegetarian Indian
        # Non-meat products should still be included but ranked lower
        assert any(p["id"] == "milk_001" for p in filtered)
    
    @pytest.mark.asyncio
    async def test_sambar_ingredients_understanding(self):
        """Test understanding of cultural dish ingredients"""
        query_context = {
            "query": "sambar ingredients",
            "detected_dish": "sambar"
        }
        
        # Mock product database with sambar ingredients
        sambar_products = [
            {"id": "dal_001", "name": "Toor Dal", "tags": ["sambar_essential"]},
            {"id": "tamarind_001", "name": "Tamarind", "tags": ["sambar_essential"]},
            {"id": "sambar_powder", "name": "MTR Sambar Powder", "tags": ["sambar_essential"]},
            {"id": "vegetables_001", "name": "Drumsticks", "tags": ["sambar_vegetable"]},
            {"id": "onion_001", "name": "Onions", "tags": ["sambar_vegetable"]},
            {"id": "tomato_001", "name": "Tomatoes", "tags": ["sambar_vegetable"]},
            # Non-sambar items
            {"id": "pasta_001", "name": "Pasta", "tags": ["italian"]},
            {"id": "cheese_001", "name": "Cheese", "tags": ["dairy"]}
        ]
        
        filtered = await self.filter.get_cultural_dish_ingredients(
            dish_name="sambar",
            all_products=sambar_products
        )
        
        # Should return sambar-specific ingredients
        assert len(filtered) == 6
        assert all(any(tag.startswith("sambar") for tag in p.get("tags", [])) for p in filtered)
        assert not any(p["id"] == "pasta_001" for p in filtered)
    
    @pytest.mark.asyncio
    async def test_learned_dietary_patterns(self):
        """Test learning from user behavior"""
        # Simulate user history
        purchase_history = [
            {"product_id": "milk_001", "attributes": ["vegan"]},
            {"product_id": "bread_001", "attributes": ["gluten-free", "vegan"]},
            {"product_id": "milk_001", "attributes": ["vegan"]},  # Repeated
        ]
        
        # Learn patterns
        patterns = await self.filter.learn_dietary_patterns(
            user_id=self.user_id,
            purchase_history=purchase_history
        )
        
        assert patterns["likely_vegan"] == True
        assert patterns["confidence"] > 0.8
        assert "vegan" in patterns["detected_restrictions"]
    
    @pytest.mark.asyncio
    async def test_auto_filter_with_learned_preferences(self):
        """Test automatic filtering based on learned patterns"""
        # Mock learned preferences
        self.filter._learned_preferences[self.user_id] = {
            "restrictions": ["vegan"],
            "confidence": 0.9,
            "last_updated": datetime.now()
        }
        
        filtered = await self.filter.auto_filter_products(
            products=self.products,
            user_id=self.user_id,
            respect_learned=True
        )
        
        # Should automatically apply vegan filter
        assert all("vegan" in p["attributes"] for p in filtered)
        assert len(filtered) == 2
    
    @pytest.mark.asyncio
    async def test_preference_override(self):
        """Test user can override auto-detected preferences"""
        preferences = UserPreferences(
            user_id=self.user_id,
            dietary_restrictions=[],  # No restrictions
            override_auto_filter=True
        )
        
        # Even with learned vegan preference
        self.filter._learned_preferences[self.user_id] = {
            "restrictions": ["vegan"],
            "confidence": 0.9
        }
        
        filtered = await self.filter.apply_dietary_filter(
            products=self.products,
            preferences=preferences
        )
        
        # Should return all products when override is true
        assert len(filtered) == len(self.products)
    
    @pytest.mark.asyncio
    async def test_dietary_filter_performance(self):
        """Test filter performs efficiently with large product lists"""
        # Create 1000 products
        large_product_list = []
        for i in range(1000):
            large_product_list.append({
                "id": f"prod_{i}",
                "name": f"Product {i}",
                "attributes": ["vegan"] if i % 3 == 0 else ["vegetarian"],
                "price": 5.99
            })
        
        preferences = UserPreferences(
            user_id=self.user_id,
            dietary_restrictions=[DietaryRestriction.VEGAN]
        )
        
        import time
        start = time.time()
        
        filtered = await self.filter.apply_dietary_filter(
            products=large_product_list,
            preferences=preferences
        )
        
        duration = time.time() - start
        
        # Should filter 1000 products in under 50ms
        assert duration < 0.05
        assert len(filtered) == 334  # ~333 vegan products
    
    @pytest.mark.asyncio
    async def test_allergen_filtering(self):
        """Test filtering for allergens"""
        products_with_allergens = [
            {
                "id": "bread_001",
                "name": "Wheat Bread",
                "allergens": ["gluten", "wheat"],
                "price": 3.99
            },
            {
                "id": "milk_001",
                "name": "Dairy Milk",
                "allergens": ["lactose", "milk"],
                "price": 4.99
            },
            {
                "id": "nuts_001",
                "name": "Mixed Nuts",
                "allergens": ["tree_nuts", "peanuts"],
                "price": 7.99
            },
            {
                "id": "rice_001",
                "name": "Brown Rice",
                "allergens": [],
                "price": 2.99
            }
        ]
        
        preferences = UserPreferences(
            user_id=self.user_id,
            allergens=["gluten", "lactose"]
        )
        
        filtered = await self.filter.apply_allergen_filter(
            products=products_with_allergens,
            preferences=preferences
        )
        
        # Should only return products without specified allergens
        assert len(filtered) == 2
        assert filtered[0]["id"] == "nuts_001"
        assert filtered[1]["id"] == "rice_001"