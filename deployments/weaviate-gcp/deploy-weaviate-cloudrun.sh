#!/bin/bash
# Deploy Weaviate to Google Cloud Run

PROJECT_ID="leafloafai"
REGION="us-central1"
SERVICE_NAME="weaviate-leafloaf"

echo "Deploying Weaviate to Cloud Run..."

# Deploy Weaviate with Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image semitechnologies/weaviate:1.24.1 \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --memory 4Gi \
  --cpu 2 \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "QUERY_DEFAULTS_LIMIT=25" \
  --set-env-vars "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=false" \
  --set-env-vars "AUTHENTICATION_APIKEY_ENABLED=true" \
  --set-env-vars "AUTHENTICATION_APIKEY_ALLOWED_KEYS=leafloaf-weaviate-key-$(openssl rand -hex 16)" \
  --set-env-vars "AUTHENTICATION_APIKEY_USERS=leafloaf-admin" \
  --set-env-vars "DEFAULT_VECTORIZER_MODULE=text2vec-huggingface" \
  --set-env-vars "ENABLE_MODULES=text2vec-huggingface" \
  --set-env-vars "TRANSFORMERS_INFERENCE_API=https://api-inference.huggingface.co" \
  --set-env-vars "HUGGINGFACE_APIKEY=$HUGGINGFACE_API_KEY" \
  --min-instances 1 \
  --max-instances 10

echo "Weaviate deployed to Cloud Run!"
echo "Getting service URL..."

WEAVIATE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")
echo "Weaviate URL: $WEAVIATE_URL"

echo ""
echo "Update your .env.yaml with:"
echo "WEAVIATE_URL: \"$WEAVIATE_URL\""
echo "WEAVIATE_API_KEY: \"<check Cloud Run logs for the generated key>\""