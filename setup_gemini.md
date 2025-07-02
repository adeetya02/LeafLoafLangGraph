# Setting Up Gemini API for Voice Supervisor

## Quick Setup

1. **Get a Gemini API Key** (free):
   - Go to: https://makersuite.google.com/app/apikey
   - Click "Create API Key"
   - Copy the key

2. **Add to your environment**:
   ```bash
   export GOOGLE_GENERATIVE_AI_API_KEY="your-key-here"
   ```

3. **Or add to .env.yaml**:
   ```yaml
   GOOGLE_GENERATIVE_AI_API_KEY: "your-key-here"
   ```

## Architecture Flow

```
Voice Input → Google STT → Text → Gemini Supervisor → Intent + Alpha → Search/Order → Response → Google TTS → Voice Output
```

- **Google STT/TTS**: Just converts speech ↔ text
- **Gemini (in Supervisor)**: Analyzes intent, determines alpha for search
- **Alpha Value**: Controls search behavior (0.3 = exact match, 0.7 = semantic)

## Why Gemini?

- Free tier available (60 requests/minute)
- Fast response times
- Good at intent analysis
- Works without Vertex AI setup

## Testing

Once you have the API key set:

```bash
# Start server with key
GOOGLE_GENERATIVE_AI_API_KEY="your-key" python3 -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Test voice
open http://localhost:8000/static/voice_google_test.html
```