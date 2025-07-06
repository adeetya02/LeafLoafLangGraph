# LeafLoaf Codebase Quick Reference 🚀

## 🎯 Most Important Files (Top 20)

### 1. **Core System**
```python
src/core/graph.py                    # LangGraph orchestration - THE BRAIN
src/models/state.py                  # SearchState definition - data flow
src/config/constants.py              # All system limits and constants
```

### 2. **Agents (Multi-Agent System)**
```python
src/agents/supervisor_optimized.py   # Voice-native routing with Gemma 2 9B
src/agents/product_search.py         # Weaviate hybrid search agent
src/agents/order_agent.py            # Cart management with React pattern
src/agents/memory_aware_base.py      # Base class all agents inherit
src/agents/response_compiler.py      # Response formatting
```

### 3. **Voice System**
```python
src/api/voice_deepgram_endpoint.py   # Main WebSocket endpoint
src/voice/deepgram/nova3_client.py   # Deepgram streaming client
src/voice/processors/transcript_processor.py  # Voice analysis
```

### 4. **Memory & Personalization**
```python
src/memory/memory_manager.py         # Unified memory interface
src/memory/graphiti_wrapper.py       # Graphiti integration
src/memory/graphiti_memory_spanner.py # Spanner backend
src/personalization/graphiti_engine.py # 10 personalization features
```

### 5. **API & Entry Points**
```python
run.py                               # Main application runner
src/api/main.py                      # FastAPI setup
```

### 6. **Data Access**
```python
src/data/weaviate_optimized.py       # Optimized Weaviate client
src/analytics/bigquery_client.py     # Analytics streaming
```

## 📍 Quick Navigation by Task

### "I want to understand the voice flow"
1. Start: `src/api/voice_deepgram_endpoint.py`
2. STT: `src/voice/deepgram/nova3_client.py`
3. Routing: `src/agents/supervisor_optimized.py`
4. Processing: Follow agent selected by supervisor

### "I want to trace a product search"
1. Entry: `src/api/main.py` → `/api/v1/search`
2. Graph: `src/core/graph.py` → workflow execution
3. Supervisor: `src/agents/supervisor_optimized.py` → routing
4. Search: `src/agents/product_search.py` → Weaviate query
5. Memory: `src/memory/memory_manager.py` → personalization
6. Response: `src/agents/response_compiler.py` → formatting

### "I want to understand memory/personalization"
1. Base: `src/memory/memory_manager.py` → unified interface
2. Graphiti: `src/memory/graphiti_wrapper.py` → entity extraction
3. Storage: `src/memory/graphiti_memory_spanner.py` → Spanner
4. Features: `src/personalization/graphiti_engine.py` → 10 features

### "I want to add a new agent"
1. Inherit: `src/agents/memory_aware_base.py`
2. Implement: Your agent logic
3. Register: `src/core/graph.py` → add to workflow
4. Route: `src/agents/supervisor_optimized.py` → add routing

### "I want to modify voice behavior"
1. STT Config: `src/voice/deepgram/nova3_client.py`
2. Metadata: `src/voice/processors/transcript_processor.py`
3. Routing: `src/agents/supervisor_optimized.py` → voice influence
4. Response: `src/agents/response_compiler.py` → adaptation

## 🔧 Key Functions & Classes

### Core Classes
```python
# src/models/state.py
class SearchState(TypedDict):
    query: str
    voice_metadata: Optional[Dict]
    routing_decision: Optional[str]
    search_results: Optional[List]
    # ... all state that flows through system

# src/agents/memory_aware_base.py
class MemoryAwareAgent(BaseAgent):
    async def get_memory_context()  # Override in each agent
    async def record_decision()     # Learning
    async def learn_from_outcome()  # Improvement

# src/core/graph.py
workflow = StateGraph(SearchState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_conditional_edges("supervisor", route_based_on_intent)
```

### Key Patterns
```python
# Voice-driven alpha calculation (supervisor_optimized.py)
if voice_metadata.get("pace") == "fast" and urgency == "high":
    search_alpha = 0.3  # More keyword-focused
elif voice_metadata.get("pace") == "slow":
    search_alpha = 0.7  # More semantic

# Memory timeout pattern (memory_manager.py)
try:
    context = await asyncio.wait_for(
        self._get_context(user_id), 
        timeout=0.05  # 50ms
    )
except asyncio.TimeoutError:
    context = {}  # Proceed without memory

# Fire-and-forget analytics (throughout)
asyncio.create_task(
    self.bigquery_client.stream_event(event)
)  # Non-blocking
```

## 📊 Performance Critical Paths

### Latency Breakdown
```
Voice Input → Response: Target <2s
├── Deepgram STT: ~500ms
├── Supervisor: 500-800ms
├── Search: 300-400ms
├── Memory: 50-100ms (parallel)
└── Response: <100ms
```

### Optimization Points
1. **Connection Pooling**: `weaviate_optimized.py`
2. **Parallel Execution**: Memory + LLM in `supervisor_optimized.py`
3. **Aggressive Timeouts**: Throughout agents
4. **Fire-and-forget**: Analytics in all agents

## 🐛 Common Issues & Solutions

### "Weaviate search failing"
- Check: `src/data/weaviate_optimized.py` → connection pool
- Verify: Credits not exhausted (currently using BM25 fallback)

### "Voice not working"
- Check: Audio format in `nova3_client.py` (must be linear16)
- Verify: WebSocket connection in browser
- Debug: `src/api/voice_deepgram_endpoint.py`

### "Memory timeout"
- Adjust: Timeout in `memory_manager.py` (currently 50ms)
- Check: Spanner connection in `graphiti_memory_spanner.py`

### "Slow response"
- Check: LLM timeouts in `supervisor_optimized.py`
- Verify: Environment (GCP vs local) for timeout adjustment
- Profile: Add timing logs to identify bottleneck

## 🔑 Environment Variables

```yaml
# .env.yaml (most important)
DEEPGRAM_API_KEY: "xxx"          # Voice STT/TTS
WEAVIATE_URL: "xxx"              # Product search
WEAVIATE_API_KEY: "xxx"          # Auth
HUGGINGFACE_API_KEY: "xxx"       # LLM fallback
GOOGLE_CLOUD_PROJECT: "xxx"      # GCP services
GRAPHITI_NEO4J_URI: "xxx"        # Dev memory
REDIS_URL: "xxx"                 # Session cache (optional)
```

## 🚦 Status Checks

### System Health
```bash
curl http://localhost:8080/health
```

### Voice Test
```
http://localhost:8080/tests/deepgram/test_deepgram_streaming.html
```

### Run Tests
```bash
python run_tests.py --component agents --verbose
```

## 💡 Pro Tips

1. **Voice Metadata is King**: Everything adapts based on voice characteristics
2. **Memory is Optional**: System works without it (50ms timeout)
3. **Fallbacks Everywhere**: HuggingFace → Vertex AI → Groq
4. **Factory Pattern**: Always create new agent instances
5. **Trace IDs**: Follow `trace_id` through logs for debugging

This quick reference should help you navigate the codebase efficiently!