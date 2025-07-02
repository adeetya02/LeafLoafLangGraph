# GCP Deployment Final Checklist

## ✅ Code Ready
- [x] Clean architecture (no test files)
- [x] Constants centralized in `constants.py`
- [x] Fast mode supervisor (<50ms local)
- [x] Test mode for local development
- [x] Docker file with health check
- [x] .gcloudignore configured
- [x] .env.yaml with all keys

## ⚠️ Things to Check Before Deploy

### 1. API Keys in .env.yaml
```yaml
✅ WEAVIATE_API_KEY (credits back tomorrow - 2k limit)
✅ HUGGINGFACE_API_KEY (for Zephyr now, Gemma later)  
✅ LANGCHAIN_API_KEY (for tracing)
✅ ELEVENLABS_API_KEY (for voice later)
⚠️ Missing: GCP_PROJECT_ID (add before deploy)
```

### 2. Dependencies
```bash
# Make sure requirements.txt has everything
✅ google-cloud-aiplatform (for Vertex AI)
❌ google-cloud-firestore (add if using Firestore)
❌ google-cloud-storage (add if using GCS)
```

### 3. Environment Variables
```yaml
Current Settings:
- ENVIRONMENT: "production" ✅
- FAST_MODE: "false" (full LLM) ✅
- TEST_MODE: "true" (until Weaviate credits) ✅
```

### 4. GCP Services to Enable
```bash
# Run these before deploying:
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  aiplatform.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com
```

### 5. Potential Issues & Solutions

**Memory**: Start with 1Gi, increase if needed
**Timeout**: 60s should be enough with Zephyr
**Cold Starts**: Min instances 0 is fine for now
**Region**: us-central1 (same as Vertex AI)

## 🚀 Deployment Commands

```bash
# 1. Set project (IMPORTANT - add your project ID)
export PROJECT_ID="your-gcp-project-id"  # <-- CHANGE THIS
gcloud config set project $PROJECT_ID

# 2. Add PROJECT_ID to env file
echo "  GCP_PROJECT_ID: \"$PROJECT_ID\"" >> .env.yaml

# 3. Build & Deploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/leafloaf
gcloud run deploy leafloaf \
  --image gcr.io/$PROJECT_ID/leafloaf \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file .env.yaml \
  --memory 1Gi \
  --timeout 60 \
  --max-instances 2

# 4. Get URL
echo "Service URL:"
gcloud run services describe leafloaf \
  --region us-central1 \
  --format 'value(status.url)'
```

## 📊 After Deployment

1. **Test endpoints**:
   - `/health`
   - `/api/v1/search`
   - `/docs` (FastAPI docs)

2. **Monitor logs**:
   ```bash
   gcloud run logs tail leafloaf --region us-central1
   ```

3. **Check costs** (should be ~$0 on free tier)

## 🔄 Tomorrow's Plan

When Weaviate credits are back:
1. Set `TEST_MODE: "false"` in Cloud Run
2. Test real product searches
3. Monitor latency (expect 200-500ms)
4. Then switch to Vertex AI Gemma

## Nothing Missing! Ready to Deploy! 🎉