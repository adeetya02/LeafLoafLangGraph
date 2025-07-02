#!/bin/bash

# Deploy LeafLoaf with Promotion Management to Google Cloud Run

echo "🚀 Deploying LeafLoaf with Promotion Management to Google Cloud Run"
echo "================================================================"

# Set variables
PROJECT_ID="leafloafai"
SERVICE_NAME="leafloaf"
REGION="us-central1"

# Ensure we're using the right project
gcloud config set project $PROJECT_ID

# Build the container
echo "📦 Building container..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --timeout=30m

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 100 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars "FAST_MODE=true" \
  --set-env-vars "CACHE_ENABLED=true" \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📋 Service Details:"
echo "   Service URL: $SERVICE_URL"
echo "   Region: $REGION"
echo ""
echo "🎯 API Endpoints:"
echo "   Main Chat: $SERVICE_URL/chat"
echo "   Health Check: $SERVICE_URL/health"
echo ""
echo "📦 Promotion Management:"
echo "   Create Promotion: POST $SERVICE_URL/promotions/create"
echo "   List Promotions: GET $SERVICE_URL/promotions/list"
echo "   Test Promo Code: GET $SERVICE_URL/promotions/test/{code}"
echo "   Deactivate: DELETE $SERVICE_URL/promotions/{promotion_id}"
echo ""
echo "🌐 Web Interfaces:"
echo "   Chat Interface: Open chatbot.html and set API URL to $SERVICE_URL"
echo "   Promotion Manager: Open promotion_manager.html and set API URL to $SERVICE_URL"
echo ""
echo "📊 BigQuery Console:"
echo "   https://console.cloud.google.com/bigquery?project=$PROJECT_ID"