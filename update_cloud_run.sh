#!/bin/bash

# Quick update to Cloud Run configuration without rebuilding

echo "=========================================="
echo "🚀 UPDATING CLOUD RUN CONFIGURATION"
echo "=========================================="

SERVICE_NAME="leafloaf"
REGION="us-central1"

echo "Updating Cloud Run service with optimized settings..."
gcloud run services update $SERVICE_NAME \
  --region $REGION \
  --memory 4Gi \
  --cpu 2 \
  --cpu-boost \
  --min-instances 1 \
  --max-instances 10 \
  --execution-environment gen2

echo -e "\n✅ Configuration updated!"
echo "Changes:"
echo "  - Min instances: 1 (no more cold starts)"
echo "  - Memory: 4Gi (more headroom)"
echo "  - CPU boost: enabled (faster startup)"
echo "  - Execution environment: gen2 (better performance)"

echo -e "\n🎯 This should improve latency by:"
echo "  - Eliminating cold starts (~100-200ms saved)"
echo "  - Faster CPU during startup"
echo "  - Better memory management"