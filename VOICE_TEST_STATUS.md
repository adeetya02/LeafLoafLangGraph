# Voice Streaming Test Status

## Current Situation
- **Problem**: Deepgram fails on ethnic products (paneer → "panel", gochujang → "go to john")
- **Solution**: Rev.ai with custom vocabulary and boost scores
- **Status**: Test files created but unable to run due to connection issues

## Files Created for Testing

### 1. `test_revai_ethnic.py`
- Direct microphone test with Rev.ai
- Shows real-time transcription with ethnic product detection
- Requires: `REVAI_ACCESS_TOKEN` in .env file

### 2. `test_revai_websocket.py`
- WebSocket server for browser-based testing
- Includes HTML interface at http://localhost:8000/test
- Bidirectional audio streaming Rev.ai ↔ Browser

### 3. `test_revai_simple.html`
- Visual comparison of Deepgram failures vs Rev.ai expected results
- Shows all ethnic products with boost scores
- No server required - just open in browser

## Rev.ai Configuration

```python
CUSTOM_VOCABULARY = [
    # South Asian
    {"phrases": ["paneer"], "boost": 15},
    {"phrases": ["ghee"], "boost": 15},
    {"phrases": ["dal", "daal"], "boost": 12},
    {"phrases": ["masala"], "boost": 10},
    
    # East Asian  
    {"phrases": ["gochujang"], "boost": 15},
    {"phrases": ["kimchi"], "boost": 12},
    {"phrases": ["miso"], "boost": 12},
    
    # Middle Eastern
    {"phrases": ["harissa"], "boost": 15},
    {"phrases": ["za'atar", "zaatar"], "boost": 15},
    {"phrases": ["tahini"], "boost": 12},
    
    # Latin American
    {"phrases": ["plantains"], "boost": 10},
    {"phrases": ["yuca", "yucca"], "boost": 15},
    {"phrases": ["mole"], "boost": 15},
]
```

## Next Steps

1. **Get Rev.ai Token**
   - Sign up at https://www.rev.ai/
   - Free tier includes 5 hours of streaming
   - Add to .env: `REVAI_ACCESS_TOKEN=your_token`

2. **Test Ethnic Product Recognition**
   ```bash
   # Option 1: Direct microphone test
   python3 test_revai_ethnic.py
   
   # Option 2: WebSocket browser test
   python3 test_revai_websocket.py
   # Then open http://localhost:8000/test
   ```

3. **If Rev.ai Works Better**
   - Replace Deepgram with Rev.ai in voice pipeline
   - Keep existing LangGraph multi-agent system
   - Keep ElevenLabs for TTS

## Architecture After Integration

```
Voice Input → Rev.ai STT (with ethnic vocabulary)
    ↓
Voice-Native Supervisor (Gemma 2 9B)
    ↓
Intent Classification & Routing
    ↓
Product Search (Weaviate)
    ↓
Response Compilation
    ↓
ElevenLabs TTS → Voice Output
```

## Why Rev.ai Should Work Better

1. **Human-in-the-loop training** - Trained on diverse accents
2. **Custom vocabulary** - Boost ethnic products by up to 18 points
3. **Lower bias** - Proven better accuracy on non-English words
4. **True streaming** - No timeout issues like Google STT

## Files to Commit

```bash
git add test_revai_ethnic.py
git add test_revai_websocket.py
git add test_revai_simple.html
git add VOICE_TEST_STATUS.md
git add VOICE_STREAMING_RECOMMENDATION.md
```