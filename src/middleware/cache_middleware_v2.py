"""
Enhanced Cache Middleware with Redis Feature Flag
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import json
import uuid
from typing import Callable, Optional
from src.cache.redis_feature import redis_feature, smart_redis_manager
import structlog

logger = structlog.get_logger()

class CacheMiddlewareV2(BaseHTTPMiddleware):
    """Middleware that gracefully handles Redis availability"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.redis = smart_redis_manager
        self.cache_stats = {
            "requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "redis_errors": 0
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with optional caching"""
        
        start_time = time.time()
        self.cache_stats["requests"] += 1
        
        # Extract user info
        user_id = request.headers.get("X-User-ID", "anonymous")
        user_uuid = request.headers.get("X-User-UUID", str(uuid.uuid4()))
        session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
        
        # Store in request state
        request.state.user_id = user_id
        request.state.user_uuid = user_uuid
        request.state.session_id = session_id
        request.state.redis_enabled = redis_feature.enabled
        
        # Only check cache if Redis is enabled and it's a GET search
        cached_response = None
        if redis_feature.enabled and request.method == "GET" and "/search" in request.url.path:
            query_params = dict(request.query_params)
            query = query_params.get("query", "")
            
            if query:
                try:
                    manager = await self.redis._get_manager()
                    cached_response = await manager.get_cached_response(
                        user_id=user_id,
                        query=query
                    )
                    
                    if cached_response:
                        self.cache_stats["cache_hits"] += 1
                        return Response(
                            content=json.dumps(cached_response),
                            media_type="application/json",
                            headers={
                                "X-Cache": "HIT",
                                "X-Redis-Enabled": str(redis_feature.enabled)
                            }
                        )
                    else:
                        self.cache_stats["cache_misses"] += 1
                        
                except Exception as e:
                    logger.error(f"Redis cache check failed: {e}")
                    self.cache_stats["redis_errors"] += 1
                    redis_feature.mark_degraded()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Log API call if Redis is enabled
        if redis_feature.enabled:
            try:
                manager = await self.redis._get_manager()
                await manager.log_api_call(
                    user_id=user_id,
                    endpoint=str(request.url.path),
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                    error=None if response.status_code < 400 else f"HTTP {response.status_code}"
                )
            except Exception as e:
                logger.error(f"Redis logging failed: {e}")
                self.cache_stats["redis_errors"] += 1
        
        # Add headers
        response.headers["X-Cache"] = "MISS" if not cached_response else "HIT"
        response.headers["X-Response-Time"] = f"{response_time_ms:.2f}ms"
        response.headers["X-Redis-Enabled"] = str(redis_feature.enabled)
        
        # Add cache stats periodically
        if self.cache_stats["requests"] % 100 == 0:
            logger.info(
                "Cache statistics",
                total_requests=self.cache_stats["requests"],
                cache_hits=self.cache_stats["cache_hits"],
                cache_misses=self.cache_stats["cache_misses"],
                hit_rate=self.cache_stats["cache_hits"] / max(1, self.cache_stats["cache_hits"] + self.cache_stats["cache_misses"]),
                redis_errors=self.cache_stats["redis_errors"],
                redis_enabled=redis_feature.enabled
            )
        
        return response

class SearchLoggingMiddlewareV2:
    """Search logging that works with or without Redis"""
    
    def __init__(self):
        self.redis = smart_redis_manager
    
    async def log_search_request(
        self,
        request_data: dict,
        response_data: dict,
        user_id: str,
        user_uuid: str,
        session_id: str,
        response_time_ms: float
    ) -> Optional[str]:
        """Log search request if Redis is enabled"""
        
        if not redis_feature.enabled:
            logger.debug("Redis disabled - skipping search logging")
            return None
        
        try:
            manager = await self.redis._get_manager()
            
            query = request_data.get("query", "")
            
            # Extract from response
            results = response_data.get("results", [])
            conversation = response_data.get("conversation", {})
            intent = conversation.get("intent", "unclear")
            confidence = conversation.get("confidence", 0.0)
            metadata = response_data.get("metadata", {})
            
            # Log to Redis
            search_id = await manager.log_search(
                user_id=user_id,
                user_uuid=user_uuid,
                session_id=session_id,
                query=query,
                intent=intent,
                confidence=confidence,
                results=results,
                response_time_ms=response_time_ms,
                metadata=metadata
            )
            
            # Cache response if appropriate
            if results and intent in ["product_search", "category_search"]:
                await manager.cache_response(
                    user_id=user_id,
                    query=query,
                    intent=intent,
                    response=response_data
                )
            
            # Track supplier queries
            for result in results:
                supplier = result.get("supplier", "")
                if supplier and supplier.lower() in query.lower():
                    await manager.track_supplier_query(supplier, query)
            
            return search_id
            
        except Exception as e:
            logger.error(f"Search logging failed: {e}")
            redis_feature.mark_degraded()
            return None

# Factory functions
def create_cache_middleware_v2(app: ASGIApp) -> CacheMiddlewareV2:
    """Create cache middleware with feature flag support"""
    return CacheMiddlewareV2(app)