# LeafLoaf LangGraph - Conversation Context Summary

## 🎯 Project Overview
LeafLoaf is a production-grade grocery shopping system with multi-agent architecture competing with major firms. The system uses LangGraph for orchestration, Weaviate for vector search, and Vertex AI (Gemma 2 9B) for LLM capabilities.

## 📅 Current Status (2025-06-26)

### ✅ Major Achievements
1. **Contextual Cart Operations**: Fixed - agents now share memory properly via singleton MemoryManager
2. **Session Memory**: Working with in-memory storage and Redis fallback
3. **Product Catalog**: 259 Laxmi products imported with full pricing ($10.50-$171.00 range)
4. **API Design**: Complete endpoint contracts defined with latency targets
5. **Search Architecture**: Two distinct search modes designed (typeahead vs natural language)

### 🚧 In Progress
1. **Natural Language Search Implementation** (`/api/v1/analyze`)
   - Handles images (OCR), text, voice inputs
   - LLM extracts grocery items with confidence scores
   - Returns rich product matches with ML metadata

2. **Performance Optimization**
   - Current: 650-900ms (too high)
   - Target: <300ms total response
   - Bottlenecks: Supervisor (150ms) + Product Search (500ms)

## 🏗️ System Architecture

### Core Components
```
User Request → API Gateway → Route Decision
                                ↓
                    ┌───────────────────────┐
                    │   Direct Endpoints    │
                    │  (Skip Supervisor)    │
                    │ • /products/search    │
                    │ • /cart/*            │
                    │ • /pricing/calculate  │
                    └───────────────────────┘
                                ↓
                    ┌───────────────────────┐
                    │  Natural Language     │
                    │   (/api/v1/chat)     │
                    │ ↓                     │
                    │ Supervisor (150ms)    │
                    │ ↓                     │
                    │ Parallel Agents       │
                    │ ↓                     │
                    │ Response Compiler     │
                    └───────────────────────┘
```

### Key Services
- **Weaviate**: Vector database for product search (hybrid search with dynamic alpha)
- **Redis**: Session memory and caching (with in-memory fallback)
- **BigQuery**: Analytics and ML data pipeline
- **Vertex AI**: Gemma 2 9B for intent analysis and extraction

## 📡 API Design Summary

### 1. Product Search (Direct)
```python
POST /api/v1/products/search
Target: <150ms

Request:
{
  "query": "rice",
  "filters": {...},
  "page": 1,
  "searchConfig": {"alpha": 0.5}
}

Response:
{
  "status": "success",
  "data": {
    "products": [...],
    "facets": {...},
    "pagination": {...}
  }
}
```

### 2. Natural Language Analysis (New)
```python
POST /api/v1/analyze
Target: <500ms

Request (Multiple Formats):
1. Multipart image upload
2. Base64 image in JSON
3. Direct text input
4. Voice transcript

Response:
{
  "data": {
    "extracted_items": [
      {
        "extraction": {
          "raw_text": "2 bags rice",
          "normalized_text": "rice",
          "quantity_detected": {"amount": 2, "unit": "bags"},
          "extraction_confidence": 0.92
        },
        "product_matches": [
          {
            "product": {...},
            "attributes": {...},
            "ml_metadata": {
              "match_score": 0.95,
              "ranking_factors": {...}
            },
            "pricing": {...}
          }
        ]
      }
    ],
    "suggestions": {
      "quick_add_all": {...}
    }
  }
}
```

### 3. Cart Operations (Direct)
```python
POST /api/v1/cart/items
Target: <50ms

Direct CRUD operations without agents
```

## 🔍 Two Search Experiences

### 1. Typeahead Search
- **Use Case**: Search bar autocomplete
- **Latency**: <100ms (ideally <50ms)
- **Implementation**: Elasticsearch/Redis with edge n-gram tokenizer
- **No LLM**: Direct prefix/fuzzy matching
- **Response**: Minimal (10 suggestions with highlights)

### 2. Natural Language Search
- **Use Case**: Photos of lists, pasted notes, voice
- **Latency**: <500ms
- **Implementation**: OCR → LLM extraction → Product matching
- **Rich Response**: Confidence scores, ML metadata, suggestions
- **Handles**: Misspellings, quantities, context ("for 20 people")

## 💡 Key Implementation Insights

### Performance Findings
1. **Response Compiler overhead**: Only 0.25ms (not the bottleneck!)
2. **Main bottlenecks**: 
   - Supervisor: ~150ms (unnecessary for simple queries)
   - Product Search Agent: 490-504ms (Weaviate query)
3. **Solution**: Direct endpoints that bypass supervisor

### Optimization Strategy
1. **Skip Supervisor** for simple product searches
2. **Aggressive caching**: 5-min for searches, 1-hour for products
3. **Connection pooling** for Weaviate
4. **Template responses** instead of LLM generation
5. **Parallel agent execution** when multiple needed

## 📊 Data Pipeline

### Laxmi Products Processing
- **Source**: PDF catalog with complex format (e.g., "8X908 GM" = 8 packets × 908g)
- **Extracted**: 259 products with prices ($10.50-$171.00)
- **Enriched with**:
  - Ethnic indicators (Indian, Korean, Chinese)
  - Search terms (10-15 meaningful terms only)
  - Dietary attributes
  - Pack size conversions (wholesale → retail)

### BigQuery Tables Structure
```
leafloaf_analytics/
├── raw_events/
│   ├── user_search_events
│   ├── product_interaction_events
│   └── cart_modification_events
├── product_intelligence/
│   └── product_purchase_patterns
└── ml_features/
    └── user_session_context
```

## 🚀 Implementation Priorities

### Phase 1 (Immediate)
1. Deploy `/api/v1/analyze` endpoint for natural language
2. Implement direct search endpoint (bypass supervisor)
3. Add Redis caching layer
4. Fix order agent error (missing time import)

### Phase 2 (This Week)
1. OCR integration (Tesseract or Cloud Vision)
2. Optimize Weaviate queries
3. Implement typeahead search
4. Set up BigQuery streaming

### Phase 3 (Next Week)
1. ML recommendations (rule-based, no LLM)
2. Pricing agent (<50ms runtime calculations)
3. A/B testing framework

## 🛠️ Technical Details

### Environment Variables
```yaml
WEAVIATE_URL: "https://leafloaf-..."
WEAVIATE_API_KEY: "dqgYp..."
LANGCHAIN_API_KEY: "lsv2_pt_..."
VERTEX_AI_PROJECT: "leafloafai"
REDIS_URL: "redis://localhost:6379"
```

### Key Files Created
1. **NATURAL_LANGUAGE_SEARCH_RESPONSE.md** - Complete response structure with ML metadata
2. **NATURAL_LANGUAGE_IMPLEMENTATION.md** - Full implementation guide
3. **TYPEAHEAD_SEARCH_DESIGN.md** - Fast autocomplete design
4. **API_ENDPOINT_CONTRACTS.md** - All endpoints with request/response
5. **API_IMPLEMENTATION_GUIDE.md** - Latency optimization strategies
6. **test_natural_language_api.py** - Complete test suite

### Testing Commands
```bash
# Test natural language API
python test_natural_language_api.py

# Run local server
python run.py

# Test specific endpoint
curl -X POST http://localhost:8000/api/v1/analyze \
  -F "image=@shopping_list.jpg" \
  -F "user_id=user123"
```

## 🎯 Success Metrics
- **Search latency**: <150ms (direct), <500ms (natural language)
- **Cart operations**: <50ms
- **Extraction accuracy**: >90% for common items
- **Match relevance**: >85% top match is correct

## 📝 Next Session Focus
1. Implement the `/api/v1/analyze` endpoint with OCR
2. Deploy and test with real shopping list images
3. Set up performance monitoring
4. Create direct search endpoint
5. Implement caching strategy

## 🔑 Critical Context
- **Multi-agent system** works but needs optimization
- **Response Compiler** is NOT the bottleneck (only 0.25ms)
- **Direct endpoints** are key to performance
- **Two search modes** serve different use cases
- **Laxmi products** successfully imported with ethnic indicators
- **Natural language** needs OCR + LLM extraction + matching

This context summary contains everything needed to continue the implementation in a new session.