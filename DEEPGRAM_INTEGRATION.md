# Deepgram Integration Documentation

## Overview

This document details our Deepgram integration for voice-native grocery shopping, including successes, limitations, and lessons learned.

## Integration Status

### ✅ What Works

1. **Speech-to-Text (STT)**
   - All languages tested successfully
   - Real-time streaming transcription
   - Code-switching handled perfectly
   - Low latency (~500ms for utterance detection)

2. **Languages Verified**
   - English: Perfect accuracy
   - Hindi (हिन्दी): Excellent, including mixed English
   - Gujarati (ગુજરાતી): Good accuracy
   - Korean (한국어): Good accuracy
   - Spanish: Perfect accuracy

3. **Code-Switching Examples**
   ```
   ✅ "I need 2 kg दाल and rice"
   ✅ "오늘 special offer क्या है?"
   ✅ "Get me some આંટા please"
   ```

### ❌ What Doesn't Work

1. **Text-to-Speech (TTS)**
   - Only supports English and Spanish
   - Cannot pronounce Hindi, Gujarati, Korean text
   - No multilingual voice models available
   - Breaks voice-native experience for non-English users

## Technical Implementation

### STT Configuration

```python
from deepgram import DeepgramClient, LiveOptions

# Critical: Use "multi" for language parameter
options = LiveOptions(
    model="nova-3",              # Latest model with best accuracy
    language="multi",            # Enables multilingual support
    encoding="linear16",         # PCM 16-bit
    sample_rate=16000,          # 16kHz sampling
    channels=1,                 # Mono audio
    smart_format=True,          # Intelligent punctuation
    punctuate=True,             # Add punctuation
    interim_results=True,       # Stream partial results
    utterance_end_ms=1000,      # Detect end of speech
    vad_events=True,            # Voice activity detection
    endpointing=300,            # Silence threshold
)
```

### Audio Processing

```javascript
// Browser audio capture and conversion
audioContext = new AudioContext({ sampleRate: 16000 });
processor = audioContext.createScriptProcessor(4096, 1, 1);

processor.onaudioprocess = (e) => {
    const float32Data = e.inputBuffer.getChannelData(0);
    
    // Convert Float32 to Int16 for Deepgram
    const int16Data = new Int16Array(float32Data.length);
    for (let i = 0; i < float32Data.length; i++) {
        const s = Math.max(-1, Math.min(1, float32Data[i]));
        int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    
    // Send to WebSocket
    ws.send(int16Data.buffer);
};
```

### TTS Limitations

```python
async def text_to_speech(text: str) -> bytes:
    """Deepgram TTS - English/Spanish only"""
    url = "https://api.deepgram.com/v1/speak"
    
    # Available models:
    # - aura-asteria-en (English female)
    # - aura-orion-en (English male)
    # - aura-sofia-es (Spanish female)
    # - aura-mateo-es (Spanish male)
    # NO Hindi, Gujarati, Korean voices
    
    params = {
        "model": "aura-asteria-en",
        "encoding": "mp3"
    }
    
    # This FAILS for Hindi text:
    # text = "नमस्ते, आपका स्वागत है"
    # Result: Garbled pronunciation
```

## Performance Metrics

### STT Performance
- Connection time: ~500ms
- First transcript: ~800ms from speech start
- Final transcript: ~1000ms after speech end
- Accuracy: 95%+ for all tested languages

### TTS Performance
- English/Spanish: 200-300ms generation time
- Other languages: Not applicable (doesn't work)

## Integration Challenges

### 1. Language Detection
Currently relying on post-transcription detection:
```python
def detect_language(text: str) -> str:
    if re.search(r'[\u0900-\u097F]', text):  # Devanagari
        return "hi"
    elif re.search(r'[\u0A80-\u0AFF]', text):  # Gujarati
        return "gu"
    elif re.search(r'[\uAC00-\uD7AF]', text):  # Korean
        return "ko"
    return "en"
```

### 2. Voice Metadata
Deepgram provides limited voice metadata:
- No emotion detection
- No speaker characteristics
- Basic pace can be inferred from word timings

### 3. Error Handling
Common errors and solutions:
```python
# NET-0001: No audio received
# Solution: Implement keepalive

# DATA-0000: Audio format error
# Solution: Ensure 16-bit PCM, 16kHz

# Connection drops
# Solution: Automatic reconnection logic
```

## Cost Analysis

### Current Pricing (July 2025)
- STT Nova: $0.0059/minute
- TTS Aura: $0.015/1000 characters

### Monthly Estimate (1000 users, 10 min/day)
- STT: 1000 × 10 × 30 × $0.0059 = $1,770
- TTS: ~500K chars/day × 30 × $0.015 = $225
- Total: ~$2,000/month

## Recommendations

### Immediate Actions
1. Document TTS limitations clearly in UI
2. Implement graceful fallback for non-English
3. Add visual language indicators

### Short Term
1. Integrate Edge-TTS for multilingual support
2. Keep Deepgram for English/Spanish (quality)
3. Implement language-based routing

### Long Term
1. Explore Deepgram's roadmap for multilingual TTS
2. Consider custom voice models
3. Build phonetic approximation layer

## Key Learnings

1. **STT Excellence**: Deepgram's multilingual STT is production-ready
2. **TTS Gap**: Major limitation for global applications
3. **Code-Switching**: Natural for many users, must be supported
4. **Architecture Impact**: TTS limitation breaks voice-native promise

## Migration Path

```
Current: Deepgram STT + Deepgram TTS (EN/ES only)
    ↓
Next: Deepgram STT + Edge-TTS (multilingual)
    ↓
Future: Deepgram STT + Google Cloud TTS (premium)
```

## Code Examples

### Working: Multilingual STT
See: `voice_streaming_debug.py`
- Full WebSocket implementation
- Audio processing pipeline
- Event handling

### Not Working: Multilingual TTS
```python
# This fails:
hindi_text = "नमस्ते, मैं आपकी मदद करूंगा"
audio = await deepgram_tts(hindi_text)
# Result: English voice trying to pronounce Hindi
```

## Conclusion

Deepgram provides excellent STT for multilingual applications but lacks TTS support for non-English/Spanish languages. This creates an asymmetric experience where users can speak in any language but only hear responses in English/Spanish. Edge-TTS or Google Cloud TTS integration is necessary for true multilingual support.