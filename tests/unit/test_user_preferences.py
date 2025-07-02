"""
Tests for user preference schema and storage
Following TDD approach - write tests first, then implement
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

# We'll create these modules after writing tests
# from src.models.user_preferences import UserPreferences, PersonalizationSettings
# from src.services.preference_service import PreferenceService


class TestUserPreferences:
    """Test suite for user preference management"""
    
    @pytest.mark.asyncio
    async def test_preference_schema_validation(self):
        """Test that preference schema validates correctly"""
        # Import after we create it
        from src.models.user_preferences import UserPreferences, PersonalizationSettings
        
        # Valid preferences
        valid_prefs = UserPreferences(
            user_id="test_user_123",
            personalization=PersonalizationSettings(
                enabled=True,
                features={
                    "smart_ranking": True,
                    "usual_orders": True,
                    "reorder_reminders": True,
                    "dietary_filters": True,
                    "cultural_awareness": True,
                    "complementary_items": True,
                    "quantity_memory": True,
                    "budget_awareness": False,
                    "household_inference": False,
                    "seasonal_suggestions": True
                }
            ),
            privacy={
                "data_retention_days": 365,
                "allow_pattern_learning": True,
                "share_patterns_for_improvement": False
            }
        )
        
        assert valid_prefs.user_id == "test_user_123"
        assert valid_prefs.personalization.enabled is True
        assert valid_prefs.personalization.features["smart_ranking"] is True
        assert valid_prefs.personalization.features["budget_awareness"] is False
        
        # Test invalid data should raise validation error
        with pytest.raises(Exception):  # Will be pydantic ValidationError
            UserPreferences(user_id=None)  # user_id is required
    
    @pytest.mark.asyncio
    async def test_all_features_enabled_by_default(self):
        """Test that all personalization features are enabled by default"""
        from src.models.user_preferences import UserPreferences, get_default_preferences
        
        # Get default preferences
        default_prefs = get_default_preferences("test_user_123")
        
        # Check all features are enabled
        assert default_prefs.personalization.enabled is True
        features = default_prefs.personalization.features
        
        # All 10 features should be enabled by default
        expected_features = [
            "smart_ranking", "usual_orders", "reorder_reminders",
            "dietary_filters", "cultural_awareness", "complementary_items",
            "quantity_memory", "budget_awareness", "household_inference",
            "seasonal_suggestions"
        ]
        
        for feature in expected_features:
            assert features[feature] is True, f"{feature} should be enabled by default"
        
        # Privacy settings should be privacy-friendly by default
        assert default_prefs.privacy["allow_pattern_learning"] is True
        assert default_prefs.privacy["share_patterns_for_improvement"] is False
    
    @pytest.mark.asyncio
    async def test_preference_storage_retrieval(self):
        """Test storing and retrieving preferences"""
        from src.services.preference_service import PreferenceService
        from src.models.user_preferences import UserPreferences, PersonalizationSettings
        
        service = PreferenceService()
        
        # Create preferences
        prefs = UserPreferences(
            user_id="test_user_123",
            personalization=PersonalizationSettings(
                enabled=True,
                features={"smart_ranking": True, "usual_orders": False}
            )
        )
        
        # Store preferences
        await service.save_preferences(prefs)
        
        # Retrieve preferences
        retrieved = await service.get_preferences("test_user_123")
        
        assert retrieved is not None
        assert retrieved.user_id == "test_user_123"
        assert retrieved.personalization.features["smart_ranking"] is True
        assert retrieved.personalization.features["usual_orders"] is False
        
        # Non-existent user should return None or default
        missing = await service.get_preferences("non_existent_user")
        assert missing is not None  # Should return defaults
    
    @pytest.mark.asyncio 
    async def test_redis_caching(self):
        """Test that preferences are cached in Redis when available"""
        from src.services.preference_service import PreferenceService
        from src.models.user_preferences import get_default_preferences
        
        # Mock Redis client
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        
        service = PreferenceService(redis_client=mock_redis)
        
        # Get preferences (should check cache first)
        prefs = await service.get_preferences("test_user_123")
        
        # Should have tried to get from cache
        mock_redis.get.assert_called_once_with("preferences:test_user_123")
        
        # Save preferences
        await service.save_preferences(prefs)
        
        # Should have saved to cache with TTL
        mock_redis.setex.assert_called()
        call_args = mock_redis.setex.call_args
        assert "preferences:test_user_123" in str(call_args)
        assert call_args[0][1] == 3600  # 1 hour TTL
    
    @pytest.mark.asyncio
    async def test_preference_updates(self):
        """Test updating individual preference settings"""
        from src.services.preference_service import PreferenceService
        
        service = PreferenceService()
        
        # Get default preferences
        prefs = await service.get_preferences("test_user_123")
        
        # Update a specific feature
        await service.update_feature(
            "test_user_123", 
            "smart_ranking", 
            False
        )
        
        # Retrieve updated preferences
        updated = await service.get_preferences("test_user_123")
        assert updated.personalization.features["smart_ranking"] is False
        
        # Other features should remain unchanged
        assert updated.personalization.features["usual_orders"] is True
        
        # Bulk update features
        await service.update_features(
            "test_user_123",
            {
                "budget_awareness": False,
                "household_inference": False
            }
        )
        
        final = await service.get_preferences("test_user_123")
        assert final.personalization.features["budget_awareness"] is False
        assert final.personalization.features["household_inference"] is False
    
    @pytest.mark.asyncio
    async def test_preference_privacy_controls(self):
        """Test privacy control settings"""
        from src.services.preference_service import PreferenceService
        
        service = PreferenceService()
        
        # Update privacy settings
        await service.update_privacy_settings(
            "test_user_123",
            {
                "data_retention_days": 90,
                "share_patterns_for_improvement": True
            }
        )
        
        prefs = await service.get_preferences("test_user_123")
        assert prefs.privacy["data_retention_days"] == 90
        assert prefs.privacy["share_patterns_for_improvement"] is True
        
        # Test data deletion
        await service.delete_user_data("test_user_123")
        
        # Should return defaults after deletion
        deleted_prefs = await service.get_preferences("test_user_123")
        assert deleted_prefs.personalization.enabled is True  # Back to defaults
    
    def test_preference_serialization(self):
        """Test that preferences can be serialized to/from JSON"""
        from src.models.user_preferences import UserPreferences, get_default_preferences
        
        prefs = get_default_preferences("test_user_123")
        
        # Serialize to JSON
        json_str = prefs.model_dump_json()
        assert isinstance(json_str, str)
        
        # Deserialize from JSON
        data = json.loads(json_str)
        restored = UserPreferences(**data)
        
        assert restored.user_id == prefs.user_id
        assert restored.personalization.enabled == prefs.personalization.enabled
        
        # Test dict serialization
        prefs_dict = prefs.model_dump()
        assert isinstance(prefs_dict, dict)
        assert prefs_dict["user_id"] == "test_user_123"
    
    @pytest.mark.asyncio
    async def test_graphiti_integration(self):
        """Test that preferences integrate with Graphiti memory"""
        from src.services.preference_service import PreferenceService
        
        # Mock Graphiti
        mock_graphiti = AsyncMock()
        mock_graphiti.get_memory.return_value = None  # No existing preferences
        mock_graphiti.add_memory.return_value = True
        service = PreferenceService(graphiti_client=mock_graphiti)
        
        # Save preferences should also update Graphiti
        prefs = await service.get_preferences("test_user_123")
        await service.save_preferences(prefs)
        
        # Should have called Graphiti to store preferences
        mock_graphiti.add_memory.assert_called()
        
        # Memory should include preference data
        call_kwargs = mock_graphiti.add_memory.call_args.kwargs
        if "memory" in call_kwargs:
            memory_data = call_kwargs["memory"]
            assert "personalization_preferences" in memory_data
            assert "enabled_features" in memory_data
    
    def test_feature_flag_helpers(self):
        """Test helper methods for checking feature flags"""
        from src.models.user_preferences import UserPreferences, PersonalizationSettings
        
        prefs = UserPreferences(
            user_id="test_user_123",
            personalization=PersonalizationSettings(
                enabled=True,
                features={
                    "smart_ranking": True,
                    "usual_orders": False
                }
            )
        )
        
        # Test is_feature_enabled helper
        assert prefs.is_feature_enabled("smart_ranking") is True
        assert prefs.is_feature_enabled("usual_orders") is False
        assert prefs.is_feature_enabled("non_existent") is True  # Default to True
        
        # Test with personalization disabled
        prefs.personalization.enabled = False
        assert prefs.is_feature_enabled("smart_ranking") is False  # All features off
    
    @pytest.mark.asyncio
    async def test_preference_migration(self):
        """Test migrating preferences when schema changes"""
        from src.services.preference_service import PreferenceService
        
        service = PreferenceService()
        
        # Simulate old preference format
        old_prefs = {
            "user_id": "test_user_123",
            "enable_personalization": True,  # Old field name
            "features": ["smart_ranking", "usual_orders"]  # Old format as list
        }
        
        # Migrate to new format
        migrated = await service.migrate_preferences(old_prefs)
        
        # Should have new structure
        assert migrated.personalization.enabled is True
        assert migrated.personalization.features["smart_ranking"] is True
        assert migrated.personalization.features["usual_orders"] is True
        # Other features should default to True
        assert migrated.personalization.features["dietary_filters"] is True