#!/bin/bash
# Check deployment configuration before deploying

echo "==================================="
echo "🔍 LeafLoaf Deployment Config Check"
echo "==================================="

# Check environment variables
echo -e "\n📋 Environment Configuration:"
echo "PROJECT_ID: ${PROJECT_ID:-NOT SET}"
echo "Region: us-northeast1"

# Check .env.yaml
echo -e "\n📄 Checking .env.yaml:"
if grep -q "GCP_PROJECT_ID: \"leafloafai\"" .env.yaml; then
    echo "✅ GCP_PROJECT_ID is set to leafloafai"
else
    echo "❌ GCP_PROJECT_ID not found or incorrect"
fi

if grep -q "GCP_LOCATION: \"us-northeast1\"" .env.yaml; then
    echo "✅ GCP_LOCATION is set to us-northeast1"
else
    echo "❌ GCP_LOCATION not found or incorrect"
fi

if grep -q "ENVIRONMENT: \"production\"" .env.yaml; then
    echo "✅ ENVIRONMENT is set to production"
else
    echo "❌ ENVIRONMENT not set to production"
fi

# Check for Vertex AI requirements
echo -e "\n🤖 Vertex AI Configuration:"
echo "Model: gemma-2-9b-it"
echo "Location: us-northeast1"
echo "Using GenerativeModel API from google.generativeai"

# Summary
echo -e "\n📊 Summary:"
echo "- Project: leafloafai"
echo "- Region: us-northeast1"
echo "- Model: Gemma 2 9B on Vertex AI"
echo "- Mode: Production with full LLM analysis"
echo "- Supervisor will use Gemma for:"
echo "  • Intent analysis"
echo "  • Context understanding"
echo "  • Dynamic alpha calculation"

echo -e "\n🚀 Ready to deploy? Run:"
echo "export PROJECT_ID=leafloafai"
echo "./scripts/deploy_to_gcp.sh"