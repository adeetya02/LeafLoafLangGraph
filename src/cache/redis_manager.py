"""
Redis Manager Implementation for LeafLoaf
"""

import redis
from redis import asyncio as aioredis
import json
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import structlog
from src.config.settings import settings
from src.cache.redis_design import (
    RedisKeys, SearchLogEntry, CallLogEntry, 
    CacheStrategy, RedisSchema
)
import uuid

logger = structlog.get_logger()

class RedisManager:
    """Manages all Redis operations for LeafLoaf"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.redis_url or "redis://localhost:6379"
        self.redis_client = None
        self.async_client = None
        self.ttl_settings = RedisSchema.get_ttl_settings()
        
    async def initialize(self):
        """Initialize Redis connections"""
        try:
            self.async_client = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.async_client.ping()
            logger.info(f"Redis connected: {self.redis_url}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    async def close(self):
        """Close Redis connections"""
        if self.async_client:
            await self.async_client.close()
    
    # ===== USER SEARCH LOGGING =====
    
    async def log_search(
        self,
        user_id: str,
        user_uuid: str,
        session_id: str,
        query: str,
        intent: str,
        confidence: float,
        results: List[Dict],
        response_time_ms: float,
        metadata: Optional[Dict] = None
    ) -> str:
        """Log a user search for ML training"""
        
        # Generate search ID
        search_id = f"search_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        
        # Create search entry
        search_entry = SearchLogEntry(
            search_id=search_id,
            user_id=user_id,
            user_uuid=user_uuid,
            session_id=session_id,
            query=query,
            intent=intent,
            confidence=confidence,
            results_count=len(results),
            response_time_ms=response_time_ms,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        # Store in Redis
        pipe = self.async_client.pipeline()
        
        # 1. Store search details
        search_key = RedisKeys.SEARCH_LOG.format(search_id=search_id)
        pipe.hset(search_key, mapping=search_entry.to_dict())
        
        # 2. Add to user's search history
        user_searches_key = RedisKeys.USER_SEARCHES.format(user_id=user_id)
        pipe.lpush(user_searches_key, search_id)
        pipe.ltrim(user_searches_key, 0, 999)  # Keep last 1000 searches
        
        # 3. Add to daily set
        daily_key = RedisKeys.SEARCH_DAILY.format(date=search_entry.date)
        pipe.sadd(daily_key, search_id)
        pipe.expire(daily_key, self.ttl_settings["daily_sets"])
        
        # 4. Update user profile
        await self._update_user_profile(pipe, user_id, user_uuid)
        
        # 5. Update analytics
        await self._update_analytics(pipe, search_entry)
        
        # Execute pipeline
        await pipe.execute()
        
        logger.info(f"Search logged: {search_id} for user {user_id}")
        return search_id
    
    # ===== CACHING =====
    
    async def get_cached_response(
        self, 
        user_id: str, 
        query: str,
        intent: Optional[str] = None
    ) -> Optional[Dict]:
        """Get cached response for a query"""
        
        # Determine caching strategy
        use_global = False
        if intent:
            use_global = CacheStrategy.should_use_global_cache(query, intent)
        
        # Generate cache key
        cache_key = CacheStrategy.generate_cache_key(user_id, query, use_global)
        
        # Check cache
        cached = await self.async_client.get(cache_key)
        if cached:
            logger.info(f"Cache hit: {cache_key}")
            return json.loads(cached)
        
        return None
    
    async def cache_response(
        self,
        user_id: str,
        query: str,
        intent: str,
        response: Dict,
        ttl: Optional[int] = None
    ):
        """Cache a search response"""
        
        # Check if should cache
        should_cache_user = CacheStrategy.should_cache_for_user(query, intent)
        should_cache_global = CacheStrategy.should_use_global_cache(query, intent)
        
        if not (should_cache_user or should_cache_global):
            return
        
        ttl = ttl or self.ttl_settings["user_cache"]
        response_json = json.dumps(response)
        
        pipe = self.async_client.pipeline()
        
        # Cache for user
        if should_cache_user:
            user_cache_key = CacheStrategy.generate_cache_key(user_id, query, False)
            pipe.setex(user_cache_key, ttl, response_json)
        
        # Cache globally
        if should_cache_global:
            global_cache_key = CacheStrategy.generate_cache_key(user_id, query, True)
            pipe.setex(global_cache_key, ttl, response_json)
        
        await pipe.execute()
        logger.info(f"Response cached for query: {query[:50]}...")
    
    # ===== CALL LOGGING =====
    
    async def log_api_call(
        self,
        user_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        error: Optional[str] = None
    ) -> str:
        """Log an API call"""
        
        call_id = f"call_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:8]}"
        
        call_entry = CallLogEntry(
            call_id=call_id,
            user_id=user_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            timestamp=datetime.now(),
            error=error
        )
        
        pipe = self.async_client.pipeline()
        
        # Store call details
        call_key = RedisKeys.CALL_LOG.format(call_id=call_id)
        pipe.hset(call_key, mapping=call_entry.__dict__)
        pipe.expire(call_key, self.ttl_settings["call_logs"])
        
        # Add to user's call history
        user_calls_key = RedisKeys.USER_CALLS.format(user_id=user_id)
        pipe.lpush(user_calls_key, call_id)
        pipe.ltrim(user_calls_key, 0, 99)  # Keep last 100 calls
        
        await pipe.execute()
        return call_id
    
    # ===== USER MANAGEMENT =====
    
    async def get_or_create_user(self, user_id: str, user_uuid: str) -> Dict:
        """Get or create user profile"""
        
        profile_key = RedisKeys.USER_PROFILE.format(user_id=user_id)
        profile = await self.async_client.hgetall(profile_key)
        
        if not profile:
            # Create new profile
            profile = {
                "user_id": user_id,
                "user_uuid": user_uuid,
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat(),
                "total_searches": 0,
                "preferred_brands": "[]",
                "dietary_preferences": "[]",
                "avg_order_value": 0.0
            }
            await self.async_client.hset(profile_key, mapping=profile)
            logger.info(f"Created new user profile: {user_id}")
        
        return profile
    
    async def _update_user_profile(self, pipe, user_id: str, user_uuid: str):
        """Update user profile stats"""
        profile_key = RedisKeys.USER_PROFILE.format(user_id=user_id)
        pipe.hset(profile_key, "last_active", datetime.now().isoformat())
        pipe.hincrby(profile_key, "total_searches", 1)
    
    # ===== ANALYTICS =====
    
    async def _update_analytics(self, pipe, search_entry: SearchLogEntry):
        """Update analytics data"""
        
        # Hourly analytics
        hourly_key = RedisKeys.ANALYTICS_HOURLY.format(
            date=search_entry.date,
            hour=search_entry.hour
        )
        pipe.hincrby(hourly_key, "total_searches", 1)
        pipe.expire(hourly_key, self.ttl_settings["analytics"])
        
        # Intent stats
        intent_key = RedisKeys.INTENT_STATS.format(date=search_entry.date)
        pipe.hincrby(intent_key, search_entry.intent, 1)
        pipe.expire(intent_key, self.ttl_settings["analytics"])
        
        # Popular products (if product search)
        if search_entry.intent == "product_search" and search_entry.results_count > 0:
            popular_key = RedisKeys.PRODUCT_POPULAR.format(date=search_entry.date)
            pipe.zincrby(popular_key, 1, search_entry.query_hash)
            pipe.expire(popular_key, self.ttl_settings["analytics"])
    
    # ===== ML DATA EXPORT =====
    
    async def export_training_data(
        self, 
        start_date: datetime,
        end_date: datetime,
        intent_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """Export search data for ML training"""
        
        training_data = []
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_key = RedisKeys.SEARCH_DAILY.format(date=date_str)
            
            # Get all search IDs for the day
            search_ids = await self.async_client.smembers(daily_key)
            
            for search_id in search_ids:
                search_key = RedisKeys.SEARCH_LOG.format(search_id=search_id)
                search_data = await self.async_client.hgetall(search_key)
                
                if search_data:
                    # Apply intent filter if specified
                    if intent_filter and search_data.get("intent") not in intent_filter:
                        continue
                    
                    # Parse metadata
                    if "metadata" in search_data:
                        search_data["metadata"] = json.loads(search_data["metadata"])
                    
                    training_data.append(search_data)
            
            current_date += timedelta(days=1)
        
        logger.info(f"Exported {len(training_data)} training examples")
        return training_data
    
    # ===== SUPPLIER ANALYTICS =====
    
    async def track_supplier_query(self, supplier_id: str, query: str):
        """Track queries mentioning a supplier"""
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        supplier_key = RedisKeys.SUPPLIER_QUERIES.format(
            supplier_id=supplier_id,
            date=date_str
        )
        
        await self.async_client.zincrby(supplier_key, 1, query)
        await self.async_client.expire(supplier_key, self.ttl_settings["analytics"])
    
    # ===== UTILITY METHODS =====
    
    async def get_user_search_history(
        self, 
        user_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """Get user's recent search history"""
        
        searches_key = RedisKeys.USER_SEARCHES.format(user_id=user_id)
        search_ids = await self.async_client.lrange(searches_key, 0, limit - 1)
        
        history = []
        for search_id in search_ids:
            search_key = RedisKeys.SEARCH_LOG.format(search_id=search_id)
            search_data = await self.async_client.hgetall(search_key)
            if search_data:
                history.append(search_data)
        
        return history
    
    async def get_popular_queries(self, date: Optional[str] = None) -> List[tuple]:
        """Get popular queries for a date"""
        
        date = date or datetime.now().strftime("%Y-%m-%d")
        popular_key = RedisKeys.PRODUCT_POPULAR.format(date=date)
        
        # Get top 20 with scores
        popular = await self.async_client.zrevrange(
            popular_key, 0, 19, withscores=True
        )
        
        return popular

# Singleton instance
redis_manager = RedisManager()