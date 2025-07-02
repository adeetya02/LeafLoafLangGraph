# Voice Architecture Comparison: Manual vs Voice Agent API

## Current Manual Approach (STT → LLM → TTS)

### Architecture
```
[User Voice] → [Deepgram STT] → [Your Gemma LLM] → [Deepgram TTS] → [User]
     ↑                                   ↓
     └────── Your Business Logic ────────┘
```

### Pros
- **Full Control**: You control every aspect of the conversation
- **Custom Logic**: Direct integration with your search, personalization, cart
- **Flexible**: Can switch any component (STT/LLM/TTS) independently
- **Tested**: Already partially working

### Cons  
- **Complex**: You manage WebSocket connections, turn-taking, interruptions
- **More Code**: Handle audio streaming, buffering, synchronization
- **Latency**: Each component adds delay (STT → LLM → TTS)
- **Current Issue**: Transcripts not firing (sync/async handler mismatch)

### Implementation Status
- ✅ TTS working (but robotic with aura-helios-en)
- ❌ STT transcripts not being received
- ✅ LLM integration ready
- ✅ Business logic integrated

## Voice Agent API Approach

### Architecture  
```
[User Voice] ←→ [Deepgram Voice Agent API] ←→ [Your Gemini LLM]
                           ↓                            ↓
                    (Handles STT/TTS)          (Your Business Logic)
```

### Pros
- **Unified**: Single WebSocket connection to Voice Agent
- **Managed**: Deepgram handles interruptions, turn-taking, audio sync
- **Lower Latency**: Optimized end-to-end pipeline
- **Less Code**: No audio handling, just business logic
- **Natural Voice**: Better TTS quality with agent optimization
- **Function Calling**: Built-in support for your search/cart functions

### Cons
- **Less Control**: Can't tweak individual STT/TTS parameters as much
- **Newer**: Voice Agent API is relatively new
- **Dependency**: Relies on Deepgram's agent infrastructure

### How It Works
1. **You provide**:
   - LLM choice (Gemini)
   - System prompt (grocery assistant personality)
   - Function definitions (search_products, add_to_cart)

2. **Voice Agent handles**:
   - Audio streaming
   - Speech detection
   - Interruption handling
   - Turn management
   - TTS generation

3. **Your LLM (Gemini) gets**:
   - User transcripts
   - Conversation context
   - Function call requests

## Recommendation

**Use Voice Agent API** because:

1. **Faster Development**: Skip all the WebSocket complexity
2. **Better UX**: Natural conversation flow out of the box
3. **Your Business Logic Intact**: Still uses your Gemini LLM and functions
4. **Production Ready**: Handles edge cases you haven't coded yet
5. **Less Maintenance**: Deepgram maintains the voice pipeline

## Migration Path

### Phase 1: Voice Agent with Gemini (Immediate)
```javascript
// Simple configuration
{
  "agent": {
    "think": {
      "provider": {
        "type": "google",
        "api_key": "YOUR_GEMINI_KEY",
        "model": "gemini-2.0-flash"
      },
      "functions": [
        // Your LeafLoaf functions
      ]
    }
  }
}
```

### Phase 2: Enhanced Integration (Later)
- Add more functions (reorder, personalization)
- Implement voice-specific responses
- Add conversation memory

## Quick Start

1. **Get Gemini API Key**:
   ```bash
   # Add to .env.yaml
   GEMINI_API_KEY: "your-key-here"
   ```

2. **Update main.py** to include Voice Agent router:
   ```python
   from src.api.voice_agent_api import router as voice_agent_router
   app.include_router(voice_agent_router)
   ```

3. **Test** at `/api/v1/voice-agent/stream`

## Cost Comparison

### Manual Approach
- Deepgram STT: $0.0125/min
- Your LLM: Gemini costs
- Deepgram TTS: $0.015/1000 chars
- **Total**: ~$1.50/hour

### Voice Agent API
- Voice Agent: ~$0.02-0.03/min (includes STT+TTS)
- Your LLM: Same Gemini costs
- **Total**: ~$1.80-2.00/hour

## Decision Matrix

| Feature | Manual | Voice Agent |
|---------|---------|-------------|
| Development Time | Weeks | Days |
| Complexity | High | Low |
| Control | Full | Moderate |
| Natural Conversation | Hard | Built-in |
| Maintenance | High | Low |
| Cost | Lower | Slightly Higher |

## Final Recommendation

**Start with Voice Agent API** to get a working voice interface quickly, then optimize later if needed. The slightly higher cost is worth the massive reduction in complexity and development time.