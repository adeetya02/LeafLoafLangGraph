"""
User preference service with optional Redis caching
Works with or without Redis - graceful fallback to in-memory storage
"""

import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import structlog

from src.models.user_preferences import (
    UserPreferences, 
    get_default_preferences,
    migrate_old_preferences
)

logger = structlog.get_logger()


class PreferenceStorage:
    """Base storage interface"""
    async def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError
    
    async def set(self, user_id: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        raise NotImplementedError
    
    async def delete(self, user_id: str) -> bool:
        raise NotImplementedError
    
    async def exists(self, user_id: str) -> bool:
        raise NotImplementedError


class InMemoryStorage(PreferenceStorage):
    """In-memory storage fallback when Redis is not available"""
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._expiry: Dict[str, datetime] = {}
        logger.info("Using in-memory preference storage")
    
    async def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        # Check expiry
        if user_id in self._expiry:
            if datetime.utcnow().timestamp() > self._expiry[user_id]:
                # Expired
                del self._storage[user_id]
                del self._expiry[user_id]
                return None
        
        return self._storage.get(user_id)
    
    async def set(self, user_id: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        self._storage[user_id] = data
        if ttl > 0:
            self._expiry[user_id] = datetime.utcnow().timestamp() + ttl
        return True
    
    async def delete(self, user_id: str) -> bool:
        if user_id in self._storage:
            del self._storage[user_id]
        if user_id in self._expiry:
            del self._expiry[user_id]
        return True
    
    async def exists(self, user_id: str) -> bool:
        return user_id in self._storage


class RedisStorage(PreferenceStorage):
    """Redis storage when available"""
    def __init__(self, redis_client):
        self.redis = redis_client
        logger.info("Using Redis for preference caching")
    
    def _key(self, user_id: str) -> str:
        return f"preferences:{user_id}"
    
    async def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            data = await self.redis.get(self._key(user_id))
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None
    
    async def set(self, user_id: str, data: Dict[str, Any], ttl: int = 3600) -> bool:
        try:
            return await self.redis.setex(
                self._key(user_id),
                ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
            return False
    
    async def delete(self, user_id: str) -> bool:
        try:
            return await self.redis.delete(self._key(user_id)) > 0
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
            return False
    
    async def exists(self, user_id: str) -> bool:
        try:
            return await self.redis.exists(self._key(user_id)) > 0
        except Exception as e:
            logger.warning(f"Redis exists failed: {e}")
            return False


class PreferenceService:
    """
    User preference service with optional Redis caching
    Falls back to in-memory storage if Redis is not available
    """
    
    def __init__(self, redis_client=None, graphiti_client=None):
        # Choose storage backend based on Redis availability
        if redis_client:
            self.storage = RedisStorage(redis_client)
            self.has_redis = True
        else:
            self.storage = InMemoryStorage()
            self.has_redis = False
        
        self.graphiti = graphiti_client
        logger.info(
            "PreferenceService initialized",
            has_redis=self.has_redis,
            has_graphiti=bool(graphiti_client)
        )
    
    async def get_preferences(self, user_id: str) -> UserPreferences:
        """Get user preferences with caching"""
        # Try cache first
        cached_data = await self.storage.get(user_id)
        if cached_data:
            logger.debug(f"Cache hit for user {user_id}")
            return UserPreferences(**cached_data)
        
        logger.debug(f"Cache miss for user {user_id}")
        
        # Try Graphiti if available
        if self.graphiti:
            try:
                graphiti_data = await self._get_from_graphiti(user_id)
                if graphiti_data:
                    prefs = UserPreferences(**graphiti_data)
                    # Cache for next time
                    await self._cache_preferences(prefs)
                    return prefs
            except Exception as e:
                logger.warning(f"Graphiti fetch failed: {e}")
        
        # Return defaults
        return get_default_preferences(user_id)
    
    async def save_preferences(self, preferences: UserPreferences) -> bool:
        """Save user preferences"""
        preferences.updated_at = datetime.utcnow()
        
        # Save to cache
        cached = await self._cache_preferences(preferences)
        
        # Save to Graphiti if available
        if self.graphiti:
            try:
                await self._save_to_graphiti(preferences)
            except Exception as e:
                logger.warning(f"Graphiti save failed: {e}")
        
        return cached
    
    async def update_feature(self, user_id: str, feature_name: str, enabled: bool) -> UserPreferences:
        """Update a single feature setting"""
        prefs = await self.get_preferences(user_id)
        prefs.update_feature(feature_name, enabled)
        await self.save_preferences(prefs)
        return prefs
    
    async def update_features(self, user_id: str, features: Dict[str, bool]) -> UserPreferences:
        """Update multiple feature settings"""
        prefs = await self.get_preferences(user_id)
        prefs.update_features(features)
        await self.save_preferences(prefs)
        return prefs
    
    async def update_privacy_settings(self, user_id: str, privacy: Dict[str, Any]) -> UserPreferences:
        """Update privacy settings"""
        prefs = await self.get_preferences(user_id)
        prefs.privacy.update(privacy)
        prefs.updated_at = datetime.utcnow()
        await self.save_preferences(prefs)
        return prefs
    
    async def delete_user_data(self, user_id: str) -> bool:
        """Delete all user preference data"""
        # Delete from cache
        cache_deleted = await self.storage.delete(user_id)
        
        # Delete from Graphiti if available
        if self.graphiti:
            try:
                await self._delete_from_graphiti(user_id)
            except Exception as e:
                logger.warning(f"Graphiti delete failed: {e}")
        
        return cache_deleted
    
    async def migrate_preferences(self, old_data: Dict[str, Any]) -> UserPreferences:
        """Migrate old preference format to new schema"""
        return migrate_old_preferences(old_data)
    
    # Private helper methods
    
    async def _cache_preferences(self, preferences: UserPreferences) -> bool:
        """Cache preferences with TTL"""
        data = preferences.model_dump()
        return await self.storage.set(preferences.user_id, data, ttl=3600)
    
    async def _get_from_graphiti(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get preferences from Graphiti memory"""
        if not self.graphiti:
            return None
        
        try:
            # Mock implementation - replace with actual Graphiti call
            memory = await self.graphiti.get_memory(user_id, "preferences")
            if memory:
                return memory.get("data")
        except Exception as e:
            logger.debug(f"Graphiti memory fetch error: {e}")
        return None
    
    async def _save_to_graphiti(self, preferences: UserPreferences) -> None:
        """Save preferences to Graphiti memory"""
        if not self.graphiti:
            return
        
        try:
            # Mock implementation - replace with actual Graphiti call
            await self.graphiti.add_memory(
                memory={
                    "user_id": preferences.user_id,
                    "memory_type": "preferences",
                    "personalization_preferences": preferences.model_dump(),
                    "enabled_features": preferences.get_enabled_features()
                }
            )
        except Exception as e:
            logger.debug(f"Graphiti memory save error: {e}")
    
    async def _delete_from_graphiti(self, user_id: str) -> None:
        """Delete preferences from Graphiti"""
        if not self.graphiti:
            return
        
        # Mock implementation - replace with actual Graphiti call
        await self.graphiti.delete_memory(user_id, "preferences")


# Global service instance (initialized on first use)
_preference_service: Optional[PreferenceService] = None


def get_preference_service(redis_client=None, graphiti_client=None) -> PreferenceService:
    """Get or create the preference service instance"""
    global _preference_service
    
    if _preference_service is None:
        _preference_service = PreferenceService(
            redis_client=redis_client,
            graphiti_client=graphiti_client
        )
    
    return _preference_service