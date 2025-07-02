"""
Tests for Reorder Intelligence functionality
Following TDD approach - write tests first, then implement
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Any


class TestReorderIntelligence:
    """Test suite for intelligent reorder predictions and reminders"""
    
    @pytest.fixture
    def mock_order_history(self):
        """Sample order history with patterns for testing"""
        return {
            "user_id": "test_user_123",
            "orders": [
                # Weekly milk pattern
                {"order_id": "O1", "date": (datetime.now() - timedelta(days=7)).isoformat(), 
                 "items": [{"sku": "MILK-001", "name": "Milk", "quantity": 2}]},
                {"order_id": "O2", "date": (datetime.now() - timedelta(days=14)).isoformat(),
                 "items": [{"sku": "MILK-001", "name": "Milk", "quantity": 2}]},
                {"order_id": "O3", "date": (datetime.now() - timedelta(days=21)).isoformat(),
                 "items": [{"sku": "MILK-001", "name": "Milk", "quantity": 2}]},
                
                # Bi-weekly eggs pattern
                {"order_id": "O4", "date": (datetime.now() - timedelta(days=14)).isoformat(),
                 "items": [{"sku": "EGGS-001", "name": "Eggs", "quantity": 1}]},
                {"order_id": "O5", "date": (datetime.now() - timedelta(days=28)).isoformat(),
                 "items": [{"sku": "EGGS-001", "name": "Eggs", "quantity": 1}]},
                
                # Irregular coffee pattern
                {"order_id": "O6", "date": (datetime.now() - timedelta(days=10)).isoformat(),
                 "items": [{"sku": "COFFEE-001", "name": "Coffee", "quantity": 1}]},
                {"order_id": "O7", "date": (datetime.now() - timedelta(days=25)).isoformat(),
                 "items": [{"sku": "COFFEE-001", "name": "Coffee", "quantity": 1}]}
            ]
        }
    
    @pytest.mark.asyncio
    async def test_reorder_cycle_calculation(self, mock_order_history):
        """Test accurate calculation of reorder cycles for each product"""
        from src.agents.reorder_intelligence import ReorderIntelligence
        
        intelligence = ReorderIntelligence()
        
        # Calculate reorder cycles
        cycles = await intelligence.calculate_reorder_cycles(mock_order_history)
        
        # Milk should have 7-day cycle
        assert cycles["MILK-001"]["average_days"] == 7
        assert cycles["MILK-001"]["consistency"] == "high"  # Very regular
        
        # Eggs should have 14-day cycle
        assert cycles["EGGS-001"]["average_days"] == 14
        assert cycles["EGGS-001"]["consistency"] == "high"
        
        # Coffee should show 15-day cycle (only one interval)
        assert cycles["COFFEE-001"]["average_days"] == 15  # Average of intervals
        assert cycles["COFFEE-001"]["consistency"] == "high"  # Only one interval, can't determine irregularity
    
    @pytest.mark.asyncio
    async def test_due_for_reorder_detection(self, mock_order_history):
        """Test detection of items due for reordering"""
        from src.agents.reorder_intelligence import ReorderIntelligence
        
        intelligence = ReorderIntelligence()
        
        # Get items due for reorder
        due_items = await intelligence.get_due_for_reorder(
            order_history=mock_order_history,
            current_date=datetime.now()
        )
        
        # Milk last ordered 7 days ago, due now
        milk_due = next((item for item in due_items if item["sku"] == "MILK-001"), None)
        assert milk_due is not None
        assert milk_due["urgency"] == "due_now"
        assert milk_due["days_until_due"] == 0
        
        # Eggs last ordered 14 days ago, due now
        eggs_due = next((item for item in due_items if item["sku"] == "EGGS-001"), None)
        assert eggs_due is not None
        assert eggs_due["urgency"] == "due_now"
    
    @pytest.mark.asyncio
    async def test_proactive_reminders(self, mock_order_history):
        """Test generation of proactive reorder reminders"""
        from src.agents.reorder_intelligence import ReorderIntelligence
        
        intelligence = ReorderIntelligence()
        
        # Get reminders for next 7 days
        reminders = await intelligence.generate_reminders(
            order_history=mock_order_history,
            days_ahead=7
        )
        
        # Should have reminders for different urgency levels
        assert len(reminders) > 0
        
        # Check reminder structure
        for reminder in reminders:
            assert "sku" in reminder
            assert "message" in reminder
            assert "urgency_level" in reminder  # critical, high, medium, low
            assert "suggested_order_date" in reminder
            assert "confidence" in reminder
    
    @pytest.mark.asyncio
    async def test_smart_bundling_suggestions(self, mock_order_history):
        """Test intelligent bundling of items with similar reorder cycles"""
        from src.agents.reorder_intelligence import ReorderIntelligence
        
        intelligence = ReorderIntelligence()
        
        # Get bundle suggestions
        bundles = await intelligence.suggest_reorder_bundles(mock_order_history)
        
        # Should suggest bundling items with similar cycles
        assert len(bundles) > 0
        
        # Check bundle structure
        for bundle in bundles:
            assert "items" in bundle
            assert "combined_cycle_days" in bundle
            assert "savings_potential" in bundle  # Delivery fee savings
            assert "convenience_score" in bundle
    
    @pytest.mark.asyncio
    async def test_seasonal_adjustment(self):
        """Test reorder predictions adjust for seasonal patterns"""
        from src.agents.reorder_intelligence import ReorderIntelligence
        
        intelligence = ReorderIntelligence()
        
        # Create history with seasonal pattern (ice cream in summer)
        seasonal_history = {
            "user_id": "test_user",
            "orders": [
                {"date": "2024-07-15", "items": [{"sku": "ICE-CREAM-001", "quantity": 2}]},
                {"date": "2024-07-01", "items": [{"sku": "ICE-CREAM-001", "quantity": 2}]},
                {"date": "2024-06-15", "items": [{"sku": "ICE-CREAM-001", "quantity": 2}]},
                # Gap in winter
                {"date": "2023-07-15", "items": [{"sku": "ICE-CREAM-001", "quantity": 2}]}
            ]
        }
        
        # Test summer vs winter predictions
        summer_pred = await intelligence.predict_reorder_date(
            "ICE-CREAM-001", 
            seasonal_history,
            current_season="summer"
        )
        
        winter_pred = await intelligence.predict_reorder_date(
            "ICE-CREAM-001",
            seasonal_history,
            current_season="winter"
        )
        
        # Summer should have shorter cycle
        assert summer_pred["confidence"] > winter_pred["confidence"]
        assert summer_pred["cycle_days"] < 30  # Frequent in summer
    
    @pytest.mark.asyncio
    async def test_stock_out_prevention(self, mock_order_history):
        """Test early warnings to prevent stock-outs"""
        from src.agents.reorder_intelligence import ReorderIntelligence
        
        intelligence = ReorderIntelligence()
        
        # Configure buffer days for critical items
        config = {
            "critical_items": ["MILK-001", "EGGS-001"],
            "buffer_days": 2  # Remind 2 days early
        }
        
        # Get preventive reminders
        preventive = await intelligence.get_stockout_prevention_reminders(
            order_history=mock_order_history,
            config=config
        )
        
        # Should remind earlier for critical items
        milk_reminder = next((r for r in preventive if r["sku"] == "MILK-001"), None)
        assert milk_reminder is not None
        assert milk_reminder["days_early"] == 2
        assert "prevent stockout" in milk_reminder["message"].lower()
    
    @pytest.mark.asyncio
    async def test_learns_from_modifications(self):
        """Test that system learns when users modify suggested reorder dates"""
        from src.agents.reorder_intelligence import ReorderIntelligence
        
        intelligence = ReorderIntelligence()
        
        # History with user modifications
        history_with_feedback = {
            "user_id": "test_user",
            "reorder_feedback": [
                {"sku": "MILK-001", "suggested_days": 7, "actual_days": 6},
                {"sku": "MILK-001", "suggested_days": 7, "actual_days": 6},
                {"sku": "MILK-001", "suggested_days": 7, "actual_days": 8}
            ]
        }
        
        # Learn from feedback
        adjusted = await intelligence.learn_from_feedback(
            "MILK-001",
            history_with_feedback
        )
        
        # Should adjust cycle based on actual behavior
        assert adjusted["learned_cycle"] != 7  # Not the original
        assert 6 <= adjusted["learned_cycle"] <= 8  # In user's range
        assert adjusted["confidence_improved"] == True
    
    @pytest.mark.asyncio
    async def test_multi_household_patterns(self):
        """Test detection of different household member patterns"""
        from src.agents.reorder_intelligence import ReorderIntelligence
        
        intelligence = ReorderIntelligence()
        
        # History suggesting multiple users (different milk types)
        multi_user_history = {
            "orders": [
                {"items": [{"sku": "MILK-WHOLE", "quantity": 1}, 
                          {"sku": "MILK-ALMOND", "quantity": 1}]},
                {"items": [{"sku": "MILK-WHOLE", "quantity": 2}]},  # Someone needs more
                {"items": [{"sku": "MILK-ALMOND", "quantity": 1}]}
            ]
        }
        
        # Detect household patterns
        patterns = await intelligence.detect_household_patterns(multi_user_history)
        
        assert patterns["household_size_estimate"] >= 2
        # Check that we detected both milk preferences
        all_preferences = []
        for member_prefs in patterns["member_preferences"].values():
            all_preferences.extend(member_prefs)
        assert "MILK-WHOLE" in all_preferences
        assert "MILK-ALMOND" in all_preferences
    
    @pytest.mark.asyncio
    async def test_holiday_awareness(self):
        """Test adjustment of reorder predictions around holidays"""
        from src.agents.reorder_intelligence import ReorderIntelligence
        
        intelligence = ReorderIntelligence()
        
        # Test Thanksgiving week (high demand)
        thanksgiving_pred = await intelligence.predict_with_holidays(
            regular_cycle_days=7,
            next_date=datetime(2024, 11, 23),  # Day before Thanksgiving
            holiday_calendar={"2024-11-28": "Thanksgiving"}
        )
        
        # Should suggest ordering earlier
        assert thanksgiving_pred["adjusted_date"] < datetime(2024, 11, 23).isoformat()
        assert "holiday" in thanksgiving_pred["reason"].lower()
        
    @pytest.mark.asyncio
    async def test_performance_under_100ms(self):
        """Test that reorder intelligence completes within performance budget"""
        from src.agents.reorder_intelligence import ReorderIntelligence
        import time
        
        intelligence = ReorderIntelligence()
        
        # Large history (200 orders)
        large_history = {
            "orders": [
                {"order_id": f"O{i}", 
                 "date": (datetime.now() - timedelta(days=i*7)).isoformat(),
                 "items": [{"sku": f"ITEM-{i%10}", "quantity": 1}]}
                for i in range(200)
            ]
        }
        
        start_time = time.time()
        
        # Run all analyses
        cycles = await intelligence.calculate_reorder_cycles(large_history)
        due_items = await intelligence.get_due_for_reorder(large_history)
        reminders = await intelligence.generate_reminders(large_history)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        assert elapsed_ms < 100, f"Analysis took {elapsed_ms:.2f}ms, should be under 100ms"
        assert len(cycles) > 0
        assert isinstance(due_items, list)
        assert isinstance(reminders, list)