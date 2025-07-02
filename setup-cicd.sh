#!/bin/bash

# Setup CI/CD for LeafLoaf
# This script configures GitHub and GCP for automatic deployments

set -e

echo "🚀 Setting up CI/CD for LeafLoaf"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first."
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ No GCP project set. Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Using GCP Project: $PROJECT_ID"

# Enable required APIs
echo "🔧 Enabling required GCP APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable sourcerepo.googleapis.com

# Create service account if it doesn't exist
echo "👤 Setting up service account..."
if ! gcloud iam service-accounts describe leafloaf-sa@$PROJECT_ID.iam.gserviceaccount.com &> /dev/null; then
    gcloud iam service-accounts create leafloaf-sa \
        --display-name="LeafLoaf Service Account" \
        --description="Service account for LeafLoaf Cloud Run deployments"
fi

# Grant necessary permissions
echo "🔐 Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:leafloaf-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/run.developer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:leafloaf-sa@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/spanner.databaseUser"

# Grant Cloud Build permissions
CLOUD_BUILD_SA="${PROJECT_ID}@cloudbuild.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${CLOUD_BUILD_SA}" \
    --role="roles/iam.serviceAccountUser"

# Create Cloud Build trigger
echo "🔨 Creating Cloud Build trigger..."
gcloud builds triggers create github \
    --repo-name=LeafLoafLangGraph \
    --repo-owner=$(git config --get remote.origin.url | sed -e 's/.*github.com[:/]\(.*\)\/.*/\1/') \
    --branch-pattern="^main$" \
    --build-config="cloudbuild-enhanced.yaml" \
    --description="Deploy to production on push to main" \
    --name="deploy-main"

# Create staging trigger for branches
gcloud builds triggers create github \
    --repo-name=LeafLoafLangGraph \
    --repo-owner=$(git config --get remote.origin.url | sed -e 's/.*github.com[:/]\(.*\)\/.*/\1/') \
    --branch-pattern="^feature/.*$" \
    --build-config="cloudbuild-enhanced.yaml" \
    --description="Deploy to staging on feature branches" \
    --name="deploy-staging"

# Create GitHub secrets instructions
echo ""
echo "📝 GitHub Actions Setup Instructions:"
echo "======================================"
echo ""
echo "1. Go to your GitHub repository settings"
echo "2. Navigate to Settings > Secrets and variables > Actions"
echo "3. Add the following secrets:"
echo ""
echo "   GCP_PROJECT_ID: $PROJECT_ID"
echo ""
echo "   GCP_SA_KEY: (run the following command and copy the output)"
echo "   gcloud iam service-accounts keys create key.json --iam-account=leafloaf-sa@$PROJECT_ID.iam.gserviceaccount.com"
echo "   cat key.json | base64"
echo "   rm key.json"
echo ""
echo "4. Commit and push the .github/workflows/deploy-to-gcp.yml file"
echo ""

# Create local git hooks
echo "🪝 Setting up local git hooks..."
cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash
# Run tests before pushing

echo "🧪 Running tests before push..."
python run_all_personalization_tests.py

if [ $? -ne 0 ]; then
    echo "❌ Tests failed! Push aborted."
    exit 1
fi

echo "✅ All tests passed! Proceeding with push..."
EOF

chmod +x .git/hooks/pre-push

echo ""
echo "✅ CI/CD Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Set up GitHub secrets as shown above"
echo "2. Choose your deployment method:"
echo "   - GitHub Actions: Push .github/workflows/deploy-to-gcp.yml"
echo "   - Cloud Build: Already configured with triggers"
echo "3. Push to main branch to trigger deployment"
echo ""
echo "Features enabled:"
echo "✓ Automatic testing before deployment"
echo "✓ Staging deployments for feature branches"
echo "✓ Canary deployments for production"
echo "✓ Automatic rollback on failure"
echo "✓ Post-deployment health checks"