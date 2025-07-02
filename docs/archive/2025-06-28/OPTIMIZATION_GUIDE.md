# LeafLoaf Performance Optimization Guide

## Current Performance Issues
- Average latency: 500-900ms (too slow)
- Gemma: 250-400ms per request
- Target: <300ms total

## Quick Wins to Implement NOW

### 1. Replace Supervisor with Optimized Version (Save ~150-200ms)
```python
# In src/core/graph.py, replace:
from src.agents.supervisor import SupervisorReactAgent
# With:
from src.agents.supervisor_optimized import OptimizedSupervisorAgent as SupervisorReactAgent
```

### 2. Reduce Weaviate Search Limit (Save ~30-50ms)
```python
# In src/config/constants.py
SEARCH_LIMIT_DEFAULT = 10  # Changed from 15
```

### 3. Add Response Caching Headers (Save network roundtrips)
```python
# In src/api/main.py, add to responses:
headers = {
    "Cache-Control": "public, max-age=60",  # Cache for 1 minute
    "X-Cache-Status": "hit" if cached else "miss"
}
```

### 4. Optimize Gemma Prompts (Save ~50ms)
```python
# Simplify prompt in gemma_client_v2.py
prompt = f"""Query: {query}
Return JSON: {{"intent": "...", "alpha": 0.X}}
Intents: product_search|add_to_order|remove_from_order|list_order
Alpha: 0.1=brand, 0.5=product, 0.8=explore"""
```

### 5. Skip Gemma for Obvious Queries
The optimized supervisor already does this with:
- Exact cache matches: 5-10ms
- Partial matches: 10-20ms
- Pattern matching: 20-50ms

## Expected Results After Optimization

### Before:
- Supervisor (Gemma): 250-400ms
- Weaviate: 130-160ms
- Network: 100-200ms
- **Total: 500-900ms**

### After:
- Supervisor (Optimized): 20-150ms
- Weaviate: 100-130ms
- Network: 80-150ms
- **Total: 200-350ms** ✅

## Deployment Steps

1. **Test Locally First**:
```bash
python3 test_optimized_supervisor.py
```

2. **Update Graph**:
```python
# src/core/graph.py
from src.agents.supervisor_optimized import OptimizedSupervisorAgent as SupervisorReactAgent
```

3. **Deploy**:
```bash
gcloud builds submit --tag gcr.io/leafloafai/leafloaf
gcloud run deploy leafloaf --image gcr.io/leafloafai/leafloaf --region us-central1
```

4. **Test Production**:
```bash
python3 test_optimized_performance.py
```

## Cache Entries to Add

Add more entries to INTENT_CACHE in supervisor_optimized.py based on your customers' common queries:
```python
INTENT_CACHE = {
    # Your customers' common queries
    "bell peppers": ("product_search", 0.9, 0.5),
    "3 pack": ("product_search", 0.85, 0.3),
    "give me": ("add_to_order", 0.8, 0.5),
    # Add more...
}
```

## Monitoring

After deployment, monitor:
1. Average latency should drop to 200-350ms
2. Cache hit rate should be >50%
3. Gemma timeouts should be <5%

## Next Steps if Still Slow

1. **Deploy Gemma 9B closer to Cloud Run** (same region)
2. **Use Cloud CDN** for static responses
3. **Implement Redis** for distributed caching
4. **Consider Cloud Tasks** for async operations