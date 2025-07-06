# Deepgram Voice Integration Guide

## Overview

Deepgram provides the core voice infrastructure for LeafLoaf, handling both Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities. The integration is designed to work directly via WebSocket connections without requiring a backend server, making it ideal for rapid prototyping and client-side voice applications.

## Architecture

```
┌─────────────┐     WebSocket      ┌──────────────┐     ┌─────────────┐
│   Browser   │ ←────────────────→ │   Deepgram   │     │   Gemini    │
│ Microphone  │     Audio Stream    │  STT + TTS   │     │     AI      │
└─────────────┘                     └──────────────┘     └─────────────┘
      ↓                                    ↓                     ↑
   Audio In                            Transcript            Response
```

## Components

### 1. **DeepgramStreamingClient** (`streaming_client.py`)
Simple STT-only client for real-time transcription.

**Features:**
- WebSocket streaming
- Interim and final results
- Confidence scores
- Timestamp information
- VAD (Voice Activity Detection)

**Usage:**
```python
client = DeepgramStreamingClient()
await client.connect(
    on_transcript=handle_transcript,
    on_error=handle_error,
    model="nova-2",
    language="en-US"
)
```

### 2. **DeepgramConversationalClient** (`conversational_client.py`)
Full duplex client supporting both STT and TTS for conversational AI.

**Features:**
- Simultaneous STT and TTS connections
- Utterance end detection
- Audio streaming in both directions
- Synchronized conversation flow

**Usage:**
```python
client = DeepgramConversationalClient()
await client.connect(
    on_transcript=handle_transcript,
    on_audio=handle_audio_output,
    stt_model="nova-2",
    tts_model="aura-asteria-en"
)
```

### 3. **DeepgramNova3Client** (`nova3_client.py`)
Enhanced client for Nova 3 model with advanced features.

**Features:**
- Nova 3 model support
- Enhanced accuracy
- Better handling of accents
- Improved punctuation

## API Models

### Speech-to-Text (STT) Models
- **Nova 2** - General purpose, balanced performance
- **Nova 3** - Latest model, highest accuracy (coming soon)
- **Enhanced** - Legacy model for specific use cases

### Text-to-Speech (TTS) Models
- **Aura Asteria** - Natural female voice
- **Aura Orion** - Natural male voice  
- **Aura Arcas** - Clear, professional voice
- **Aura Perseus** - Dynamic, energetic voice

## Configuration Options

### STT Configuration
```python
LiveOptions(
    model="nova-2",              # Model selection
    language="en-US",            # Language code
    smart_format=True,           # Automatic formatting
    interim_results=True,        # Show partial results
    utterance_end_ms=1000,       # Silence detection (ms)
    vad_events=True,             # Voice activity events
    endpointing=300             # End of speech detection
)
```

### TTS Configuration
```python
{
    "model": "aura-asteria-en",  # Voice model
    "encoding": "linear16",       # Audio encoding
    "sample_rate": "16000"        # Sample rate (Hz)
}
```

## Integration with Gemini

The Deepgram + Gemini integration provides intelligent conversational AI:

1. **User speaks** → Deepgram STT → Transcript
2. **Process transcript** → Gemini AI → Response
3. **Generate speech** → Deepgram TTS → Audio output

### Example Flow
```javascript
// 1. Capture user speech
const transcript = await deepgram.transcribe(audioStream);

// 2. Generate AI response
const response = await gemini.generateResponse(transcript);

// 3. Speak the response
await deepgram.speak(response);
```

## HTML Test Interfaces

### 1. **deepgram_direct_test.html**
Basic STT testing without server dependencies.
- Direct WebSocket connection
- Real-time transcription display
- Interim result visualization

### 2. **deepgram_conversation.html**
Two-way conversation with simple responses.
- STT + TTS integration
- Pattern-based responses
- Audio playback handling

### 3. **deepgram_gemini_conversation.html**
Full conversational AI with Gemini integration.
- Complete voice assistant
- Context-aware responses
- Conversation history
- Grocery shopping focus

## Performance Considerations

### Latency Breakdown
- **STT Processing**: ~200-300ms
- **Gemini Response**: ~500-800ms
- **TTS Generation**: ~200-300ms
- **Total Round Trip**: ~1-1.5s

### Optimization Tips
1. Use `interim_results=true` for perceived responsiveness
2. Set appropriate `utterance_end_ms` (1000ms recommended)
3. Enable `smart_format` for better transcription quality
4. Use `vad_events` to detect speech activity

## WebSocket Connection

### Connection URL
```
wss://api.deepgram.com/v1/listen?{parameters}
```

### Authentication
```javascript
new WebSocket(url, ['token', DEEPGRAM_API_KEY])
```

### Audio Format
- **Encoding**: Linear16 (PCM)
- **Sample Rate**: 16000 Hz
- **Channels**: 1 (mono)
- **Chunk Size**: 250ms recommended

## Error Handling

Common errors and solutions:

1. **Connection Refused**
   - Check API key validity
   - Verify network connectivity
   - Ensure WebSocket support

2. **Audio Format Error**
   - Verify audio encoding matches configuration
   - Check sample rate compatibility
   - Ensure mono channel audio

3. **Timeout Issues**
   - Implement reconnection logic
   - Monitor connection state
   - Use keepalive settings

## Testing

### Basic STT Test
```bash
# Open in browser
open deepgram_direct_test.html
# Click "Start Listening"
# Speak into microphone
```

### Conversational Test
```bash
# Set Gemini API key in environment or UI
export GEMINI_API_KEY="your-key"
# Open in browser
open deepgram_gemini_conversation.html
```

## Best Practices

1. **API Key Security**
   - Never commit API keys
   - Use environment variables
   - Implement key rotation

2. **Audio Quality**
   - Use echo cancellation
   - Enable noise suppression
   - Test with different microphones

3. **User Experience**
   - Show interim results for responsiveness
   - Provide visual feedback for speech detection
   - Handle errors gracefully

4. **Conversation Design**
   - Keep responses concise for voice
   - Use natural language
   - Confirm important actions

## Troubleshooting

### No Transcription
- Check microphone permissions
- Verify API key is valid
- Ensure audio is being sent

### Poor Accuracy
- Check background noise levels
- Verify language settings
- Try different STT models

### TTS Not Working
- Confirm TTS model is valid
- Check audio playback permissions
- Verify response format

## Future Enhancements

1. **Nova 3 Integration** - Enhanced accuracy model
2. **Multi-language Support** - Expand beyond English
3. **Custom Vocabulary** - Domain-specific terms
4. **Speaker Diarization** - Multi-speaker recognition
5. **Emotion Detection** - Sentiment analysis from voice