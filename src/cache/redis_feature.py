"""
Redis Feature Flag and Manager
Allows enabling/disabling Redis without code changes
"""

import os
from typing import Optional, Dict, Any
from datetime import datetime
import structlog
from src.config.settings import settings

logger = structlog.get_logger()

class RedisFeature:
    """Feature flag for Redis functionality"""
    
    def __init__(self):
        # Check multiple sources for Redis enable flag
        self._enabled = self._check_redis_enabled()
        self._degraded_mode = False
        self._last_health_check = None
        self._health_check_interval = 60  # seconds
        
    def _check_redis_enabled(self) -> bool:
        """Check if Redis should be enabled from various sources"""
        
        # 1. Environment variable (highest priority)
        env_redis = os.getenv("REDIS_ENABLED", "").lower()
        if env_redis in ["false", "0", "no", "off"]:
            logger.info("Redis disabled via REDIS_ENABLED env var")
            return False
        elif env_redis in ["true", "1", "yes", "on"]:
            logger.info("Redis enabled via REDIS_ENABLED env var")
            return True
        
        # 2. Check if Redis URL is configured
        if not settings.redis_url:
            logger.info("Redis disabled - no REDIS_URL configured")
            return False
        
        # 3. Check environment (disable in test by default)
        if settings.environment == "test":
            logger.info("Redis disabled in test environment")
            return False
        
        # 4. Default to enabled if URL exists
        logger.info(f"Redis enabled with URL: {settings.redis_url}")
        return True
    
    @property
    def enabled(self) -> bool:
        """Check if Redis is enabled and healthy"""
        if not self._enabled:
            return False
        
        # If in degraded mode, check if we should retry
        if self._degraded_mode:
            now = datetime.now()
            if self._last_health_check:
                time_since_check = (now - self._last_health_check).seconds
                if time_since_check < self._health_check_interval:
                    return False
            
            # Time to retry
            self._last_health_check = now
            # Health check will be done by RedisManager
            
        return not self._degraded_mode
    
    def disable(self):
        """Manually disable Redis"""
        logger.warning("Redis manually disabled")
        self._enabled = False
    
    def enable(self):
        """Manually enable Redis"""
        logger.info("Redis manually enabled")
        self._enabled = True
        self._degraded_mode = False
    
    def mark_degraded(self):
        """Mark Redis as degraded (temporary failure)"""
        logger.warning("Redis marked as degraded - entering fallback mode")
        self._degraded_mode = True
        self._last_health_check = datetime.now()
    
    def mark_healthy(self):
        """Mark Redis as healthy again"""
        logger.info("Redis marked as healthy - exiting fallback mode")
        self._degraded_mode = False

# Global feature flag instance
redis_feature = RedisFeature()

class MockRedisManager:
    """Mock Redis manager for when Redis is disabled"""
    
    async def initialize(self):
        """Mock initialization"""
        logger.info("Mock Redis initialized (Redis feature disabled)")
        return True
    
    async def close(self):
        """Mock close"""
        return True
    
    async def log_search(self, **kwargs) -> str:
        """Mock search logging"""
        return f"mock_search_{datetime.now().timestamp()}"
    
    async def get_cached_response(self, **kwargs) -> Optional[Dict]:
        """Mock cache get - always returns None"""
        return None
    
    async def cache_response(self, **kwargs):
        """Mock cache set - does nothing"""
        pass
    
    async def log_api_call(self, **kwargs) -> str:
        """Mock API call logging"""
        return f"mock_call_{datetime.now().timestamp()}"
    
    async def get_or_create_user(self, **kwargs) -> Dict:
        """Mock user creation"""
        return {
            "user_id": kwargs.get("user_id", "anonymous"),
            "created_at": datetime.now().isoformat(),
            "mock": True
        }
    
    async def export_training_data(self, **kwargs) -> list:
        """Mock data export"""
        return []
    
    async def get_user_search_history(self, **kwargs) -> list:
        """Mock search history"""
        return []
    
    async def track_supplier_query(self, **kwargs):
        """Mock supplier tracking"""
        pass

# Smart Redis Manager that respects feature flag
class SmartRedisManager:
    """Redis manager that automatically falls back when disabled"""
    
    def __init__(self):
        self._real_manager = None
        self._mock_manager = MockRedisManager()
        self._initialized = False
    
    async def _get_manager(self):
        """Get the appropriate manager based on feature flag"""
        if redis_feature.enabled and not self._real_manager:
            # Lazy load real Redis manager
            from src.cache.redis_manager import RedisManager
            self._real_manager = RedisManager()
            
            # Try to initialize
            try:
                await self._real_manager.initialize()
                redis_feature.mark_healthy()
            except Exception as e:
                logger.error(f"Redis initialization failed: {e}")
                redis_feature.mark_degraded()
                self._real_manager = None
        
        if redis_feature.enabled and self._real_manager:
            return self._real_manager
        else:
            return self._mock_manager
    
    async def __getattr__(self, name):
        """Proxy all method calls to the appropriate manager"""
        manager = await self._get_manager()
        return getattr(manager, name)

# Export the smart manager
smart_redis_manager = SmartRedisManager()