#!/bin/bash

# Production deployment script for LeafLoaf
set -e

echo "🚀 DEPLOYING LEAFLOAF TO PRODUCTION"
echo "===================================="

# Check if logged into gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "❌ Not logged into gcloud. Please run: gcloud auth login"
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project)
echo "📦 Project: $PROJECT_ID"

# Build and push to GCR
echo ""
echo "1️⃣ Building Docker image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/leafloaf-prod

# Deploy to Cloud Run
echo ""
echo "2️⃣ Deploying to Cloud Run..."
gcloud run deploy leafloaf \
    --image gcr.io/$PROJECT_ID/leafloaf-prod \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --concurrency 100 \
    --min-instances 1 \
    --max-instances 10 \
    --env-vars-file .env.production.yaml

# Get the service URL
SERVICE_URL=$(gcloud run services describe leafloaf --region us-central1 --format="value(status.url)")

echo ""
echo "✅ DEPLOYMENT COMPLETE!"
echo "======================"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📊 Next steps:"
echo "1. Test the API: curl $SERVICE_URL/health"
echo "2. Monitor logs: gcloud logging read 'resource.type=cloud_run_revision'"
echo "3. View metrics in Cloud Console"