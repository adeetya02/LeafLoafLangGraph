# LeafLoaf Agent Interaction Documentation

## Overview
This document captures all agent interactions in the LeafLoaf system with detailed workflows, latency measurements, and optimization strategies.

## System Architecture

```
User → API → Supervisor → [Product Search | Order Agent | Response Compiler] → Response
                 ↓
           Graphiti Memory
```

## Agent Roles & Responsibilities

### 1. Supervisor Agent (`src/agents/supervisor.py`)
- **Role**: Intent classification and routing
- **Graphiti Integration**: Extracts entities, manages session context
- **Latency**: 10-50ms (local), 100-300ms (GCP)

### 2. Product Search Agent (`src/agents/product_search.py`)
- **Role**: Weaviate hybrid search
- **Dynamic Alpha**: LLM-driven (0.2 keyword → 0.8 semantic)
- **Latency**: 200-800ms (Weaviate dependent)

### 3. Order Agent (`src/agents/order_agent.py`)
- **Role**: Cart management with React pattern
- **Tools**: add_to_cart, remove_from_cart, update_quantity, view_cart
- **Graphiti**: Uses for reorder patterns ("usual order")
- **Latency**: 50-200ms per tool call

### 4. Response Compiler (`src/agents/response_compiler.py`)
- **Role**: Format final response
- **Future**: ML recommendation integration
- **Latency**: 20-50ms

## Detailed Workflows

### Workflow 1: Simple Search
```
User: "I need milk"
```

**Flow**:
1. API receives request → creates SearchState
2. Supervisor analyzes intent → routes to "product_search"
3. Product Search:
   - LLM determines alpha=0.4 (balanced search)
   - Queries Weaviate with hybrid search
   - Returns products
4. Response Compiler formats results

**Latency Breakdown** (GCP):
- Cold start: ~2800ms total
  - Supervisor: 300ms
  - Product Search: 2400ms (Weaviate)
  - Response Compiler: 100ms
- Warm: ~600ms total
  - Supervisor: 100ms
  - Product Search: 450ms
  - Response Compiler: 50ms

### Workflow 2: Add to Cart
```
User: "I want bananas"
User: "Add 2 bunches to cart"
```

**Flow**:
1. First message → product search (as above)
2. Second message:
   - Supervisor detects order intent → routes to "order"
   - Order Agent:
     - Uses add_to_cart tool
     - Updates session cart state
     - Returns confirmation
3. Response Compiler formats cart update

**Latency Breakdown**:
- Message 1: Same as simple search
- Message 2: ~150ms (warm)
  - Supervisor: 50ms
  - Order Agent: 80ms
  - Response Compiler: 20ms

### Workflow 3: Update Quantity
```
User: "Add apples to cart"
User: "Actually, make that 5 apples"
```

**Flow**:
1. Add to cart (standard flow)
2. Update:
   - Supervisor → order agent
   - Order Agent uses update_quantity tool
   - Modifies existing cart item

**Edge Cases**:
- Item not in cart → helpful error message
- Invalid quantity → validation error

### Workflow 4: Remove from Cart
```
User: "Remove the bread from my cart"
```

**Flow**:
- Supervisor → order agent
- Order Agent:
  - Searches cart for "bread"
  - Uses remove_from_cart tool
  - Confirms removal

### Workflow 5: View Cart
```
User: "What's in my cart?"
```

**Flow**:
- Supervisor → order agent
- Order Agent uses view_cart tool
- Response Compiler formats cart contents

### Workflow 6: Reorder (Graphiti)
```
User: "What did I order last time?"
User: "Add my usual milk"
```

**Flow**:
1. First message:
   - Supervisor extracts entity "last order"
   - Order Agent queries Graphiti memory
   - Returns previous order items
2. Second message:
   - Order Agent uses Graphiti context
   - Adds "usual" items from memory

**Latency Impact**: +200-300ms for Graphiti queries

### Workflow 7: Complex Multi-Step
```
User: "I'm making pasta tonight"
User: "I need pasta and sauce"
User: "Add garlic bread too"
User: "Show my cart"
```

**Flow**:
- Context maintained across messages
- Each add operation preserves cart state
- Final view shows accumulated items

## Performance Analysis

### Current Latency (GCP Production)

| Metric | Cold Start | Warm |
|--------|-----------|------|
| P50 | 120ms | 120ms |
| P95 | 2788ms | 500ms |
| P99 | 2800ms | 800ms |

### Bottlenecks Identified

1. **Weaviate Search**: 200-800ms
   - Solution: Implement caching layer
   - Use Redis for frequent queries

2. **Cold Starts**: 2000-3000ms
   - Solution: Keep-warm strategy
   - Reduce container size

3. **Graphiti Queries**: +200-300ms
   - Solution: Async pre-fetching
   - Cache user context at login

## Optimization Strategy

### Phase 1: Quick Wins (Target: <500ms P95)
1. **Redis Caching**:
   ```python
   # Cache frequent searches
   cache_key = f"search:{query_embedding}"
   if cached := redis.get(cache_key):
       return cached
   ```

2. **Parallel Agent Execution**:
   ```python
   # Run independent agents concurrently
   search_task = asyncio.create_task(search_agent())
   ml_task = asyncio.create_task(get_recommendations())
   results = await asyncio.gather(search_task, ml_task)
   ```

3. **Connection Pooling**:
   - Weaviate: Persistent connections
   - Spanner: Connection pool size 10

### Phase 2: Architecture (Target: <300ms P95)
1. **Edge Caching**: CloudFlare for static responses
2. **Regional Deployment**: Multi-region Cloud Run
3. **Async Everything**: Fire-and-forget logging

### Phase 3: Advanced (Target: <200ms P95)
1. **Predictive Pre-fetching**:
   - Pre-load likely next queries
   - ML-based prediction

2. **Graph Optimization**:
   - Skip unnecessary agents
   - Direct routing for simple queries

## Testing Strategy (TDD)

### Unit Tests (Per Agent)
```python
# test_supervisor.py
async def test_intent_classification():
    result = await supervisor.classify("I need milk")
    assert result.intent == "product_search"
    assert result.confidence > 0.8

async def test_entity_extraction():
    entities = await supervisor.extract_entities("Show me Oatly products")
    assert "Oatly" in entities.brands
```

### Integration Tests (Workflows)
```python
# test_workflows.py
async def test_add_to_cart_flow():
    # Step 1: Search
    state1 = await graph.ainvoke({"query": "I want apples"})
    assert len(state1.products) > 0
    
    # Step 2: Add to cart
    state2 = await graph.ainvoke({"query": "Add 3 to cart"})
    assert state2.cart.items[0].quantity == 3
```

### Performance Tests
```python
# test_performance.py
@pytest.mark.benchmark
async def test_search_latency():
    start = time.time()
    await graph.ainvoke({"query": "organic milk"})
    latency = (time.time() - start) * 1000
    assert latency < 500  # 500ms threshold
```

## Maintenance Strategy

### 1. Monitoring
- **Datadog/OpenTelemetry**: Full tracing
- **Alerts**: P95 > 1s, Error rate > 1%
- **Dashboards**: Real-time latency by agent

### 2. Regular Tasks
- **Weekly**: Review slow queries, optimize
- **Monthly**: Update test data, review coverage
- **Quarterly**: Architecture review

### 3. Code Quality
- **Pre-commit**: Ruff, type checking
- **CI/CD**: All tests must pass
- **Code Review**: Required for agent changes

### 4. Documentation
- **Agent Changes**: Update this doc
- **New Workflows**: Add examples
- **Performance**: Track improvements

## Common Issues & Solutions

### Issue 1: "No products found"
- **Cause**: Weaviate credits exhausted
- **Solution**: BM25 fallback active
- **Fix**: Upgrade Weaviate plan

### Issue 2: High latency spikes
- **Cause**: Cold starts
- **Solution**: Implement keep-warm
- **Monitoring**: Track cold start frequency

### Issue 3: Cart state lost
- **Cause**: Session timeout
- **Solution**: Redis persistence
- **Backup**: In-memory fallback

## Future Enhancements

1. **ML Recommendations**:
   - Integrate at Response Compiler
   - 5 products always returned
   - Track conversion metrics

2. **Voice Optimization**:
   - Streaming responses
   - Interrupt handling
   - Natural pauses

3. **Personalization**:
   - User preference learning
   - Dynamic reranking
   - Behavioral patterns