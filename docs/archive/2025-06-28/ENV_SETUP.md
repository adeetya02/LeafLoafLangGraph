# Environment Setup

## Important: Never commit secrets to git!

### Local Development

1. Copy the template file:
```bash
cp .env.yaml.template .env.yaml
```

2. Fill in your actual API keys in `.env.yaml`

3. The `.env.yaml` file is gitignored and should never be committed

### Production Deployment (GCP)

For Cloud Run deployment, set environment variables directly:

```bash
gcloud run services update leafloaf \
    --update-env-vars \
    WEAVIATE_URL=your-url,\
    WEAVIATE_API_KEY=your-key,\
    HUGGINGFACE_API_KEY=your-key,\
    ELEVENLABS_API_KEY=your-key,\
    LANGCHAIN_API_KEY=your-key
```

Or use Secret Manager (recommended):

```bash
# Create secrets
echo -n "your-api-key" | gcloud secrets create weaviate-api-key --data-file=-
echo -n "your-api-key" | gcloud secrets create huggingface-api-key --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding weaviate-api-key \
    --member=serviceAccount:YOUR-SERVICE-ACCOUNT \
    --role=roles/secretmanager.secretAccessor

# Use in Cloud Run
gcloud run services update leafloaf \
    --update-secrets=WEAVIATE_API_KEY=weaviate-api-key:latest
```

### Environment Variables

See `.env.yaml.template` for all required variables.

### Security Best Practices

1. Never commit `.env.yaml` or any file with secrets
2. Use Secret Manager for production
3. Rotate keys regularly
4. Use different keys for dev/staging/prod
5. Monitor key usage in provider dashboards