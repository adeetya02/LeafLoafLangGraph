# Memory-Aware System Deployment Guide

## What We're Deploying

### 1. Memory-Aware Agents
- **Supervisor**: Uses routing patterns to improve decisions
- **Search Agent**: Integrates with GraphitiSearchEnhancer
- **Order Agent**: Suggests usual quantities from memory
- **Learning Loop**: Records user interactions for continuous improvement

### 2. Configurable Search Results
- API accepts `graphiti_mode`: enhance, supplement, both, off
- API accepts `show_all`: true/false for personalization override
- API accepts `source`: app/voice/web
- Dual results structure for UI flexibility

### 3. Enabled Features
- GraphitiSearchEnhancer in "supplement" mode
- Memory context with 100ms timeout
- Learning loop collecting feedback
- Click tracking endpoint

## Pre-Deployment Testing

```bash
# 1. Run local tests
python test_memory_aware_system.py

# 2. Quick production readiness check
python test_production_deploy.py
```

## Deployment Steps

### 1. Deploy to Production

```bash
# Deploy using Cloud Build
gcloud builds submit --config cloudbuild-secure.yaml

# Or direct deployment
gcloud run deploy leafloaf \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### 2. Verify Deployment

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe leafloaf --region us-central1 --format 'value(status.url)')

# Test health
curl $SERVICE_URL/health

# Test basic search
curl -X POST $SERVICE_URL/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "organic milk"}'

# Test with memory features
curl -X POST $SERVICE_URL/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "milk",
    "user_id": "demo-user",
    "graphiti_mode": "supplement",
    "source": "app"
  }'
```

## What's Enabled in Production

### GraphitiSearchEnhancer
- Mode: **supplement** (adds recommendations alongside regular results)
- Strength: 0.5 (moderate personalization)
- Max Recommendations: 5

### Memory Features
- Context timeout: 100ms (won't slow down requests)
- Learning batch size: 50 interactions
- Processing interval: 30 seconds

### Search Defaults
- Default limit: 20 products
- Default alpha: 0.5 (balanced semantic/keyword)

## API Examples

### 1. App Search with Personalization
```json
POST /api/v1/search
{
  "query": "milk",
  "user_id": "user-123",
  "session_id": "session-456",
  "graphiti_mode": "supplement",
  "source": "app"
}
```

### 2. Voice Search with Override
```json
POST /api/v1/search
{
  "query": "show me all milk options",
  "user_id": "user-123",
  "source": "voice"
}
// Gemma will detect override intent
```

### 3. Track Product Click
```json
POST /api/v1/track/click
{
  "user_id": "user-123",
  "query": "milk",
  "product": {
    "sku": "OATLY-001",
    "name": "Oatly Barista Edition"
  },
  "position": 0
}
```

## Monitoring

### Check Logs
```bash
# View recent logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=leafloaf" --limit 50

# Check for memory features
gcloud logging read "Memory context fetch" --limit 10
gcloud logging read "Graphiti enhancement applied" --limit 10
gcloud logging read "Recorded supervisor decision" --limit 10
```

### Key Metrics to Watch
- Response latency (should stay under 300ms)
- Memory context fetch success rate
- Learning loop processing rate
- GraphitiSearchEnhancer performance

## Rollback if Needed

If issues arise:

1. **Quick disable via environment**:
   ```bash
   gcloud run services update leafloaf \
     --update-env-vars GRAPHITI_SEARCH_MODE=off
   ```

2. **Revert to previous revision**:
   ```bash
   gcloud run services update-traffic leafloaf --to-revisions=PREVIOUS_REVISION=100
   ```

## Next Steps

Once deployed and verified:
1. Monitor performance for 24 hours
2. Check learning loop is collecting data
3. Verify memory patterns are building
4. Consider switching to "enhance" mode for stronger personalization
5. Complete remaining personalization features (7/10 done)

## Success Criteria

✅ API accepts new parameters
✅ No performance degradation
✅ Learning loop collecting feedback
✅ Memory context working
✅ Logs show features active
✅ Users can override personalization