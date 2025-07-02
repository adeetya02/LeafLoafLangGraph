#!/bin/bash
# Direct production deployment using existing image

set -e

echo "🚀 Direct Production Deployment"
echo "=============================="

# First, let's use the latest working image
IMAGE="gcr.io/leafloafai/leafloaf:latest"

echo "Deploying to Cloud Run..."
gcloud run deploy leafloaf \
  --image $IMAGE \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 60 \
  --concurrency 100 \
  --set-env-vars "ENVIRONMENT=production,FAST_MODE=false,TEST_MODE=false,WEAVIATE_CLASS_NAME=Product,SPANNER_INSTANCE_ID=leafloaf-graphiti,SPANNER_DATABASE_ID=graphiti-memory,GOOGLE_CLOUD_PROJECT=leafloafai,GCP_PROJECT_ID=leafloafai,GCP_LOCATION=us-central1,VERTEX_AI_ENDPOINT_ID=6438719201535328256,VERTEX_AI_ENDPOINT_RESOURCE_NAME=projects/32905605817/locations/us-central1/endpoints/6438719201535328256,REDIS_ENABLED=false,LANGCHAIN_TRACING_V2=true,LANGCHAIN_PROJECT=leafandloaf-production,LANGCHAIN_ENDPOINT=https://api.smith.langchain.com,OPENAI_API_KEY=not-used,ANTHROPIC_API_KEY=not-used,TAVILY_API_KEY=not-used" \
  --set-secrets "WEAVIATE_URL=weaviate-url:latest,WEAVIATE_API_KEY=weaviate-api-key:latest,HUGGINGFACE_API_KEY=huggingface-api-key:latest,LANGCHAIN_API_KEY=langchain-api-key:latest" \
  --service-account leafloaf-sa@leafloafai.iam.gserviceaccount.com

# Get URL
PROD_URL=$(gcloud run services describe leafloaf --region us-central1 --format 'value(status.url)')

echo ""
echo "✅ Production deployment complete!"
echo "URL: $PROD_URL"
echo ""
echo "Testing health endpoint..."
curl -s $PROD_URL/health | python -m json.tool || echo "Health check failed"