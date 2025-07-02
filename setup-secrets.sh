#!/bin/bash
# Script to set up secrets in Google Secret Manager
# This reads from .env.yaml to avoid any hardcoded values

PROJECT_ID="leafloafai"
ENV_FILE=".env.yaml"

# Check if .env.yaml exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: $ENV_FILE not found!"
    echo "Please ensure .env.yaml exists with your production values."
    exit 1
fi

echo "Setting up secrets in Google Secret Manager from $ENV_FILE..."

# Function to extract value from yaml
get_yaml_value() {
    local key=$1
    grep -E "^[[:space:]]*$key:" "$ENV_FILE" | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//' | tr -d '\n'
}

# Create secrets from .env.yaml
WEAVIATE_URL=$(get_yaml_value "WEAVIATE_URL")
WEAVIATE_API_KEY=$(get_yaml_value "WEAVIATE_API_KEY")
HUGGINGFACE_API_KEY=$(get_yaml_value "HUGGINGFACE_API_KEY")
LANGCHAIN_API_KEY=$(get_yaml_value "LANGCHAIN_API_KEY")
ELEVENLABS_API_KEY=$(get_yaml_value "ELEVENLABS_API_KEY")
GROQ_API_KEY=$(get_yaml_value "GROQ_API_KEY")

# Validate we got the values
if [ -z "$WEAVIATE_URL" ] || [ -z "$WEAVIATE_API_KEY" ]; then
    echo "❌ Error: Could not extract Weaviate credentials from $ENV_FILE"
    exit 1
fi

# Create/update secrets
echo "Creating/updating secrets..."
gcloud secrets create weaviate-url --data-file=<(echo -n "$WEAVIATE_URL") --project=$PROJECT_ID 2>/dev/null || 
    gcloud secrets versions add weaviate-url --data-file=<(echo -n "$WEAVIATE_URL") --project=$PROJECT_ID

gcloud secrets create weaviate-api-key --data-file=<(echo -n "$WEAVIATE_API_KEY") --project=$PROJECT_ID 2>/dev/null || 
    gcloud secrets versions add weaviate-api-key --data-file=<(echo -n "$WEAVIATE_API_KEY") --project=$PROJECT_ID

gcloud secrets create huggingface-api-key --data-file=<(echo -n "$HUGGINGFACE_API_KEY") --project=$PROJECT_ID 2>/dev/null || 
    gcloud secrets versions add huggingface-api-key --data-file=<(echo -n "$HUGGINGFACE_API_KEY") --project=$PROJECT_ID

gcloud secrets create langchain-api-key --data-file=<(echo -n "$LANGCHAIN_API_KEY") --project=$PROJECT_ID 2>/dev/null || 
    gcloud secrets versions add langchain-api-key --data-file=<(echo -n "$LANGCHAIN_API_KEY") --project=$PROJECT_ID

if [ ! -z "$ELEVENLABS_API_KEY" ]; then
    gcloud secrets create elevenlabs-api-key --data-file=<(echo -n "$ELEVENLABS_API_KEY") --project=$PROJECT_ID 2>/dev/null || 
        gcloud secrets versions add elevenlabs-api-key --data-file=<(echo -n "$ELEVENLABS_API_KEY") --project=$PROJECT_ID
fi

if [ ! -z "$GROQ_API_KEY" ]; then
    gcloud secrets create groq-api-key --data-file=<(echo -n "$GROQ_API_KEY") --project=$PROJECT_ID 2>/dev/null || 
        gcloud secrets versions add groq-api-key --data-file=<(echo -n "$GROQ_API_KEY") --project=$PROJECT_ID
fi

echo "\nGranting Cloud Run service account access to secrets..."
SERVICE_ACCOUNT="leafloaf-sa@$PROJECT_ID.iam.gserviceaccount.com"

# List of all secrets to grant access to
SECRETS="weaviate-url weaviate-api-key huggingface-api-key langchain-api-key"

# Add optional secrets if they exist
if [ ! -z "$ELEVENLABS_API_KEY" ]; then
    SECRETS="$SECRETS elevenlabs-api-key"
fi
if [ ! -z "$GROQ_API_KEY" ]; then
    SECRETS="$SECRETS groq-api-key"
fi

# Grant access to secrets
for secret in $SECRETS; do
    echo "  Granting access to $secret..."
    gcloud secrets add-iam-policy-binding $secret \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID \
        --quiet
done

echo "✅ Secrets configured successfully!"
echo ""
echo "Now deploy using: gcloud builds submit --config cloudbuild-secure.yaml"