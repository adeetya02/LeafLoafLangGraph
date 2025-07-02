# LeafLoaf Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Local Development](#local-development)
4. [Production Deployment](#production-deployment)
5. [Configuration Management](#configuration-management)
6. [Monitoring Setup](#monitoring-setup)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Services
- Google Cloud Platform account
- Weaviate instance (cloud or self-hosted)
- Redis instance (optional, but recommended)
- Google Cloud Spanner (for Graphiti)
- BigQuery dataset

### Required Tools
- Python 3.11+
- Docker & Docker Compose
- Google Cloud SDK (`gcloud`)
- `ngrok` (for webhook testing)

## Environment Setup

### 1. Clone Repository
```bash
git clone https://github.com/leafloaf/langgraph.git
cd leafloaf-langgraph
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Variables
Create `.env.yaml` for local development:

```yaml
# Core Services
OPENAI_API_KEY: "not-used"
ANTHROPIC_API_KEY: "not-used"
TAVILY_API_KEY: "not-used"

# LangChain
LANGCHAIN_API_KEY: "lsv2_pt_your_key_here"
LANGCHAIN_TRACING_V2: "true"
LANGCHAIN_PROJECT: "leafloaf-dev"

# Weaviate
WEAVIATE_URL: "https://your-instance.weaviate.network"
WEAVIATE_API_KEY: "your-weaviate-key"

# LLM Configuration
HUGGINGFACE_API_KEY: "hf_your_key_here"
VERTEX_AI_PROJECT: "your-gcp-project"
VERTEX_AI_LOCATION: "us-central1"

# Voice Integration
ELEVENLABS_API_KEY: "sk_your_key_here"

# Personalization Services
REDIS_URL: "redis://localhost:6379"  # Optional
GRAPHITI_SPANNER_INSTANCE: "leafloaf-dev"
GRAPHITI_SPANNER_DATABASE: "graphiti"

# Analytics
BIGQUERY_PROJECT: "your-gcp-project"
BIGQUERY_DATASET: "leafloaf_analytics"

# Feature Flags
PERSONALIZATION_ENABLED: "true"
USE_REDIS_CACHE: "true"
ENABLE_VOICE: "true"
```

### 4. Service Account Setup
```bash
# Create service account
gcloud iam service-accounts create leafloaf-backend \
    --display-name="LeafLoaf Backend Service"

# Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:leafloaf-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/spanner.databaseUser"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:leafloaf-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"

# Download key
gcloud iam service-accounts keys create service-account-key.json \
    --iam-account=leafloaf-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

## Local Development

### 1. Start Dependencies
```bash
# Start Redis (optional)
docker run -d -p 6379:6379 redis:alpine

# Start ngrok for webhooks
ngrok http 8000
```

### 2. Initialize Databases
```bash
# Create Spanner instance and database
gcloud spanner instances create leafloaf-dev \
    --config=regional-us-central1 \
    --nodes=1 \
    --description="LeafLoaf Development"

gcloud spanner databases create graphiti \
    --instance=leafloaf-dev

# Create BigQuery dataset
bq mk --dataset \
    --location=US \
    YOUR_PROJECT_ID:leafloaf_analytics
```

### 3. Run Application
```bash
# Set environment
export GOOGLE_APPLICATION_CREDENTIALS="service-account-key.json"

# Run development server
python run.py
```

### 4. Run Tests
```bash
# Run all personalization tests
python run_all_personalization_tests.py

# Run specific test suites
pytest tests/unit/test_reorder_intelligence.py -v
```

## Production Deployment

### 1. Build Container
```bash
# Build with Cloud Build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/leafloaf:latest

# Or build locally
docker build -t gcr.io/YOUR_PROJECT_ID/leafloaf:latest .
docker push gcr.io/YOUR_PROJECT_ID/leafloaf:latest
```

### 2. Deploy to Cloud Run
```bash
gcloud run deploy leafloaf \
    --image gcr.io/YOUR_PROJECT_ID/leafloaf:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --service-account leafloaf-backend@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --env-vars-file .env.production.yaml \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 100 \
    --concurrency 100
```

### 3. Production Environment Variables
Create `.env.production.yaml`:

```yaml
# Production Configuration
ENVIRONMENT: "production"
LOG_LEVEL: "INFO"

# Services (use production URLs)
WEAVIATE_URL: "https://leafloaf-prod.weaviate.network"
REDIS_URL: "redis://10.0.0.3:6379"  # Internal IP
GRAPHITI_SPANNER_INSTANCE: "leafloaf-prod"

# Performance Settings
PERSONALIZATION_CACHE_TTL: "300"  # 5 minutes
SESSION_TIMEOUT: "1800"  # 30 minutes
MAX_SEARCH_RESULTS: "50"

# Feature Flags
PERSONALIZATION_ENABLED: "true"
ENABLE_REORDER_INTELLIGENCE: "true"
ENABLE_BUNDLE_SUGGESTIONS: "true"
```

### 4. Setup Load Balancer
```bash
# Reserve static IP
gcloud compute addresses create leafloaf-ip --global

# Create NEG for Cloud Run
gcloud compute network-endpoint-groups create leafloaf-neg \
    --region=us-central1 \
    --network-endpoint-type=serverless \
    --cloud-run-service=leafloaf

# Configure Load Balancer (see terraform/lb.tf)
```

### 5. Configure Domain
```bash
# Add custom domain to Cloud Run
gcloud run domain-mappings create \
    --service leafloaf \
    --domain api.leafloaf.com \
    --region us-central1
```

## Configuration Management

### 1. Feature Flags
```python
# src/config/features.py
FEATURE_FLAGS = {
    "personalization": {
        "smart_search_ranking": True,
        "my_usual_orders": True,
        "reorder_intelligence": True,
        "dietary_filters": True,
        "bundle_suggestions": True,
        "quantity_memory": True,
        "seasonal_patterns": True,
        "holiday_awareness": True
    },
    "performance": {
        "use_redis_cache": True,
        "parallel_agent_execution": True,
        "batch_bigquery_inserts": True
    }
}
```

### 2. Agent Configuration
```python
# src/config/agents.py
AGENT_CONFIG = {
    "supervisor": {
        "timeout": 5000,  # 5 seconds
        "max_retries": 2
    },
    "product_search": {
        "max_results": 50,
        "personalization_weight": 0.3,
        "cache_ttl": 120  # 2 minutes
    },
    "order_agent": {
        "max_cart_items": 100,
        "usual_confidence_threshold": 0.8
    }
}
```

### 3. Personalization Settings
```python
# src/config/personalization.py
PERSONALIZATION_CONFIG = {
    "ranker": {
        "brand_boost": 1.5,
        "price_sensitivity_weight": 0.3,
        "dietary_filter_strict": True
    },
    "my_usual": {
        "min_frequency": 0.5,
        "min_orders": 3,
        "confidence_threshold": 0.8
    },
    "reorder": {
        "lookahead_days": 7,
        "buffer_days": 2,
        "holiday_adjustment": True
    }
}
```

## Monitoring Setup

### 1. Cloud Monitoring
```bash
# Create uptime check
gcloud monitoring uptime create leafloaf-health \
    --display-name="LeafLoaf API Health" \
    --uri="https://api.leafloaf.com/health"

# Create alerts
gcloud monitoring policies create \
    --notification-channels=CHANNEL_ID \
    --display-name="High Error Rate" \
    --condition-display-name="Error rate > 1%" \
    --condition-threshold-value=0.01
```

### 2. Custom Metrics
```python
# Instrument code with OpenTelemetry
from opentelemetry import metrics

meter = metrics.get_meter("leafloaf")

# Create counters
personalization_counter = meter.create_counter(
    "personalization_requests",
    description="Number of personalization requests"
)

# Create histograms  
response_time_histogram = meter.create_histogram(
    "response_time_ms",
    description="Response time in milliseconds"
)
```

### 3. Dashboards
Create Grafana dashboards for:
- API response times
- Personalization feature usage
- Cache hit rates
- Error rates by endpoint
- Business metrics (reorder rate, basket size)

## Database Migrations

### 1. Spanner Schema Updates
```sql
-- Create Graphiti tables
CREATE TABLE entities (
    id STRING(36) NOT NULL,
    type STRING(50) NOT NULL,
    properties JSON,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (id);

CREATE TABLE relationships (
    id STRING(36) NOT NULL,
    source_id STRING(36) NOT NULL,
    target_id STRING(36) NOT NULL,
    type STRING(50) NOT NULL,
    properties JSON,
    created_at TIMESTAMP NOT NULL,
) PRIMARY KEY (id);
```

### 2. BigQuery Schema
```sql
-- Create event tables
CREATE TABLE IF NOT EXISTS `project.leafloaf_analytics.user_search_events` (
    event_id STRING NOT NULL,
    user_id STRING NOT NULL,
    session_id STRING,
    query STRING NOT NULL,
    intent STRING,
    results_count INT64,
    personalization_applied BOOL,
    timestamp TIMESTAMP NOT NULL,
    metadata JSON
);

CREATE TABLE IF NOT EXISTS `project.leafloaf_analytics.reorder_events` (
    event_id STRING NOT NULL,
    user_id STRING NOT NULL,
    sku STRING NOT NULL,
    action STRING NOT NULL,
    cycle_days INT64,
    confidence FLOAT64,
    timestamp TIMESTAMP NOT NULL
);
```

## Health Checks

### 1. Application Health
```python
@app.get("/health")
async def health_check():
    checks = {
        "api": "healthy",
        "weaviate": check_weaviate(),
        "redis": check_redis(),
        "spanner": check_spanner(),
        "bigquery": check_bigquery()
    }
    
    status = "healthy" if all(
        v == "healthy" for v in checks.values()
    ) else "degraded"
    
    return {
        "status": status,
        "checks": checks,
        "version": "2.0.0",
        "features": FEATURE_FLAGS
    }
```

### 2. Dependency Checks
```python
async def check_weaviate():
    try:
        client = get_weaviate_client()
        client.schema.get()
        return "healthy"
    except Exception as e:
        logger.error(f"Weaviate health check failed: {e}")
        return "unhealthy"
```

## Troubleshooting

### Common Issues

#### 1. Personalization Not Working
```bash
# Check Redis connection
redis-cli ping

# Check user preferences
curl -X GET https://api.leafloaf.com/debug/preferences/user_123

# Check feature flags
curl -X GET https://api.leafloaf.com/health
```

#### 2. Slow Response Times
```bash
# Check cache hit rates
redis-cli INFO stats | grep hit

# Profile slow queries
python -m cProfile -o profile.stats src/api/main.py

# Analyze profile
python -m pstats profile.stats
```

#### 3. Memory Issues
```bash
# Increase Cloud Run memory
gcloud run services update leafloaf --memory 4Gi

# Monitor memory usage
gcloud monitoring read \
    --filter='metric.type="run.googleapis.com/container/memory/utilization"'
```

### Debug Endpoints
```python
# Add debug endpoints (disable in production)
@app.get("/debug/cache/{key}")
async def debug_cache(key: str):
    value = await redis_client.get(key)
    return {"key": key, "value": value, "ttl": await redis_client.ttl(key)}

@app.post("/debug/clear-cache")
async def clear_cache():
    await redis_client.flushdb()
    return {"status": "cache cleared"}
```

## Rollback Procedure

### 1. Quick Rollback
```bash
# List revisions
gcloud run revisions list --service leafloaf

# Route traffic to previous revision
gcloud run services update-traffic leafloaf \
    --to-revisions PREVIOUS_REVISION=100
```

### 2. Database Rollback
```bash
# Restore Spanner backup
gcloud spanner databases restore graphiti-restore \
    --source-backup=graphiti-backup-20250627 \
    --instance=leafloaf-prod

# Point application to restored database
gcloud run services update leafloaf \
    --set-env-vars GRAPHITI_DATABASE=graphiti-restore
```

## Security Checklist

- [ ] All secrets in Secret Manager
- [ ] Service accounts with minimal permissions
- [ ] API authentication enabled
- [ ] Rate limiting configured
- [ ] SQL injection prevention
- [ ] XSS protection headers
- [ ] CORS properly configured
- [ ] Audit logging enabled
- [ ] Encryption at rest
- [ ] Regular security scans

## Performance Optimization

### 1. Caching Strategy
- User preferences: 5 min TTL
- Search results: 2 min TTL
- Product catalog: 10 min TTL
- Reorder cycles: 24 hour TTL

### 2. Database Optimization
- Weaviate: Proper indexing
- Spanner: Query optimization
- BigQuery: Partitioning by date
- Redis: Memory limits

### 3. Code Optimization
- Async everything
- Parallel agent execution
- Batch database operations
- Connection pooling