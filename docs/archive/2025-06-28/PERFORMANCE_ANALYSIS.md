# Performance Analysis & Voice Integration Plan

## Current Latency Breakdown (Observed)
- **Weaviate Search**: 600-1200ms ❌ (Target: <200ms)
- **Gemma Intent**: Unknown (need to measure)
- **Graphiti Processing**: Unknown (need to measure)
- **Total Response**: Way over 300ms target

## Component Testing Plan for Tomorrow

### 1. Isolate Each Component
```python
# Test 1: Weaviate only
start = time.time()
results = await weaviate.search("milk")
print(f"Weaviate: {(time.time()-start)*1000}ms")

# Test 2: Gemma only
start = time.time()
intent = await gemma.analyze("I need milk")
print(f"Gemma: {(time.time()-start)*1000}ms")

# Test 3: Graphiti only
start = time.time()
memory = await graphiti.extract_entities("bought milk")
print(f"Graphiti: {(time.time()-start)*1000}ms")
```

### 2. Optimization Strategies
- **Weaviate**: 
  - Use connection pooling ✅ (already implemented)
  - Reduce result limit (30 → 10)
  - Cache common queries
  - Consider BM25 for speed-critical paths
  
- **Gemma**:
  - Cache intent patterns
  - Use faster model for simple queries
  - Pre-compute alpha for common terms

- **Parallel Processing**:
  - Run Gemma + Weaviate in parallel
  - Start Graphiti before search completes

## Voice Integration Architecture

### You Need BOTH STT and TTS:

```
User speaks → STT (Speech-to-Text) → Your AI → TTS (Text-to-Speech) → User hears
```

### 11Labs Capabilities:
- **11Labs**: TTS only (Text-to-Speech) ✅
- **Does NOT do**: STT (Speech-to-Text) ❌

### Recommended Architecture:

```
1. Speech-to-Text (STT) Options:
   - Google Cloud Speech-to-Text (fast, accurate)
   - OpenAI Whisper API (good accuracy)
   - Deepgram (very fast, streaming)
   - Web Speech API (browser-based, free)

2. Your Processing:
   - Gemma → Weaviate → Graphiti

3. Text-to-Speech (TTS):
   - 11Labs (high quality) ✅
   - Already integrated in your codebase
```

### Optimal Voice Flow:
```
User: "I need organic milk" (audio)
↓
STT (Deepgram): 50-100ms
↓
Gemma: 100ms (cached)
Weaviate: 200ms (optimized)
Graphiti: Async (0ms perceived)
↓
Response: "I found 5 organic milk options"
↓
11Labs TTS: 200-300ms
↓
User hears response

Total: ~550-650ms (acceptable for voice)
```

## Implementation Code Structure:

```python
# voice_handler.py
class VoiceHandler:
    def __init__(self):
        self.stt = DeepgramSTT()  # or Google STT
        self.tts = ElevenLabsTTS()  # you have this
        self.processor = LeafLoafProcessor()
    
    async def handle_voice(self, audio_stream):
        # 1. STT
        text = await self.stt.transcribe(audio_stream)
        
        # 2. Process (parallel where possible)
        response = await self.processor.process(text)
        
        # 3. TTS
        audio = await self.tts.synthesize(response)
        
        return audio
```

## For 11Labs Webhook Integration:

Your current setup expects:
1. User → Some STT service → Text
2. Text → Your webhook
3. Your response → 11Labs TTS → User

So you need to add STT before 11Labs in the flow.

## Performance Targets for Voice:
- STT: <100ms
- Processing: <400ms
- TTS: <300ms
- **Total: <800ms** (1 second max)

## Tomorrow's Testing Priority:
1. Measure each component separately
2. Find the bottlenecks
3. Optimize the slowest parts
4. Then integrate voice

Without optimization, current latency (>1s) is too high for natural voice interaction.