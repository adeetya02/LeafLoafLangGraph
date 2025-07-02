# Request A2 Quota for Gemma 2 9B Deployment

## Current Status
- **A2_CPUS**: 0 (need 12)
- **NVIDIA_A100_GPUS**: 0 (need 1) 
- **Region**: us-central1

## Request Quota Increase

### Option 1: Through Console (Fastest)
1. Go to: https://console.cloud.google.com/iam-admin/quotas
2. Search for "A2_CPUS"
3. Select "Compute Engine API" → "A2_CPUS" → "us-central1"
4. Click "EDIT QUOTAS"
5. Request: **12 A2_CPUS**
6. Justification: "Machine learning model deployment for Gemma 2 9B"

### Option 2: Through gcloud
```bash
# Request A2 CPU quota
gcloud services enable compute.googleapis.com
gcloud alpha quotas update --service=compute.googleapis.com \
  --quota-rule=limit=us-central1:a2_cpus:12 \
  --consumer=leafloafai
```

### Option 3: Alternative Machine Types (if A2 denied)

If A2 quota is denied, alternatives:

1. **n1-highmem-8 + T4 GPU** (cheaper option)
   - CPUs: 8 (you have 24 available ✅)
   - GPU: 1x NVIDIA T4 (you have 1 available ✅)
   - Cost: ~$1.00/hour vs $3.00/hour for A2

2. **g2-standard-8** (GPU optimized)
   - CPUs: 8 ✅
   - GPU: 1x NVIDIA L4 (you have 1 available ✅)  
   - Cost: ~$1.50/hour

## Recommended Action

**Start with n1-highmem-8 + T4** to test immediately:
- No quota increase needed
- Works for Gemma 2 9B (slower but functional)
- Much cheaper for testing
- Can upgrade to A2 later

## Deployment Commands

### For n1-highmem-8 + T4 (immediate):
```bash
# Deploy endpoint with T4 GPU
gcloud ai endpoints create --region=us-central1 --display-name=gemma-t4-endpoint

# Deploy model (when available in Model Garden)
gcloud ai models deploy MODEL_ID \
  --region=us-central1 \
  --endpoint=ENDPOINT_ID \
  --machine-type=n1-highmem-8 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --min-replica-count=1 \
  --max-replica-count=1
```

### For A2 (after quota approval):
```bash
# Deploy with A2 (much faster)
gcloud ai models deploy MODEL_ID \
  --region=us-central1 \
  --endpoint=ENDPOINT_ID \
  --machine-type=a2-highgpu-1g \
  --min-replica-count=1 \
  --max-replica-count=1
```

## Cost Comparison
- **T4 option**: ~$1.00/hour (testing friendly)
- **A2 option**: ~$3.00/hour (production ready)
- **L4 option**: ~$1.50/hour (balanced)

## Next Steps
1. Try deploying with **n1-highmem-8 + T4** first (no quota needed)
2. Request A2 quota in parallel for later upgrade
3. Test integration with whatever works first