# Redis Data Storage - Current Implementation

## What Data is Actually Being Stored

### 1. **Search Logs** (Permanent Storage for ML)
```redis
search:{search_id} → {
    "search_id": "search_1737939600_a1b2c3d4",
    "user_id": "user_123",
    "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "session_abc123",
    "query": "organic oat milk",
    "query_hash": "a1b2c3d4",  # MD5 hash for caching
    "intent": "product_search",
    "confidence": 0.95,
    "results_count": 12,
    "response_time_ms": 145.5,
    "timestamp": "2024-01-24T10:30:00Z",
    "date": "2024-01-24",
    "hour": 10,
    "metadata": "{\"search_config\": {\"alpha\": 0.5}}"
}
```

### 2. **User Search History** (Last 1000 searches)
```redis
user:{user_id}:searches → LIST [
    "search_1737939600_a1b2c3d4",
    "search_1737939500_b2c3d4e5",
    "search_1737939400_c3d4e5f6",
    ...
]
```

### 3. **Cached Search Results** (TTL: 1 hour)
```redis
user:{user_id}:cache:{query_hash} → {
    "results": [
        {
            "product_id": "123",
            "product_name": "Oatly Barista Edition",
            "price": 5.99,
            "supplier": "Oatly",
            "category": "Dairy Alternatives",
            ...
        }
    ],
    "metadata": {
        "total_count": 12,
        "search_time_ms": 145.5,
        "cache_hit": false
    },
    "conversation": {
        "intent": "product_search",
        "confidence": 0.95,
        "response": "I found 12 oat milk products for you"
    }
}
```

### 4. **Global Product Cache** (TTL: 1 hour)
```redis
product:cache:{query_hash} → {
    # Same structure as user cache
    # Shared across all users for common queries
}
```

### 5. **User Profile** (Permanent)
```redis
user:{user_id}:profile → {
    "user_id": "user_123",
    "user_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-01-20T10:00:00Z",
    "last_active": "2024-01-24T10:30:00Z",
    "total_searches": 156,
    "preferred_brands": "[]",  # JSON array (to be populated)
    "dietary_preferences": "[]",  # JSON array (to be populated)
    "avg_order_value": 0.0  # To be calculated
}
```

### 6. **API Call Logs** (TTL: 30 days)
```redis
call:{call_id} → {
    "call_id": "call_1737939600_x1y2z3",
    "user_id": "user_123",
    "endpoint": "/api/v1/search",
    "method": "POST",
    "status_code": 200,
    "response_time_ms": 145.5,
    "timestamp": "2024-01-24T10:30:00Z",
    "error": null
}
```

### 7. **Daily Search Index** (TTL: 90 days)
```redis
searches:daily:2024-01-24 → SET [
    "search_1737939600_a1b2c3d4",
    "search_1737939500_b2c3d4e5",
    ...
]
```

### 8. **Analytics Data**

#### Popular Products by Day (TTL: 90 days)
```redis
products:popular:2024-01-24 → ZSET {
    "a1b2c3d4": 45,  # query_hash: search_count
    "b2c3d4e5": 32,
    "c3d4e5f6": 28
}
```

#### Intent Statistics (TTL: 180 days)
```redis
intent:stats:2024-01-24 → {
    "product_search": 1523,
    "add_to_order": 234,
    "list_order": 156,
    "category_search": 89,
    "unclear": 12
}
```

#### Hourly Analytics (TTL: 180 days)
```redis
analytics:hourly:2024-01-24:10 → {
    "total_searches": 234,
    "unique_users": 89,
    "avg_response_time": 156.7,
    "error_rate": 0.02
}
```

### 9. **Supplier Query Tracking** (TTL: 180 days)
```redis
supplier:OrganicValley:queries:2024-01-24 → ZSET {
    "organic valley milk": 15,
    "organic valley yogurt": 8,
    "organic valley cheese": 5
}
```

## Data Flow When User Searches

1. **User searches "organic oat milk"**
   - Check cache: `user:123:cache:a1b2c3d4`
   - If miss, perform search
   - Log search: `search:search_1737939600_a1b2c3d4`
   - Update user history: `user:123:searches`
   - Cache results: `user:123:cache:a1b2c3d4`
   - Update analytics: `products:popular:2024-01-24`

2. **Same user searches again within 1 hour**
   - Cache hit! Return from `user:123:cache:a1b2c3d4`
   - Still log the search for ML training
   - Update counters

## Data NOT Currently Stored (Planned)

1. **Cart State** - Not implemented yet
2. **Order History** - Not implemented yet
3. **User Preferences Learning** - Collected but not processed
4. **Product Recommendations** - Not generated yet
5. **Session Context** - Basic only

## Storage Size Estimates

For 1000 daily active users:
- Search logs: ~50MB/day
- Cache data: ~100MB (rotating)
- User profiles: ~10MB
- Analytics: ~20MB/day
- **Total**: ~200MB active data + growing logs

## Privacy Considerations

- User UUIDs are stored (not PII)
- Search queries are stored (could be sensitive)
- No payment information
- No personal details (name, address, etc.)
- All data has TTL except search logs (for ML)

## Current Status in Production

Since Redis is **disabled** (`REDIS_ENABLED=false`), currently:
- ❌ No data is being stored
- ❌ No caching is happening
- ❌ No ML data collection
- ✅ System works fine without it
- ✅ Ready to enable when you deploy Redis