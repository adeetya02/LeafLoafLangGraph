# Voice-Aware Multi-Modal Agentic RAG Architecture

## Overview
Transform the existing Supervisor into a multi-modal agent that handles voice, text, and visual inputs seamlessly using an agentic RAG approach.

## Architecture Components

### 1. Multi-Modal Supervisor (Enhanced)
The existing Supervisor becomes the central orchestrator with voice awareness:

```
┌─────────────────────────────────────────────────────────────┐
│                   Multi-Modal Supervisor                      │
│                                                              │
│  Capabilities:                                               │
│  - Voice Intent Recognition (from audio features)            │
│  - Emotion Detection (from voice + text)                     │
│  - Language Detection & Cultural Context                     │
│  - Multi-Modal State Management                              │
│  - Conversation Flow Control                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────┬────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Voice RAG     │  │ Product RAG   │  │ Order RAG     │
│ Agent         │  │ Agent         │  │ Agent         │
└───────────────┘  └───────────────┘  └───────────────┘
```

### 2. Voice RAG Agent (New)
Specialized agent for voice-specific retrieval and generation:

**Responsibilities:**
- Voice pattern recognition and learning
- Accent/dialect adaptation
- Speaking rate adjustment
- Emotional tone matching
- Conversation history RAG

**Tools:**
- `VoicePatternRetriever`: Retrieves similar voice interactions
- `EmotionAnalyzer`: Analyzes voice emotions
- `CulturalAdapter`: Adapts responses for cultural context
- `ConversationMemory`: RAG over past voice conversations

### 3. Enhanced State Structure

```python
class MultiModalState(TypedDict):
    # Existing fields
    messages: List[BaseMessage]
    query: str
    search_results: List[Dict]
    
    # New multi-modal fields
    voice_features: Dict[str, Any]
    audio_context: Dict[str, Any]
    visual_context: Optional[Dict[str, Any]]
    emotion_state: Dict[str, float]
    language_context: Dict[str, str]
    conversation_mode: Literal["voice", "text", "mixed"]
    
    # RAG-specific fields
    retrieved_voice_patterns: List[Dict]
    retrieved_conversations: List[Dict]
    voice_embeddings: List[float]
    multi_modal_embeddings: List[float]
```

### 4. Agentic RAG Flow

```python
# 1. Voice Input Processing
voice_input → STT → Extract Features → Create Multi-Modal Embedding

# 2. Multi-Modal RAG Retrieval
embedding → Retrieve from:
  - Voice Pattern Database (how user usually speaks)
  - Conversation History (what they usually ask for)
  - Product Preferences (voice-mentioned preferences)
  - Cultural Context (accent/language patterns)

# 3. Enhanced Supervisor Decision
supervisor_decision = f(
    text_intent,
    voice_features,
    emotion_state,
    retrieved_context,
    conversation_history
)

# 4. Agent Routing with Context
if supervisor_decision == "product_search":
    # Route to Product Agent with voice context
    product_agent.invoke({
        ...state,
        voice_hints: extracted_preferences,
        emotion_context: emotion_state
    })
```

### 5. Implementation Plan

#### Phase 1: Multi-Modal State Enhancement
```python
# src/core/state.py
class VoiceFeatures(BaseModel):
    speaking_rate: float
    pitch: float
    energy: float
    emotion_scores: Dict[str, float]
    language_confidence: Dict[str, float]
    hesitation_markers: List[float]
    
class MultiModalSearchState(SearchState):
    # Voice-specific
    voice_features: Optional[VoiceFeatures]
    audio_chunks: List[bytes]
    
    # Multi-modal RAG
    voice_embeddings: List[float]
    retrieved_voice_context: List[Dict]
    conversation_style: str
    
    # Real-time features
    is_speaking: bool
    interruption_detected: bool
    silence_duration: float
```

#### Phase 2: Voice RAG Agent
```python
# src/agents/voice_rag_agent.py
class VoiceRAGAgent:
    def __init__(self):
        self.voice_vectorstore = ChromaDB(collection="voice_patterns")
        self.conversation_store = ChromaDB(collection="conversations")
        
    async def retrieve_voice_context(self, state: MultiModalSearchState):
        # Create multi-modal embedding
        embedding = self.create_multimodal_embedding(
            text=state.query,
            voice_features=state.voice_features,
            emotion=state.emotion_state
        )
        
        # Retrieve similar patterns
        voice_patterns = self.voice_vectorstore.similarity_search(
            embedding, k=5
        )
        
        # Retrieve relevant conversations
        conversations = self.conversation_store.similarity_search(
            embedding, k=3
        )
        
        return {
            "voice_patterns": voice_patterns,
            "conversations": conversations,
            "personalization_hints": self.extract_hints(voice_patterns)
        }
```

#### Phase 3: Enhanced Supervisor
```python
# src/agents/supervisor.py (enhanced)
class MultiModalSupervisor:
    async def route_query(self, state: MultiModalSearchState):
        # Multi-modal analysis
        analysis = await self.analyze_multimodal_input(
            text=state.query,
            voice=state.voice_features,
            context=state.retrieved_voice_context
        )
        
        # Emotion-aware routing
        if analysis.emotion_state.get("frustrated", 0) > 0.7:
            # Route to specialized handling
            return "empathetic_response"
        
        # Language-aware routing
        if analysis.language != "en-US":
            state.cultural_context = self.get_cultural_context(
                analysis.language
            )
        
        # Standard routing with multi-modal context
        return self.route_with_context(analysis)
```

### 6. Benefits of This Architecture

1. **Unified Multi-Modal Understanding**: Single supervisor handles all modalities
2. **Context-Rich RAG**: Retrieves based on voice patterns, not just text
3. **Personalized Voice Responses**: Adapts to user's speaking style
4. **Emotion-Aware**: Responds appropriately to user emotions
5. **Cultural Sensitivity**: Handles multi-ethnic customers naturally
6. **Scalable**: Easy to add new modalities (vision, gesture)

### 7. Integration Points

```python
# src/api/voice_google.py integration
async def process_voice_input(self, audio_data: bytes):
    # 1. Process audio through Google STT
    stt_result = await self.stt.streaming_recognize(audio_data)
    
    # 2. Extract voice features
    voice_features = self.extract_voice_features(audio_data)
    
    # 3. Create multi-modal state
    state = MultiModalSearchState(
        query=stt_result.transcript,
        voice_features=voice_features,
        conversation_mode="voice",
        audio_chunks=[audio_data]
    )
    
    # 4. Run through enhanced graph
    result = await multi_modal_graph.ainvoke(state)
    
    # 5. Generate voice response with personalization
    return await self.generate_voice_response(result)
```

### 8. Voice-Specific RAG Collections

1. **Voice Patterns Collection**
   - User speech patterns
   - Common phrases
   - Pronunciation preferences
   - Speaking speed preferences

2. **Conversation Context Collection**
   - Past conversations
   - Topic transitions
   - Preferred response styles
   - Cultural communication patterns

3. **Emotion Patterns Collection**
   - Emotional states → appropriate responses
   - Tone matching patterns
   - Empathy triggers

### 9. Real-Time Considerations

```python
# Streaming architecture for low latency
async def stream_voice_processing():
    async for audio_chunk in audio_stream:
        # Parallel processing
        await asyncio.gather(
            process_stt(audio_chunk),
            extract_features(audio_chunk),
            update_rag_context(audio_chunk)
        )
        
        # Yield intermediate results
        if interim_result_ready():
            yield generate_response()
```

This architecture makes the Supervisor truly multi-modal while leveraging RAG for personalized, context-aware voice interactions.