#!/bin/bash
# Script to set up staging secrets in Google Secret Manager
# This reads from .env.staging.yaml to avoid any hardcoded values

PROJECT_ID="leafloafai"
ENV_FILE=".env.staging.yaml"

# Check if .env.staging.yaml exists
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  Warning: $ENV_FILE not found!"
    echo "Staging will use production secrets with staging-specific overrides."
    echo "To use separate staging credentials, create $ENV_FILE from template."
    ENV_FILE=".env.yaml"  # Fallback to production env
fi

echo "Setting up staging secrets from $ENV_FILE..."

# Function to extract value from yaml
get_yaml_value() {
    local key=$1
    local file=${2:-$ENV_FILE}
    grep "^$key:" "$file" | sed 's/^[^:]*: *"\\?//' | sed 's/"\\?$//' | tr -d '\\n'
}

# Create staging-specific secrets with -staging suffix
WEAVIATE_URL=$(get_yaml_value "WEAVIATE_URL")
WEAVIATE_API_KEY=$(get_yaml_value "WEAVIATE_API_KEY")
HUGGINGFACE_API_KEY=$(get_yaml_value "HUGGINGFACE_API_KEY")
LANGCHAIN_API_KEY=$(get_yaml_value "LANGCHAIN_API_KEY")
ELEVENLABS_API_KEY=$(get_yaml_value "ELEVENLABS_API_KEY")
GROQ_API_KEY=$(get_yaml_value "GROQ_API_KEY")

# Create/update staging secrets
echo "Creating/updating staging secrets..."
gcloud secrets create weaviate-url-staging --data-file=<(echo -n "$WEAVIATE_URL") --project=$PROJECT_ID 2>/dev/null || 
    gcloud secrets versions add weaviate-url-staging --data-file=<(echo -n "$WEAVIATE_URL") --project=$PROJECT_ID

gcloud secrets create weaviate-api-key-staging --data-file=<(echo -n "$WEAVIATE_API_KEY") --project=$PROJECT_ID 2>/dev/null || 
    gcloud secrets versions add weaviate-api-key-staging --data-file=<(echo -n "$WEAVIATE_API_KEY") --project=$PROJECT_ID

gcloud secrets create huggingface-api-key-staging --data-file=<(echo -n "$HUGGINGFACE_API_KEY") --project=$PROJECT_ID 2>/dev/null || 
    gcloud secrets versions add huggingface-api-key-staging --data-file=<(echo -n "$HUGGINGFACE_API_KEY") --project=$PROJECT_ID

gcloud secrets create langchain-api-key-staging --data-file=<(echo -n "$LANGCHAIN_API_KEY") --project=$PROJECT_ID 2>/dev/null || 
    gcloud secrets versions add langchain-api-key-staging --data-file=<(echo -n "$LANGCHAIN_API_KEY") --project=$PROJECT_ID

echo ""
echo "Granting Cloud Run service account access to staging secrets..."
SERVICE_ACCOUNT="leafloaf-sa@$PROJECT_ID.iam.gserviceaccount.com"

# Grant access to staging secrets
SECRETS="weaviate-url-staging weaviate-api-key-staging huggingface-api-key-staging langchain-api-key-staging"

for secret in $SECRETS; do
    echo "  Granting access to $secret..."
    gcloud secrets add-iam-policy-binding $secret \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID \
        --quiet 2>/dev/null || true
done

echo "✅ Staging secrets configured successfully!"