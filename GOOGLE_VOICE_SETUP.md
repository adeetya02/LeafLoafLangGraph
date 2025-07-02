# Google Cloud Voice Setup Guide

## Overview
This guide helps you set up Google Cloud Speech-to-Text and Text-to-Speech for the voice-native supervisor.

## Prerequisites
1. Google Cloud Project
2. Billing enabled on the project
3. gcloud CLI installed

## Step 1: Enable Required APIs

```bash
# Enable Speech-to-Text API
gcloud services enable speech.googleapis.com

# Enable Text-to-Speech API  
gcloud services enable texttospeech.googleapis.com

# Enable Vertex AI (for Gemini models)
gcloud services enable aiplatform.googleapis.com
```

## Step 2: Create Service Account

```bash
# Create service account
gcloud iam service-accounts create leafloaf-voice \
    --display-name="LeafLoaf Voice Service"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:leafloaf-voice@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.client"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:leafloaf-voice@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/texttospeech.client"

# Download key
gcloud iam service-accounts keys create leafloaf-voice-key.json \
    --iam-account=leafloaf-voice@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

## Step 3: Set Environment Variables

```bash
# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/leafloaf-voice-key.json"

# Set project ID
export GCP_PROJECT_ID="YOUR_PROJECT_ID"
export GCP_LOCATION="us-central1"
```

## Step 4: Test Voice Integration

```bash
# Run test script
python test_voice_google_unified.py

# Expected output:
# ✅ All imports successful
# ✅ TTS generated audio
# ✅ Voice metadata extracted
# ✅ Routing decision made
# ✅ Multi-language support working
```

## Step 5: Run the Server

```bash
# Start the server
python run.py

# Access voice interface
# http://localhost:8000/static/voice_google_test.html
```

## Voice Features

### 1. Multi-Language Support
- 17+ languages including English, Spanish, Hindi, Chinese, Korean, etc.
- Automatic language detection
- Cultural context awareness

### 2. Voice Metadata Processing
- **Pace**: Fast/Normal/Slow → Influences search strategy
- **Emotion**: Neutral/Excited/Frustrated/Confused → Affects response tone
- **Clarity**: Low/Medium/High → Confidence in understanding
- **Stress Level**: Relaxed/Normal/Stressed → Response adaptation

### 3. Voice-Aware Routing
- Fast pace + urgency → Quick keyword search (α=0.3)
- Slow pace + exploration → Semantic search (α=0.7)
- Confusion detected → Offer clarification
- Frustration detected → Empathetic response

### 4. Natural Conversation
- Multi-turn dialogue support
- Context carryover between turns
- Interruption handling
- Clarification requests

## API Endpoints

### WebSocket: `/api/v1/voice/google/ws`
Real-time voice conversation with streaming STT/TTS

### GET: `/api/v1/voice/google/languages`
List of supported languages

### GET: `/api/v1/voice/google/voices?language=en-US`
Available voices for a language

## WebSocket Protocol

### Client → Server
```json
// Audio stream
{"type": "audio", "audio": "base64_encoded_audio"}

// Text input
{"type": "text", "text": "Show me milk"}

// Configuration
{"type": "config", "config": {"language": "es-US"}}

// End stream
{"type": "end_stream"}
```

### Server → Client
```json
// Transcript
{
  "type": "transcript",
  "text": "Show me milk",
  "is_final": true,
  "confidence": 0.95,
  "language": "en-US"
}

// Response
{
  "type": "response",
  "text": "I found 15 milk products...",
  "metadata": {
    "intent": "search",
    "confidence": 0.9,
    "products_found": 15,
    "execution_time": 250
  }
}

// Audio response
{
  "type": "audio_response",
  "audio": "base64_encoded_tts",
  "format": {
    "encoding": "LINEAR16",
    "sample_rate": 24000,
    "channels": 1
  }
}
```

## Cost Estimates

### Speech-to-Text
- First 60 minutes/month: Free
- After: $0.006 per 15 seconds

### Text-to-Speech
- First 1 million characters/month: Free (Standard voices)
- After: $4 per million characters

### Typical Usage
- 1000 voice queries/day ≈ $10-15/month
- Mostly covered by free tier for development

## Troubleshooting

### 1. "Permission denied" error
```bash
# Ensure APIs are enabled
gcloud services list --enabled | grep -E "(speech|texttospeech)"

# Check service account permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:leafloaf-voice@"
```

### 2. Audio not playing in browser
- Check browser console for errors
- Ensure audio context is created after user interaction
- Try different audio format (change sample rate)

### 3. Language not detected correctly
- Speak clearly for first 2-3 seconds
- Specify language hint in initial connection
- Check microphone quality

### 4. High latency
- Use regional endpoints closer to users
- Enable streaming recognition
- Optimize audio chunk size (4096 bytes recommended)

## Best Practices

1. **Privacy**: Don't log audio data
2. **Error Handling**: Graceful fallbacks for API failures
3. **Cost Control**: Set quotas and alerts
4. **Performance**: Cache TTS for common responses
5. **Accessibility**: Provide text alternatives

## Next Steps

1. **Production Setup**
   - Use Cloud Run for deployment
   - Set up load balancing
   - Enable Cloud CDN for static assets

2. **Advanced Features**
   - Speaker diarization (multiple speakers)
   - Custom voice models
   - Real-time translation
   - Emotion detection models

3. **Monitoring**
   - Set up Cloud Monitoring dashboards
   - Track language usage patterns
   - Monitor API quotas