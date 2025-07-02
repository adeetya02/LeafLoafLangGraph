# Graphiti Integration Deployment Guide

## Overview

This branch contains the Graphiti integration with Spanner backend for LeafLoaf. Graphiti provides temporal knowledge graphs for tracking user preferences, order patterns, and contextual understanding across conversations.

## Key Features

### 1. Entity Extraction
- Automatic extraction of products, brands, preferences, events
- Real-time processing during API calls
- Non-blocking async implementation

### 2. Memory Management
- Thread-safe singleton pattern with dependency injection
- Support for multiple backends (Spanner, Neo4j, In-Memory)
- Session and graph memory separation

### 3. Spanner Integration
- Native Google Cloud Spanner support
- GraphRAG capabilities
- Scalable graph storage

## Local Testing

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional for local)
export SPANNER_INSTANCE_ID=""  # Leave empty for in-memory mode
```

### Run Tests

1. **Test Graphiti locally:**
```bash
python3 test_graphiti_spanner_local.py
```

2. **Test API integration:**
```bash
# Start API server
PORT=8080 python3 run.py

# In another terminal, run tests
python3 test_graphiti_api_integration.py
```

3. **Test cart operations:**
```bash
python3 test_cart_operations_with_graphiti.py
```

## GCP Deployment

### Prerequisites
1. GCP Project with billing enabled
2. gcloud CLI installed and authenticated
3. Sufficient permissions for:
   - Cloud Run
   - Cloud Spanner
   - Vertex AI
   - Cloud Build

### Deploy to GCP

1. **Run deployment script:**
```bash
./deploy_to_gcp.sh
```

This script will:
- Create Spanner instance and database
- Set up service account with proper permissions
- Build and deploy to Cloud Run
- Run health checks

2. **Manual deployment (if needed):**
```bash
# Create Spanner instance
gcloud spanner instances create leafloaf-graph \
    --config=regional-us-central1 \
    --description="LeafLoaf GraphRAG Instance" \
    --nodes=1

# Create database
gcloud spanner databases create leafloaf-graphrag \
    --instance=leafloaf-graph

# Create schema
python3 create_spanner_schema.py

# Build and deploy
gcloud builds submit --config cloudbuild.yaml .
```

3. **Test production deployment:**
```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe leafloaf --region=us-central1 --format="value(status.url)")

# Run production tests
python3 test_production_gcp.py $SERVICE_URL
```

## Configuration

### Environment Variables
```yaml
# Spanner Configuration
SPANNER_INSTANCE_ID: "leafloaf-graph"
SPANNER_DATABASE_ID: "leafloaf-graphrag"
GCP_PROJECT_ID: "leafloafai"

# Optional - defaults to in-memory if not set
NEO4J_URI: "bolt://localhost:7687"
NEO4J_USERNAME: "neo4j"
NEO4J_PASSWORD: "password"
```

### Memory Backend Selection
The system automatically selects the appropriate backend:
1. Spanner (if SPANNER_INSTANCE_ID is set)
2. Neo4j (if NEO4J_URI is set)
3. In-Memory (fallback)

## API Changes

### New Response Fields
```json
{
  "metadata": {
    "graphiti": {
      "entities_extracted": 5,
      "entities": [...],
      "context_available": true,
      "cached_entities": [...],
      "reorder_patterns": [...]
    }
  }
}
```

### Performance Impact
- Entity extraction: <1ms overhead
- Context retrieval: <50ms
- Total API response: ~500ms (optimization ongoing)

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   API       │────▶│   Memory    │────▶│  Spanner    │
│  Endpoint   │     │  Manager    │     │   Graph     │
└─────────────┘     └─────────────┘     └─────────────┘
                            │
                            ▼
                    ┌─────────────┐
                    │  Graphiti   │
                    │  Extractor  │
                    └─────────────┘
```

## Monitoring

### Key Metrics
- Entity extraction rate
- Context hit rate
- Memory operation latency
- Spanner connection health

### Logs
```bash
# View Cloud Run logs
gcloud logging tail --service=leafloaf

# Filter Graphiti logs
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.logger=~graphiti"
```

## Troubleshooting

### Common Issues

1. **Spanner connection fails**
   - Check service account permissions
   - Verify Spanner instance exists
   - Check network connectivity

2. **High latency**
   - Enable connection pooling
   - Check Spanner node count
   - Review entity extraction patterns

3. **Memory not persisting**
   - Verify user_id consistency
   - Check Spanner write permissions
   - Review error logs

## Cost Considerations

- Spanner: ~$65/month for 1 node
- Cloud Run: Pay per request
- Vertex AI: Pay per prediction

## Next Steps

1. **Performance Optimization**
   - Implement caching layer
   - Optimize entity extraction
   - Batch Spanner operations

2. **Feature Enhancement**
   - Add more entity types
   - Implement pattern learning
   - Enhanced GraphRAG queries

3. **Integration**
   - Connect to BigQuery for analytics
   - Implement ML recommendations
   - Add A/B testing framework

## Support

For issues or questions:
1. Check logs in Cloud Console
2. Review test outputs
3. Contact team for assistance