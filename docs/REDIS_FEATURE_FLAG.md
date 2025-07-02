# Redis Feature Flag Configuration

## Overview
Redis can be enabled/disabled without code changes using environment variables and automatic fallback.

## Configuration Options

### 1. Environment Variable Control

```bash
# Enable Redis (default if REDIS_URL is set)
export REDIS_ENABLED=true

# Disable Redis (force in-memory mode)
export REDIS_ENABLED=false

# Other values that work
REDIS_ENABLED=1     # Enable
REDIS_ENABLED=yes   # Enable
REDIS_ENABLED=on    # Enable

REDIS_ENABLED=0     # Disable
REDIS_ENABLED=no    # Disable
REDIS_ENABLED=off   # Disable
```

### 2. Automatic Detection

Redis is automatically **enabled** when:
- `REDIS_URL` environment variable is set
- Environment is not "test"
- `REDIS_ENABLED` is not explicitly set to false

Redis is automatically **disabled** when:
- No `REDIS_URL` is configured
- Environment is "test"
- `REDIS_ENABLED` is set to false

### 3. Graceful Degradation

If Redis fails during operation:
- System automatically enters "degraded mode"
- All operations continue using in-memory fallback
- Retry attempts every 60 seconds
- No user impact except cache misses

## Usage Examples

### Local Development (No Redis)
```bash
# Just run without Redis URL
python run.py
# Redis will be disabled automatically
```

### Local Development (With Redis)
```bash
# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Run with Redis
export REDIS_URL="redis://localhost:6379"
python run.py
```

### Production (Enable Redis)
```bash
# In Cloud Run
gcloud run services update leafloaf \
  --update-env-vars "REDIS_URL=redis://10.x.x.x:6379,REDIS_ENABLED=true"
```

### Production (Disable Redis Temporarily)
```bash
# Disable without removing URL
gcloud run services update leafloaf \
  --update-env-vars "REDIS_ENABLED=false"
```

### Testing Without Redis
```bash
# Force disable for testing
export REDIS_ENABLED=false
python -m pytest
```

## Health Check API

The `/health` endpoint shows Redis status:

```json
{
  "status": "healthy",
  "redis": {
    "enabled": true,
    "status": "healthy",  // or "disabled", "degraded", "mock_mode"
    "url_configured": true,
    "environment": "production"
  }
}
```

## Monitoring Redis Status

### Check if Redis is being used:
```bash
curl https://your-api.com/health | jq .redis
```

### Check cache hit rate:
Look for headers in responses:
- `X-Cache: HIT` or `X-Cache: MISS`
- `X-Redis-Enabled: true` or `false`

### View logs:
```bash
# Local
grep "Redis" app.log

# Cloud Run
gcloud run logs read leafloaf --filter="Redis"
```

## Fallback Behavior

When Redis is disabled or fails:

1. **Search Caching**: No caching, all searches hit the backend
2. **User History**: Not stored, no personalization
3. **Analytics**: No data collection for ML
4. **API Logging**: Basic in-memory logging only
5. **Performance**: Slightly slower due to no cache

## Best Practices

1. **Development**: Run without Redis for simplicity
2. **Staging**: Test with Redis enabled
3. **Production**: Always enable Redis with monitoring
4. **Incidents**: Can disable Redis as emergency measure

## Testing Redis Toggle

```bash
# Start with Redis enabled
export REDIS_URL="redis://localhost:6379"
export REDIS_ENABLED=true
python run.py

# In another terminal, test
curl http://localhost:8080/health

# Disable Redis
export REDIS_ENABLED=false
# Restart app

# Test again - should show disabled
curl http://localhost:8080/health
```

## Troubleshooting

### Redis shows "degraded"
- Check Redis server is running
- Verify network connectivity
- Check Redis URL is correct
- Look at logs for specific errors

### Cache not working
- Verify Redis is enabled in health check
- Check `X-Redis-Enabled` header
- Look for cache-related log entries

### High memory usage
- Redis might be disabled, causing in-memory caching
- Check health endpoint for Redis status

## Performance Impact

| Scenario | Search Latency | Cache Hit Rate | Memory Usage |
|----------|---------------|----------------|--------------|
| Redis Enabled | 100-150ms | 30-50% | Low |
| Redis Disabled | 150-200ms | 0% | Medium |
| Redis Degraded | 150-200ms | 0% | Medium |

## Deployment Checklist

- [ ] Decide Redis strategy for environment
- [ ] Set REDIS_URL if using Redis  
- [ ] Set REDIS_ENABLED if forcing on/off
- [ ] Test health endpoint shows correct status
- [ ] Monitor cache hit rates
- [ ] Set up alerts for Redis failures