"""
User preference models for personalization
Redis-agnostic design - works with or without Redis
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum


class DietaryRestriction(str, Enum):
    """Dietary restrictions enum"""
    VEGAN = "vegan"
    VEGETARIAN = "vegetarian"
    GLUTEN_FREE = "gluten-free"
    KOSHER = "kosher"
    HALAL = "halal"
    DAIRY_FREE = "dairy-free"
    NUT_FREE = "nut-free"


class PersonalizationSettings(BaseModel):
    """Personalization feature settings"""
    enabled: bool = True
    features: Dict[str, bool] = Field(default_factory=lambda: {
        "smart_ranking": True,
        "usual_orders": True,
        "reorder_reminders": True,
        "dietary_filters": True,
        "cultural_awareness": True,
        "complementary_items": True,
        "quantity_memory": True,
        "budget_awareness": True,
        "household_inference": True,
        "seasonal_suggestions": True
    })


class PrivacySettings(BaseModel):
    """Privacy control settings"""
    data_retention_days: int = 365
    allow_pattern_learning: bool = True
    share_patterns_for_improvement: bool = False


class UserPreferences(BaseModel):
    """Complete user preference model"""
    user_id: str
    personalization: PersonalizationSettings = Field(default_factory=PersonalizationSettings)
    privacy: Dict[str, Any] = Field(default_factory=lambda: {
        "data_retention_days": 365,
        "allow_pattern_learning": True,
        "share_patterns_for_improvement": False
    })
    dietary_restrictions: List[DietaryRestriction] = Field(default_factory=list)
    cultural_preferences: List[str] = Field(default_factory=list)
    allergens: List[str] = Field(default_factory=list)
    override_auto_filter: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled"""
        if not self.personalization.enabled:
            return False
        return self.personalization.features.get(feature_name, True)
    
    def get_enabled_features(self) -> List[str]:
        """Get list of all enabled features"""
        if not self.personalization.enabled:
            return []
        return [
            feature for feature, enabled in self.personalization.features.items()
            if enabled
        ]
    
    def update_feature(self, feature_name: str, enabled: bool) -> None:
        """Update a single feature setting"""
        self.personalization.features[feature_name] = enabled
        self.updated_at = datetime.utcnow()
    
    def update_features(self, features: Dict[str, bool]) -> None:
        """Update multiple feature settings"""
        self.personalization.features.update(features)
        self.updated_at = datetime.utcnow()
    
    def disable_all_personalization(self) -> None:
        """Disable all personalization features"""
        self.personalization.enabled = False
        self.updated_at = datetime.utcnow()
    
    def enable_all_personalization(self) -> None:
        """Enable all personalization features"""
        self.personalization.enabled = True
        # Reset all features to True
        for feature in self.personalization.features:
            self.personalization.features[feature] = True
        self.updated_at = datetime.utcnow()
    
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )


def get_default_preferences(user_id: str) -> UserPreferences:
    """Get default preferences for a new user"""
    return UserPreferences(
        user_id=user_id,
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
                "budget_awareness": True,
                "household_inference": True,
                "seasonal_suggestions": True
            }
        ),
        privacy={
            "data_retention_days": 365,
            "allow_pattern_learning": True,
            "share_patterns_for_improvement": False
        }
    )


def migrate_old_preferences(old_data: Dict[str, Any]) -> UserPreferences:
    """Migrate old preference format to new schema"""
    user_id = old_data.get("user_id", "unknown")
    
    # Handle old format where features might be a list
    old_features = old_data.get("features", [])
    if isinstance(old_features, list):
        # Convert list to dict
        all_features = [
            "smart_ranking", "usual_orders", "reorder_reminders",
            "dietary_filters", "cultural_awareness", "complementary_items",
            "quantity_memory", "budget_awareness", "household_inference",
            "seasonal_suggestions"
        ]
        # Set features that were in the list to True
        features_dict = {}
        for feature in all_features:
            if feature in old_features:
                features_dict[feature] = True
            else:
                # Default missing features to True (opt-in by default)
                features_dict[feature] = True
    else:
        features_dict = old_features
    
    # Create new preferences
    return UserPreferences(
        user_id=user_id,
        personalization=PersonalizationSettings(
            enabled=old_data.get("enable_personalization", True),
            features=features_dict
        ),
        privacy=old_data.get("privacy", {
            "data_retention_days": 365,
            "allow_pattern_learning": True,
            "share_patterns_for_improvement": False
        })
    )