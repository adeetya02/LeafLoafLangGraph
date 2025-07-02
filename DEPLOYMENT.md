# Production Deployment Guide

## Overview

This guide ensures secure production deployment with **NO hardcoded values**.

## Prerequisites

1. **Google Cloud SDK** installed and authenticated
2. **Project access** to `leafloafai`
3. **`.env.yaml`** file with production values (never commit this!)

## Environment Setup

### 1. Create `.env.yaml` from template

```bash
cp .env.production.yaml.template .env.yaml
# Edit .env.yaml with your actual values
```

### 2. Verify no hardcoded values

```bash
# This should return nothing:
grep -r "https://.*weaviate" src/ --include="*.py" | grep -v "settings"
grep -r "hf_[a-zA-Z0-9]" src/ --include="*.py" | grep -v "settings"
grep -r "sk_[a-zA-Z0-9]" src/ --include="*.py" | grep -v "settings"
```

## Deployment Options

### Option A: Automated Secure Deployment (Recommended)

```bash
# This script handles everything:
./deploy-production.sh
```

This script:
- ✅ Checks prerequisites
- ✅ Sets up Google Secret Manager
- ✅ Deploys with secure environment variables
- ✅ No hardcoded values anywhere

### Option B: Manual Deployment

1. **Set up secrets**:
   ```bash
   ./setup-secrets.sh
   ```

2. **Deploy**:
   ```bash
   gcloud builds submit --config cloudbuild-secure.yaml
   ```

## Testing Production

```bash
# Get your service URL
SERVICE_URL=$(gcloud run services describe leafloaf --region us-central1 --format 'value(status.url)')

# Test it
python test_production.py $SERVICE_URL
```

## Environment Variables

All sensitive values are stored in Google Secret Manager:

| Variable | Secret Name | Description |
|----------|------------|-------------|
| WEAVIATE_URL | weaviate-url | Weaviate instance URL |
| WEAVIATE_API_KEY | weaviate-api-key | Weaviate authentication |
| HUGGINGFACE_API_KEY | huggingface-api-key | HuggingFace API access |
| LANGCHAIN_API_KEY | langchain-api-key | LangSmith tracing |
| ELEVENLABS_API_KEY | elevenlabs-api-key | Voice synthesis |
| GROQ_API_KEY | groq-api-key | Groq LLM access |

## Security Best Practices

1. **Never commit** `.env.yaml` or `.env.production.yaml`
2. **Use Secret Manager** for all sensitive values
3. **Rotate keys** regularly
4. **Monitor access** via Cloud Console
5. **Use service accounts** with minimal permissions

## Troubleshooting

### Search returns no results
1. Check Weaviate connection in health endpoint
2. Verify WEAVIATE_URL and WEAVIATE_API_KEY are set
3. Check Cloud Run logs: `gcloud run logs read leafloaf --region us-central1`

### Environment variables missing
1. Check Secret Manager: `gcloud secrets list`
2. Verify service account permissions
3. Check Cloud Run configuration: `gcloud run services describe leafloaf --region us-central1`

### Connection errors
1. Ensure Weaviate instance is accessible from Cloud Run
2. Check network/firewall settings
3. Verify API keys are valid

## Monitoring

- **Logs**: Cloud Console → Cloud Run → leafloaf → Logs
- **Metrics**: Cloud Console → Cloud Run → leafloaf → Metrics
- **Traces**: [LangSmith Dashboard](https://smith.langchain.com)

## Rollback

```bash
# List all revisions
gcloud run revisions list --service leafloaf --region us-central1

# Route traffic to previous revision
gcloud run services update-traffic leafloaf \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```