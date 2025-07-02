# Redis Cache Structure Design for LeafLoaf

## Overview
Comprehensive Redis schema for search optimization, cart tracking, and ML data collection with graceful fallback.

## 1. Search & Intent Optimization

### User + Query Cache
```redis
# User-specific search results
user:{user_id}:search:{query_hash} → {
    "query": "organic milk",
    "normalized_query": "organic milk",  # cleaned/normalized
    "intent": "product_search",
    "confidence": 0.95,
    "results": [...],
    "result_count": 12,
    "filters_applied": {},
    "search_config": {"alpha": 0.3},
    "timestamp": "2024-01-24T10:30:00Z",
    "ttl": 3600
}

# User search patterns (for intent learning)
user:{user_id}:search:patterns → ZSET {
    "organic milk": 5,      # score = frequency
    "oat milk": 3,
    "gluten free bread": 2
}

# User intent history
user:{user_id}:intents → LIST [
    {"query": "milk", "intent": "product_search", "timestamp": "..."},
    {"query": "add 2", "intent": "add_to_order", "timestamp": "..."}
]
```

### Global Query Intelligence
```redis
# Query intent mapping (learned from all users)
query:intent:{query_hash} → {
    "query": "organic milk",
    "intents": {
        "product_search": 0.85,
        "category_browse": 0.10,
        "brand_search": 0.05
    },
    "common_filters": ["organic", "dairy"],
    "avg_alpha": 0.3
}

# Query performance metrics
query:metrics:{query_hash} → {
    "avg_response_time": 145.5,
    "cache_hit_rate": 0.75,
    "result_click_rate": 0.65,
    "zero_result_rate": 0.02
}
```

## 2. User + Product Interactions

### Personalized Product Data
```redis
# User-specific product views
user:{user_id}:product:{product_id} → {
    "view_count": 5,
    "last_viewed": "2024-01-24T10:30:00Z",
    "added_to_cart": 3,
    "purchased": 2,
    "avg_quantity": 2.5,
    "preferred_size": "1 gallon",
    "rating": 4.5
}

# User product preferences
user:{user_id}:preferences:products → ZSET {
    "product_123": 10,    # score = affinity score
    "product_456": 8,
    "product_789": 6
}

# Product interaction history
user:{user_id}:products:history → LIST [
    {
        "product_id": "123",
        "action": "view|add_cart|purchase|rate",
        "timestamp": "...",
        "context": {"from_search": "organic milk", "session": "..."}
    }
]
```

### Product Recommendations Cache
```redis
# Personalized recommendations
user:{user_id}:recommendations → {
    "based_on": ["purchase_history", "view_history", "cart_patterns"],
    "products": [
        {"id": "123", "score": 0.95, "reason": "frequently_bought"},
        {"id": "456", "score": 0.87, "reason": "similar_to_purchased"}
    ],
    "generated_at": "2024-01-24T10:00:00Z",
    "ttl": 3600
}
```

## 3. Cart Behavior Tracking

### Active Cart State
```redis
# Current cart contents
user:{user_id}:cart:current → {
    "cart_id": "cart_abc123",
    "created_at": "2024-01-24T10:00:00Z",
    "updated_at": "2024-01-24T10:30:00Z",
    "items": [
        {
            "product_id": "123",
            "quantity": 2,
            "added_at": "2024-01-24T10:15:00Z",
            "price": 5.99,
            "from_search": "organic milk"
        }
    ],
    "total_value": 11.98,
    "item_count": 2
}

# Cart modification history
user:{user_id}:cart:history → LIST [
    {
        "action": "add|remove|update|clear",
        "product_id": "123",
        "quantity_change": 2,
        "timestamp": "...",
        "cart_value_after": 11.98
    }
]
```

### Cart Analytics
```redis
# Abandoned cart tracking
user:{user_id}:cart:abandoned → LIST [
    {
        "cart_id": "cart_xyz789",
        "abandoned_at": "2024-01-23T15:00:00Z",
        "value": 45.67,
        "items": [...],
        "session_duration": 1800,
        "last_action": "add_item"
    }
]

# Cart conversion metrics
user:{user_id}:cart:metrics → {
    "total_carts": 25,
    "completed_carts": 18,
    "abandoned_carts": 7,
    "avg_cart_value": 67.89,
    "avg_items_per_cart": 8.5,
    "conversion_rate": 0.72,
    "common_abandoned_items": ["product_123", "product_456"]
}

# Global cart patterns
analytics:cart:patterns:{date} → {
    "total_carts_created": 1523,
    "total_completed": 1098,
    "total_abandoned": 425,
    "peak_hours": [11, 12, 18, 19],
    "avg_time_to_complete": 1200,  # seconds
    "abandonment_reasons": {
        "browsing_only": 0.4,
        "price_sensitivity": 0.3,
        "found_elsewhere": 0.2,
        "technical_issues": 0.1
    }
}
```

### Cart Recovery
```redis
# Cart recovery tokens
cart:recovery:{token} → {
    "user_id": "user_123",
    "cart_id": "cart_abc123",
    "expires_at": "2024-01-25T10:00:00Z",
    "items_snapshot": [...],
    "recovery_incentive": {"type": "discount", "value": 10}
}

# Recovery attempts
user:{user_id}:cart:recovery:attempts → LIST [
    {
        "cart_id": "cart_abc123",
        "attempted_at": "2024-01-24T16:00:00Z",
        "method": "email|sms|push",
        "clicked": true,
        "converted": false
    }
]
```

## 4. Session Management

### Session State
```redis
# Active session
session:{session_id} → {
    "user_id": "user_123",
    "started_at": "2024-01-24T10:00:00Z",
    "last_activity": "2024-01-24T10:30:00Z",
    "page_views": 15,
    "searches": 5,
    "cart_modifications": 3,
    "device": "mobile",
    "entry_point": "search",
    "referrer": "google"
}

# Session search context
session:{session_id}:context → {
    "recent_queries": ["milk", "bread", "eggs"],
    "recent_intents": ["product_search", "add_to_order"],
    "categories_browsed": ["dairy", "bakery"],
    "price_range": [2.99, 15.99],
    "brands_viewed": ["Organic Valley", "Horizon"]
}
```

## 5. ML Training Data Collection

### Search Training Data
```redis
# Daily search logs for ML
ml:searches:{date} → SET [
    "search_id_1",
    "search_id_2",
    ...
]

# Individual search record
ml:search:{search_id} → {
    "user_id": "user_123",
    "query": "organic milk",
    "intent": "product_search",
    "results_shown": 12,
    "results_clicked": ["product_123", "product_456"],
    "time_to_click": 3.5,
    "converted": true,
    "session_context": {...}
}
```

### User Behavior Patterns
```redis
# User journey tracking
ml:user:{user_id}:journeys → LIST [
    {
        "journey_id": "journey_123",
        "start": "search",
        "steps": ["search", "view_product", "add_cart", "checkout"],
        "duration": 1800,
        "completed": true,
        "value": 67.89
    }
]

# Feature vectors for ML
ml:user:{user_id}:features → {
    "avg_session_duration": 1200,
    "search_frequency": 2.5,  # per session
    "category_preferences": {"dairy": 0.3, "organic": 0.5},
    "price_sensitivity": 0.7,
    "brand_loyalty": {"Organic Valley": 0.8},
    "cart_abandonment_rate": 0.2,
    "preferred_shopping_time": "evening",
    "last_updated": "2024-01-24T10:00:00Z"
}
```

## 6. Fallback Strategy

### Redis Availability Check
```redis
# Health check key
health:redis → "OK" (TTL: 10 seconds)
```

### Fallback Behavior
```python
class CacheManager:
    def __init__(self):
        self.redis_available = True
        self.local_cache = {}  # In-memory fallback
        
    async def get(self, key):
        if self.redis_available:
            try:
                return await redis.get(key)
            except RedisError:
                self.redis_available = False
                self.schedule_reconnect()
        
        # Fallback to local cache
        return self.local_cache.get(key)
    
    async def set(self, key, value, ttl=3600):
        if self.redis_available:
            try:
                await redis.setex(key, ttl, value)
            except RedisError:
                self.redis_available = False
        
        # Always update local cache
        self.local_cache[key] = value
```

## 7. TTL Strategy

```yaml
ttl_settings:
  # Search & Intent
  user_search_cache: 3600        # 1 hour
  query_intent_mapping: 86400    # 24 hours
  search_patterns: 604800        # 7 days
  
  # Product & User
  user_product_interaction: 2592000  # 30 days
  recommendations: 3600              # 1 hour
  
  # Cart
  active_cart: 86400            # 24 hours
  abandoned_cart: 604800        # 7 days (for recovery)
  cart_metrics: 2592000         # 30 days
  
  # Session
  active_session: 3600          # 1 hour
  session_context: 86400        # 24 hours
  
  # ML Data
  search_logs: null             # Permanent
  user_features: 604800         # 7 days (regenerated)
  training_data: null           # Permanent
```

## 8. Key Naming Convention

```
Pattern: {scope}:{entity_id}:{data_type}:{optional_qualifier}

Examples:
- user:123:search:abc123
- user:123:cart:current
- session:xyz:context
- ml:search:search_456
- analytics:cart:patterns:2024-01-24
```

## 9. Data Access Patterns

### Read Patterns
1. **Cache-aside**: Check cache → miss → fetch → update cache
2. **Read-through**: Automatic loading on cache miss
3. **Refresh-ahead**: Proactive refresh before expiry

### Write Patterns
1. **Write-through**: Write to cache and database
2. **Write-behind**: Write to cache, async to database
3. **Write-around**: Write to database, invalidate cache

## 10. Performance Considerations

- Use pipeline for batch operations
- Implement connection pooling
- Monitor memory usage
- Set up eviction policies (LRU)
- Use Redis Cluster for scaling
- Implement circuit breakers