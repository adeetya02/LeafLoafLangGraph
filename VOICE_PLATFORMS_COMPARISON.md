# Voice Platform Comparison: Deepgram vs ElevenLabs vs Gemini

## Overview
Comprehensive comparison of three voice platforms for LeafLoaf's conversational AI.

## 1. Deepgram (Current Implementation)

### Architecture
```
[Audio] → Deepgram STT → Your LLM → Deepgram TTS → [Audio]
```

### Pros
- **Excellent STT**: Industry-leading accuracy with Nova-2 model
- **Low Latency**: 50-200ms for STT
- **Real-time Streaming**: WebSocket support
- **Audio Intelligence**: Sentiment, intent detection (batch API)
- **Good Documentation**: Well-documented APIs

### Cons
- **Robotic TTS**: Even "aura-helios-en" sounds mechanical
- **Complex Integration**: Separate STT/TTS connections
- **Limited Voice Options**: Few natural-sounding voices
- **No Native LLM**: Need to integrate your own

### Implementation Status
- ✅ STT WebSocket connection
- ✅ TTS WebSocket connection  
- ⚠️ Transcript events not firing (debugging needed)
- ✅ Audio streaming working

### Cost
- STT: $0.0125/minute
- TTS: $0.015/1000 chars
- Total: ~$1.50/hour conversation

### Code Sample
```python
# Current implementation
self.stt_connection = self.deepgram.listen.websocket.v("1")
self.tts_connection = self.deepgram.speak.websocket.v("1")
```

## 2. ElevenLabs (Industry Standard for Natural TTS)

### Architecture  
```
[Audio] → Deepgram STT → Your LLM → ElevenLabs TTS → [Audio]
```

### Pros
- **Most Natural TTS**: Industry-leading voice quality
- **Emotional Expression**: Conveys tone and emotion
- **Voice Cloning**: Create custom voices
- **Multiple Voices**: Rachel, Domi, Bella, Antoni, etc.
- **WebSocket Streaming**: Real-time audio

### Cons
- **No STT**: TTS only, need Deepgram for STT
- **Higher Cost**: 20x more expensive than Deepgram
- **Rate Limits**: Strict limits on lower tiers
- **Latency**: 200-400ms (higher than Deepgram)

### Best Voices for Grocery Assistant
1. **Rachel** - Warm, friendly, clear
2. **Bella** - Young, enthusiastic
3. **Antoni** - Professional, trustworthy
4. **Domi** - Energetic, helpful

### Cost
- TTS: $0.30/1000 chars (Starter plan)
- With Deepgram STT: ~$15/hour conversation

### Integration Example
```python
# ElevenLabs WebSocket
uri = "wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"
headers = {"xi-api-key": ELEVENLABS_KEY}

# Send text
await websocket.send(json.dumps({
    "text": "I found organic milk for $5.99!",
    "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.75,
        "style": 0.5,  # Conversational
        "use_speaker_boost": True
    }
}))
```

## 3. Gemini 2.5 (NEW - Native Voice on GCP)

### Architecture
```
[Audio] → Gemini (STT + LLM + TTS) → [Audio]
```

### Pros
- **All-in-One**: STT + LLM + TTS in single API
- **Native GCP**: Perfect for your infrastructure
- **Natural Language Control**: Control voice with prompts
- **Multilingual**: 24+ languages with accent control
- **Context Aware**: Maintains conversation context
- **Style Control**: Tone, pace, pitch, accent

### Cons
- **Newer**: Less battle-tested than others
- **Documentation**: Still evolving
- **Limited Voice Variety**: Fewer voice options than ElevenLabs
- **GCP Lock-in**: Tied to Google Cloud

### Voice Configuration
```python
"voice_config": {
    "style": "friendly",      # friendly, professional, casual
    "pace": "medium",         # slow, medium, fast
    "pitch": "medium",        # low, medium, high
    "accent": "american"      # american, british, australian
}
```

### Cost (Estimated)
- Gemini 2.0 Flash: ~$0.075/1000 chars
- Total: ~$4-5/hour conversation

### Unique Features
- **Interruption Handling**: Native support
- **Turn-Taking**: Automatic management
- **Function Calling**: Built-in with voice context
- **Emotion Understanding**: Better context awareness

## Side-by-Side Comparison

| Feature | Deepgram | ElevenLabs | Gemini 2.5 |
|---------|----------|------------|------------|
| **STT Quality** | ⭐⭐⭐⭐⭐ | N/A | ⭐⭐⭐⭐ |
| **TTS Quality** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Latency** | 50-200ms | 200-400ms | 100-300ms |
| **Natural Voice** | Limited | Excellent | Good |
| **Integration** | Complex | Simple (TTS only) | Simple |
| **Cost/Hour** | $1.50 | $15 | $4-5 |
| **GCP Native** | No | No | Yes |
| **LLM Included** | No | No | Yes |
| **Voice Control** | Basic | Advanced | Natural Language |
| **Interruptions** | Manual | Manual | Automatic |

## Recommended Combinations

### 1. **Budget Conscious**: Deepgram STT + Gemma LLM + Deepgram TTS
- Cost: $1.50/hour
- Quality: Functional but robotic

### 2. **Best Quality**: Deepgram STT + Gemini LLM + ElevenLabs TTS
- Cost: $15/hour
- Quality: Professional, natural

### 3. **GCP Native**: Gemini 2.5 (All-in-One)
- Cost: $4-5/hour
- Quality: Good, improving rapidly

### 4. **Balanced**: Deepgram STT + Gemini LLM + Gemini TTS
- Cost: $3-4/hour
- Quality: Good STT, natural TTS

## Implementation Strategy

### Phase 1: Test All Three (This Week)
1. Fix Deepgram transcript issue
2. Add ElevenLabs TTS option
3. Implement Gemini native voice
4. Create A/B testing framework

### Phase 2: Evaluate (Next Week)
- User preference testing
- Latency measurements
- Cost analysis
- Quality assessment

### Phase 3: Optimize (Week 3)
- Choose primary platform
- Implement fallbacks
- Optimize for production

## Quick Setup for Each

### Deepgram
```bash
# Already configured
DEEPGRAM_API_KEY: "36a821d351939023aabad9beeaa68b391caa124a"
```

### ElevenLabs
```bash
# Add to .env.yaml
ELEVENLABS_API_KEY: "your-key-here"
```

### Gemini
```bash
# Add to .env.yaml
GOOGLE_API_KEY: "your-key-here"
GCP_PROJECT_ID: "leafloaf-production"
```

## Testing URLs
- Deepgram: `/static/voice_conversational.html`
- ElevenLabs: `/static/voice_elevenlabs.html` (to create)
- Gemini: `/static/voice_gemini.html` (to create)

## Final Recommendation

**Start with Gemini 2.5** for these reasons:
1. Native GCP integration (you're already on GCP)
2. Unified solution (less complexity)
3. Good balance of quality and cost
4. Rapidly improving platform

**Use ElevenLabs** if:
- Voice quality is paramount
- Budget is not a concern
- You need voice cloning

**Keep Deepgram** for:
- Fallback STT (most reliable)
- Cost-sensitive deployments
- Maximum STT accuracy needs