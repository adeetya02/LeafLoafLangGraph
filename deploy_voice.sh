#!/bin/bash

echo "🚀 Deploying Leaf & Loaf Voice to Production..."

# Build the image
echo "📦 Building Docker image..."
gcloud builds submit --tag gcr.io/leafloafai/leafloaf-voice --timeout=30m

# Deploy to Cloud Run
echo "☁️ Deploying to Cloud Run..."
gcloud run deploy leafloaf \
  --image gcr.io/leafloafai/leafloaf-voice \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 600 \
  --max-instances 10 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=leafloafai"

# Get the service URL
SERVICE_URL=$(gcloud run services describe leafloaf --platform managed --region us-central1 --format 'value(status.url)')

echo "✅ Deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"
echo ""
echo "📱 Voice Demo: $SERVICE_URL/voice_demo_production.html"
echo "📝 Feedback Form: $SERVICE_URL/voice_feedback_form.html"
echo ""
echo "📧 Share these with your test users:"
echo "- Instructions: https://github.com/adityamarella/LeafLoafLangGraph/blob/main/VOICE_TEST_INSTRUCTIONS.md"
echo "- Demo Link: $SERVICE_URL/voice_demo_production.html"
echo "- Feedback: $SERVICE_URL/voice_feedback_form.html"