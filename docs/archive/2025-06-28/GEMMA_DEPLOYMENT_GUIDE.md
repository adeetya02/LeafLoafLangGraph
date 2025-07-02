# Gemma Model Garden Deployment Guide

## Overview
This guide will help you deploy Gemma 2 9B through Model Garden and prepare it for fine-tuning with your supplier data.

## Step 1: Access Model Garden

1. **Go to Model Garden**: 
   ```
   https://console.cloud.google.com/vertex-ai/model-garden?project=leafloafai
   ```

2. **Search for Gemma**:
   - In the search bar, type "Gemma"
   - Look for "Gemma 2" models
   - You should see options like:
     - Gemma 2 2B
     - Gemma 2 9B ← **Select this one**
     - Gemma 2 27B

## Step 2: Deploy Gemma 2 9B

1. **Click on "Gemma 2 9B"** model card

2. **Click "Deploy" button**

3. **Configure Deployment**:
   ```yaml
   Endpoint name: leafloaf-gemma-9b-endpoint
   
   Machine Configuration:
   - Machine type: g2-standard-8
   - Accelerator: NVIDIA L4 GPU (1x)
   - Min replicas: 1
   - Max replicas: 2
   
   Advanced Settings:
   - Enable logging: Yes
   - Enable request-response logging: Yes
   ```

4. **Estimated Costs**:
   - ~$1.50/hour when running
   - Scales down to 0 when not in use (with min_replicas=0)

5. **Click "Deploy"** (takes 10-15 minutes)

## Step 3: Prepare Training Data

Run the training data preparation script:

```bash
cd /Users/adi/Desktop/LeafLoafLangGraph
python3 scripts/prepare_training_data.py
```

This creates:
- `training_data/grocery_conversations_train.jsonl`
- `training_data/grocery_conversations_val.jsonl`

## Step 4: Upload Supplier Data

1. **Create a Cloud Storage bucket**:
   ```bash
   gsutil mb -p leafloafai -l us-central1 gs://leafloaf-training-data
   ```

2. **Upload training files**:
   ```bash
   gsutil cp training_data/*.jsonl gs://leafloaf-training-data/
   ```

3. **Add your supplier data**:
   Create a file `supplier_training_data.jsonl` with your supplier-specific examples:
   
   ```json
   {"messages": [
     {"role": "system", "content": "You are a grocery assistant with knowledge of LeafLoaf suppliers."},
     {"role": "user", "content": "What Organic Valley products do you have?"},
     {"role": "assistant", "content": "{\"intent\": \"supplier_search\", \"supplier\": \"Organic Valley\", \"confidence\": 0.95}"}
   ]}
   ```

## Step 5: Fine-tune the Model

### Option A: Through Console UI

1. Go to **Model Registry**: 
   ```
   https://console.cloud.google.com/vertex-ai/model-registry?project=leafloafai
   ```

2. Find your deployed Gemma model

3. Click **"Fine-tune"**

4. Configure fine-tuning:
   ```yaml
   Training data: gs://leafloaf-training-data/grocery_conversations_train.jsonl
   Validation data: gs://leafloaf-training-data/grocery_conversations_val.jsonl
   
   Hyperparameters:
   - Learning rate: 2e-5
   - Train epochs: 3
   - Batch size: 4
   - Warmup steps: 100
   
   Output model name: leafloaf-gemma-9b-finetuned
   ```

### Option B: Using Python SDK

Create `fine_tune_gemma.py`:

```python
from google.cloud import aiplatform

aiplatform.init(project="leafloafai", location="us-central1")

# Start fine-tuning job
job = aiplatform.CustomTrainingJob(
    display_name="leafloaf-gemma-finetuning",
    script_path="train.py",
    container_uri="us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.1-13:latest",
    requirements=["transformers", "datasets", "peft"],
)

model = job.run(
    dataset=dataset,
    model_display_name="leafloaf-gemma-finetuned",
    machine_type="n1-highmem-8",
    accelerator_type="NVIDIA_TESLA_T4",
    accelerator_count=1,
)
```

## Step 6: Update Your Code

Once deployed, update `gemma_deployment_info.json`:

```json
{
  "endpoint_id": "projects/123/locations/us-central1/endpoints/456",
  "endpoint_resource_name": "projects/leafloafai/locations/us-central1/endpoints/456",
  "model_id": "projects/123/locations/us-central1/models/789",
  "project_id": "leafloafai",
  "location": "us-central1",
  "deployed_at": "2024-01-24 00:00:00",
  "model_name": "gemma-2-9b-it",
  "fine_tuned": true
}
```

## Step 7: Test Deployment

```bash
# Quick test
curl -X POST \
  https://us-central1-aiplatform.googleapis.com/v1/projects/leafloafai/locations/us-central1/endpoints/YOUR_ENDPOINT_ID:predict \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{
      "prompt": "What Organic Valley products do you have?",
      "temperature": 0.7,
      "max_tokens": 256
    }]
  }'
```

## Benefits of Model Garden Deployment

1. **Fine-tuning Capability**: Train on your supplier data
2. **Better Performance**: Dedicated GPU resources
3. **Custom Optimization**: Tune for your specific use cases
4. **Version Control**: Deploy multiple versions
5. **A/B Testing**: Route traffic between models
6. **Monitoring**: Built-in metrics and logging

## Next Steps

1. Deploy through Model Garden UI (easiest)
2. Prepare comprehensive supplier training data
3. Fine-tune with your data
4. Update `gemma_client_v2.py` to use the endpoint
5. Implement Redis caching for responses
6. Monitor performance improvements

## Estimated Timeline

- Model deployment: 15 minutes
- Data preparation: 1-2 hours
- Fine-tuning: 2-4 hours
- Integration: 30 minutes
- Total: ~1 day

## Cost Optimization

- Use `min_replicas: 0` for auto-scaling to zero
- Schedule scaling for business hours only
- Cache responses in Redis
- Batch requests when possible