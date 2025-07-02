"""
Tests for enhanced response compiler with personalization features
Following TDD approach - write tests first, then implement
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import asyncio
import time

from src.agents.response_compiler import ResponseCompilerAgent
from src.models.state import SearchState


class TestResponseCompilerPersonalization:
    """Test suite for response compiler personalization features"""
    
    @pytest.fixture
    def response_compiler(self):
        """Create response compiler instance"""
        return ResponseCompilerAgent()
    
    @pytest.fixture
    def base_state(self):
        """Create base state for testing"""
        return {
            "query": "organic milk",
            "user_id": "test_user_123",
            "session_id": "session_456",
            "search_results": [
                {
                    "sku": "12345",
                    "name": "Organic Valley Whole Milk",
                    "price": 5.99,
                    "category": "Dairy",
                    "supplier": "Organic Valley"
                },
                {
                    "sku": "12346",
                    "name": "Horizon Organic 2% Milk",
                    "price": 6.49,
                    "category": "Dairy",
                    "supplier": "Horizon"
                }
            ],
            "agent_status": {
                "supervisor": "completed",
                "product_search": "completed",
                "response_compiler": "running"
            },
            "agent_timings": {
                "supervisor": 50,
                "product_search": 150
            },
            "reasoning": ["Searching for organic milk", "Found 2 products"],
            "routing_decision": "product_search",
            "search_metadata": {
                "categories": ["Dairy"],
                "brands": ["Organic Valley", "Horizon"],
                "search_config": {"limit": 10},
                "alpha": 0.75
            }
        }
    
    @pytest.mark.asyncio
    async def test_response_includes_personalization_section(self, response_compiler, base_state):
        """Test that response includes personalization section when user_id is present"""
        # Add personalization data to state
        base_state["personalization_data"] = {
            "usual_items": [
                {"sku": "12345", "name": "Organic Valley Whole Milk", "usual_quantity": 2}
            ],
            "reorder_suggestions": [],
            "complementary_products": []
        }
        
        # Run compiler
        result = await response_compiler._run(base_state)
        
        # Check that personalization section exists
        assert "final_response" in result
        assert "personalization" in result["final_response"]
        
        # Check personalization structure
        personalization = result["final_response"]["personalization"]
        assert "enabled" in personalization
        assert "usual_items" in personalization
        assert "reorder_suggestions" in personalization
        assert "complementary_products" in personalization
        assert "applied_features" in personalization
        assert "confidence" in personalization
    
    @pytest.mark.asyncio
    async def test_backward_compatibility_maintained(self, response_compiler, base_state):
        """Test that response works without personalization data (backward compatibility)"""
        # Remove user_id to simulate anonymous request
        base_state.pop("user_id", None)
        
        # Run compiler
        result = await response_compiler._run(base_state)
        
        # Check standard response structure is maintained
        assert "final_response" in result
        response = result["final_response"]
        assert "success" in response
        assert "query" in response
        assert "products" in response
        assert "metadata" in response
        assert "execution" in response
        
        # Personalization should be absent or minimal
        if "personalization" in response:
            assert response["personalization"]["enabled"] is False
    
    @pytest.mark.asyncio
    async def test_personalization_metadata_tracking(self, response_compiler, base_state):
        """Test that personalization metadata is properly tracked"""
        base_state["personalization_data"] = {
            "usual_items": [{"sku": "12345", "name": "Milk", "usual_quantity": 2}],
            "reorder_suggestions": [{"sku": "12347", "name": "Bread", "days_until_reorder": 2}],
            "features_used": ["purchase_history", "reorder_patterns"],
            "processing_time_ms": 45
        }
        
        result = await response_compiler._run(base_state)
        
        # Check metadata includes personalization info
        metadata = result["final_response"]["metadata"]
        assert "personalization_metadata" in metadata
        
        pers_meta = metadata["personalization_metadata"]
        assert "features_used" in pers_meta
        assert "processing_time_ms" in pers_meta
        assert pers_meta["features_used"] == ["purchase_history", "reorder_patterns"]
    
    @pytest.mark.asyncio
    async def test_for_you_section_structure(self, response_compiler, base_state):
        """Test the 'for_you' section structure in personalized responses"""
        base_state["personalization_data"] = {
            "usual_items": [
                {"sku": "12345", "name": "Organic Valley Milk", "usual_quantity": 2},
                {"sku": "12348", "name": "Oatly Barista", "usual_quantity": 1}
            ],
            "reorder_suggestions": [
                {"sku": "12349", "name": "Bread", "days_until_reorder": 1, "usual_quantity": 2}
            ],
            "complementary_products": [
                {"sku": "12350", "name": "Organic Coffee", "reason": "Often bought with milk"}
            ]
        }
        
        result = await response_compiler._run(base_state)
        personalization = result["final_response"]["personalization"]
        
        # Verify usual items
        assert len(personalization["usual_items"]) == 2
        assert personalization["usual_items"][0]["name"] == "Organic Valley Milk"
        
        # Verify reorder suggestions
        assert len(personalization["reorder_suggestions"]) == 1
        assert personalization["reorder_suggestions"][0]["days_until_reorder"] == 1
        
        # Verify complementary products
        assert len(personalization["complementary_products"]) == 1
        assert "reason" in personalization["complementary_products"][0]
    
    @pytest.mark.asyncio
    async def test_handles_missing_personalization_data(self, response_compiler, base_state):
        """Test graceful handling when personalization data is missing or incomplete"""
        # Add empty personalization data
        base_state["personalization_data"] = {}
        
        result = await response_compiler._run(base_state)
        
        # Should not crash and should provide empty sections
        assert "final_response" in result
        personalization = result["final_response"].get("personalization", {})
        
        if personalization:
            assert personalization.get("usual_items", []) == []
            assert personalization.get("reorder_suggestions", []) == []
            assert personalization.get("complementary_products", []) == []
    
    @pytest.mark.asyncio
    async def test_performance_under_50ms_added(self, response_compiler, base_state):
        """Test that personalization adds less than 50ms to response time"""
        # First run without personalization
        start_time = time.time()
        result_without = await response_compiler._run(base_state.copy())
        time_without = (time.time() - start_time) * 1000
        
        # Then run with personalization
        base_state["personalization_data"] = {
            "usual_items": [{"sku": "12345", "name": "Milk", "usual_quantity": 2}] * 10,
            "reorder_suggestions": [{"sku": "12346", "name": "Bread", "days_until_reorder": 1}] * 5,
            "complementary_products": [{"sku": "12347", "name": "Coffee"}] * 5
        }
        
        start_time = time.time()
        result_with = await response_compiler._run(base_state)
        time_with = (time.time() - start_time) * 1000
        
        # Personalization should add less than 50ms
        time_added = time_with - time_without
        assert time_added < 50, f"Personalization added {time_added:.2f}ms, should be under 50ms"
    
    @pytest.mark.asyncio
    async def test_personalization_with_order_response(self, response_compiler):
        """Test personalization works with order operations"""
        order_state = {
            "query": "add my usual milk",
            "user_id": "test_user_123",
            "routing_decision": "order_agent",
            "order_response": True,
            "current_order": {
                "items": [
                    {"sku": "12345", "name": "Organic Valley Milk", "quantity": 2, "price": 5.99}
                ],
                "total": 11.98
            },
            "personalization_data": {
                "usual_items": [{"sku": "12345", "name": "Organic Valley Milk", "usual_quantity": 2}]
            },
            "agent_status": {"order_agent": "completed"},
            "agent_timings": {"order_agent": 100},
            "reasoning": ["Added usual milk to order"],
            "messages": []
        }
        
        result = await response_compiler._run(order_state)
        
        # Should compile order response with personalization
        assert "final_response" in result
        assert "order" in result["final_response"]
        
        # Personalization should be included even in order response
        if "personalization" in result["final_response"]:
            assert len(result["final_response"]["personalization"]["usual_items"]) > 0
    
    @pytest.mark.asyncio
    async def test_personalization_feature_flags(self, response_compiler, base_state):
        """Test that personalization respects feature flags"""
        base_state["user_preferences"] = {
            "personalization": {
                "enabled": True,
                "features": {
                    "smart_ranking": True,
                    "usual_orders": False,  # Disabled
                    "reorder_reminders": True,
                    "complementary_items": False  # Disabled
                }
            }
        }
        
        base_state["personalization_data"] = {
            "usual_items": [{"sku": "12345", "name": "Milk"}],  # Should be filtered out
            "reorder_suggestions": [{"sku": "12346", "name": "Bread"}],  # Should be included
            "complementary_products": [{"sku": "12347", "name": "Coffee"}],  # Should be filtered out
            "applied_features": ["smart_ranking", "reorder_reminders"]
        }
        
        result = await response_compiler._run(base_state)
        personalization = result["final_response"]["personalization"]
        
        # Check that disabled features are filtered
        assert personalization["applied_features"] == ["smart_ranking", "reorder_reminders"]
        
        # Usual orders disabled, so should be empty
        assert len(personalization.get("usual_items", [])) == 0
        
        # Reorder reminders enabled
        assert len(personalization["reorder_suggestions"]) == 1
        
        # Complementary disabled
        assert len(personalization.get("complementary_products", [])) == 0
    
    @pytest.mark.asyncio
    async def test_personalization_confidence_scoring(self, response_compiler, base_state):
        """Test that personalization confidence is calculated correctly"""
        # High confidence scenario - lots of data
        base_state["personalization_data"] = {
            "usual_items": [{"sku": f"1234{i}", "name": f"Item {i}"} for i in range(5)],
            "reorder_suggestions": [{"sku": "12350", "name": "Bread"}],
            "purchase_history_count": 50,
            "days_of_history": 180,
            "confidence_factors": {
                "data_points": 50,
                "recency": 0.9,
                "consistency": 0.85
            }
        }
        
        result = await response_compiler._run(base_state)
        confidence = result["final_response"]["personalization"]["confidence"]
        
        # High data points should give high confidence
        assert confidence >= 0.8
        
        # Low confidence scenario
        base_state["personalization_data"] = {
            "usual_items": [],
            "purchase_history_count": 2,
            "days_of_history": 7,
            "confidence_factors": {
                "data_points": 2,
                "recency": 0.5,
                "consistency": 0.3
            }
        }
        
        result = await response_compiler._run(base_state)
        confidence = result["final_response"]["personalization"]["confidence"]
        
        # Low data should give low confidence
        assert confidence <= 0.5