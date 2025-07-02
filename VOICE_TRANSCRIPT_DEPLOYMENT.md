# Voice Transcript Processing - GCP Deployment Guide

## Architecture Overview

```
User Voice → WebSocket → Cloud Storage → Pub/Sub → Cloud Function → BigQuery
                ↓                                           ↓
            Real-time Response                    Deepgram Analysis
```

## 1. Prerequisites

```bash
# Set your project
export PROJECT_ID=leafloaf-prod
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable storage.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudrun.googleapis.com
```

## 2. Create Cloud Storage Bucket

```bash
# Create bucket for voice transcripts
gsutil mb -p $PROJECT_ID -c standard -l us-central1 gs://leafloaf-voice/

# Set lifecycle rule to move old transcripts to coldline
cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 90}
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://leafloaf-voice/
```

## 3. Create Pub/Sub Topic

```bash
# Create topic for transcript processing
gcloud pubsub topics create voice-transcripts

# Create subscription (for debugging/monitoring)
gcloud pubsub subscriptions create voice-transcripts-debug \
  --topic=voice-transcripts \
  --ack-deadline=60
```

## 4. Create BigQuery Tables

```bash
# Run the SQL script in BigQuery console
# Or use bq command line:
bq mk --dataset --location=us-central1 leafloaf_analytics

# Then run the SQL from scripts/create_voice_tables.sql
```

## 5. Deploy Cloud Function

```bash
cd functions/process_voice_transcript

# Deploy the function
gcloud functions deploy process-voice-transcript \
  --gen2 \
  --runtime=python311 \
  --region=us-central1 \
  --source=. \
  --entry-point=process_transcript \
  --trigger-topic=voice-transcripts \
  --set-env-vars="DEEPGRAM_API_KEY=$DEEPGRAM_API_KEY,GCP_PROJECT_ID=$PROJECT_ID" \
  --memory=512MB \
  --timeout=60s
```

## 6. Update Cloud Run Service

```bash
# Add environment variables to your Cloud Run service
gcloud run services update leafloaf \
  --add-env-vars="VOICE_BUCKET=leafloaf-voice,VOICE_TOPIC=voice-transcripts,GCP_PROJECT_ID=$PROJECT_ID" \
  --region=us-central1
```

## 7. IAM Permissions

```bash
# Grant Cloud Run service account permissions
export SERVICE_ACCOUNT=leafloaf@$PROJECT_ID.iam.gserviceaccount.com

# Storage permissions
gsutil iam ch serviceAccount:$SERVICE_ACCOUNT:objectCreator gs://leafloaf-voice
gsutil iam ch serviceAccount:$SERVICE_ACCOUNT:objectViewer gs://leafloaf-voice

# Pub/Sub permissions
gcloud pubsub topics add-iam-policy-binding voice-transcripts \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/pubsub.publisher"

# BigQuery permissions
bq add-iam-policy-binding \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/bigquery.dataEditor" \
  leafloaf_analytics
```

## 8. Testing

```bash
# Test the full flow
curl -X POST https://your-cloud-run-url/api/v1/voice-conv/test-capture \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "transcript": "I need organic milk",
    "response": "Here are organic milk options..."
  }'

# Check Cloud Storage
gsutil ls -r gs://leafloaf-voice/transcripts/

# Check Pub/Sub messages
gcloud pubsub subscriptions pull voice-transcripts-debug --limit=10

# Check BigQuery
bq query --use_legacy_sql=false \
  'SELECT * FROM leafloaf_analytics.voice_conversations LIMIT 10'
```

## 9. Monitoring

```bash
# View Cloud Function logs
gcloud functions logs read process-voice-transcript --limit=50

# Set up alerts for failures
gcloud alpha monitoring policies create \
  --notification-channels=$CHANNEL_ID \
  --display-name="Voice Transcript Processing Failures" \
  --condition-display-name="Function Error Rate > 5%" \
  --condition-error-rate-trigger \
  --condition-error-rate-trigger-count=5
```

## 10. Cost Optimization

- **Cloud Storage**: ~$0.02/GB/month for standard, $0.004/GB/month for coldline
- **Pub/Sub**: ~$0.05/GB after 10GB free
- **Cloud Function**: ~$0.40/million invocations + compute time
- **BigQuery**: ~$5/TB for queries, $0.02/GB/month storage
- **Deepgram**: ~$0.0125/minute for transcription

### Optimizations:
1. Batch transcripts before sending to Deepgram
2. Use BigQuery partitioning and clustering
3. Archive old transcripts to coldline storage
4. Use Cloud Scheduler to process in batches during off-peak

## Local Development

For local testing, you can use the local file-based processor:

```python
# Use local processor
from src.services.transcript_processor import TranscriptProcessor

# Or use GCP processor with emulators
from src.services.gcp_transcript_service import GCPTranscriptService
```

## Environment Variables

Add to `.env.yaml`:

```yaml
# Voice transcript processing
VOICE_BUCKET: "leafloaf-voice"
VOICE_TOPIC: "voice-transcripts"
GCP_PROJECT_ID: "leafloaf-prod"
```

## Next Steps

1. **Add Graphiti Integration**: Send processed insights to Graphiti for memory
2. **Real-time Dashboard**: Use BigQuery BI Engine for voice analytics
3. **ML Pipeline**: Use processed transcripts for training personalization models
4. **Multi-language**: Add language detection and translation