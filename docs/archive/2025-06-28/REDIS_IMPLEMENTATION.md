# Redis Implementation for LeafLoaf

## Overview
Redis has been integrated into LeafLoaf for user data collection, caching, and ML data preparation.

## Key Features

### 1. User Search Logging
Every search is logged with:
- User ID and UUID
- Session ID
- Query and intent
- Response time
- Results count
- Timestamp

### 2. Response Caching
- **User-specific cache**: Personalized results cached for 1 hour
- **Global product cache**: Common queries cached across users
- **Smart caching**: Only caches appropriate queries (not orders/cart operations)

### 3. Data Collection for ML
Collects data for future ML features:
- Search patterns by user
- Intent distribution
- Popular products
- Supplier performance
- Temporal patterns

## Redis Data Structure

### User Data
```
user:{user_id}:profile          # User profile and preferences
user:{user_id}:searches         # Search history (last 1000)
user:{user_id}:cache:{hash}     # Cached search results
```

### Search Logs
```
search:{search_id}              # Individual search details
searches:daily:{date}           # Daily search index
```

### Analytics
```
products:popular:{date}         # Popular products by day
intent:stats:{date}            # Intent distribution
supplier:{id}:queries:{date}   # Supplier-specific queries
```

## Usage in Code

### API Integration
The Redis integration is automatic through middleware:

```python
# In src/api/main.py
@app.on_event("startup")
async def startup_event():
    await redis_manager.initialize()

@app.post("/api/v1/search")
async def search_products(request: SearchRequest, req: Request):
    # Automatic cache checking
    # Automatic logging after response
```

### Manual Usage
```python
from src.cache import redis_manager

# Log a search
await redis_manager.log_search(
    user_id="user123",
    user_uuid="uuid456",
    session_id="session789",
    query="organic milk",
    intent="product_search",
    confidence=0.95,
    results=products,
    response_time_ms=145.5
)

# Get cached response
cached = await redis_manager.get_cached_response(
    user_id="user123",
    query="organic milk"
)

# Export training data
training_data = await redis_manager.export_training_data(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 1, 31),
    intent_filter=["product_search", "add_to_order"]
)
```

## Deployment

### Local Development
```bash
# Start Redis locally
docker run -d -p 6379:6379 redis:alpine

# Set environment variable
export REDIS_URL="redis://localhost:6379"
```

### Google Cloud Production
```bash
# Create Memorystore Redis instance
gcloud redis instances create leafloaf-cache \
    --size=1 \
    --region=northamerica-northeast1 \
    --redis-version=redis_6_x

# Get connection info
gcloud redis instances describe leafloaf-cache \
    --region=northamerica-northeast1

# Update Cloud Run with Redis URL
gcloud run services update leafloaf \
    --update-env-vars REDIS_URL=redis://10.x.x.x:6379
```

## ML Data Pipeline

### Daily Export
```python
# Export daily data for training
from datetime import datetime, timedelta

yesterday = datetime.now() - timedelta(days=1)
data = await redis_manager.export_training_data(
    start_date=yesterday,
    end_date=yesterday
)

# Save to Cloud Storage for Gemma fine-tuning
```

### User Behavior Analysis
```python
# Get user search patterns
history = await redis_manager.get_user_search_history("user123", limit=50)

# Analyze intent patterns
intents = [h["intent"] for h in history]
intent_distribution = Counter(intents)
```

## Benefits

1. **Performance**: Sub-50ms cache hits for repeated queries
2. **Personalization**: User-specific caching and history
3. **ML Ready**: All data structured for training
4. **Scalability**: Redis handles millions of queries
5. **Analytics**: Real-time insights into usage patterns

## Next Steps

1. **Deploy Redis on GCP**:
   ```bash
   gcloud redis instances create leafloaf-cache --size=1 --region=northamerica-northeast1
   ```

2. **Update Cloud Run**:
   ```bash
   gcloud run services update leafloaf --update-env-vars REDIS_URL=<redis-url>
   ```

3. **Start collecting data** for Gemma fine-tuning

4. **Set up daily exports** to Cloud Storage

5. **Monitor cache performance** in Redis dashboard