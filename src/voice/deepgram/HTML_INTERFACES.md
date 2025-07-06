# Deepgram HTML Test Interfaces Documentation

## Overview

The HTML test interfaces provide standalone web pages for testing Deepgram voice functionality without requiring a backend server. These interfaces demonstrate progressively more complex integrations, from basic STT to full conversational AI.

## Test Interfaces

### 1. deepgram_direct_test.html

**Purpose**: Basic Speech-to-Text testing with real-time transcription display.

**Features**:
- Direct WebSocket connection to Deepgram
- Real-time interim and final transcripts
- No server dependencies
- Visual feedback for connection status

**Key Code**:
```javascript
// Direct WebSocket connection
websocket = new WebSocket(deepgramUrl, ['token', DEEPGRAM_API_KEY]);

// Handle transcripts
websocket.onmessage = (event) => {
    const response = JSON.parse(event.data);
    if (response.channel?.alternatives?.[0]?.transcript) {
        // Display transcript
    }
};
```

**Usage**:
1. Open file in browser
2. Click "Start Listening"
3. Speak into microphone
4. View real-time transcription

### 2. deepgram_conversation.html

**Purpose**: Two-way conversation with STT input and TTS output.

**Features**:
- Speech-to-Text for user input
- Text-to-Speech for responses
- Simple pattern-based responses
- Audio playback management

**Key Components**:
```javascript
// STT WebSocket for listening
sttWebsocket = new WebSocket(sttUrl, ['token', DEEPGRAM_API_KEY]);

// TTS API for speaking
async function speak(text) {
    const response = await fetch(ttsUrl, {
        method: 'POST',
        headers: {
            'Authorization': 'Token ' + DEEPGRAM_API_KEY,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
    });
}
```

**Response Logic**:
- Greetings → "Hello! How can I help you?"
- Product queries → "Let me find that for you"
- Default → "I can help you find groceries"

### 3. deepgram_gemini_conversation.html

**Purpose**: Full conversational AI assistant using Deepgram + Gemini.

**Features**:
- Natural language understanding via Gemini
- Context-aware responses
- Conversation history
- Grocery shopping focused prompts
- API key management

**Architecture**:
```
User Speech → Deepgram STT → Transcript → Gemini AI → Response → Deepgram TTS → Audio
```

**Key Integration**:
```javascript
// Process flow
sttWebsocket.onmessage = async (event) => {
    const transcript = extractTranscript(event);
    if (transcript && isFinal) {
        // Generate AI response
        const response = await generateResponse(transcript);
        // Speak response
        await speak(response);
    }
};
```

**Gemini Configuration**:
- Model: gemini-pro
- Temperature: 0.7
- Max tokens: 150
- Custom grocery assistant prompt

### 4. deepgram_vertex_gemini_conversation.html

**Purpose**: Production-ready version using Vertex AI for GCP deployment.

**Features**:
- Vertex AI integration for production
- GCP authentication support
- Enhanced error handling
- Production-grade prompts

**Differences from Standard Version**:
- Uses Vertex AI endpoint
- Requires GCP project configuration
- Better suited for production deployment

## Common Features Across All Interfaces

### Audio Configuration
```javascript
// Consistent audio settings
audio: {
    channelCount: 1,
    sampleRate: 16000,
    echoCancellation: true,
    noiseSuppression: true
}
```

### WebSocket Parameters
```javascript
// Standard Deepgram parameters
const params = {
    model: 'nova-2',
    language: 'en-US',
    smart_format: 'true',
    interim_results: 'true',
    utterance_end_ms: '1000',
    vad_events: 'true'
};
```

### Error Handling
All interfaces include:
- Connection error recovery
- Microphone permission handling
- WebSocket state management
- User-friendly error messages

## UI/UX Patterns

### Visual Feedback
- **Connection Status**: Clear indicators for connected/disconnected
- **Interim Results**: Shown in italics or lighter color
- **Final Transcripts**: Bold or normal text
- **System Messages**: Distinct styling for system notifications

### Message Styling
```css
.user { 
    background: #e3f2fd; 
    border-left: 4px solid #2196F3; 
}
.assistant { 
    background: #f3e5f5; 
    border-left: 4px solid #9c27b0; 
}
.interim { 
    opacity: 0.6; 
    font-style: italic; 
}
```

## Testing Workflow

### Basic STT Test
1. Open `deepgram_direct_test.html`
2. No configuration needed
3. Test microphone and transcription

### Conversation Test
1. Open `deepgram_conversation.html`
2. Test two-way audio flow
3. Verify TTS playback

### Full AI Assistant
1. Open `deepgram_gemini_conversation.html`
2. Add Gemini API key
3. Test natural conversations
4. Verify context retention

## Best Practices

### API Key Management
- Use localStorage for persistence
- Never commit keys to repository
- Provide clear instructions for obtaining keys

### Audio Handling
```javascript
// Proper cleanup
function stopConversation() {
    mediaRecorder?.stop();
    audioStream?.getTracks().forEach(track => track.stop());
    sttWebsocket?.close();
}
```

### User Experience
1. Show clear start/stop controls
2. Provide visual feedback during processing
3. Display interim results for responsiveness
4. Handle errors gracefully

## Troubleshooting Guide

### Common Issues

**No Transcription**:
- Check browser microphone permissions
- Verify Deepgram API key
- Ensure secure context (HTTPS/localhost)

**Audio Not Playing**:
- Check browser autoplay policies
- Verify TTS response format
- Test with different browsers

**Connection Errors**:
- Validate API key format
- Check network connectivity
- Review browser console for errors

### Browser Compatibility
- **Chrome/Edge**: Full support
- **Firefox**: Full support
- **Safari**: May require user interaction for audio
- **Mobile**: Touch interaction required for audio

## Future Enhancements

1. **Multi-language Support**: Add language selection
2. **Voice Selection**: Choose different TTS voices
3. **Conversation Export**: Save chat history
4. **Custom Prompts**: User-defined AI behavior
5. **Visual Indicators**: Waveform visualization