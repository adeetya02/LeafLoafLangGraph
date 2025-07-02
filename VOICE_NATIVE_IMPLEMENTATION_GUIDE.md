# Voice-Native Implementation Guide

## Quick Start for Tomorrow

### Current Situation
- **What Works**: supervisor_optimized.py has voice processing logic
- **What's Missing**: Voice fields in SearchState, integration with Google Voice
- **Main Issue**: Voice is "bolted on" not native to the architecture

### Immediate Tasks (Start Here)

#### 1. Update SearchState (30 mins)
```python
# In src/models/state.py, add:
voice_metadata: Optional[Dict[str, Any]]  # Make it optional for backward compatibility
is_voice_request: bool = False
voice_session_id: Optional[str]
audio_stream: Optional[bytes]  # For future audio streaming
```

#### 2. Create Voice Models (20 mins)
```python
# Create src/models/voice.py:
from typing import TypedDict, Literal, List, Optional

class VoiceMetadata(TypedDict):
    pace: Literal["slow", "normal", "fast"]
    emotion: Literal["neutral", "excited", "frustrated", "confused"]
    volume: Literal["quiet", "normal", "loud"]  
    noise_level: Literal["quiet", "moderate", "noisy"]
    duration: float
    language: str
    confidence: float
```

#### 3. Update Supervisor Invoke (1 hour)
```python
# In src/core/graph.py - how supervisor is called:
# Currently: supervisor gets raw state
# Need: Pass voice context from API layer

# From API endpoint:
state = {
    "query": text,
    "voice_metadata": voice_metadata,  # From Google STT
    "is_voice_request": True,
    "voice_session_id": session_id,
    # ... other fields
}
```

#### 4. Connect Google Voice to System (2 hours)
The key integration point is `/src/api/voice_google.py`:

```python
# Current: Processes voice separately
# Need: Route through supervisor

# After STT completes:
if transcript:
    # Create state for supervisor
    state = create_voice_state(transcript, voice_features)
    
    # Invoke supervisor workflow
    result = await workflow.ainvoke(state)
    
    # Extract response and convert to speech
    response_text = result["final_response"]["message"]
    audio = await tts_handler.synthesize(response_text)
```

### Testing Plan

#### Test 1: Voice Metadata Flow
```python
# Create test_voice_state_flow.py
# Verify voice_metadata passes through all agents
```

#### Test 2: End-to-End Voice
```bash
# Start server
python3 run.py

# Open browser
http://localhost:8080/static/voice_google_test.html

# Speak: "Show me organic milk"
# Verify: Goes through supervisor → product search → response
```

### Common Issues to Avoid

1. **Type Errors**: 
   - SearchState is a TypedDict, be careful with optional fields
   - Use `.get()` not direct access for voice fields

2. **State Mutation**:
   - Don't modify state directly in agents
   - Return new state updates

3. **Audio Data Size**:
   - Don't store raw audio in state (too large)
   - Store references or stream separately

4. **Backward Compatibility**:
   - Make voice fields optional
   - Check `is_voice_request` before accessing voice data

### Integration Checkpoints

✅ **Checkpoint 1**: Voice metadata in SearchState
- Run existing tests - should still pass
- Add one test with voice_metadata

✅ **Checkpoint 2**: Supervisor processes voice
- Log voice_metadata in supervisor
- Verify it influences routing

✅ **Checkpoint 3**: Google Voice connected
- Voice input → Supervisor → Response
- Basic flow working

✅ **Checkpoint 4**: Audio streaming
- STT streaming works
- TTS response plays

### File Locations Reference

```
Core Files to Modify:
- src/models/state.py          # Add voice fields
- src/models/voice.py          # New voice models (create)
- src/agents/supervisor.py     # Ensure voice handling
- src/core/graph.py           # How agents are invoked
- src/api/voice_google.py     # Integration point

Test Files:
- test_voice_state_flow.py    # New test (create)
- src/static/voice_google_test.html  # Browser testing
```

### Tomorrow's Goal

Get ONE voice request flowing through the system:
1. Speak into microphone
2. STT converts to text + voice metadata  
3. Supervisor sees voice context
4. Routes to product search
5. Gets response
6. TTS speaks response

Once this works, everything else is incremental improvements!

### Remember

- supervisor_optimized.py already has voice logic - use it!
- Don't over-engineer - get basic flow working first
- Test each step before moving on
- Voice metadata is already partially working - just formalize it

### Debugging Commands

```bash
# Watch server logs for voice flow
tail -f server.log | grep -i "voice\|audio\|stt\|tts"

# Test supervisor directly with voice metadata
python3 -c "
from src.core.graph import workflow
state = {
    'query': 'show me milk',
    'voice_metadata': {'pace': 'fast', 'emotion': 'neutral'},
    'is_voice_request': True
}
result = workflow.invoke(state)
print(result)
"
```

Good luck! The foundation is there - just need to connect the pieces properly.