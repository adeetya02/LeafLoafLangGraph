"""
Redis Cache Design for LeafLoaf
================================

This module defines the Redis data structures and patterns for:
1. User search logging for ML
2. Response caching with TTL
3. User session management
4. Analytics data collection
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum

# Redis Key Patterns
class RedisKeys:
    """Centralized Redis key patterns"""
    
    # User-specific keys
    USER_PROFILE = "user:{user_id}:profile"
    USER_SEARCHES = "user:{user_id}:searches"  # List of search IDs
    USER_CACHE = "user:{user_id}:cache:{query_hash}"  # Cached responses
    USER_SESSION = "user:{user_id}:session:{session_id}"
    
    # Search logs for ML
    SEARCH_LOG = "search:{search_id}"  # Individual search details
    SEARCH_DAILY = "searches:daily:{date}"  # Set of search IDs for a day
    
    # Product cache
    PRODUCT_CACHE = "product:cache:{query_hash}"
    PRODUCT_POPULAR = "products:popular:{date}"  # Sorted set of popular products
    
    # Intent patterns
    INTENT_PATTERNS = "intent:patterns:{intent_type}"
    INTENT_STATS = "intent:stats:{date}"
    
    # Call logs
    CALL_LOG = "call:{call_id}"
    USER_CALLS = "user:{user_id}:calls"  # List of call IDs
    
    # Analytics
    ANALYTICS_HOURLY = "analytics:hourly:{date}:{hour}"
    SUPPLIER_QUERIES = "supplier:{supplier_id}:queries:{date}"

class SearchLogEntry:
    """Structure for search log entries"""
    
    def __init__(
        self,
        search_id: str,
        user_id: str,
        user_uuid: str,
        session_id: str,
        query: str,
        intent: str,
        confidence: float,
        results_count: int,
        response_time_ms: float,
        timestamp: datetime,
        metadata: Optional[Dict] = None
    ):
        self.search_id = search_id
        self.user_id = user_id
        self.user_uuid = user_uuid
        self.session_id = session_id
        self.query = query
        self.intent = intent
        self.confidence = confidence
        self.results_count = results_count
        self.response_time_ms = response_time_ms
        self.timestamp = timestamp
        self.metadata = metadata or {}
        
        # Derived fields
        self.query_hash = self._generate_query_hash(query)
        self.date = timestamp.strftime("%Y-%m-%d")
        self.hour = timestamp.hour
        
    def _generate_query_hash(self, query: str) -> str:
        """Generate consistent hash for query caching"""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for Redis storage"""
        return {
            "search_id": self.search_id,
            "user_id": self.user_id,
            "user_uuid": self.user_uuid,
            "session_id": self.session_id,
            "query": self.query,
            "query_hash": self.query_hash,
            "intent": self.intent,
            "confidence": self.confidence,
            "results_count": self.results_count,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "date": self.date,
            "hour": self.hour,
            "metadata": json.dumps(self.metadata)
        }

class CallLogEntry:
    """Structure for API call logs"""
    
    def __init__(
        self,
        call_id: str,
        user_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        timestamp: datetime,
        error: Optional[str] = None
    ):
        self.call_id = call_id
        self.user_id = user_id
        self.endpoint = endpoint
        self.method = method
        self.status_code = status_code
        self.response_time_ms = response_time_ms
        self.timestamp = timestamp
        self.error = error

class RedisSchema:
    """
    Redis Data Schema Documentation
    ==============================
    
    1. USER DATA COLLECTION
    -----------------------
    user:{user_id}:profile (HASH)
        - user_id: string
        - user_uuid: string
        - created_at: timestamp
        - last_active: timestamp
        - total_searches: int
        - preferred_brands: JSON array
        - dietary_preferences: JSON array
        - avg_order_value: float
        
    user:{user_id}:searches (LIST)
        - Stores search_ids in chronological order
        - Used to build user search history
        - Trimmed to last 1000 searches
        
    user:{user_id}:cache:{query_hash} (STRING)
        - Cached search results for this user
        - TTL: 1 hour (3600 seconds)
        - Stores full response JSON
        
    2. SEARCH LOGS FOR ML
    ---------------------
    search:{search_id} (HASH)
        - All fields from SearchLogEntry
        - Permanent storage for ML training
        - Includes: query, intent, timestamp, results, etc.
        
    searches:daily:{YYYY-MM-DD} (SET)
        - Set of all search_ids for a given day
        - Used for daily batch processing
        - TTL: 90 days
        
    3. PRODUCT CACHING
    ------------------
    product:cache:{query_hash} (STRING)
        - Global product search cache
        - TTL: 1 hour
        - Shared across all users
        
    products:popular:{YYYY-MM-DD} (ZSET)
        - Sorted set of product_ids by search frequency
        - Score = number of searches
        - Used for recommendations
        
    4. INTENT ANALYTICS
    -------------------
    intent:patterns:{intent_type} (HASH)
        - Common queries for each intent
        - Query pattern -> frequency
        - Updated in real-time
        
    intent:stats:{YYYY-MM-DD} (HASH)
        - Daily intent distribution
        - intent_type -> count
        - Used for monitoring
        
    5. API CALL LOGS
    ----------------
    call:{call_id} (HASH)
        - API call details
        - Status, latency, errors
        - TTL: 30 days
        
    user:{user_id}:calls (LIST)
        - User's API call history
        - Limited to last 100 calls
        
    6. ANALYTICS
    ------------
    analytics:hourly:{YYYY-MM-DD}:{HH} (HASH)
        - total_searches: int
        - unique_users: int
        - avg_response_time: float
        - error_rate: float
        - top_queries: JSON array
        
    supplier:{supplier_id}:queries:{YYYY-MM-DD} (ZSET)
        - Queries mentioning this supplier
        - Score = frequency
        - Used for supplier analytics
    """
    
    @staticmethod
    def get_ttl_settings():
        """TTL settings for different key types"""
        return {
            "user_cache": 3600,  # 1 hour
            "product_cache": 3600,  # 1 hour
            "session": 86400,  # 24 hours
            "daily_sets": 7776000,  # 90 days
            "call_logs": 2592000,  # 30 days
            "analytics": 15552000,  # 180 days
        }
    
    @staticmethod
    def get_data_pipeline():
        """Data pipeline for ML preparation"""
        return {
            "daily_jobs": [
                "aggregate_search_patterns",
                "compute_user_preferences",
                "identify_trending_products",
                "calculate_intent_accuracy"
            ],
            "weekly_jobs": [
                "export_training_data",
                "update_user_segments",
                "analyze_supplier_performance"
            ],
            "ml_features": [
                "user_search_history",
                "query_intent_patterns",
                "temporal_patterns",
                "product_affinity",
                "session_behavior"
            ]
        }

class CacheStrategy:
    """Caching strategies for different scenarios"""
    
    @staticmethod
    def should_cache_for_user(query: str, intent: str) -> bool:
        """Determine if query should be cached per user"""
        # Don't cache highly personalized queries
        non_cacheable_intents = ["list_order", "confirm_order", "update_order"]
        if intent in non_cacheable_intents:
            return False
        
        # Don't cache vague queries
        if len(query.split()) < 2:
            return False
            
        return True
    
    @staticmethod
    def should_use_global_cache(query: str, intent: str) -> bool:
        """Determine if query can use global cache"""
        # Use global cache for generic product searches
        cacheable_intents = ["product_search", "category_search"]
        if intent not in cacheable_intents:
            return False
            
        # Check if query contains user-specific terms
        personal_terms = ["my", "i", "me", "previous", "last", "again"]
        query_lower = query.lower()
        if any(term in query_lower for term in personal_terms):
            return False
            
        return True
    
    @staticmethod
    def generate_cache_key(user_id: str, query: str, use_global: bool = False) -> str:
        """Generate appropriate cache key"""
        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()[:16]
        
        if use_global:
            return f"product:cache:{query_hash}"
        else:
            return f"user:{user_id}:cache:{query_hash}"

# Example Redis operations
"""
# Store search log
search_entry = SearchLogEntry(
    search_id="search_123",
    user_id="user_456", 
    user_uuid="uuid_789",
    session_id="session_abc",
    query="organic oat milk",
    intent="product_search",
    confidence=0.95,
    results_count=12,
    response_time_ms=145.5,
    timestamp=datetime.now()
)

# Redis commands:
HSET search:search_123 <all fields from search_entry.to_dict()>
LPUSH user:user_456:searches search_123
SADD searches:daily:2024-01-24 search_123
EXPIRE user:user_456:cache:a1b2c3d4 3600

# Check cache before searching
cache_key = "user:user_456:cache:a1b2c3d4"
cached_result = GET cache_key
if cached_result:
    return json.loads(cached_result)
else:
    # Perform search
    result = search_products(query)
    # Cache result
    SET cache_key json.dumps(result) EX 3600
"""