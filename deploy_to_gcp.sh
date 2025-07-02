#!/bin/bash

# Deploy LeafLoaf to GCP with Spanner and Graphiti

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="leafloafai"
REGION="us-central1"
INSTANCE_ID="leafloaf-graph"
DATABASE_ID="leafloaf-graphrag"
SERVICE_ACCOUNT="leafloaf-sa"

echo -e "${GREEN}🚀 Deploying LeafLoaf to GCP${NC}"
echo "=================================="

# Check if gcloud is authenticated
echo -e "\n${YELLOW}1. Checking GCP authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &>/dev/null; then
    echo -e "${RED}❌ Not authenticated. Please run: gcloud auth login${NC}"
    exit 1
fi

# Set project
echo -e "\n${YELLOW}2. Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}

# Create service account if it doesn't exist
echo -e "\n${YELLOW}3. Checking service account...${NC}"
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com &>/dev/null; then
    echo "Creating service account..."
    gcloud iam service-accounts create ${SERVICE_ACCOUNT} \
        --display-name="LeafLoaf Service Account"
    
    # Grant necessary permissions
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/spanner.databaseUser"
    
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/aiplatform.user"
else
    echo -e "${GREEN}✅ Service account exists${NC}"
fi

# Create Spanner instance if it doesn't exist
echo -e "\n${YELLOW}4. Checking Spanner instance...${NC}"
if ! gcloud spanner instances describe ${INSTANCE_ID} &>/dev/null; then
    echo "Creating Spanner instance..."
    gcloud spanner instances create ${INSTANCE_ID} \
        --config=regional-${REGION} \
        --description="LeafLoaf GraphRAG Instance" \
        --nodes=1
else
    echo -e "${GREEN}✅ Spanner instance exists${NC}"
fi

# Create Spanner database if it doesn't exist
echo -e "\n${YELLOW}5. Checking Spanner database...${NC}"
if ! gcloud spanner databases describe ${DATABASE_ID} --instance=${INSTANCE_ID} &>/dev/null; then
    echo "Creating Spanner database..."
    gcloud spanner databases create ${DATABASE_ID} \
        --instance=${INSTANCE_ID}
    
    # Run schema creation
    echo "Creating schema..."
    python3 create_spanner_schema.py
else
    echo -e "${GREEN}✅ Spanner database exists${NC}"
fi

# Build and deploy using Cloud Build
echo -e "\n${YELLOW}6. Building and deploying application...${NC}"
gcloud builds submit --config cloudbuild.yaml .

# Get the service URL
echo -e "\n${YELLOW}7. Getting service URL...${NC}"
SERVICE_URL=$(gcloud run services describe leafloaf --region=${REGION} --format="value(status.url)")

echo -e "\n${GREEN}✅ Deployment complete!${NC}"
echo "=================================="
echo -e "Service URL: ${GREEN}${SERVICE_URL}${NC}"
echo -e "Health check: ${GREEN}${SERVICE_URL}/health${NC}"
echo -e "API docs: ${GREEN}${SERVICE_URL}/docs${NC}"

# Test the deployment
echo -e "\n${YELLOW}8. Testing deployment...${NC}"
sleep 5  # Wait for service to be ready

if curl -s "${SERVICE_URL}/health" | jq . ; then
    echo -e "\n${GREEN}✅ Service is healthy!${NC}"
else
    echo -e "\n${RED}❌ Health check failed${NC}"
fi

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Run production tests: python3 test_production_gcp.py ${SERVICE_URL}"
echo "2. Monitor logs: gcloud logging tail"
echo "3. Check metrics: gcloud monitoring dashboards list"