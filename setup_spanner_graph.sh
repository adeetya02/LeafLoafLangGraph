#!/bin/bash
# Setup script for Spanner Graph on GCP

set -e

echo "🚀 Setting up Spanner Graph for LeafLoaf"
echo "========================================"

# Configuration
PROJECT_ID="leafloafai"
INSTANCE_ID="leafloaf-graph"
DATABASE_ID="leafloaf-graphrag"
REGION="us-central1"
SERVICE_ACCOUNT="leafloaf-api@${PROJECT_ID}.iam.gserviceaccount.com"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}1. Checking prerequisites...${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first."
    exit 1
fi

# Check current project
CURRENT_PROJECT=$(gcloud config get-value project)
if [ "$CURRENT_PROJECT" != "$PROJECT_ID" ]; then
    echo "Setting project to $PROJECT_ID..."
    gcloud config set project $PROJECT_ID
fi

echo -e "${GREEN}✓ Prerequisites checked${NC}"

echo -e "${YELLOW}2. Enabling required APIs...${NC}"

# Enable required APIs
gcloud services enable spanner.googleapis.com \
    aiplatform.googleapis.com \
    compute.googleapis.com \
    cloudresourcemanager.googleapis.com

echo -e "${GREEN}✓ APIs enabled${NC}"

echo -e "${YELLOW}3. Creating Spanner instance...${NC}"

# Check if instance exists
if gcloud spanner instances describe $INSTANCE_ID --quiet 2>/dev/null; then
    echo "Instance $INSTANCE_ID already exists"
else
    echo "Creating new Spanner instance..."
    gcloud spanner instances create $INSTANCE_ID \
        --config=regional-${REGION} \
        --description="LeafLoaf GraphRAG with Spanner Graph" \
        --nodes=1 \
        --processing-units=100
fi

echo -e "${GREEN}✓ Spanner instance ready${NC}"

echo -e "${YELLOW}4. Creating database with graph schema...${NC}"

# Create database if it doesn't exist
if gcloud spanner databases describe $DATABASE_ID --instance=$INSTANCE_ID --quiet 2>/dev/null; then
    echo "Database $DATABASE_ID already exists"
else
    echo "Creating new database..."
    gcloud spanner databases create $DATABASE_ID \
        --instance=$INSTANCE_ID \
        --database-dialect=GOOGLE_STANDARD_SQL
fi

echo -e "${GREEN}✓ Database created${NC}"

echo -e "${YELLOW}5. Setting up IAM permissions...${NC}"

# Grant necessary permissions
gcloud spanner databases add-iam-policy-binding $DATABASE_ID \
    --instance=$INSTANCE_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/spanner.databaseUser"

# Grant Vertex AI permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user"

echo -e "${GREEN}✓ IAM permissions configured${NC}"

echo -e "${YELLOW}6. Instance details:${NC}"
echo "Instance: $INSTANCE_ID"
echo "Database: $DATABASE_ID"
echo "Region: $REGION"
echo "Connection string: projects/$PROJECT_ID/instances/$INSTANCE_ID/databases/$DATABASE_ID"

echo -e "${GREEN}✅ Spanner Graph setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Run: python create_spanner_schema.py"
echo "2. Run: python test_spanner_graph_gcp.py"