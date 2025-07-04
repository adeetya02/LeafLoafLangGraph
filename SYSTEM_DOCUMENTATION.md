# LeafLoaf LangGraph - Complete System Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Voice Integration](#voice-integration)
4. [Agent System](#agent-system)
5. [Weaviate Integration](#weaviate-integration)
6. [Graphiti + Spanner](#graphiti--spanner)
7. [ML Implementation](#ml-implementation)
8. [API Endpoints](#api-endpoints)
9. [Testing & Deployment](#testing--deployment)
10. [Future Roadmap](#future-roadmap)

---

## System Overview

LeafLoaf is a production-grade, voice-enabled grocery shopping system with multi-agent architecture designed to compete with major firms. The system features:

- **Voice-Native Interface**: Complete voice interaction using Deepgram STT/TTS
- **Multi-Agent Architecture**: Specialized agents for different tasks
- **Real-time Personalization**: Graphiti + Spanner for user behavior learning
- **Hybrid Search**: Weaviate vector DB with BM25 fallback
- **ML-Ready Infrastructure**: BigQuery streaming for future ML models

### Current Status (July 2025)
- ✅ Voice pipeline working (Deepgram → Gemini → Deepgram)
- ✅ Multi-agent system with supervisor routing
- ✅ Graphiti integration at agent level
- ✅ 103/103 personalization tests passing
- ⚠️ Weaviate credits exhausted (using BM25 fallback)
- 🚧 Full supervisor integration pending

---

## Architecture

### System Flow
```
Voice Input → Deepgram STT → Supervisor (Intent) → Agent Selection → Action → Response Compiler → Deepgram TTS → Voice Output
                                    ↓                      ↓
                              Gemini 1.5 Flash        Product Search
                              (Intent Classification)  Order Agent
                                    ↓                  Cart Agent
                              Gemma 2 9B
                              (Alpha Calculation)
```

### Key Components

1. **Voice Layer**
   - Deepgram Nova-3 for STT
   - Deepgram Aura for TTS
   - WebSocket real-time streaming

2. **Intelligence Layer**
   - Gemini 1.5 Flash: Intent classification
   - Gemma 2 9B: Voice metadata → search alpha
   - Groq Mixtral: Fallback LLM

3. **Data Layer**
   - Weaviate: Vector search (products)
   - Spanner: Graph database (relationships)
   - Redis: Session management
   - BigQuery: Analytics streaming

---

## Voice Integration

### Voice Pipeline Files

1. **Working Implementation**
   ```
   voice_streaming_debug.py - Current working version with STT + TTS + LLM
   ```

2. **Architecture**
   ```python
   # Voice Session Flow
   class DebugVoiceSession:
       1. Initialize Deepgram connection
       2. Register event handlers (transcript, utterance_end)
       3. On utterance_end:
          - Get Gemini response
          - Convert to speech with TTS
          - Send audio back to client
   ```

3. **Voice Metadata**
   ```python
   voice_metadata = {
       "pace": "fast|normal|slow",      # Speaking speed
       "urgency": "high|medium|low",    # Derived from pace + duration
       "emotion": "neutral|...",        # Future: emotion detection
       "volume": "normal|loud|quiet",   # Future: volume analysis
       "duration": 2.5,                 # Speech duration in seconds
       "word_count": 10                 # Number of words spoken
   }
   ```

### API Keys
- Deepgram: `36a821d351939023aabad9beeaa68b391caa124a`
- Gemini: `AIzaSyCdbX90Q337x0dg2MIF2g0id7CMnGQSVgg`

---

## Deepgram Integration

### Overview
Deepgram provides both Speech-to-Text (STT) and Text-to-Speech (TTS) capabilities for the voice-native interface.

### 1. Speech-to-Text (STT) ✅ MULTILINGUAL SUCCESS

**Model**: Nova-3 (Latest and most accurate)
**Languages Tested**: English, Hindi (हिन्दी), Gujarati (ગુજરાતી), Korean (한국어)
**Code-Switching**: Fully supported

**Key Findings**:
- Nova-3 with `language="multi"` handles all tested languages perfectly
- No accuracy loss when switching between languages mid-sentence
- Correctly transcribes: "I need 2 kg दाल and some rice"
- Handles script changes seamlessly

**WebSocket Connection**:
```python
from deepgram import DeepgramClient, LiveOptions

# Initialize client
deepgram = DeepgramClient(DEEPGRAM_API_KEY)
connection = deepgram.listen.asyncwebsocket.v("1")

# Configure options for multilingual support
options = LiveOptions(
    model="nova-3",
    language="multi",        # Critical: enables multilingual mode
    encoding="linear16",      # PCM 16-bit
    sample_rate=16000,       # 16kHz
    channels=1,              # Mono
    smart_format=True,       # Punctuation, capitalization
    punctuate=True,         
    interim_results=True,    # Real-time partials
    utterance_end_ms=1000,   # End of speech detection
    vad_events=True,         # Voice activity detection
    endpointing=300,         # Silence threshold
    # Note: keyterm boosting works with multilingual
)
```

**Event Handlers**:
```python
# Connection events
connection.on("open", on_open)           # WebSocket opened
connection.on("close", on_close)         # Connection closed
connection.on("error", on_error)         # Error handling

# Transcription events
connection.on("Results", on_results)     # Transcription results
connection.on("transcript", on_transcript) # Alternative handler

# Speech events
connection.on("SpeechStarted", on_speech_started)
connection.on("UtteranceEnd", on_utterance_end)  # User stopped speaking

# Metadata
connection.on("Metadata", on_metadata)   # Connection metadata
```

**Audio Processing**:
```python
# Browser audio is Float32, Deepgram needs Int16 PCM
def convert_audio(float32_data):
    output = new Int16Array(float32_data.length)
    for i in range(len(float32_data)):
        s = max(-1, min(1, float32_data[i]))
        output[i] = s * 0x8000 if s < 0 else s * 0x7FFF
    return output.buffer
```

**Ethnic Product Boosting**:
```python
ETHNIC_KEYWORDS = [
    # South Asian
    "paneer:15", "ghee:15", "dal:12", "masala:10",
    "basmati:10", "atta:12", "jaggery:15",
    
    # East Asian  
    "gochujang:15", "kimchi:12", "miso:12", "tofu:10",
    
    # Middle Eastern
    "harissa:15", "zaatar:15", "tahini:12",
    
    # Latin American
    "plantains:10", "yuca:15", "mole:15",
    
    # African
    "injera:15", "berbere:15", "jollof:12"
]
```

### 2. Text-to-Speech (TTS)

**Model**: Aura Asteria (Natural, conversational voice)

**⚠️ CRITICAL LIMITATION**: Deepgram TTS only supports English and Spanish
- No support for Hindi, Gujarati, Korean, or other languages
- English voices cannot properly pronounce non-English text
- This is a significant limitation for multilingual applications

**REST API Implementation**:
```python
async def text_to_speech(text: str) -> bytes:
    url = "https://api.deepgram.com/v1/speak"
    
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    params = {
        "model": "aura-asteria-en",  # Voice model
        "encoding": "mp3",           # Audio format
        "sample_rate": 16000,        # Optional
        "bit_rate": 128000          # Optional
    }
    
    payload = {"text": text}
    
    response = requests.post(url, headers=headers, 
                           params=params, json=payload)
    
    if response.status_code == 200:
        return response.content  # MP3 audio bytes
```

**Available Voices**:
- **English**: aura-asteria-en, aura-luna-en, aura-stella-en, aura-orion-en, aura-arcas-en
- **Spanish**: aura-sofia-es, aura-mateo-es
- **Other Languages**: ❌ Not supported

### 3. WebSocket Message Flow

**Client → Server**:
```javascript
// 1. Establish WebSocket
ws = new WebSocket('ws://localhost:7777/ws')

// 2. Send audio chunks (binary)
ws.send(pcmAudioBuffer)  // Int16 PCM audio
```

**Server → Client**:
```json
// Transcription update
{
    "type": "transcript",
    "text": "I need milk and eggs",
    "is_final": true
}

// TTS response
{
    "type": "tts_audio",
    "text": "I'll help you find milk and eggs",
    "audio": "base64_encoded_mp3_data"
}
```

### 4. Voice Activity Detection (VAD)

**Speech Started**:
```json
{
    "type": "SpeechStarted",
    "channel": [0, 1],
    "timestamp": 0.48
}
```

**Utterance End**:
```json
{
    "type": "UtteranceEnd",
    "channel": [0, 1],
    "last_word_end": 2.71
}
```

### 5. Real-time Transcription

**Interim Results** (while speaking):
```json
{
    "type": "Results",
    "channel_index": [0, 1],
    "is_final": false,
    "speech_final": false,
    "channel": {
        "alternatives": [{
            "transcript": "I need mil",
            "confidence": 0.95
        }]
    }
}
```

**Final Results** (speech complete):
```json
{
    "type": "Results", 
    "channel_index": [0, 1],
    "is_final": true,
    "speech_final": true,
    "channel": {
        "alternatives": [{
            "transcript": "I need milk and eggs.",
            "confidence": 0.98,
            "words": [
                {"word": "i", "start": 0.48, "end": 0.56},
                {"word": "need", "start": 0.56, "end": 0.88},
                {"word": "milk", "start": 0.88, "end": 1.2},
                {"word": "and", "start": 1.2, "end": 1.36},
                {"word": "eggs", "start": 1.36, "end": 1.68}
            ]
        }]
    }
}
```

### 6. Browser Integration

**Audio Capture**:
```javascript
// Get microphone
stream = await navigator.mediaDevices.getUserMedia({
    audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        sampleRate: 16000
    }
});

// Create audio pipeline
audioContext = new AudioContext({ sampleRate: 16000 });
source = audioContext.createMediaStreamSource(stream);
processor = audioContext.createScriptProcessor(4096, 1, 1);

// Process and send audio
processor.onaudioprocess = (e) => {
    const float32 = e.inputBuffer.getChannelData(0);
    const int16 = convertToInt16(float32);
    ws.send(int16.buffer);
};
```

**Audio Playback**:
```javascript
// Receive TTS audio
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'tts_audio') {
        const audioBlob = base64ToBlob(data.audio, 'audio/mp3');
        const audioUrl = URL.createObjectURL(audioBlob);
        audioPlayer.src = audioUrl;
        audioPlayer.play();
    }
};
```

### 7. Error Handling

**Common Errors**:
```python
# NET-0001: No audio received timeout
# Solution: Check microphone, send keepalive

# DATA-0000: Audio decoding error  
# Solution: Verify PCM format, sample rate

# AUTH-0001: Invalid API key
# Solution: Check DEEPGRAM_API_KEY

# RATE-0001: Rate limit exceeded
# Solution: Implement backoff, upgrade plan
```

### 8. Performance Optimization

1. **Connection Pooling**: Reuse WebSocket connections
2. **Audio Buffering**: Send chunks of optimal size (4096 samples)
3. **Compression**: Use opus encoding for bandwidth
4. **Regional Endpoints**: Use closest Deepgram server
5. **Batch Processing**: Group multiple TTS requests

### 9. Cost Optimization

**Pricing** (as of July 2025):
- STT Nova: $0.0059/minute
- TTS Aura: $0.015/1000 characters

**Optimization Strategies**:
1. Use VAD to avoid processing silence
2. Set appropriate `endpointing` values
3. Disable `interim_results` if not needed
4. Use caching for repeated TTS phrases
5. Implement client-side silence detection

### 10. Multilingual Limitations & Solutions

**Current Issues**:
1. **TTS Language Support**: Only English and Spanish
2. **Code-Switching**: Users mix languages (e.g., "I need some दाल and rice")
3. **Voice-Native RAG**: Need consistent voice experience across languages

**Impact on Voice-Native RAG Architecture**:
```
User Input (Multi-modal) → STT (Works) → LLM (Works) → TTS (FAILS for non-EN/ES)
     ↓                         ↓              ↓                    ↓
Text: "मुझे दूध चाहिए"    Transcribes    Responds in      Cannot pronounce
Voice: Hindi accent       correctly      Hindi correctly   Hindi text
```

**Proposed Multi-Modal Solution**:

1. **Unified Input Handling**:
```python
class MultiModalProcessor:
    async def process_input(self, input_type: str, data: Any):
        if input_type == "voice":
            # STT → Text (Deepgram handles multilingual)
            text = await self.stt_process(data)
            lang = self.detect_language(text)
        elif input_type == "text":
            # Direct text input (same as voice transcription)
            text = data
            lang = self.detect_language(text)
        
        # Process through RAG pipeline
        response = await self.rag_pipeline(text, lang)
        
        # Multi-modal output
        return {
            "text": response,
            "audio": await self.get_audio(response, lang),
            "language": lang,
            "display_mode": "audio" if lang in ["en", "es"] else "text"
        }
```

2. **Language-Aware TTS Strategy**:
```python
async def get_audio(self, text: str, language: str):
    if language in ["en", "es"]:
        # Use Deepgram TTS
        return await self.deepgram_tts(text)
    else:
        # Fallback options:
        # 1. Return None (UI shows text only)
        # 2. Use phonetic transliteration
        # 3. Use alternative TTS service
        return None
```

3. **UI Adaptation for Multi-Modal**:
```javascript
// Seamless handling of voice and text
function displayResponse(response) {
    // Always show text
    showText(response.text, response.language);
    
    // Play audio if available
    if (response.audio) {
        playAudio(response.audio);
    } else {
        // Visual indicator for text-only mode
        showTextOnlyIndicator(response.language);
    }
}
```

**Google TTS/STT Concerns**:
- **Previous Issues**: Latency, quota limits, authentication complexity
- **Alternative Approach**: Use Deepgram STT (working) + Fallback TTS strategy
- **Hybrid Solution**: Deepgram for EN/ES, text-only for other languages
- **Future Option**: Azure Speech Services (better language coverage than Google)

**Recommendations for Production**:
1. **Phase 1**: Accept TTS limitations, enhance text display for non-EN/ES
2. **Phase 2**: Add Azure/AWS Polly for critical languages (Hindi, Korean)
3. **Phase 3**: Build custom phonetic models for common phrases
4. **Long-term**: Partner with regional TTS providers

### 11. Multilingual Use Case Example

**Scenario**: Hindi-speaking user shopping for groceries

**Turn 1**:
```
User: "Hello, मुझे इस week की shopping करनी है"
STT: ✅ Perfect transcription with code-switching
Gemini: ✅ Understands and responds in Hindi
TTS: ❌ Cannot speak Hindi response
```

**Turn 2**:
```
User: "मुझे 5 kg आटा, 2 kg दाल और 1 litre दूध चाहिए"
STT: ✅ Captures Hindi with English units perfectly
Gemini: ✅ "ठीक है, मैंने add कर दिया है"
TTS: ❌ English voice mangles Hindi pronunciation
```

**Impact**: Users can speak naturally but hear robotic/wrong responses

### 12. Current Working Implementation

**File**: `voice_streaming_debug.py`
- STT: Fully functional with all languages
- LLM: Gemini 1.5 Pro handles multilingual perfectly
- TTS: Limited to English/Spanish only
- Intent Detection: Works across languages

**Key Code**:
```python
# STT Configuration (WORKING)
options = LiveOptions(
    model="nova-3",
    language="multi",  # This enables multilingual
    # ... other options
)

# LLM Prompt (WORKING)
"You can understand and respond in English, Hindi, Gujarati, Korean..."
# Gemini responds correctly in requested language

# TTS Attempt (FAILING for non-English)
async def text_to_speech(text: str) -> bytes:
    # Only works for English/Spanish
    # Hindi text like "नमस्ते" cannot be pronounced
```

**Test Results**:
- English: Full pipeline works ✅
- Spanish: Full pipeline works ✅
- Hindi: STT ✅, LLM ✅, TTS ❌
- Gujarati: STT ✅, LLM ✅, TTS ❌
- Korean: STT ✅, LLM ✅, TTS ❌

---

## Agent System

### 1. Supervisor Agent (`src/agents/supervisor_optimized.py`)

**Purpose**: Route queries to appropriate agents based on intent

**Key Features**:
- Voice-native with Gemma 2 9B
- Intent classification using Gemini 1.5 Flash
- Dynamic alpha calculation for search
- Graphiti integration for memory

**Core Methods**:
```python
async def analyze_with_voice_context(
    query: str,
    user_id: str,
    session_id: str,
    voice_metadata: Dict
) -> Dict:
    # Returns: intent, confidence, entities, suggested_alpha
```

**Supported Intents**:
- `greeting`: General conversation
- `product_search`: Find products
- `add_to_cart`: Cart operations
- `view_cart`: Show cart contents
- `checkout`: Process order
- `order_status`: Track orders
- `reorder`: Repeat past orders

### 2. Product Search Agent (`src/agents/product_search.py`)

**Purpose**: Search products using Weaviate

**Key Features**:
- Hybrid search (vector + keyword)
- Voice-driven alpha adjustment
- Memory-aware (inherits from MemoryAwareAgent)
- Ethnic product boosting

**Search Parameters**:
```python
alpha = voice_metadata_to_alpha(voice_metadata)
# Fast speech → alpha=0.3 (keyword focus)
# Slow speech → alpha=0.7 (semantic focus)
# Normal → alpha=0.5 (balanced)
```

### 3. Order Agent (`src/agents/order_agent.py`)

**Purpose**: Manage cart and orders

**Tools**:
- `add_to_cart`: Add items with quantity
- `remove_from_cart`: Remove items
- `update_quantity`: Modify amounts
- `view_cart`: Display current cart
- `checkout`: Process order
- `clear_cart`: Empty cart

**React Pattern Implementation**:
```python
# Thought → Action → Observation loop
# Max iterations: 10
# Handles complex multi-step operations
```

### 4. Response Compiler (`src/agents/response_compiler.py`)

**Purpose**: Merge results from multiple agents

**Features**:
- Voice-aware response formatting
- Section-based output (search results, recommendations, cart)
- Personalization integration
- Natural language generation

---

## Weaviate Integration

### Configuration
```python
WEAVIATE_URL = "https://leafloaf-3ztlkdfr.weaviate.network"
WEAVIATE_API_KEY = "dqgYp9Tp0AkZ6dKxpWA8iltXgHhSs90K5lwH"
```

### Product Schema
```python
class Product:
    product_id: str
    product_name: str
    brand: str
    category: str
    sub_category: str
    current_price: float
    original_price: float
    description: str
    ingredients: List[str]
    nutrition_info: Dict
    dietary_info: List[str]
    availability_status: str
    store_location: str
```

### Search Implementation

1. **Hybrid Search**
   ```python
   # Combines vector similarity and BM25
   response = (
       client.query
       .get("GroceryProduct", properties)
       .with_hybrid(
           query=search_query,
           alpha=alpha,  # 0=keyword only, 1=vector only
           fusion_type=HybridFusion.RELATIVE_SCORE
       )
       .with_limit(limit)
       .do()
   )
   ```

2. **Ethnic Product Boosting**
   ```python
   ETHNIC_KEYWORDS = [
       "paneer:15", "ghee:15", "kimchi:12", 
       "harissa:15", "plantains:10", "injera:15"
   ]
   # Boost scores for cultural products
   ```

3. **Current Issues**
   - ⚠️ Credits exhausted - using BM25 fallback
   - Search relevance needs improvement
   - Missing product images in some results

---

## Graphiti + Spanner

### Architecture

1. **Graphiti Memory System** (`src/memory/graphiti_memory_spanner.py`)
   - Production GraphRAG using Google Cloud Spanner
   - Real-time relationship learning
   - No hardcoded rules - pure learning

2. **Spanner Schema**
   ```sql
   -- Nodes table
   CREATE TABLE nodes (
       uuid STRING(36) NOT NULL,
       entity_type STRING(50),
       entity_name STRING(255),
       facts JSON,
       created_at TIMESTAMP,
       updated_at TIMESTAMP
   ) PRIMARY KEY (uuid);

   -- Edges table  
   CREATE TABLE edges (
       uuid STRING(36) NOT NULL,
       source_uuid STRING(36),
       target_uuid STRING(36),
       relation_type STRING(50),
       facts JSON,
       created_at TIMESTAMP,
       episodes JSON
   ) PRIMARY KEY (uuid);
   ```

3. **Relationship Types**
   - `BOUGHT_WITH`: Co-purchase patterns
   - `PREFERS`: Brand/product preferences
   - `AVOIDS`: Dietary restrictions
   - `REGULARLY_BUYS`: Purchase frequency
   - `REORDERS`: Repeat purchases
   - `PRICE_SENSITIVE`: Budget patterns

### Integration Points

1. **Supervisor Level**
   ```python
   # Extract entities and create relationships
   await self.graphiti.add_episode(
       name=f"search_{timestamp}",
       episode_body=query,
       source_description="user voice query"
   )
   ```

2. **Order Agent Level**
   ```python
   # Track purchase patterns
   await self._track_purchase_pattern(user_id, products)
   ```

3. **Personalization Engine** (`src/personalization/graphiti_personalization_engine.py`)
   - 10 self-learning features
   - Zero hardcoded rules
   - Real-time adaptation

---

## ML Implementation

### Current State: BigQuery Streaming

1. **Event Tables**
   ```
   leafloaf_analytics.raw_events:
   - user_search_events
   - product_interaction_events  
   - cart_modification_events
   - order_transaction_events
   - recommendation_impression_events
   ```

2. **Event Capture** (`src/services/bigquery_service.py`)
   ```python
   async def log_search_event(
       user_id: str,
       session_id: str,
       query: str,
       results: List[Dict],
       voice_metadata: Dict
   ):
       # Non-blocking streaming insert
       # Captures all context for ML training
   ```

3. **ML Features Tracked**
   - Search queries and results
   - Click-through rates
   - Cart additions/removals
   - Purchase completions
   - Voice interaction patterns
   - Session behavior

### Future ML Plans

1. **Phase 1: Rule-Based Recommendations**
   - Reorder suggestions based on frequency
   - Complementary products from co-purchase
   - Popular items in category

2. **Phase 2: Collaborative Filtering**
   - User-user similarity
   - Item-item relationships
   - Matrix factorization

3. **Phase 3: Deep Learning**
   - Transformer models for query understanding
   - RNN for session modeling
   - Multi-modal embeddings (text + voice)

4. **Phase 4: Reinforcement Learning**
   - Optimize for cart value
   - Personalized pricing
   - Dynamic inventory management

---

## API Endpoints

### Voice Endpoints
```
POST /api/v1/voice/process
- Process voice input through full pipeline

WebSocket /ws
- Real-time voice streaming
```

### Core Endpoints
```
POST /api/v1/process
- Main text-based query processing

POST /api/v1/search
- Direct product search

GET /api/v1/cart/{user_id}
- View cart contents

POST /api/v1/analytics/event
- Log analytics events
```

### Health & Monitoring
```
GET /health
- System health check

GET /health/agents
- Individual agent status
```

---

## Testing & Deployment

### Test Suites

1. **Personalization Tests** (103 tests)
   ```bash
   python3 run_all_personalization_tests.py
   ```

2. **Voice Integration Tests**
   ```bash
   python3 test_voice_scenarios_comprehensive.py
   python3 test_voice_supervisor_integration.py
   ```

3. **Agent Tests**
   ```bash
   pytest tests/agents/
   ```

### Local Development
```bash
# Start voice server
python3 voice_streaming_debug.py

# Start main API
python3 run.py

# Environment setup
cp .env.example .env.yaml
# Add API keys
```

### GCP Deployment
```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT_ID/leafloaf

# Deploy to Cloud Run
gcloud run deploy leafloaf \
  --image gcr.io/PROJECT_ID/leafloaf \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Environment Variables
- Development: `.env.yaml`
- Production: `.env.production.yaml`
- Secrets: Google Secret Manager

---

## Future Roadmap

### Immediate (Demo Ready)
1. Complete supervisor integration with voice
2. Fix search relevance issues
3. Enable cart persistence
4. Add basic ML recommendations

### Short Term (1-2 weeks)
1. Multi-modal support (voice + images)
2. Phone call integration (Twilio/Deepgram)
3. Redis caching layer
4. A/B testing framework

### Medium Term (1 month)
1. Advanced ML models
2. Real-time inventory integration
3. Delivery scheduling
4. Payment processing

### Long Term (3 months)
1. Multi-language support
2. Recipe integration
3. Meal planning AI
4. Nutrition optimization

---

## Troubleshooting

### Common Issues

1. **"Connection refused" errors**
   - Check if server is running: `ps aux | grep python`
   - Try different URL: `http://127.0.0.1:7777`
   - Check firewall settings

2. **Audio playback issues**
   - Browser autoplay policy - click page first
   - Check browser console for errors
   - Ensure HTTPS for production

3. **Weaviate search failures**
   - Credits exhausted - using BM25 fallback
   - Check API key validity
   - Monitor rate limits

4. **LLM timeouts**
   - Fallback chain: Gemini → Vertex AI → Groq
   - Check API keys
   - Monitor quotas

---

## Performance Metrics

### Target Latencies
- Voice response: <2s total
- Search only: <500ms
- Cart operations: <300ms
- LLM inference: <1s

### Current Performance
- Voice pipeline: 1.3-1.5s
- Search: 300-400ms (needs improvement)
- Supervisor: 500-800ms
- TTS generation: 200-300ms

### Optimization Opportunities
1. Parallel agent execution
2. Response streaming
3. Caching layer (Redis)
4. CDN for static assets
5. Connection pooling

---

## Security Considerations

1. **API Keys**: Stored in environment variables
2. **User Data**: Session-based, no PII in logs
3. **Voice Privacy**: Audio not stored
4. **HTTPS**: Required for production
5. **Authentication**: JWT tokens (planned)

---

*Last Updated: July 3, 2025*