# LeafLoaf Knowledge Base - Single Source of Truth

Last Updated: 2025-06-28

## 1. CODEBASE OVERVIEW

### Architecture
- **Multi-Agent System**: Supervisor → Product Search → Order → Response Compiler
- **API Layer**: FastAPI endpoints (will thin out later)
- **LLM**: Vertex AI Gemma 2 (currently using Zephyr-7B for dev)
- **Search**: Weaviate hybrid search with dynamic alpha
- **State Management**: LangGraph for orchestration

### Key Files
```
src/
├── api/main.py                    # API endpoints (836 lines - to be thinned)
├── core/graph.py                  # LangGraph orchestration
├── agents/
│   ├── supervisor.py              # Routes queries with LLM
│   ├── product_search.py          # Weaviate search + filtering
│   └── order_agent.py             # Cart management with React pattern
├── personalization/
│   └── instant_personalizer.py   # Real-time personalization (<10ms)
└── utils/category_mapper.py      # Category filtering logic
```

### Current Status
- ✅ Multi-agent system working
- ✅ Real-time personalization (<300ms total)
- ✅ Category filtering (45→13 products for milk)
- ✅ Demo UI with instant feedback
- ✅ Graphiti/Spanner (connected and working)
- ✅ BigQuery (production ready, streaming working)
- ✅ 10/10 Personalization features complete
- ✅ 103/103 tests passing

## 2. PERSONALIZATION SYSTEM

### Instant Personalization (Working)
- **In-memory store**: <10ms updates
- **Signal weights**: Click(0.2), View(0.3), Cart(0.5), Purchase(1.0)
- **Thread-safe**: Handles concurrent users
- **No dependencies**: Works without Graphiti/BigQuery

### Three-Tier Architecture
```
Tier 1: Instant (In-Memory) ✅
  └─ <10ms updates, session-based

Tier 2: Graphiti/Spanner 🟡
  └─ Relationship memory, cross-session

Tier 3: BigQuery 🔴
  └─ Analytics, ML training
```

### Demo Flow
1. Search "milk" → generic results
2. Click organic items → instant "For You" badges
3. Preferences build → reranking happens
4. New searches → personalization carries over

## 3. INTEGRATION POINTS

### Weaviate
- **Status**: Working with BM25 fallback
- **Performance**: 200-400ms queries
- **Retrieval**: Fetch 50, filter, return 15
- **Credits**: Exhausted, using keyword search

### Graphiti/Spanner
- **Status**: ✅ Connected and working in production
- **Integration**: Agent-level implementation
- **Architecture**: GraphitiPersonalizationEngine
- **Features**: All 10 personalization features using Pure Graphiti

### BigQuery
- **Status**: ✅ Production ready, all schemas fixed
- **Purpose**: Analytics and ML training
- **Non-blocking**: Fire-and-forget pattern
- **Tables**: 10 tables across ML pipeline and analytics

## 4. ML LAYER (Planned)

### Current
- Rule-based personalization only
- No ML models in production
- LLM for intent/routing only

### Future ML Pipeline
```
BigQuery Historical Data
    ↓
Feature Engineering
    ↓
Model Training (Vertex AI)
    ↓
Model Serving
    ↓
Real-time Scoring
```

### Planned Models
1. **User Embeddings**: Collaborative filtering
2. **Product Similarity**: Better recommendations
3. **Reorder Prediction**: Anticipate needs
4. **Price Sensitivity**: Personalized pricing

## 5. PERFORMANCE & TESTING

### Current Metrics
- **Search Latency**: 200-400ms ✅
- **Total Response**: <350ms ✅
- **Personalization**: <10ms ✅
- **Category Filtering**: ~70% reduction ✅

### Test Coverage
- **TDD Implementation**: 49/49 tests passing
- **Personalization Features**: 6/10 complete
- **Integration Tests**: Basic coverage

### Monitoring
- Response time tracking
- Personalization hit rate
- Error rates per component
- User interaction tracking

## 6. NEXT STEPS

### Immediate (Demo Ready)
1. BigQuery connection optional
2. Graphiti runs in-memory
3. Focus on demo experience

### Short Term
1. Fix BigQuery schema
2. Connect Spanner (production)
3. Implement remaining personalization features
4. Add more signal types

### Long Term
1. Thin API to 100 lines
2. ML model training
3. Cross-device sync
4. Predictive features

## 7. DEMO COMMANDS

```bash
# Start server
cd /Users/adi/Desktop/LeafLoafLangGraph
PORT=8000 python3 run.py

# Open demo
open demo_realtime_personalization.html

# Test search
python3 test_category_filtering.py
```

## 8. KEY INSIGHTS

1. **Agent Autonomy**: Agents make all decisions
2. **API as Messenger**: Just protocol translation  
3. **Graceful Degradation**: Each tier fails independently
4. **Privacy First**: User controls all data
5. **Performance Obsessed**: <350ms is non-negotiable

---
This single file replaces 150+ scattered docs. Update this file only.