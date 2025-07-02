# API Migration Plan - Current State to Target State

## 📊 Current API Analysis

### What We Have Now:
1. **Single Search Endpoint** (`/api/v1/search`) handling everything
2. **Order Endpoint** (`/api/v1/order`) with errors (missing time import)
3. **Mixed Response Format** - not standardized
4. **All requests go through Supervisor** - even simple cart operations
5. **Response Compiler runs for all searches** - adds unnecessary latency

### Current Response Structure:
```json
{
  "success": true/false,
  "query": "original query",
  "products": [...],
  "metadata": {...},
  "execution": {...},
  "conversation": {...},
  "message": "...",
  "error": null,
  "order": null
}
```

### Performance Observations:
- Search latency: 650-900ms (TOO HIGH)
- Supervisor: ~150ms
- Product Search: 500-650ms  
- Response Compiler: ~0.25ms (minimal, but unnecessary for simple searches)

## 🎯 Migration Steps

### Phase 1: Fix Immediate Issues (Do Now)
1. **Fix Order Agent Error** - Missing time import
2. **Optimize Search** - Skip Response Compiler for simple product searches
3. **Add Cart Endpoints** - Separate from chat/order flow

### Phase 2: Standardize Responses
Transform current format to:
```json
{
  "status": "success",
  "data": {
    "products": [...],
    "cart": {...},  // if applicable
    "message": "..."  // if natural language
  },
  "meta": {
    "query": {...},
    "performance": {...},
    "session": {...}
  }
}
```

### Phase 3: Separate Endpoints
1. **GET /api/v1/products** - Direct product listing
2. **POST /api/v1/products/search** - Product search only
3. **POST /api/v1/cart/add** - Direct cart addition
4. **POST /api/v1/cart/remove** - Direct cart removal
5. **GET /api/v1/cart** - Get current cart
6. **POST /api/v1/chat** - Natural language processing

### Phase 4: Optimize Flow

#### Simple Product Search:
```
User → Search Endpoint → Weaviate → Response
(Skip Supervisor, Skip Response Compiler)
Target: <200ms
```

#### Cart Operations:
```
User → Cart Endpoint → Redis/Memory → Response  
(No agents needed)
Target: <50ms
```

#### Natural Language:
```
User → Chat Endpoint → Supervisor → Agents → Response Compiler → Response
(Full flow for complex queries)
Target: <500ms
```

## 🚀 Quick Wins (Implement First)

### 1. Create Direct Search Function
```python
@app.post("/api/v1/products/search")
async def direct_search(request: DirectSearchRequest):
    # Skip supervisor for direct product searches
    results = await weaviate_client.search(
        query=request.query,
        limit=request.limit,
        filters=request.filters
    )
    
    return StandardResponse(
        status="success",
        data={"products": results},
        meta={
            "performance": {"totalMs": elapsed},
            "query": {"original": request.query}
        }
    )
```

### 2. Create Cart Service
```python
@app.post("/api/v1/cart/add")
async def add_to_cart(request: AddToCartRequest):
    cart = await cart_service.add_item(
        session_id=request.session_id,
        product_id=request.product_id,
        quantity=request.quantity
    )
    
    return StandardResponse(
        status="success",
        data={"cart": cart},
        meta={"performance": {"totalMs": elapsed}}
    )
```

### 3. Fix Response Compiler Usage
```python
# In supervisor agent
if intent == "product_search" and not has_complex_filters:
    # Direct search - no response compiler needed
    return {"products": search_results, "skip_compiler": True}
else:
    # Complex query - use response compiler
    return {"products": search_results, "needs_compilation": True}
```

## 📈 Expected Improvements

### Current vs Target Latencies:
- Simple search: 800ms → 200ms (-75%)
- Cart add: 500ms → 50ms (-90%)  
- Complex query: 900ms → 500ms (-44%)

### Benefits:
1. **Better UX** - Faster responses
2. **Clearer API** - Each endpoint has one job
3. **Easier Testing** - Predictable behavior
4. **Better Caching** - Can cache at endpoint level
5. **Scalability** - Can scale services independently

## 🔧 Implementation Order

1. **Today**: Fix order agent error, create cart endpoints
2. **Tomorrow**: Create direct search endpoint
3. **Next Week**: Standardize all responses
4. **Next Sprint**: Full OpenAPI spec with Swagger UI

## 📝 Notes for Development

1. **Keep backward compatibility** during migration
2. **Version the API** properly (v1 → v2)
3. **Monitor performance** at each step
4. **Test with production load** before switching
5. **Document all changes** in OpenAPI spec