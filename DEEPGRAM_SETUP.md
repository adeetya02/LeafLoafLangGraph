# Deepgram Setup Guide

## 1. Get Your Deepgram API Key

1. Go to [console.deepgram.com](https://console.deepgram.com)
2. Sign up for a free account (you get $200 credits)
3. Create a new API key with these permissions:
   - `usage:write` - For transcription
   - `keys:read` - For API access
   - `projects:read` - For project info

## 2. Add to Environment

Add this to your `.env.yaml`:

```yaml
# Deepgram Configuration
DEEPGRAM_API_KEY: "your-deepgram-api-key-here"
```

## 3. Quick Test

Once you have the API key, run this test:

```bash
curl -X POST "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true" \
  -H "Authorization: Token YOUR_DEEPGRAM_API_KEY" \
  -H "Content-Type: audio/wav" \
  --data-binary @test-audio.wav
```

## Ready to Continue?

Once you have your API key, we'll:
1. Build the streaming voice endpoint
2. Enable all audio intelligence features
3. Set up real-time data capture
4. Test with your voice!

Let me know when you have the API key and we'll start building!