# Voice-Native Architecture Plan

## Current State Analysis (July 2, 2025)

### What Exists Now
1. **Partial Voice Implementation**:
   - `supervisor_optimized.py` processes voice_metadata
   - Voice metadata is added dynamically to state (not type-safe)
   - Voice features: pace, emotion, volume, noise_level, duration
   - Voice influences routing decisions and response style

2. **Text-First Architecture**:
   - SearchState TypedDict has no voice fields
   - Agents are text-focused with voice "bolted on"
   - No audio streaming in state
   - Voice is not a first-class citizen

3. **Google Voice Implementation**:
   - Separate from main system
   - STT/TTS handlers exist but not integrated
   - WebSocket endpoints created but not connected to supervisor

## Voice-Native Architecture Plan

### Phase 1: Core State Changes
**Goal**: Make voice a first-class citizen in the system

1. **Update SearchState TypedDict**:
```python
class SearchState(TypedDict):
    # Existing fields...
    
    # Voice-Native Fields
    voice_metadata: VoiceMetadata
    audio_stream: Optional[bytes]  # Raw audio data
    voice_session_id: Optional[str]
    voice_transcript: Optional[VoiceTranscript]
    voice_response_audio: Optional[bytes]  # TTS output
    is_voice_request: bool
    voice_interaction_mode: VoiceMode  # "conversation", "command", "query"
```

2. **Create Voice Data Models**:
```python
class VoiceMetadata(TypedDict):
    pace: Literal["slow", "normal", "fast"]
    emotion: Literal["neutral", "excited", "frustrated", "confused"]
    volume: Literal["quiet", "normal", "loud"]
    noise_level: Literal["quiet", "moderate", "noisy"]
    duration: float
    language: str  # Detected language
    confidence: float
    hesitations: int
    interruptions: bool
    
class VoiceTranscript(TypedDict):
    text: str
    confidence: float
    is_final: bool
    alternatives: List[str]
    language: str
    timestamps: List[WordTimestamp]
```

### Phase 2: Agent Updates
**Goal**: Make all agents voice-aware natively

1. **Base Agent Changes**:
   - Update MemoryAwareAgent to be VoiceAwareAgent
   - Add voice processing methods to base class
   - Ensure voice context flows through all agents

2. **Supervisor Updates**:
   - Merge supervisor.py and supervisor_optimized.py
   - Make voice processing primary, text secondary
   - Add voice-specific routing logic

3. **Product Search Updates**:
   - Voice-driven search parameters
   - Audio feedback for search results
   - Voice-optimized result formatting

4. **Order Agent Updates**:
   - Voice confirmation flows
   - Audio feedback for cart operations
   - Natural language order modifications

### Phase 3: Integration Points
**Goal**: Connect Google Voice implementation to core system

1. **WebSocket Integration**:
   - Connect `/api/v1/google-voice/connect` to supervisor
   - Stream audio through SearchState
   - Real-time STT → Supervisor → Agents → TTS

2. **Session Management**:
   - Voice sessions tied to user sessions
   - Maintain conversation context
   - Handle interruptions and turn-taking

3. **Response Generation**:
   - TTS-optimized response formatting
   - SSML generation for natural speech
   - Cultural voice adaptations

### Phase 4: Voice-First Features
**Goal**: Features that only make sense with voice

1. **Conversational Features**:
   - Multi-turn conversations
   - Context carryover
   - Clarification dialogs
   - Interruption handling

2. **Voice Shopping Features**:
   - "Add my usual items"
   - "What did I buy last week?"
   - "I'm making dinner for 6"
   - Shopping list dictation

3. **Accessibility Features**:
   - Voice-only navigation
   - Audio descriptions
   - Confirmation sounds
   - Error audio cues

## Implementation Order

### Day 1: Foundation
1. Update SearchState with voice fields
2. Create voice data models
3. Update base agent class
4. Test state passing with voice data

### Day 2: Agent Updates  
1. Update supervisor to be voice-native
2. Update product search for voice
3. Update order agent for voice
4. Update response compiler for voice

### Day 3: Integration
1. Connect Google Voice to supervisor
2. Implement voice session management
3. Test end-to-end voice flow
4. Fix audio streaming issues

### Day 4: Polish
1. Add voice-first features
2. Optimize latency
3. Add error handling
4. Test with multiple languages

## Key Design Decisions

1. **Voice-First, Text-Compatible**:
   - System works primarily with voice
   - Text requests converted to "voice-like" format
   - All responses optimized for speech

2. **Streaming Architecture**:
   - Audio streams through state
   - Real-time processing
   - Chunked responses for low latency

3. **Multi-Modal Ready**:
   - Architecture supports voice + text + image
   - Unified state model
   - Agent abstraction handles all modalities

4. **Language Agnostic**:
   - Detect language from voice
   - Route to appropriate models
   - Respond in user's language

## Success Metrics

1. **Latency**: < 500ms first response
2. **Accuracy**: > 95% intent recognition
3. **Naturalness**: Conversational flow
4. **Reliability**: < 1% error rate
5. **Languages**: Support 5+ languages

## Risks & Mitigations

1. **Risk**: State size with audio data
   - **Mitigation**: Stream audio, don't store

2. **Risk**: Latency with voice processing
   - **Mitigation**: Parallel processing, caching

3. **Risk**: Type safety with dynamic fields
   - **Mitigation**: Proper TypedDict definitions

4. **Risk**: Integration complexity
   - **Mitigation**: Incremental updates, testing

## Next Steps

1. Review and approve plan
2. Create detailed tickets for each phase
3. Set up voice testing environment
4. Begin Phase 1 implementation

## Notes

- Current supervisor_optimized.py has good voice logic - preserve it
- Google Voice implementation is solid - just needs integration
- Focus on making voice primary, not an add-on
- Consider voice-only testing mode