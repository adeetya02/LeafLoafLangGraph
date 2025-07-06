# Voice Testing Guide - Dynamic Intents & Weaviate-Only Products

## Quick Start

### 1. Environment Setup
```bash
# Deepgram API key is already in .env.yaml
DEEPGRAM_API_KEY=36a821d351939023aabad9beeaa68b391caa124a
```

### 2. Run Voice Server
```bash
# Start the FastAPI server
python3 run.py

# In another terminal, start the voice WebSocket server
python3 -m src.api.voice_deepgram_dynamic_intents
```

### 3. Access Test Interface
Open in browser: http://localhost:8080/api/v1/voice/deepgram-intents/test

## Key Features to Test

### 1. Dynamic Intent Classification
- **No hardcoded intents** - System learns from usage
- **Test queries**:
  - "I need milk" → Creates/uses product search intent
  - "Add paneer to cart" → Creates/uses cart operation intent
  - "Hello there" → Creates/uses greeting intent
  - "What's on sale?" → Creates new intent dynamically

### 2. Weaviate-Only Products
- **All products from local database** - No internet searches
- **Test by**:
  - Searching for common items: "organic milk"
  - Searching for ethnic items: "paneer", "ghee", "kimchi"
  - Checking product IDs start with "wv_" or have SKU format

### 3. Ethnic Product Recognition
- **Boosted keywords** for better recognition
- **Test phrases**:
  ```
  "I need ghee for cooking"
  "Get me some paneer and dal"
  "I want kimchi and gochujang"
  "Show me tahini and harissa"
  "Looking for injera bread"
  ```

### 4. Voice Metadata Influence
- **Pace affects search**:
  - Fast pace → Lower alpha (0.3) for exact matches
  - Slow pace → Higher alpha (0.7) for exploration
  - Normal pace → Balanced alpha (0.5)

## Testing Checklist

### ✅ Basic Voice Flow
- [ ] Microphone permission granted
- [ ] Voice is transcribed correctly
- [ ] Intent is classified dynamically
- [ ] Products are returned from search

### ✅ Dynamic Intent Learning
- [ ] New intents are created for novel queries
- [ ] Intent statistics show learning progress
- [ ] Deepgram custom intents update after multiple queries
- [ ] Similar queries use consistent intents

### ✅ Weaviate-Only Verification
- [ ] No external API calls in network tab
- [ ] All product IDs have consistent format
- [ ] Search works without internet (after initial load)
- [ ] Ethnic products found in local database

### ✅ Ethnic Product Testing
- [ ] Ethnic terms transcribed accurately
- [ ] Relevant products returned for ethnic queries
- [ ] No spelling corrections needed
- [ ] Cultural context preserved

## Monitoring Intent Learning

### View Statistics
Click "📊 Get Stats" button in test interface to see:
- Total observations
- Learned intent types
- Custom patterns for Deepgram
- Top intent patterns

### Example Learning Progression
```
Query 1: "I need milk" → Creates "product_search" intent
Query 2: "I need eggs" → Uses "product_search" intent
Query 3: "I need bread" → Uses "product_search" intent
Pattern learned: "I need" → "product_search"
```

## Troubleshooting

### Issue: Poor ethnic product recognition
**Solution**: Check if Deepgram is using Nova-3 model with custom keywords

### Issue: Products not found
**Solution**: Verify test mode is enabled (uses mock products)

### Issue: Intent not learning
**Solution**: Need at least 3 occurrences of a pattern for learning

### Issue: No voice input
**Solution**: Check microphone permissions and HTTPS connection

## Advanced Testing

### Test Intent Evolution
1. Start with simple queries
2. Gradually introduce complex queries
3. Watch how intents evolve and consolidate
4. Check suggestions for intent merging

### Test Voice Influence
1. Speak fast: "I need milk eggs bread cheese"
2. Speak slow: "Hmm... I'm looking for... organic... vegetables"
3. Check different alpha values in response

### Test Learning Persistence
1. Make several queries of same type
2. Refresh page
3. Check if patterns are remembered (in-memory only currently)

## Production Deployment

### Required Environment Variables
```yaml
DEEPGRAM_API_KEY: "36a821d351939023aabad9beeaa68b391caa124a"
WEAVIATE_URL: "your-weaviate-instance"
WEAVIATE_API_KEY: "your-weaviate-key"
```

### Health Checks
- Deepgram connection: `/api/v1/voice/deepgram-intents/health`
- Intent statistics: `/api/v1/voice/deepgram-intents/stats`
- Weaviate status: `/api/v1/health/weaviate`

## Next Steps

1. **Test with real audio**: Connect microphone and test voice queries
2. **Monitor learning**: Track how intents evolve with usage
3. **Tune parameters**: Adjust learning thresholds and refresh intervals
4. **Add persistence**: Save learned intents to database
5. **Multi-user support**: Separate intent learning per user/group
EOF < /dev/null