# Staging Environment Guide

## Overview

Staging is a complete mirror of production with:
- ✅ Same infrastructure (Cloud Run, Weaviate, Spanner)
- ✅ NO hardcoded values
- ✅ Automated testing
- ✅ Lower resource allocation for cost savings

## Quick Deploy

```bash
# One command to deploy to staging
./deploy-staging.sh
```

## Environment Differences

| Aspect | Production | Staging |
|--------|------------|---------|
| Memory | 2Gi | 1Gi |
| CPU | 2 | 1 |
| Concurrency | 100 | 50 |
| Environment | production | staging |
| LangSmith Project | leafandloaf-production | leafandloaf-staging |
| Log Level | info | debug |

## Staging Workflow

### 1. Local Development
```bash
# Test locally
python run.py

# Run tests
python run_all_personalization_tests.py
```

### 2. Deploy to Staging
```bash
# Deploy with automated tests
./deploy-staging.sh

# This will:
# - Run basic tests
# - Build and push image
# - Deploy to Cloud Run
# - Run smoke tests
# - Display staging URL
```

### 3. Test in Staging
```bash
# Comprehensive staging tests
python test_staging.py

# Manual testing
curl https://leafloaf-staging-xxx.a.run.app/health
```

### 4. Promote to Production
```bash
# If staging tests pass
./deploy-production.sh
```

## Staging Features

### 1. Same Weaviate Instance (Optional)
By default, staging uses the same Weaviate instance as production. To use a separate instance:

1. Create `.env.staging.yaml` from template
2. Set different Weaviate credentials
3. Run `./deploy-staging.sh`

### 2. Debug Logging
Staging has `LOG_LEVEL=debug` for detailed troubleshooting:
- All LLM prompts and responses
- Detailed timing information
- Memory operation logs
- Graphiti entity extraction details

### 3. Experimental Features
Set `ENABLE_EXPERIMENTAL_FEATURES=true` to test:
- New personalization algorithms
- Beta LLM models
- Experimental search strategies

## Testing in Staging

### Automated Tests
The deployment runs these automatically:
1. Basic health checks
2. Search functionality
3. Smoke tests

### Manual Test Scenarios

#### 1. Basic Search
```bash
curl -X POST https://your-staging-url/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "organic milk", "limit": 5}'
```

#### 2. Personalization
```bash
# First search (no personalization)
curl -X POST https://your-staging-url/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "milk", "user_id": "test-user-123"}'

# Add to cart
curl -X POST https://your-staging-url/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "add oat milk to cart", "user_id": "test-user-123", "session_id": "test-session"}'

# Second search (should show personalization)
curl -X POST https://your-staging-url/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "milk", "user_id": "test-user-123"}'
```

#### 3. Memory Testing
```bash
# Search with session
curl -X POST https://your-staging-url/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "show me gluten free options", "session_id": "test-session-456"}'

# Follow-up in same session
curl -X POST https://your-staging-url/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what about bread?", "session_id": "test-session-456"}'
```

## Monitoring Staging

### Logs
```bash
# Stream logs
gcloud run logs tail leafloaf-staging --region us-central1

# View in console
https://console.cloud.google.com/run/detail/us-central1/leafloaf-staging/logs
```

### Metrics
- Response times
- Error rates
- Memory usage
- CPU usage

### LangSmith Tracing
View traces at: https://smith.langchain.com
- Project: `leafandloaf-staging`
- Filter by environment tag

## Troubleshooting

### Issue: Search returns no results
```bash
# Check health endpoint
curl https://your-staging-url/health

# Look for:
# - "weaviate": "connected"
# - "environment": "staging"
```

### Issue: Slow performance
```bash
# Check resource allocation
gcloud run services describe leafloaf-staging \
  --region us-central1 \
  --format "value(spec.template.spec.containers[0].resources)"
```

### Issue: Deployment fails
```bash
# Check Cloud Build logs
gcloud builds list --limit 5

# Get detailed logs
gcloud builds log <BUILD_ID>
```

## Rollback Staging

```bash
# List revisions
gcloud run revisions list \
  --service leafloaf-staging \
  --region us-central1

# Rollback to previous
gcloud run services update-traffic leafloaf-staging \
  --to-revisions <PREVIOUS_REVISION>=100 \
  --region us-central1
```

## Best Practices

1. **Always test in staging first**
   - New features
   - Configuration changes
   - Dependency updates

2. **Keep staging close to production**
   - Same APIs (Weaviate, Spanner)
   - Same authentication flow
   - Similar data

3. **Monitor staging actively**
   - Set up alerts for errors
   - Track performance metrics
   - Review logs regularly

4. **Clean up old revisions**
   ```bash
   # List old revisions
   gcloud run revisions list \
     --service leafloaf-staging \
     --region us-central1 \
     --filter "metadata.creationTimestamp<'-P7D'"
   
   # Delete old ones
   gcloud run revisions delete <OLD_REVISION> \
     --region us-central1
   ```

## Security Notes

- Staging uses same service account as production
- Secrets are suffixed with `-staging` in Secret Manager
- No customer data should be in staging
- Use synthetic test data only