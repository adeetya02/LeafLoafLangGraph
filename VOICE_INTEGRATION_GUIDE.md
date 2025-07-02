# Voice Integration Guide - LeafLoaf LangGraph

## Overview

LeafLoaf now has a **voice-native conversational AI** system that processes voice input through a memory-aware, multi-agent architecture. The system maintains all personalization features while adding voice metadata processing for enhanced understanding.

## Architecture

### Voice Flow
```
Audio Input → STT → Voice-Native Supervisor → Multi-Agent System → Response Compiler → TTS → Audio Output
```

### Key Components

1. **Voice-Native Supervisor** (`/src/agents/supervisor_optimized.py`)
   - Inherits from MemoryAwareAgent
   - Processes voice metadata (pace, emotion, urgency, volume)
   - Calculates search parameters based on voice characteristics
   - Routes to appropriate agents while maintaining context

2. **Memory-Aware Agents** (`/src/agents/memory_aware_base.py`)
   - All agents inherit from MemoryAwareAgent base class
   - Shared memory context across voice interactions
   - Graphiti integration for learning from voice patterns

3. **WebSocket Voice API** (`/src/api/voice_deepgram_conversational.py`)
   - Real-time STT/TTS processing
   - Session persistence across voice calls
   - Error handling and reconnection logic

## Voice Metadata Processing

### Extracted Metadata
- **Pace**: Fast, normal, slow speech patterns
- **Emotion**: Urgency, excitement, calm, frustration
- **Volume**: Loud, normal, quiet
- **Clarity**: Clear, unclear speech patterns

### Search Parameter Influence
```python
# Voice metadata affects search strategy
if voice_metadata.get("pace") == "fast" and voice_metadata.get("emotion") == "urgent":
    alpha = 0.3  # More keyword-focused for quick results
elif voice_metadata.get("emotion") == "calm":
    alpha = 0.7  # More semantic for exploration
```

## Testing Voice Integration

### Quick Test Commands
```bash
# Test voice integration and search results
python3 test_voice_search_integration.py

# Test system integrity (all components)
python3 test_system_integrity.py

# Test cart operations with voice
python3 test_cart_voice_integration.py
```

### Manual Testing
1. **Start Server**: `python3 run.py`
2. **Open Interface**: Navigate to `/static/voice_deepgram_working.html`
3. **Test Scenarios**:
   - "I need organic milk" (search)
   - "Add 2 gallons to my cart" (cart operation)
   - "What's in my cart?" (cart display)
   - "Confirm my order" (checkout)

## Performance Metrics

### Current Performance
- **Voice Response Time**: 1.3-1.5s average
- **STT Latency**: ~200ms
- **Agent Processing**: ~800ms
- **TTS Generation**: ~300ms

### Optimization Areas
- Reduce Graphiti query time when active
- Optimize Weaviate search for voice queries
- Implement response streaming for faster perceived performance

## Voice-Specific Features

### 1. Conversational Context
- Maintains conversation history across voice interactions
- References previous queries and cart contents
- Understands context like "add more" or "remove that"

### 2. Natural Language Processing
- Handles casual speech patterns
- Understands incomplete sentences
- Processes corrections and clarifications

### 3. Voice-Optimized Responses
- Shorter, more conversational responses
- Structured for speech synthesis
- Includes confirmation and clarification requests

## Integration with Existing System

### Multi-Agent Workflow
Voice queries follow the complete multi-agent workflow:
1. **Supervisor**: Analyzes intent with voice metadata
2. **Product Search**: Uses voice-influenced parameters
3. **Order Agent**: Handles cart operations naturally
4. **Response Compiler**: Creates voice-optimized responses

### Personalization Features
All 10 personalization features work with voice:
- Smart Search Ranking
- "My Usual" Orders
- Reorder Intelligence
- Dietary Intelligence
- Cultural Understanding
- Complementary Products
- Quantity Memory
- Budget Awareness
- Household Intelligence
- Seasonal Patterns

### Memory Integration
- **Graphiti Learning**: Voice interactions stored in knowledge graph
- **Session Memory**: Conversation context maintained
- **User Preferences**: Voice patterns influence personalization

## Configuration

### Environment Variables
```yaml
# Voice configuration
ELEVENLABS_API_KEY: "sk_..."
DEEPGRAM_API_KEY: "..."

# Model selection (environment-aware)
ENVIRONMENT: "local"  # or "gcp"
HUGGINGFACE_API_KEY: "hf_..."  # for local Gemma 2 9B
```

### Voice Settings
```python
# In supervisor_optimized.py
VOICE_METADATA_WEIGHT = 0.3  # How much voice affects search
VOICE_RESPONSE_MAX_LENGTH = 150  # Keep responses concise
VOICE_TIMEOUT_SECONDS = 30  # WebSocket timeout
```

## Troubleshooting

### Common Issues

1. **WebSocket Connection Failures**
   - Check CORS settings in FastAPI
   - Verify SSL certificate for HTTPS
   - Ensure proper error handling in client

2. **Voice Quality Issues**
   - Adjust Deepgram model settings
   - Check audio format compatibility
   - Verify sample rate and encoding

3. **Response Latency**
   - Monitor Graphiti query performance
   - Check Weaviate search timing
   - Optimize agent processing logic

### Debug Commands
```bash
# Check WebSocket connectivity
python3 test_websocket_connection.py

# Monitor voice processing pipeline
python3 debug_voice_pipeline.py

# Test individual components
python3 test_voice_components.py
```

## Next Development Phases

### Phase 1: Voice Call Testing (Current)
- End-to-end voice call functionality
- Real-world conversation scenarios
- Performance benchmarking and optimization

### Phase 2: Search Relevance
- Improve Weaviate search accuracy for voice queries
- Optimize alpha calculation based on voice patterns
- Enhanced product ranking for spoken requests

### Phase 3: Multi-Modal Integration
- Add image processing (OCR for shopping lists)
- Visual product recognition
- Multi-modal supervisor architecture

## API Reference

### WebSocket Endpoints
- **Primary**: `ws://localhost:8000/api/v1/voice/stream`
- **Deepgram**: `ws://localhost:8000/api/v1/voice-deepgram/stream`

### Voice Message Format
```json
{
  "type": "voice_input",
  "audio_data": "base64_encoded_audio",
  "session_id": "session_123",
  "user_id": "user_456",
  "metadata": {
    "sample_rate": 16000,
    "format": "wav",
    "duration_ms": 2500
  }
}
```

### Response Format
```json
{
  "type": "voice_response",
  "text": "I found 5 organic milk options for you.",
  "audio_data": "base64_encoded_audio",
  "metadata": {
    "products_found": 5,
    "search_time_ms": 1200,
    "voice_metadata": {
      "pace": "normal",
      "emotion": "neutral"
    }
  }
}
```

## Conclusion

The LeafLoaf voice integration is production-ready with comprehensive multi-agent support, memory awareness, and all personalization features active. The system processes voice metadata to enhance understanding and provides natural, conversational interactions while maintaining the full power of the underlying AI grocery shopping system.