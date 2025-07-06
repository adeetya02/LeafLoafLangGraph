# Deepgram Implementation Tests

This folder contains working Deepgram implementations being tested before integration.

## Current Files

### test_deepgram_streaming.html
- Working implementation of Deepgram streaming with linear16 audio
- Converts browser audio to proper format
- Connects to `/api/v1/voice/deepgram/ws` endpoint
- Successfully processes voice and returns products

## Key Findings

1. **Audio Format**: Must be linear16 PCM, 16kHz, mono
2. **Conversion**: Browser MediaRecorder sends webm, must convert to PCM
3. **WebSocket**: Binary data sent as ArrayBuffer
4. **Connection**: Stays alive with proper audio format

## Testing

1. Start server: `python run.py`
2. Open: http://localhost:8080/tests/implementation/deepgram/test_deepgram_streaming.html
3. Click "Start Recording" and speak
4. Verify transcript and products appear

## Next Steps

Once this is fully tested and working:
1. Create production version in `src/static/`
2. Add proper error handling
3. Add voice metadata extraction
4. Integrate with supervisor flow