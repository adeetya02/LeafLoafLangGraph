"""
Tests for smart search ranking with personalization
Following TDD approach - write tests first, then implement
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import asyncio
import time
from typing import List, Dict, Any


class TestSmartSearchRanking:
    """Test suite for personalized search ranking"""
    
    @pytest.fixture
    def mock_products(self):
        """Sample products for testing"""
        return [
            {
                "sku": "MILK-001",
                "name": "Oatly Barista Edition",
                "category": "Dairy Alternatives",
                "brand": "Oatly",
                "price": 5.99,
                "score": 0.8
            },
            {
                "sku": "MILK-002",
                "name": "Organic Valley Whole Milk",
                "category": "Dairy",
                "brand": "Organic Valley",
                "price": 6.49,
                "score": 0.85
            },
            {
                "sku": "MILK-003",
                "name": "Horizon Organic 2% Milk",
                "category": "Dairy",
                "brand": "Horizon",
                "price": 6.99,
                "score": 0.82
            },
            {
                "sku": "MILK-004",
                "name": "Store Brand Milk",
                "category": "Dairy", 
                "brand": "Store Brand",
                "price": 3.99,
                "score": 0.75
            }
        ]
    
    @pytest.fixture
    def user_preferences(self):
        """Sample user preferences for testing"""
        from src.models.user_preferences import UserPreferences, PersonalizationSettings
        
        return UserPreferences(
            user_id="test_user_123",
            personalization=PersonalizationSettings(
                enabled=True,
                features={
                    "smart_ranking": True,
                    "dietary_filters": True,
                    "budget_awareness": True
                }
            )
        )
    
    @pytest.fixture
    def purchase_history(self):
        """Sample purchase history"""
        return {
            "frequent_brands": {
                "Oatly": 15,  # 15 purchases
                "Organic Valley": 5,
                "Horizon": 2,
                "Store Brand": 1
            },
            "category_preferences": {
                "Dairy Alternatives": 0.7,  # 70% of dairy purchases
                "Dairy": 0.3
            },
            "price_patterns": {
                "average_price": 5.50,
                "price_sensitivity": "medium"  # willing to pay for quality
            },
            "dietary_preferences": ["plant-based", "organic"]
        }
    
    @pytest.mark.asyncio
    async def test_search_reranks_based_on_purchase_history(self, mock_products, purchase_history):
        """Test that search results are reranked based on purchase history"""
        from src.agents.personalized_ranker import PersonalizedRanker
        
        ranker = PersonalizedRanker()
        
        # Rerank products
        reranked = await ranker.rerank_products(
            products=mock_products.copy(),
            purchase_history=purchase_history,
            user_id="test_user_123"
        )
        
        # Oatly should be first (most purchased brand)
        assert reranked[0]["sku"] == "MILK-001"
        assert reranked[0]["personalization_score"] > 0
        
        # Store brand should be last (least purchased)
        assert reranked[-1]["sku"] == "MILK-004"
        
        # Verify personalization scores were added
        for product in reranked:
            assert "personalization_score" in product
            assert "ranking_factors" in product
    
    @pytest.mark.asyncio
    async def test_preferred_brands_boost(self, mock_products, purchase_history):
        """Test that preferred brands get score boost"""
        from src.agents.personalized_ranker import PersonalizedRanker
        
        ranker = PersonalizedRanker()
        
        # Calculate brand boost
        oatly_product = mock_products[0]
        store_brand_product = mock_products[3]
        
        oatly_boost = ranker.calculate_brand_boost(
            oatly_product["brand"],
            purchase_history["frequent_brands"]
        )
        
        store_boost = ranker.calculate_brand_boost(
            store_brand_product["brand"],
            purchase_history["frequent_brands"]
        )
        
        # Oatly should get higher boost
        assert oatly_boost > store_boost
        assert oatly_boost > 0.5  # Significant boost for frequent brand
        assert store_boost < 0.2  # Minimal boost for rarely purchased
    
    @pytest.mark.asyncio
    async def test_category_preferences_applied(self, mock_products, purchase_history):
        """Test that category preferences influence ranking"""
        from src.agents.personalized_ranker import PersonalizedRanker
        
        ranker = PersonalizedRanker()
        
        # Rerank with category preferences
        reranked = await ranker.rerank_products(
            products=mock_products.copy(),
            purchase_history=purchase_history,
            user_id="test_user_123"
        )
        
        # Find dairy alternative vs regular dairy
        dairy_alt = next(p for p in reranked if p["category"] == "Dairy Alternatives")
        regular_dairy = next(p for p in reranked if p["category"] == "Dairy")
        
        # Dairy alternative should rank higher due to preference
        dairy_alt_index = reranked.index(dairy_alt)
        dairy_index = reranked.index(regular_dairy)
        
        assert dairy_alt_index < dairy_index
    
    @pytest.mark.asyncio
    async def test_dietary_filters_work(self, mock_products, user_preferences):
        """Test that dietary preferences filter results when enabled"""
        from src.agents.personalized_ranker import PersonalizedRanker
        
        ranker = PersonalizedRanker()
        
        purchase_history = {
            "dietary_preferences": ["vegan", "dairy-free"]
        }
        
        # Apply dietary filtering
        filtered = await ranker.apply_dietary_filters(
            products=mock_products.copy(),
            dietary_preferences=purchase_history["dietary_preferences"],
            user_preferences=user_preferences
        )
        
        # Only Oatly (dairy alternative) should remain
        assert len(filtered) == 1
        assert filtered[0]["sku"] == "MILK-001"
        
        # Test with dietary filters disabled
        user_preferences.personalization.features["dietary_filters"] = False
        
        unfiltered = await ranker.apply_dietary_filters(
            products=mock_products.copy(),
            dietary_preferences=purchase_history["dietary_preferences"],
            user_preferences=user_preferences
        )
        
        # All products should remain
        assert len(unfiltered) == len(mock_products)
    
    @pytest.mark.asyncio
    async def test_price_preference_respected(self, mock_products, purchase_history):
        """Test that price preferences influence ranking"""
        from src.agents.personalized_ranker import PersonalizedRanker
        
        ranker = PersonalizedRanker()
        
        # Test premium preference
        history_premium = {
            **purchase_history,
            "price_patterns": {
                "average_price": 6.50,
                "price_sensitivity": "low"
            }
        }
        
        reranked = await ranker.rerank_products(
            products=mock_products.copy(),
            purchase_history=history_premium,
            user_id="test_user_123"
        )
        
        # Store brand should rank lower for premium buyers
        store_brand_index = next(
            i for i, p in enumerate(reranked) 
            if p["sku"] == "MILK-004"
        )
        assert store_brand_index >= 2  # Not in top 2
        
        # Check that premium products rank higher
        premium_products = [p for p in reranked[:2] if p["price"] >= 6.0]
        assert len(premium_products) >= 1  # At least one premium product in top 2
        
        # Test budget preference
        history_budget = {
            **purchase_history,
            "price_patterns": {
                "average_price": 4.00,
                "price_sensitivity": "high"
            }
        }
        
        reranked_budget = await ranker.rerank_products(
            products=mock_products.copy(),
            purchase_history=history_budget,
            user_id="test_user_123"
        )
        
        # Store brand should rank higher for budget buyers
        store_brand_index_budget = next(
            i for i, p in enumerate(reranked_budget)
            if p["sku"] == "MILK-004"
        )
        # For budget buyers, store brand should rank higher than for premium buyers
        assert store_brand_index_budget < store_brand_index
        
        # Store brand should be in top 3 for budget buyers
        assert store_brand_index_budget <= 2
        
        # At least one budget option (under $5) should be in top 2
        budget_in_top2 = [p for p in reranked_budget[:2] if p["price"] < 5.0]
        assert len(budget_in_top2) >= 1
    
    @pytest.mark.asyncio
    async def test_performance_under_100ms(self, mock_products):
        """Test that personalization adds less than 100ms"""
        from src.agents.personalized_ranker import PersonalizedRanker
        
        ranker = PersonalizedRanker()
        
        # Create larger dataset
        large_products = mock_products * 25  # 100 products
        
        purchase_history = {
            "frequent_brands": {"Oatly": 10, "Horizon": 5},
            "category_preferences": {"Dairy": 0.6},
            "price_patterns": {"average_price": 5.0}
        }
        
        start_time = time.time()
        
        reranked = await ranker.rerank_products(
            products=large_products,
            purchase_history=purchase_history,
            user_id="test_user_123"
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert elapsed_ms < 100, f"Ranking took {elapsed_ms:.2f}ms, should be under 100ms"
        assert len(reranked) == len(large_products)
    
    @pytest.mark.asyncio
    async def test_works_without_personalization_data(self, mock_products):
        """Test graceful handling when no personalization data available"""
        from src.agents.personalized_ranker import PersonalizedRanker
        
        ranker = PersonalizedRanker()
        
        # No purchase history
        reranked = await ranker.rerank_products(
            products=mock_products.copy(),
            purchase_history=None,
            user_id="test_user_123"
        )
        
        # Should return products in original order
        assert len(reranked) == len(mock_products)
        for i, product in enumerate(reranked):
            assert product["sku"] == mock_products[i]["sku"]
        
        # Should still have base scores
        for product in reranked:
            assert "score" in product
    
    @pytest.mark.asyncio
    async def test_respects_feature_flags(self, mock_products, user_preferences):
        """Test that personalization respects feature flags"""
        from src.agents.personalized_ranker import PersonalizedRanker
        
        ranker = PersonalizedRanker()
        
        purchase_history = {
            "frequent_brands": {"Oatly": 15},
            "category_preferences": {"Dairy Alternatives": 0.8}
        }
        
        # Disable smart ranking
        user_preferences.personalization.features["smart_ranking"] = False
        
        reranked = await ranker.rerank_products(
            products=mock_products.copy(),
            purchase_history=purchase_history,
            user_id="test_user_123",
            user_preferences=user_preferences
        )
        
        # Should maintain original order when disabled
        for i, product in enumerate(reranked):
            assert product["sku"] == mock_products[i]["sku"]
        
        # Should not have personalization scores
        for product in reranked:
            assert product.get("personalization_score", 0) == 0
    
    @pytest.mark.asyncio
    async def test_combined_ranking_factors(self, mock_products):
        """Test that multiple factors combine correctly"""
        from src.agents.personalized_ranker import PersonalizedRanker
        
        ranker = PersonalizedRanker()
        
        # Rich purchase history
        history = {
            "frequent_brands": {
                "Oatly": 20,
                "Organic Valley": 10
            },
            "category_preferences": {
                "Dairy Alternatives": 0.8,
                "Dairy": 0.2
            },
            "price_patterns": {
                "average_price": 5.99,
                "price_sensitivity": "low"
            },
            "dietary_preferences": ["organic"],
            "recent_purchases": ["MILK-001", "MILK-002"]
        }
        
        reranked = await ranker.rerank_products(
            products=mock_products.copy(),
            purchase_history=history,
            user_id="test_user_123"
        )
        
        # Check ranking factors
        top_product = reranked[0]
        assert "ranking_factors" in top_product
        
        factors = top_product["ranking_factors"]
        assert "brand_affinity" in factors
        assert "category_match" in factors
        assert "price_match" in factors
        assert "recency_boost" in factors
        
        # Oatly should be first (high brand affinity + category match + recent)
        assert top_product["sku"] == "MILK-001"
        assert top_product["personalization_score"] > 0.8
    
    @pytest.mark.asyncio
    async def test_search_agent_integration(self):
        """Test integration with product search agent"""
        from src.agents.product_search import ProductSearchAgent
        from src.models.state import SearchState
        
        # Mock dependencies
        mock_weaviate = AsyncMock()
        mock_weaviate.search.return_value = {
            "products": [
                {"sku": "MILK-001", "name": "Oatly", "score": 0.8},
                {"sku": "MILK-002", "name": "Organic Valley", "score": 0.85}
            ]
        }
        
        mock_preference_service = AsyncMock()
        mock_preference_service.get_preferences.return_value = Mock(
            is_feature_enabled=Mock(return_value=True)
        )
        
        # Create agent with mocks
        agent = ProductSearchAgent(
            weaviate_client=mock_weaviate,
            preference_service=mock_preference_service
        )
        
        # Create state
        state = {
            "query": "milk",
            "user_id": "test_user_123",
            "personalization_data": {
                "purchase_history": {
                    "frequent_brands": {"Oatly": 10}
                }
            }
        }
        
        # Run search
        result = await agent._run(state)
        
        # Should have personalized results
        assert "search_results" in result
        assert len(result["search_results"]) > 0
        
        # Should include personalization metadata
        assert "search_metadata" in result
        metadata = result["search_metadata"]
        assert metadata.get("personalization_applied") is True