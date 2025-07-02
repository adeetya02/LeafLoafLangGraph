#!/bin/bash
# Production deployment script with no hardcoded values

set -e  # Exit on error

echo "🚀 LeafLoaf Production Deployment"
echo "================================"

# Check prerequisites
echo "Checking prerequisites..."

# 1. Check if .env.yaml exists
if [ ! -f ".env.yaml" ]; then
    echo "❌ Error: .env.yaml not found!"
    echo "   Please create .env.yaml with your production values."
    echo "   You can use .env.production.yaml.template as a starting point."
    exit 1
fi

# 2. Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found!"
    echo "   Please install Google Cloud SDK: https://cloud.google.com/sdk/install"
    exit 1
fi

# 3. Check if authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
    echo "❌ Error: Not authenticated with gcloud!"
    echo "   Please run: gcloud auth login"
    exit 1
fi

# 4. Set project
PROJECT_ID="leafloafai"
echo "Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# 5. Ensure service account exists
SERVICE_ACCOUNT="leafloaf-sa@$PROJECT_ID.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT &> /dev/null; then
    echo "Creating service account..."
    gcloud iam service-accounts create leafloaf-sa \
        --display-name="LeafLoaf Cloud Run Service Account" \
        --project=$PROJECT_ID
fi

# 6. Set up secrets
echo ""
echo "Setting up secrets in Secret Manager..."
./setup-secrets.sh
if [ $? -ne 0 ]; then
    echo "❌ Secret setup failed!"
    exit 1
fi

# 7. Build and deploy
echo ""
echo "Building and deploying to Cloud Run..."
gcloud builds submit --config cloudbuild-secure.yaml

# 8. Get the service URL
echo ""
echo "Getting service URL..."
SERVICE_URL=$(gcloud run services describe leafloaf --region us-central1 --format 'value(status.url)')

if [ ! -z "$SERVICE_URL" ]; then
    echo ""
    echo "✅ Deployment successful!"
    echo "   Service URL: $SERVICE_URL"
    echo ""
    echo "Test your deployment:"
    echo "   python test_production.py $SERVICE_URL"
else
    echo "❌ Could not retrieve service URL. Check Cloud Run console for status."
fi