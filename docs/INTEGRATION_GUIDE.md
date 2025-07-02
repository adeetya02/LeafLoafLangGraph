# Integration Guide: Flexible Data Capture

## Quick Integration

### 1. Update Search Endpoint

In `src/api/main.py`, modify the search endpoint:

```python
from src.api.search_with_ml import search_with_ml

@app.post("/api/v1/search")
async def search_products(request: SearchRequest, req: Request):
    # Your existing search logic
    initial_state = create_initial_state(request, calculated_alpha)
    
    # Execute search
    final_state = await search_graph.ainvoke(initial_state)
    
    # OLD: Build response directly
    # response = SearchResponse(...)
    
    # NEW: Use ML-enhanced search
    response = await search_with_ml(
        request_data=request.dict(),
        search_function=lambda r: build_search_response(final_state),
        req=req
    )
    
    return response
```

### 2. No Changes Needed When Redis Disabled

The system automatically:
- Skips Redis operations
- Uses Cloud Storage for data capture
- Returns results without delay
- No code changes required

### 3. Enable Features Gradually

```bash
# Stage 1: Basic data capture (current)
REDIS_ENABLED=false
# Captures to Cloud Storage only

# Stage 2: Add Redis for caching
REDIS_ENABLED=true
REDIS_URL=redis://your-redis:6379
# Adds real-time caching and personalization

# Stage 3: Add BigQuery for analytics
ENABLE_BIGQUERY=true
# Adds analytics and ML training data
```

## Data Flow Examples

### Example 1: Search without Redis
```
User searches "organic milk"
  │
  ├─> Search executes (150ms)
  ├─> Results returned immediately
  └─> Background: Data saved to Cloud Storage
```

### Example 2: Search with Redis
```
User searches "organic milk"
  │
  ├─> Check Redis cache (10ms)
  ├─> If hit: Return cached results
  ├─> If miss: Execute search (150ms)
  ├─> Get recommendations (parallel, max 500ms)
  ├─> Return enriched results
  └─> Background: Update all data stores
```

### Example 3: ML Timeout
```
User searches "organic milk"
  │
  ├─> Search executes (150ms)
  ├─> Try recommendations (times out at 500ms)
  ├─> Return results without recommendations
  └─> Background: Continue data capture
```

## Benefits

### 1. No Performance Impact
- Main search flow unchanged
- Data capture is async
- ML features are optional

### 2. Graceful Degradation
- Works without Redis
- Works without ML
- Works without BigQuery

### 3. Progressive Enhancement
- Start simple
- Add features as needed
- No big bang deployment

## Testing

### Test Data Capture
```bash
# Check if events are being captured
gsutil ls gs://leafloaf-user-data/events/
```

### Test with Mock ML
```python
# In tests, ML returns immediately
async def test_search_with_ml():
    response = await search_with_ml(
        {"query": "milk"},
        mock_search_function,
        mock_request
    )
    assert "results" in response
    # Recommendations may or may not be present
```

### Monitor Performance
```bash
# Check latency hasn't increased
curl -w "@curl-format.txt" https://your-api/api/v1/search
```

## Deployment Checklist

- [ ] Create Cloud Storage bucket
- [ ] Set bucket permissions
- [ ] Deploy with REDIS_ENABLED=false
- [ ] Verify data capture working
- [ ] Monitor performance metrics
- [ ] Enable Redis when ready
- [ ] Enable BigQuery when ready