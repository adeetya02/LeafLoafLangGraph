# Google Voice Implementation Documentation

## Overview
Implementation of Google Cloud Speech-to-Text (STT) and Text-to-Speech (TTS) for multi-ethnic voice support in the LeafLoaf grocery shopping system.

## Implementation Date
July 1-2, 2025

## Current Status
- ✅ Google STT/TTS handlers implemented
- ✅ Multi-language support configured (English, Spanish, Hindi, Chinese, Korean)
- ✅ WebSocket streaming endpoint created
- ✅ Fixed API call issues with streaming_recognize
- ⚠️ Server connectivity issues to be resolved

## Files Created/Modified

### 1. Core STT Handler
**File**: `/src/api/voice_google_stt.py`
- Implements Google Cloud Speech-to-Text streaming
- Multi-language detection with automatic language switching
- Voice feature extraction (speaking rate, confidence, hesitation detection)
- Handles real-time audio streaming via WebSocket

**Key Features**:
- Primary language: en-US
- Alternative languages: Spanish, Hindi, Chinese, Korean, Indian English
- Speech contexts for grocery-specific terms
- Enhanced model with latest_short for real-time streaming

### 2. Core TTS Handler
**File**: `/src/api/voice_google_tts.py`
- Google Cloud Text-to-Speech implementation
- Cultural text adaptation using SSML
- Product name pronunciation guides
- Multi-voice profiles for different languages

**Voice Profiles**:
- English: Journey-O (male, warm)
- Spanish: Journey-F (female, friendly)
- Hindi/Indian: en-IN-Journey-F
- Chinese: cmn-CN-Journey-D
- Korean: ko-KR-Journey-D

### 3. Main WebSocket Endpoint
**File**: `/src/api/voice_google.py`
- Real-time WebSocket communication
- Parallel audio reception and STT processing
- Integration with LeafLoaf supervisor
- Session management

### 4. Test Implementations
**Files**: 
- `/src/api/voice_google_test.py` - Simplified test endpoint
- `/src/api/voice_google_simple.py` - Minimal STT implementation

### 5. Web Interfaces
**Files**:
- `/src/static/voice_google_test.html` - Full implementation test
- `/src/static/voice_google_simple_test.html` - Simplified test interface

## Technical Issues Resolved

### 1. API Call Signature Issue
**Problem**: `streaming_recognize() missing 1 required positional argument: 'requests'`

**Solution**: The Google Cloud Speech API expects two positional arguments:
```python
# Correct usage:
responses = client.streaming_recognize(
    streaming_config,  # First positional argument
    request_generator() # Second positional argument
)
```

**Important**: The request generator should NOT include the streaming_config in the first request since it's passed separately.

### 2. Audio Timeout Error
**Problem**: "400 Audio Timeout Error: Long duration elapsed without audio"

**Attempted Solutions**:
- Removed silence detection
- Added initial audio burst
- Modified request_generator to wait for first chunk
- Reduced buffer sizes

**Status**: Partially resolved but needs further testing

### 3. Protobuf Version Conflicts
**Problem**: ImportError with protobuf and grpcio versions

**Solution**: Compatible versions installed that work with both Graphiti and Google Cloud libraries

## Architecture Decisions

### 1. Streaming vs Batch
- Chose real-time streaming for natural conversation flow
- WebSocket for bi-directional audio communication
- Thread-based audio queue management for async-to-sync conversion

### 2. Multi-language Strategy
- Automatic language detection using alternative_language_codes
- Cultural adaptation at TTS level
- Product name pronunciation guides for ethnic items

### 3. Integration Approach
- Voice capabilities separate from supervisor (for now)
- Plan to make supervisor multi-modal after voice foundation works
- No hardcoded responses - all handled by LLM (Gemma)

## Next Steps

### Immediate (Fix Foundation)
1. Debug server connectivity issue ("site can't be reached")
2. Test end-to-end voice flow once server is accessible
3. Verify Google STT is receiving audio correctly

### Short Term
1. Implement voice activity detection (VAD) for better audio flow
2. Add interruption handling for natural conversation
3. Implement proper error recovery and reconnection

### Long Term (After Foundation Works)
1. Make supervisor multi-modal with voice awareness
2. Implement agentic RAG with LangGraph for voice
3. Integrate voice patterns with Graphiti learning
4. Add emotion detection from voice features

## Testing Instructions

1. Start the server:
```bash
python3 run.py
```

2. Access test interfaces:
- Full test: http://localhost:8080/static/voice_google_test.html
- Simple test: http://localhost:8080/static/voice_google_simple_test.html

3. Test multi-language support:
- Click language buttons to switch
- Speak in different languages
- Check product name adaptations

## Configuration

### Environment Variables
Google Cloud credentials should be set:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
```

### API Enablement
Required Google Cloud APIs:
- Cloud Speech-to-Text API
- Cloud Text-to-Speech API

Enable with:
```bash
gcloud services enable speech.googleapis.com
gcloud services enable texttospeech.googleapis.com
```

## Known Issues

1. **Server Connectivity**: Current issue with "site can't be reached" - likely port binding or firewall issue
2. **Audio Flow**: Need to ensure continuous audio flow to prevent timeouts
3. **WebSocket Stability**: Handle disconnections gracefully

## Performance Considerations

- STT adds ~200-300ms latency
- TTS synthesis takes ~100-200ms
- Total round-trip: ~500ms target
- Buffer size: 2048 samples (128ms at 16kHz)

## Security Notes

- No audio is stored permanently
- All processing happens in real-time
- Google Cloud handles encryption in transit
- No PII logged in voice traces