"""
Cache Middleware for FastAPI
Integrates Redis caching and logging into the API flow
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import json
import uuid
from typing import Callable, Optional
from src.cache.redis_manager import redis_manager
import structlog

logger = structlog.get_logger()

class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for caching and logging requests"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.redis = redis_manager
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with caching and logging"""
        
        start_time = time.time()
        
        # Extract user info
        user_id = request.headers.get("X-User-ID", "anonymous")
        user_uuid = request.headers.get("X-User-UUID", str(uuid.uuid4()))
        session_id = request.headers.get("X-Session-ID", str(uuid.uuid4()))
        
        # Store in request state for use in endpoints
        request.state.user_id = user_id
        request.state.user_uuid = user_uuid
        request.state.session_id = session_id
        
        # Check cache for GET requests on search endpoint
        cached_response = None
        if request.method == "GET" and "/search" in request.url.path:
            query_params = dict(request.query_params)
            query = query_params.get("query", "")
            
            if query:
                cached_response = await self.redis.get_cached_response(
                    user_id=user_id,
                    query=query
                )
                
                if cached_response:
                    # Return cached response
                    return Response(
                        content=json.dumps(cached_response),
                        media_type="application/json",
                        headers={
                            "X-Cache": "HIT",
                            "X-Cache-TTL": str(self.redis.ttl_settings["user_cache"])
                        }
                    )
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000
        
        # Log API call
        await self.redis.log_api_call(
            user_id=user_id,
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            error=None if response.status_code < 400 else f"HTTP {response.status_code}"
        )
        
        # Add cache headers
        response.headers["X-Cache"] = "MISS" if not cached_response else "HIT"
        response.headers["X-Response-Time"] = f"{response_time_ms:.2f}ms"
        
        return response

class SearchLoggingMiddleware:
    """Specialized middleware for logging search requests"""
    
    def __init__(self, redis_manager):
        self.redis = redis_manager
    
    async def log_search_request(
        self,
        request_data: dict,
        response_data: dict,
        user_id: str,
        user_uuid: str,
        session_id: str,
        response_time_ms: float
    ):
        """Log search request and response"""
        
        query = request_data.get("query", "")
        
        # Extract from response
        results = response_data.get("results", [])
        conversation = response_data.get("conversation", {})
        intent = conversation.get("intent", "unclear")
        confidence = conversation.get("confidence", 0.0)
        metadata = response_data.get("metadata", {})
        
        # Log to Redis
        search_id = await self.redis.log_search(
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
            await self.redis.cache_response(
                user_id=user_id,
                query=query,
                intent=intent,
                response=response_data
            )
        
        # Track supplier queries
        for result in results:
            supplier = result.get("supplier", "")
            if supplier and supplier.lower() in query.lower():
                await self.redis.track_supplier_query(supplier, query)
        
        return search_id

# Factory function
def create_cache_middleware(app: ASGIApp) -> CacheMiddleware:
    """Create cache middleware instance"""
    return CacheMiddleware(app)