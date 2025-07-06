# LeafLoaf Component Interactions Guide

## Component Dependencies and Interactions

### 1. API Layer → Core System

#### Main API (`src/api/main.py`)
**Depends on:**
- `src/core/graph.py` - LangGraph orchestration
- `src/models/state.py` - State definitions
- `src/memory/memory_registry.py` - Memory management
- `src/cache/redis_feature.py` - Caching layer

**Interactions:**
```python
# Request flow
POST /api/v1/search → search_graph.ainvoke(state) → Agent Pipeline → Response
POST /api/v1/cart/* → Order Agent Tools → State Update → Response
```

#### Voice Endpoints (`src/api/voice_*.py`)
**Depends on:**
- `src/voice/deepgram/*` - STT/TTS processing
- `src/integrations/voice_analyzer.py` - Voice metadata extraction
- `src/agents/supervisor_voice_native.py` - Voice-aware routing

**Interactions:**
```python
# Voice flow
WebSocket → Deepgram STT → Voice Metadata → Supervisor → Agent Pipeline → TTS → WebSocket
```

### 2. Core Graph → Agent System

#### LangGraph (`src/core/graph.py`)
**Manages:**
- Agent instantiation (factory pattern)
- State transitions
- Node execution order
- Error handling and retries

**Agent Nodes:**
```python
supervisor_node → Routes based on intent
product_search_node → Executes search
order_node → Manages cart operations
response_compiler_node → Merges results
```

### 3. Agent → Memory System

#### Memory-Aware Agents
**Base Class:** `src/agents/memory_aware_base.py`

**Inheritance Chain:**
```
MemoryAwareAgent
    ├── OptimizedSupervisorAgent
    ├── ProductSearchReactAgent
    ├── OrderReactAgent
    └── ResponseCompilerAgent
```

**Memory Access Pattern:**
```python
async def get_memory_context(self, user_id, session_id, query):
    # 1. Get user preferences from Graphiti
    # 2. Get session context from Redis
    # 3. Get recent interactions
    # 4. Merge into agent-specific context
```

### 4. Memory System Architecture

#### Registry Pattern (`src/memory/memory_registry.py`)
**Manages:**
- Multiple memory backend instances
- Configuration per instance
- Lifecycle management

**Backends:**
```python
MemoryRegistry.register("graphiti", GraphitiMemoryWrapper())
MemoryRegistry.register("session", SessionMemory())
MemoryRegistry.register("redis", RedisMemory())
```

#### Graphiti Integration
**Flow:**
```
User Action → Entity Extraction → Graph Update → Spanner Storage
                    ↓
            Pattern Recognition → Personalization
```

### 5. Search System Integration

#### Weaviate Search (`src/integrations/weaviate_client_optimized.py`)
**Features:**
- Hybrid search (keyword + semantic)
- Voice-driven alpha adjustment
- Category filtering
- Result ranking

**Search Flow:**
```python
Voice Metadata → Alpha Calculation → Hybrid Search → Re-ranking → Results
    ↓                                      ↓              ↓
pace="fast"                           α=0.3         Personalization
→ keyword focus                    (BM25 weighted)   via Graphiti
```

### 6. Personalization Engine

#### Graphiti Personalization (`src/personalization/graphiti_personalization_engine.py`)
**Relationships:**
- BOUGHT_WITH - Complementary products
- PREFERS - Brand/type preferences  
- AVOIDS - Dietary restrictions
- REGULARLY_BUYS - Reorder patterns
- PRICE_SENSITIVE - Budget awareness

**Integration Points:**
```python
Search Results → Personalization Engine → Re-ranked Results
                        ↓
                Extract Patterns → Update Graph
```

### 7. Voice Processing Pipeline

#### Deepgram Integration
**Components:**
- `conversational_client.py` - Full duplex communication
- `streaming_client.py` - Real-time processing
- `dynamic_intent_learner.py` - Intent evolution

**Voice Metadata Processing:**
```python
{
    "pace": "fast/normal/slow",
    "emotion": "urgent/calm/exploring",
    "volume": 0.0-1.0,
    "clarity": 0.0-1.0
}
→ Influences search alpha, response style, routing decisions
```

### 8. Analytics Pipeline

#### BigQuery Streaming (`src/analytics/bigquery_client.py`)
**Events Captured:**
- Search queries and results
- Cart modifications
- Order completions
- Voice interactions
- Personalization effects

**Non-blocking Pattern:**
```python
async def log_event(event):
    # Fire and forget
    asyncio.create_task(bigquery.insert_rows_json(rows))
```

### 9. Caching Strategy

#### Redis Cache (`src/cache/redis_manager.py`)
**Cached Data:**
- Session state (5 min TTL)
- Search results (2 min TTL)
- User preferences (10 min TTL)
- LLM responses (5 min TTL)

**Cache Key Patterns:**
```
session:{session_id}:state
search:{query_hash}:results
user:{user_id}:preferences
llm:{prompt_hash}:response
```

### 10. Tool Execution

#### Order Tools (`src/tools/order_tools.py`)
**Available Tools:**
- add_to_cart
- remove_from_cart
- update_cart_quantity
- clear_cart
- confirm_order

**Execution Pattern:**
```python
Agent → Tool Selection → Validation → Execution → State Update
  ↓          ↓              ↓           ↓             ↓
React    Based on      Input params  Database    Return to
Pattern   Intent       Validation    Updates     Agent
```

## Critical Integration Patterns

### 1. State Management
```python
# State flows through entire system
Initial State → Agent Updates → Accumulated State → Final Response
     ↓              ↓                ↓                    ↓
  Request ID    Tool calls      Memory updates     Compiled result
```

### 2. Error Handling Chain
```python
Primary Service → Timeout/Error → Fallback Service → Cache → Default
      ↓                ↓                ↓              ↓        ↓
   Gemini 2B      After 2.5s      HuggingFace    Redis hit  Static
```

### 3. Memory Consistency
```python
Write Path: Action → Graphiti → Spanner → Cache Invalidation
Read Path: Cache → If miss → Spanner → Update Cache
```

### 4. Voice Context Flow
```python
Audio → STT → Text + Metadata → Enhanced Query → Agent Routing
  ↓      ↓           ↓                ↓              ↓
Raw   Deepgram  Voice features  Context-aware   Optimized
Audio   Nova 2   (pace, tone)     Search         Response
```

## Performance Considerations

### 1. Connection Pooling
- Weaviate: 10 connections
- Redis: 20 connections  
- Spanner: 5 connections
- HTTP clients: Per-service pools

### 2. Async Patterns
- All database operations are async
- Fire-and-forget for analytics
- Parallel agent execution where possible
- Non-blocking cache operations

### 3. Resource Management
- Per-request agent instances
- Automatic cleanup via context managers
- Memory limits enforced
- Timeout management (2.5s for LLMs)

## Debugging & Monitoring

### 1. Trace Points
- Request ID flows through all components
- LangSmith integration for agent tracing
- Structured logging with context
- Performance timing at each stage

### 2. Health Checks
- `/health` - Basic liveness
- `/ready` - Dependency checks
- Component-specific health endpoints
- Graceful degradation on failures

### 3. Metrics Collection
- Latency per component
- Success/failure rates
- Cache hit rates
- Memory usage patterns

This comprehensive guide shows how all components in the LeafLoaf system interact to create a cohesive, high-performance grocery shopping assistant with voice-native capabilities and advanced personalization.