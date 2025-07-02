# Deploy Gemma 2 9B on Vertex AI Model Garden

## Step 1: Enable Required APIs

```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Enable Compute Engine API (required for deployment)
gcloud services enable compute.googleapis.com

# Set your project
gcloud config set project leafloafai
```

## Step 2: Access Model Garden

1. Go to Google Cloud Console: https://console.cloud.google.com
2. Navigate to Vertex AI → Model Garden
3. Search for "Gemma 2"
4. Select "Gemma 2 9B IT" (Instruction Tuned version)

## Step 3: Deploy the Model

### Option A: Through Console UI
1. Click on "Gemma 2 9B IT" in Model Garden
2. Click "Deploy"
3. Configure deployment:
   - Endpoint name: `gemma-2-9b-endpoint`
   - Region: `us-central1`
   - Machine type: `n1-standard-8` (or `g2-standard-8` for GPU)
   - Accelerator: Optional - add 1 x NVIDIA L4 for faster inference
   - Min replicas: 1
   - Max replicas: 2

### Option B: Through gcloud CLI

```bash
# First, get the model resource name from Model Garden
# It should look like: projects/PROJECT_ID/locations/us-central1/models/MODEL_ID

# Create an endpoint
gcloud ai endpoints create \
  --region=us-central1 \
  --display-name=gemma-2-9b-endpoint

# Deploy the model to endpoint
gcloud ai models deploy MODEL_ID \
  --region=us-central1 \
  --endpoint=ENDPOINT_ID \
  --deployed-model-display-name=gemma-2-9b \
  --machine-type=n1-standard-8 \
  --min-replica-count=1 \
  --max-replica-count=2 \
  --traffic-split=0=100
```

## Step 4: Wait for Deployment
- Deployment typically takes 10-15 minutes
- You'll see the status in Vertex AI → Endpoints

## Step 5: Get Endpoint Details
Once deployed, note down:
- Endpoint ID
- Endpoint resource name
- Region

## Step 6: Test the Endpoint

```python
from google.cloud import aiplatform

aiplatform.init(project='leafloafai', location='us-central1')

endpoint = aiplatform.Endpoint('YOUR_ENDPOINT_ID')

# Test prediction
response = endpoint.predict(
    instances=[{
        "prompt": "What is the capital of France?",
        "max_tokens": 100
    }]
)
print(response)
```

## Estimated Costs
- Deployment: ~$0.60/hour for n1-standard-8
- With GPU (L4): ~$1.20/hour
- Inference: ~$0.00025 per 1K characters

## Next Steps
Once deployed, we'll update the code to use this endpoint instead of the Generative AI API.