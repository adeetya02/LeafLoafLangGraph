#!/bin/bash
# Deploy LeafLoaf to GCP with Vertex AI Gemma

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 LeafLoaf GCP Deployment Script${NC}"
echo "=================================="

# Check if PROJECT_ID is set
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}ERROR: PROJECT_ID not set${NC}"
    echo "Please run: export PROJECT_ID=your-gcp-project-id"
    exit 1
fi

echo -e "${YELLOW}Using project: $PROJECT_ID${NC}"

# 1. Set project
echo -e "\n${GREEN}1. Setting GCP project...${NC}"
gcloud config set project $PROJECT_ID

# 2. Enable required APIs
echo -e "\n${GREEN}2. Enabling required APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    aiplatform.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com

# 3. Add PROJECT_ID to env file
echo -e "\n${GREEN}3. Updating environment variables...${NC}"
if ! grep -q "GCP_PROJECT_ID" .env.yaml; then
    echo "  GCP_PROJECT_ID: \"$PROJECT_ID\"" >> .env.yaml
    echo "  GCP_LOCATION: \"us-central1\"" >> .env.yaml
    echo "Added GCP_PROJECT_ID to .env.yaml"
fi

# 4. Build container
echo -e "\n${GREEN}4. Building container...${NC}"
gcloud builds submit --tag gcr.io/$PROJECT_ID/leafloaf

# 5. Deploy to Cloud Run
echo -e "\n${GREEN}5. Deploying to Cloud Run...${NC}"
gcloud run deploy leafloaf \
    --image gcr.io/$PROJECT_ID/leafloaf \
    --platform managed \
    --region us-northeast1 \
    --allow-unauthenticated \
    --env-vars-file .env.yaml \
    --memory 1Gi \
    --cpu 2 \
    --timeout 60 \
    --min-instances 0 \
    --max-instances 2 \
    --service-account leafloaf-sa@$PROJECT_ID.iam.gserviceaccount.com 2>/dev/null || \
gcloud run deploy leafloaf \
    --image gcr.io/$PROJECT_ID/leafloaf \
    --platform managed \
    --region us-northeast1 \
    --allow-unauthenticated \
    --env-vars-file .env.yaml \
    --memory 1Gi \
    --cpu 2 \
    --timeout 60 \
    --min-instances 0 \
    --max-instances 2

# 6. Get service URL
echo -e "\n${GREEN}6. Getting service URL...${NC}"
SERVICE_URL=$(gcloud run services describe leafloaf \
    --region us-northeast1 \
    --format 'value(status.url)')

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "Service URL: ${YELLOW}$SERVICE_URL${NC}"

# 7. Test the deployment
echo -e "\n${GREEN}7. Testing deployment...${NC}"

# Test health endpoint
echo -e "\n${YELLOW}Testing /health...${NC}"
curl -s $SERVICE_URL/health | jq .

# Test search endpoint
echo -e "\n${YELLOW}Testing /api/v1/search...${NC}"
curl -s -X POST $SERVICE_URL/api/v1/search \
    -H "Content-Type: application/json" \
    -d '{
        "query": "organic milk",
        "session_id": "test-gcp-deployment",
        "filters": {"dietary": ["organic"]},
        "preferences": {"preferred_brands": ["Oatly"]}
    }' | jq .

echo -e "\n${GREEN}📊 View logs:${NC}"
echo "gcloud run logs tail leafloaf --region us-central1"

echo -e "\n${GREEN}📈 View metrics:${NC}"
echo "https://console.cloud.google.com/run/detail/us-central1/leafloaf/metrics?project=$PROJECT_ID"

echo -e "\n${GREEN}🔍 OpenAPI docs:${NC}"
echo "$SERVICE_URL/docs"