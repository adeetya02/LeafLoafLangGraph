# GCP Deployment - Step by Step

## Step 1: Prepare for GCP Deployment

### 1.1 Update .gcloudignore
```bash
# Check what will be deployed
cat .gcloudignore
```

### 1.2 Create Production Environment File
```bash
# Copy the production template
cp .env.production.yaml .env.yaml

# Update with your actual values:
# - Keep FAST_MODE: "false" for full Gemma
# - Keep TEST_MODE: "false" for real Weaviate
# - Add your API keys
```

### 1.3 Test Locally with Production Settings
```bash
# Test with production config
FAST_MODE=false TEST_MODE=false python3 run.py

# This will use:
# - Real Gemma/Zephyr calls
# - Real Weaviate (if credits available)
```

## Step 2: Deploy to Cloud Run

### 2.1 Set GCP Project
```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  aiplatform.googleapis.com
```

### 2.2 Build and Deploy
```bash
# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/leafloaf

# Deploy to Cloud Run
gcloud run deploy leafloaf \
  --image gcr.io/$PROJECT_ID/leafloaf \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file .env.yaml \
  --memory 1Gi \
  --timeout 60 \
  --max-instances 2
```

### 2.3 Test Deployed Service
```bash
# Get the URL
export SERVICE_URL=$(gcloud run services describe leafloaf --region us-central1 --format 'value(status.url)')

# Test health
curl $SERVICE_URL/health

# Test search
curl -X POST $SERVICE_URL/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "organic milk", "session_id": "test-gcp"}'
```

## Step 3: Switch to Vertex AI Gemma

### 3.1 Enable Vertex AI
```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Set up service account (if needed)
gcloud iam service-accounts create leafloaf-vertex \
  --display-name="LeafLoaf Vertex AI Service"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:leafloaf-vertex@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

### 3.2 Update Gemma Client for Vertex AI
```python
# src/integrations/gemma_client.py
class GemmaClient:
    def __init__(self):
        self.environment = ENVIRONMENT
        
        if self.environment == "production":
            # Use Vertex AI
            from google.cloud import aiplatform
            aiplatform.init(
                project=os.getenv("GCP_PROJECT_ID"),
                location="us-central1"
            )
            self.use_vertex = True
        else:
            # Use HuggingFace
            self.use_vertex = False
            self.hf_api_key = settings.huggingface_api_key
            
    async def analyze_query(self, query: str, context: Optional[Dict] = None):
        if self.use_vertex:
            return await self._call_vertex_ai(query, context)
        else:
            return await self._call_huggingface(query, context)
```

### 3.3 Test Gemma Integration
```bash
# Deploy with Vertex AI enabled
gcloud run deploy leafloaf \
  --image gcr.io/$PROJECT_ID/leafloaf \
  --set-env-vars ENVIRONMENT=production,GCP_PROJECT_ID=$PROJECT_ID

# Monitor logs
gcloud run logs read --service leafloaf --region us-central1
```

## Step 4: Monitor and Validate

### 4.1 Check Latency
```bash
# Run latency test against GCP
python3 test_all_scenarios_with_metrics.py \
  --url $SERVICE_URL/api/v1
```

### 4.2 Monitor Costs
```bash
# Check Cloud Run costs
gcloud billing accounts list

# Check Vertex AI usage
gcloud ai models list --region=us-central1
```

### 4.3 Set Up Monitoring
```bash
# Create uptime check
gcloud monitoring uptime create leafloaf \
  --resource-type=gae-app \
  --http-check-path=/health \
  --check-interval=5m
```

## Step 5: Troubleshooting

### Common Issues:

1. **Timeout errors**
   - Increase Cloud Run timeout: `--timeout 300`
   - Check Gemma response times in logs

2. **Memory errors**
   - Increase memory: `--memory 2Gi`
   - Check for memory leaks

3. **Weaviate connection fails**
   - Verify API keys in .env.yaml
   - Check network connectivity
   - Confirm credits available

4. **Gemma not working**
   - Verify Vertex AI is enabled
   - Check service account permissions
   - Review quota limits

## Next Steps (After Everything Works)

Only after confirming all components work on GCP:

1. ✅ Cloud Run deployment successful
2. ✅ Gemma on Vertex AI responding
3. ✅ Weaviate searches working (or mock data)
4. ✅ Latency acceptable (<1s)

THEN we can:
- Add Redis caching layer
- Implement ML features
- Set up 11Labs
- Add personalization

## DO NOT proceed to Redis until basic GCP deployment is stable!