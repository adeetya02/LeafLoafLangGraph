# Next Session Prompt: Deepgram Streaming & Voice-Native Architecture

## 🎯 Session Goals

"Hi Claude! Let's continue implementing the Deepgram streaming integration and voice-native architecture for LeafLoaf. Here's what we need to accomplish:

### 1. **Fix Deepgram Streaming (Priority 1)**
- The WebSocket connects but disconnects after 6-7 seconds without processing audio
- We have a working test at `/tests/implementation/deepgram/test_deepgram_streaming.html`
- Audio format is correctly converted to linear16 PCM
- Need to debug why `nova3_client.py` isn't processing the audio stream
- Ensure voice metadata flows from client → Deepgram → Supervisor → Search

### 2. **Complete Voice Integration Flow**
```
Voice → Deepgram STT → Voice Metadata → Supervisor → Product Search → Results
```
- Verify the complete pipeline works end-to-end
- Test with queries like "I urgently need milk" and see voice-influenced search
- Ensure voice metadata (pace, emotion, urgency) affects search alpha
- Confirm products are returned through the WebSocket

### 3. **Implement Multi-Modal Supervisor**
- Extend `supervisor_optimized.py` to handle:
  - Voice + Text (current)
  - Voice + Image (new)
  - Voice + Text + Image (new)
- Add image analysis capability for:
  - Shopping lists (photo of handwritten list)
  - Product recognition (photo of empty milk carton)
  - Pantry analysis (photo of fridge/pantry)
- Maintain <2s response time

### 4. **Voice-Native Architecture Throughout**
Based on our `HOLISTIC_VOICE_ANALYTICS.md` design:

#### A. Enhance Voice Metadata Collection
```python
voice_metadata = {
    # Current (working)
    "pace": "slow/normal/fast",
    "volume": "quiet/normal/loud",
    
    # Add these
    "emotional_state": "frustrated/happy/neutral/confused",
    "conversation_stage": "greeting/browsing/deciding/purchasing", 
    "engagement_level": "high/medium/low",
    "confidence_score": 0.85,
    "interruptions": count,
    "hesitations": ["um", "uh"],
    "background_activity": "walking/driving/stationary"
}
```

#### B. Implement Voice Analytics in Supervisor
- Emotional state detection from voice patterns
- Conversation stage tracking
- Engagement level monitoring
- Adapt routing and response based on these factors

#### C. Voice-Driven Personalization
- Store voice patterns in Graphiti as relationships
- Learn user's preferred interaction style
- Adapt search and response strategies over time

### 5. **Testing & Verification**
- Get streaming working in test environment first
- Move working implementation from `tests/implementation/` to `src/`
- Create comprehensive tests for voice flow
- Verify performance stays under 2s

## 📂 Key Files to Work With

### Deepgram Streaming
- `src/voice/deepgram/nova3_client.py` - Fix streaming issue
- `src/api/voice_deepgram_endpoint.py` - WebSocket handler
- `tests/implementation/deepgram/test_deepgram_streaming.html` - Working test

### Supervisor Enhancement
- `src/agents/supervisor_optimized.py` - Add multi-modal support
- `src/models/state.py` - Extend SearchState for images
- `src/core/graph.py` - Update workflow if needed

### Voice Analytics
- `src/voice/processors/transcript_processor.py` - Enhance analysis
- `src/memory/graphiti_wrapper.py` - Add voice relationships
- `HOLISTIC_VOICE_ANALYTICS.md` - Implementation guide

## 🔍 Current Status

### What's Working
- ✅ Deepgram API key is valid
- ✅ WebSocket connection establishes
- ✅ Audio format conversion (linear16 PCM)
- ✅ Supervisor routes queries correctly
- ✅ Product search returns results
- ✅ Memory and personalization work

### What Needs Fixing
- ❌ Deepgram streaming audio processing
- ❌ Voice metadata not passed through pipeline
- ❌ Multi-modal capability not implemented
- ❌ Enhanced voice analytics not integrated

## 🎬 Let's Start With

1. Debug why Deepgram isn't processing audio stream
2. Trace the complete voice flow end-to-end
3. Implement basic multi-modal (voice + image)
4. Enhance voice metadata collection
5. Test everything in `tests/implementation/` first

Remember:
- Keep everything in `tests/implementation/` until working
- Maintain <2s response time
- Use fire-and-forget for analytics
- Add proper error handling and fallbacks

The codebase structure is in `CODEBASE_STRUCTURE.md`, flows are in `CODEBASE_FLOW_DIAGRAM.md`, and quick reference in `CODEBASE_QUICK_REFERENCE.md`.

Ready to make LeafLoaf truly voice-native! 🚀"

## 🔧 Additional Context for Next Session

### Debugging Approach for Streaming
1. Add detailed logging in `nova3_client.py` to see where it fails
2. Check if audio data is actually being received
3. Verify Deepgram connection stays alive with keepalive
4. Test with Deepgram's direct API to isolate issue

### Multi-Modal Implementation Strategy
1. Add `image_data` field to SearchState
2. Use Vision LLM (Gemini Pro Vision) for image analysis
3. Combine image context with voice metadata in supervisor
4. Route to appropriate agents based on multi-modal input

### Voice-Native Enhancements Priority
1. Get basic streaming working first
2. Add emotion detection from voice
3. Implement conversation stage tracking
4. Store voice patterns in Graphiti
5. Use patterns for personalization

This prompt will help us continue exactly where we left off and make significant progress on the voice-native architecture!