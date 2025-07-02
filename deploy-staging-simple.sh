#!/bin/bash
# Simple staging deployment script

set -e

echo "🚀 Simple Staging Deployment"
echo "==========================="

# Build and push image
echo "Building Docker image..."
docker build -t gcr.io/leafloafai/leafloaf-staging:latest .

echo "Pushing to GCR..."
docker push gcr.io/leafloafai/leafloaf-staging:latest

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy leafloaf-staging \
  --image gcr.io/leafloafai/leafloaf-staging:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 60 \
  --concurrency 50 \
  --set-env-vars "ENVIRONMENT=staging,WEAVIATE_CLASS_NAME=Product,SPANNER_INSTANCE_ID=leafloaf-graphiti,SPANNER_DATABASE_ID=graphiti-memory,GOOGLE_CLOUD_PROJECT=leafloafai,GCP_PROJECT_ID=leafloafai,GCP_LOCATION=us-central1,VERTEX_AI_ENDPOINT_ID=6438719201535328256,LANGCHAIN_TRACING_V2=true,LANGCHAIN_PROJECT=leafandloaf-staging,LOG_LEVEL=debug" \
  --set-secrets "WEAVIATE_URL=weaviate-url-staging:latest,WEAVIATE_API_KEY=weaviate-api-key-staging:latest,HUGGINGFACE_API_KEY=huggingface-api-key-staging:latest,LANGCHAIN_API_KEY=langchain-api-key-staging:latest" \
  --service-account leafloaf-sa@leafloafai.iam.gserviceaccount.com

# Get URL
STAGING_URL=$(gcloud run services describe leafloaf-staging --region us-central1 --format 'value(status.url)')
echo ""
echo "✅ Staging deployment complete!"
echo "URL: $STAGING_URL"
echo ""
echo "Test with:"
echo "  curl $STAGING_URL/health"
echo "  python test_staging.py $STAGING_URL"