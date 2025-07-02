# Secure Deployment Guide for LeafLoaf

## Setting up Environment Variables in Google Cloud Run

### Step 1: Store Secrets in Google Secret Manager

```bash
# Create secrets in Secret Manager
echo -n "your-weaviate-api-key" | gcloud secrets create weaviate-api-key --data-file=-
echo -n "your-huggingface-api-key" | gcloud secrets create huggingface-api-key --data-file=-
echo -n "your-deepgram-api-key" | gcloud secrets create deepgram-api-key --data-file=-
echo -n "your-langchain-api-key" | gcloud secrets create langchain-api-key --data-file=-
echo -n "your-groq-api-key" | gcloud secrets create groq-api-key --data-file=-
echo -n "your-elevenlabs-api-key" | gcloud secrets create elevenlabs-api-key --data-file=-
```

### Step 2: Deploy with Secrets

```bash
gcloud run deploy leafloaf \
  --image gcr.io/leafloafai/leafloaf-voice-v2 \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 600 \
  --max-instances 10 \
  --set-env-vars="ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT=leafloafai,WEAVIATE_URL=https://7cijosfpsryfteazzawhjw.c0.us-east1.gcp.weaviate.cloud" \
  --set-secrets="WEAVIATE_API_KEY=weaviate-api-key:latest,HUGGINGFACE_API_KEY=huggingface-api-key:latest,DEEPGRAM_API_KEY=deepgram-api-key:latest,LANGCHAIN_API_KEY=langchain-api-key:latest,GROQ_API_KEY=groq-api-key:latest,ELEVENLABS_API_KEY=elevenlabs-api-key:latest"
```

### Step 3: For Local Development

1. Copy `.env.yaml.example` to `.env.yaml`
2. Fill in your actual API keys
3. Never commit `.env.yaml` to git

### Step 4: GitHub Actions Deployment

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - id: 'auth'
      uses: 'google-github-actions/auth@v2'
      with:
        credentials_json: '${{ secrets.GCP_SA_KEY }}'
    
    - name: 'Set up Cloud SDK'
      uses: 'google-github-actions/setup-gcloud@v2'
    
    - name: 'Build and push image'
      run: |
        gcloud builds submit --tag gcr.io/leafloafai/leafloaf
    
    - name: 'Deploy to Cloud Run'
      run: |
        gcloud run deploy leafloaf \
          --image gcr.io/leafloafai/leafloaf \
          --platform managed \
          --region us-central1 \
          --allow-unauthenticated
```

## Security Best Practices

1. **Never commit secrets** - Use `.gitignore`
2. **Use Secret Manager** - For production deployments
3. **Rotate keys regularly** - Update in Secret Manager
4. **Use service accounts** - For GCP authentication
5. **Enable audit logging** - Track secret access

## Current Secrets to Migrate

- WEAVIATE_API_KEY
- HUGGINGFACE_API_KEY  
- ELEVENLABS_API_KEY
- GROQ_API_KEY
- DEEPGRAM_API_KEY
- LANGCHAIN_API_KEY
- NEO4J_PASSWORD