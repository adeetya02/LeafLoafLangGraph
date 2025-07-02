# Deepgram Voice Solution for LeafLoaf

## Overview
We've implemented an HTTP-based voice solution using Deepgram that works with Google Cloud Run's limitations (no WebSocket support).

## Architecture
1. **HTTP Polling**: Instead of WebSockets, we use HTTP endpoints for voice processing
2. **Deepgram REST API**: Uses Deepgram's REST API for transcription
3. **Session Management**: In-memory session storage for conversation context
4. **Cloud Run Compatible**: Works within Cloud Run's request/response model

## Endpoints

### Start Session
```bash
POST /api/v1/voice-http/start-session
{
  "user_id": "demo_user"
}
```

### Process Audio
```bash
POST /api/v1/voice-http/process-audio/{session_id}
{
  "audio": "base64_encoded_audio",
  "format": "webm"
}
```

## Demo URL
- Local: http://localhost:8080/voice_demo_deepgram.html
- Production: https://leafloaf-32905605817.us-central1.run.app/voice_demo_deepgram.html

## Features
1. **Voice Transcription**: Using Deepgram's Nova 2 model
2. **Product Search**: Transcribed text is processed through LangGraph
3. **Voice Response**: Text responses (TTS can be added)
4. **Test Mode**: Built-in test buttons for quick testing

## Deployment
```bash
# Set environment variable
export DEEPGRAM_API_KEY="your_key_here"

# Deploy to Cloud Run
gcloud run deploy leafloaf \
    --image gcr.io/leafloafai/leafloaf \
    --set-env-vars "DEEPGRAM_API_KEY=${DEEPGRAM_API_KEY}"
```

## Testing Instructions for 5 Users

### For Test Users:
1. **Open the Demo**: https://leafloaf-32905605817.us-central1.run.app/voice_demo_deepgram.html
2. **Allow Microphone**: Click "Allow" when browser asks for permission
3. **Test Scenarios**:
   - Click test buttons first to verify it's working
   - Then click microphone and say:
     - "I need organic valley milk"
     - "Show me gluten free bread"
     - "I want to buy some bananas"
4. **Provide Feedback**: Use the feedback form link on the page

### Known Limitations:
- Cloud Run doesn't support WebSockets, so real-time streaming isn't available
- Audio is processed in chunks after recording stops
- Response time depends on audio length

## Next Steps
1. **Add Deepgram TTS**: For voice responses
2. **Implement Streaming**: Move to Cloud Run with WebSocket support when available
3. **Add Voice Analytics**: Sentiment, urgency detection
4. **Personalization**: Use voice patterns for better recommendations