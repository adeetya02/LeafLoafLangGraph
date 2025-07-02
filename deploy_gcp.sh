#!/bin/bash

# GCP Deployment Script for LeafLoaf with Gemma Integration

set -e

echo "=========================================="
echo "🚀 DEPLOYING LEAFLOAF TO GCP WITH GEMMA"
echo "=========================================="

# Configuration
PROJECT_ID="leafloafai"
REGION="us-central1"
SERVICE_NAME="leafloaf"
IMAGE_NAME="gcr.io/${PROJECT_ID}/leafloaf"

# Set active project
echo "1. Setting active project..."
gcloud config set project $PROJECT_ID

# Build and push Docker image
echo -e "\n2. Building Docker image..."
gcloud builds submit --tag $IMAGE_NAME

# Deploy to Cloud Run
echo -e "\n3. Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --cpu-boost \
  --timeout 300 \
  --concurrency 80 \
  --min-instances 1 \
  --max-instances 10 \
  --execution-environment gen2 \
  --env-vars-file .env.yaml \
  --set-env-vars="ENVIRONMENT=production,FAST_MODE=false,TEST_MODE=false"

# Get the service URL
echo -e "\n4. Getting service URL..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo -e "\n✅ DEPLOYMENT COMPLETE!"
echo "Service URL: $SERVICE_URL"
echo ""
echo "Test endpoints:"
echo "  - Health: $SERVICE_URL/health"
echo "  - Search: $SERVICE_URL/api/v1/search"
echo "  - Docs: $SERVICE_URL/docs"
echo ""
echo "Gemma endpoint: 6438719201535328256.us-central1-fasttryout.prediction.vertexai.goog"
echo ""
echo "🎯 Next steps:"
echo "  1. Test search with Gemma intent recognition"
echo "  2. Test cart operations with voice commands"
echo "  3. Monitor logs: gcloud run logs read --service=$SERVICE_NAME"