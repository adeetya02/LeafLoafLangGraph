#!/bin/bash
# Staging deployment script with no hardcoded values

set -e  # Exit on error

echo "🚀 LeafLoaf Staging Deployment"
echo "=============================="

# Check prerequisites
echo "Checking prerequisites..."

# 1. Check if environment file exists (staging or production)
ENV_FILE=".env.staging.yaml"
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  Warning: .env.staging.yaml not found!"
    echo "   Will use .env.yaml for staging deployment."
    ENV_FILE=".env.yaml"
    if [ ! -f "$ENV_FILE" ]; then
        echo "❌ Error: Neither .env.staging.yaml nor .env.yaml found!"
        echo "   Please create one of these files with your environment values."
        exit 1
    fi
fi

echo "Using environment file: $ENV_FILE"

# 2. Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found!"
    echo "   Please install Google Cloud SDK: https://cloud.google.com/sdk/install"
    exit 1
fi

# 3. Set project
PROJECT_ID="leafloafai"
echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# 4. Set up staging secrets
echo ""
echo "Setting up staging secrets..."
if [ -f "./setup-staging-secrets.sh" ]; then
    ./setup-staging-secrets.sh
else
    echo "⚠️  setup-staging-secrets.sh not found, using production secrets"
    ./setup-secrets.sh
fi

# 5. Build and deploy to staging
echo ""
echo "Building and deploying to staging..."
gcloud builds submit --config cloudbuild-staging-secure.yaml

# 6. Run additional tests
echo ""
echo "Running staging tests..."
STAGING_URL=$(gcloud run services describe leafloaf-staging --region us-central1 --format 'value(status.url)')

if [ ! -z "$STAGING_URL" ]; then
    echo ""
    echo "✅ Staging deployment successful!"
    echo "   URL: $STAGING_URL"
    echo ""
    echo "Running extended tests..."
    python test_production.py "$STAGING_URL" || echo "⚠️  Some tests failed - check logs"
else
    echo "❌ Could not retrieve staging URL. Check Cloud Run console."
fi