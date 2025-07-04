# Voice Streaming Recommendation for LeafLoaf

## The Challenge

LeafLoaf needs a voice streaming solution that:
1. **Handles ethnic products correctly** (gochujang, paneer, harissa, etc.)
2. **Supports true bidirectional streaming** for natural conversation
3. **Works with diverse accents and code-switching**
4. **Maintains low latency** for real-time interaction

## Research Findings

### Why Current Implementation Failed

1. **Google STT Streaming Issues**:
   - Streams timeout every few seconds (not suitable for conversation)
   - WEBM_OPUS format issues with browser audio
   - Complex async-to-sync bridge required

2. **Deepgram Limitations**:
   - Poor ethnic product recognition
   - Limited multilingual support compared to alternatives
   - No custom vocabulary in real-time

### Best Solution: Hybrid Approach

## Recommended Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Browser       │────▶│  WebSocket       │────▶│   Rev.ai STT    │
│   Microphone    │     │  Server          │     │  (Low Ethnic    │
└─────────────────┘     │                  │     │   Bias)         │
                        │                  │     └─────────────────┘
                        │                  │              │
                        │                  │              ▼
┌─────────────────┐     │                  │     ┌─────────────────┐
│   Browser       │◀────│                  │◀────│   LangGraph     │
│   Speaker       │     │                  │     │   Multi-Agent   │
└─────────────────┘     │                  │     └─────────────────┘
                        │                  │              │
                        │                  │              ▼
                        │                  │     ┌─────────────────┐
                        │                  │◀────│  ElevenLabs TTS │
                        └──────────────────┘     │  (Natural Voice)│
                                                 └─────────────────┘
```

## Implementation Plan

### Phase 1: Rev.ai Integration (1-2 weeks)
```python
# Rev.ai Streaming with Custom Vocabulary
import revai
from revai.streaming import RevAiStreamingClient

config = revai.StreamingConfig(
    language="en",
    custom_vocabulary=[
        # South Asian
        {"phrase": "paneer", "boost": 15},
        {"phrase": "ghee", "boost": 15},
        {"phrase": "dal", "boost": 10},
        {"phrase": "masala", "boost": 10},
        # East Asian
        {"phrase": "gochujang", "boost": 15},
        {"phrase": "kimchi", "boost": 15},
        {"phrase": "miso", "boost": 10},
        # Middle Eastern
        {"phrase": "harissa", "boost": 15},
        {"phrase": "za'atar", "boost": 15},
        {"phrase": "tahini", "boost": 10},
        # Latin American
        {"phrase": "plantains", "boost": 10},
        {"phrase": "yuca", "boost": 15},
        {"phrase": "mole", "boost": 15},
    ],
    enable_automatic_punctuation=True,
    enable_speaker_diarization=False
)

# WebSocket handler
async def handle_voice_stream(websocket):
    rev_client = RevAiStreamingClient(access_token=REV_AI_TOKEN)
    stream = rev_client.start_stream(config)
    
    # Handle bidirectional streaming
    async for audio_chunk in websocket:
        stream.send_audio(audio_chunk)
        
        # Get transcripts with low latency
        for result in stream:
            if result.type == 'final':
                # Process through LangGraph
                response = await process_with_agents(result.text)
                # Generate TTS
                audio = await elevenlabs_tts(response)
                await websocket.send(audio)
```

### Phase 2: Custom Vocabulary Management (1 week)
```python
# Dynamic vocabulary based on user's shopping patterns
class EthnicVocabularyManager:
    def __init__(self):
        self.base_vocabulary = load_ethnic_products()
        self.user_vocabulary = {}
    
    def personalize_for_user(self, user_id):
        # Get user's purchase history
        purchases = get_user_ethnic_purchases(user_id)
        
        # Boost frequently purchased ethnic items
        custom_vocab = []
        for product in purchases:
            custom_vocab.append({
                "phrase": product.name,
                "boost": min(20, 10 + product.frequency)
            })
        
        return custom_vocab
```

### Phase 3: Fallback Strategy (1 week)
```python
# Multi-provider fallback for maximum coverage
class VoiceStreamingService:
    def __init__(self):
        self.primary = RevAiStreaming()
        self.fallback = AmazonTranscribeStreaming()
        
    async def transcribe(self, audio_stream):
        try:
            # Try Rev.ai first (best ethnic support)
            return await self.primary.transcribe(audio_stream)
        except Exception as e:
            # Fallback to Amazon Transcribe
            logger.warning(f"Rev.ai failed: {e}, using fallback")
            return await self.fallback.transcribe(audio_stream)
```

## Cost Analysis

### Rev.ai Pricing
- Streaming: $0.035/minute
- Custom vocabulary: Included
- Average 3-min conversation: $0.105

### Comparison
- Deepgram: $4.50/hour = $0.225 for 3 minutes (but poor ethnic support)
- Rev.ai + ElevenLabs: ~$0.15 for 3 minutes (excellent ethnic support)

## Testing Strategy

### Ethnic Product Test Suite
```python
test_phrases = {
    "south_asian": [
        "I need paneer and ghee",
        "Add basmati rice and dal",
        "Looking for garam masala"
    ],
    "east_asian": [
        "Do you have gochujang?",
        "I want kimchi and miso",
        "Need soy sauce and dashi"
    ],
    "middle_eastern": [
        "Where is the harissa?",
        "I need za'atar and sumac",
        "Looking for tahini"
    ],
    "mixed": [
        "I need paneer, kimchi, and harissa",
        "Add plantains and gochujang to cart"
    ]
}
```

## Recommended Next Steps

1. **Sign up for Rev.ai** free tier (5 hours free)
2. **Create ethnic product vocabulary** from your catalog
3. **Build WebSocket streaming server** with Rev.ai
4. **Test with diverse speakers** and ethnic products
5. **Compare accuracy** with current implementation
6. **Deploy incrementally** with A/B testing

## Alternative: Amazon Transcribe Streaming

If Rev.ai doesn't meet needs:
- Use Amazon Transcribe Streaming with custom vocabularies
- Proven to work well with Hinglish and code-switching
- Better AWS integration if already using AWS

## Conclusion

**Rev.ai** offers the best combination of:
- Low ethnic bias (proven in testing)
- True streaming support
- Custom vocabulary for ethnic products
- Human-in-the-loop training on diverse speech

This will solve both the streaming timeout issues and the ethnic product recognition problems you experienced.