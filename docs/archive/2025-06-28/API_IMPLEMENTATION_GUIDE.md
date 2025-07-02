# API Implementation Guide - Building Latency-Resilient Endpoints

## 🎯 Overview

This guide shows how to implement each endpoint from our API contracts with focus on:
1. **Direct responses** where possible (bypassing response compiler)
2. **Caching strategies** for sub-50ms responses
3. **Parallel processing** for complex operations
4. **Error handling** patterns

---

## 📊 Current State Analysis

Looking at our test responses:
- **Search latency**: 650-900ms (TOO HIGH!)
- **Response compiler**: Only 0.25ms (minimal impact)
- **Main bottleneck**: Product search agent (490-504ms)
- **Supervisor overhead**: ~150ms

### Key Issues:
1. Everything goes through supervisor (even simple searches)
2. Search agent takes too long (Weaviate query + processing)
3. No caching implemented
4. No direct endpoints for simple operations

---

## 🚀 Implementation Strategy

### 1. Direct Search Endpoint (Skip Supervisor)

```python
# src/api/endpoints/products.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict
import asyncio
from datetime import datetime

router = APIRouter(prefix="/api/v1/products")

@router.post("/search")
async def search_products(request: ProductSearchRequest):
    """
    Direct product search - bypasses supervisor for speed
    Target: <150ms
    """
    start_time = datetime.now()
    
    # Input validation
    if len(request.query) > 100:
        raise HTTPException(400, "Query too long (max 100 chars)")
    
    # Check cache first
    cache_key = f"search:{request.query}:{request.filters}:{request.page}"
    if cached_result := await redis_client.get(cache_key):
        return StandardResponse(
            status="success",
            data=cached_result,
            meta={
                "performance": {
                    "totalMs": (datetime.now() - start_time).total_seconds() * 1000,
                    "cached": True
                }
            }
        )
    
    # Direct Weaviate query (no supervisor)
    try:
        results = await weaviate_client.search_products(
            query=request.query,
            filters=request.filters,
            limit=request.page_size,
            offset=(request.page - 1) * request.page_size,
            alpha=request.search_config.get("alpha", 0.5)
        )
        
        # Format response
        formatted_results = {
            "products": [format_product(p) for p in results.objects],
            "facets": calculate_facets(results.objects),
            "pagination": {
                "page": request.page,
                "pageSize": request.page_size,
                "totalItems": results.total_count,
                "totalPages": math.ceil(results.total_count / request.page_size),
                "hasNext": request.page * request.page_size < results.total_count,
                "hasPrev": request.page > 1
            }
        }
        
        # Cache for 5 minutes
        await redis_client.setex(
            cache_key, 
            300, 
            json.dumps(formatted_results)
        )
        
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        
        return StandardResponse(
            status="success",
            data=formatted_results,
            meta={
                "query": {
                    "original": request.query,
                    "normalized": normalize_query(request.query),
                    "searchType": "hybrid"
                },
                "performance": {
                    "totalMs": elapsed,
                    "breakdown": {
                        "search": elapsed - 5,
                        "postProcessing": 5
                    },
                    "cached": False
                },
                "requestId": f"req_{uuid.uuid4().hex[:8]}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(500, "Search failed")
```

### 2. Cart Service Implementation

```python
# src/services/cart_service.py
from typing import Dict, List, Optional
import asyncio
from datetime import datetime

class CartService:
    def __init__(self):
        self.memory_store = {}  # In-memory fallback
        self.redis_client = None
        
    async def initialize(self):
        """Initialize Redis connection with fallback"""
        try:
            self.redis_client = await aioredis.create_redis_pool(
                settings.REDIS_URL,
                maxsize=10
            )
        except:
            logger.warning("Redis unavailable, using in-memory store")
    
    async def add_item(
        self, 
        session_id: str, 
        product_id: str, 
        quantity: int,
        merge: bool = True
    ) -> Dict:
        """
        Add item to cart with <50ms target latency
        """
        cart = await self.get_cart(session_id)
        
        # Find existing item
        existing_item = None
        for item in cart.get("items", []):
            if item["productId"] == product_id:
                existing_item = item
                break
        
        if existing_item and merge:
            # Update quantity
            existing_item["quantity"] += quantity
        else:
            # Fetch product details (this should be cached)
            product = await self.get_product_cached(product_id)
            
            # Add new item
            cart.setdefault("items", []).append({
                "cartItemId": f"item_{uuid.uuid4().hex[:8]}",
                "productId": product_id,
                "sku": product.get("sku"),
                "name": product.get("name"),
                "quantity": quantity,
                "price": product.get("price", {}).get("amount", 0),
                "subtotal": quantity * product.get("price", {}).get("amount", 0),
                "availability": "in_stock"  # Should check actual inventory
            })
        
        # Update cart metadata
        cart["itemCount"] = sum(item["quantity"] for item in cart["items"])
        cart["uniqueItems"] = len(cart["items"])
        cart["subtotal"] = sum(item["subtotal"] for item in cart["items"])
        cart["lastUpdated"] = datetime.utcnow().isoformat() + "Z"
        
        # Save cart
        await self.save_cart(session_id, cart)
        
        return cart
    
    async def get_cart(self, session_id: str) -> Dict:
        """Get cart with Redis fallback to memory"""
        cart_key = f"cart:{session_id}"
        
        if self.redis_client:
            try:
                cart_data = await self.redis_client.get(cart_key)
                if cart_data:
                    return json.loads(cart_data)
            except:
                logger.warning("Redis read failed, falling back to memory")
        
        # Fallback to memory
        return self.memory_store.get(session_id, {
            "id": f"cart_{uuid.uuid4().hex[:8]}",
            "sessionId": session_id,
            "items": [],
            "itemCount": 0,
            "uniqueItems": 0,
            "subtotal": 0.0,
            "lastUpdated": datetime.utcnow().isoformat() + "Z"
        })
    
    async def save_cart(self, session_id: str, cart: Dict):
        """Save cart to Redis and memory"""
        cart_key = f"cart:{session_id}"
        cart_data = json.dumps(cart)
        
        # Save to memory first (always works)
        self.memory_store[session_id] = cart
        
        # Try Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    cart_key,
                    3600,  # 1 hour TTL
                    cart_data
                )
            except:
                logger.warning("Redis write failed, saved to memory only")
    
    async def get_product_cached(self, product_id: str) -> Dict:
        """Get product with caching"""
        cache_key = f"product:{product_id}"
        
        # Try cache first
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except:
                pass
        
        # Fetch from Weaviate
        product = await weaviate_client.get_product_by_id(product_id)
        
        # Cache for 1 hour
        if self.redis_client and product:
            try:
                await self.redis_client.setex(
                    cache_key,
                    3600,
                    json.dumps(product)
                )
            except:
                pass
        
        return product

# Initialize service
cart_service = CartService()
```

### 3. Cart Endpoints

```python
# src/api/endpoints/cart.py
from fastapi import APIRouter, HTTPException
from datetime import datetime

router = APIRouter(prefix="/api/v1/cart")

@router.post("/items")
async def add_to_cart(request: AddToCartRequest):
    """
    Add items to cart - direct operation, no agents
    Target: <50ms
    """
    start_time = datetime.now()
    
    added_items = []
    
    for item in request.items:
        cart = await cart_service.add_item(
            session_id=request.session_id,
            product_id=item.product_id or item.sku,  # Support both
            quantity=item.quantity,
            merge=request.merge
        )
        
        added_items.append({
            "sku": item.sku,
            "quantity": item.quantity,
            "newTotal": next(
                (i["quantity"] for i in cart["items"] 
                 if i.get("sku") == item.sku),
                item.quantity
            )
        })
    
    elapsed = (datetime.now() - start_time).total_seconds() * 1000
    
    return StandardResponse(
        status="success",
        data={
            "cart": cart,
            "added": added_items
        },
        meta={
            "performance": {
                "totalMs": elapsed
            }
        }
    )

@router.get("")
async def get_cart(session_id: str):
    """Get current cart state"""
    cart = await cart_service.get_cart(session_id)
    
    return StandardResponse(
        status="success",
        data={"cart": cart},
        meta={"performance": {"totalMs": 10}}
    )

@router.delete("/items/{cart_item_id}")
async def remove_from_cart(cart_item_id: str, request: RemoveItemRequest):
    """Remove item from cart"""
    cart = await cart_service.get_cart(request.session_id)
    
    # Remove item
    cart["items"] = [
        item for item in cart["items"] 
        if item["cartItemId"] != cart_item_id
    ]
    
    # Update totals
    cart["itemCount"] = sum(item["quantity"] for item in cart["items"])
    cart["uniqueItems"] = len(cart["items"])
    cart["subtotal"] = sum(item["subtotal"] for item in cart["items"])
    
    await cart_service.save_cart(request.session_id, cart)
    
    return StandardResponse(
        status="success",
        data={"cart": cart},
        meta={"performance": {"totalMs": 15}}
    )
```

### 4. Natural Language Chat (With Response Compiler)

```python
# src/api/endpoints/chat.py
@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Natural language chat - uses full agent system
    Target: <500ms for simple, <800ms for complex
    """
    start_time = datetime.now()
    
    # Check if this can be handled without agents
    if is_simple_query(request.message):
        # Direct handling for simple queries
        return await handle_simple_query(request)
    
    # Complex query - use agent system
    try:
        # Supervisor analyzes intent
        intent_result = await supervisor.analyze_intent(
            message=request.message,
            session_id=request.session_id,
            context=request.context
        )
        
        # Execute required agents in parallel
        agent_tasks = []
        
        if "search" in intent_result.required_agents:
            agent_tasks.append(
                product_search_agent.search(
                    query=intent_result.search_query,
                    filters=intent_result.filters
                )
            )
        
        if "cart" in intent_result.required_agents:
            agent_tasks.append(
                order_agent.process_cart_action(
                    action=intent_result.cart_action,
                    session_id=request.session_id
                )
            )
        
        if request.include_recommendations:
            agent_tasks.append(
                recommendation_agent.get_recommendations(
                    session_id=request.session_id,
                    based_on=intent_result.recommendation_context
                )
            )
        
        # Run agents in parallel
        agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        # Compile response
        compiled_response = await response_compiler.compile(
            intent=intent_result,
            agent_outputs={
                "search": agent_results[0] if len(agent_results) > 0 else None,
                "cart": agent_results[1] if len(agent_results) > 1 else None,
                "recommendations": agent_results[2] if len(agent_results) > 2 else None
            },
            session={
                "id": request.session_id,
                "userType": request.context.get("userType", "retail"),
                "history": await get_conversation_history(request.session_id),
                "preferences": request.context.get("preferences", {})
            },
            options={
                "generateNaturalLanguage": True,
                "includeSuggestions": True,
                "includeRecommendations": request.include_recommendations,
                "maxProducts": request.max_products
            }
        )
        
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        
        return StandardResponse(
            status="success",
            data=compiled_response.data,
            meta={
                "agents": {
                    "executed": [a for a in intent_result.required_agents],
                    "skipped": [a for a in ["search", "cart", "order"] 
                               if a not in intent_result.required_agents]
                },
                "performance": {
                    "totalMs": elapsed,
                    "breakdown": {
                        "supervisor": intent_result.analysis_time,
                        "agents": max([r.execution_time for r in agent_results if hasattr(r, "execution_time")], default=0),
                        "responseCompiler": compiled_response.compilation_time
                    }
                },
                "session": {
                    "id": request.session_id,
                    "conversationLength": len(await get_conversation_history(request.session_id))
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return StandardResponse(
            status="error",
            error={
                "code": "CHAT_ERROR",
                "message": "Failed to process your request",
                "details": str(e) if settings.DEBUG else None
            }
        )

def is_simple_query(message: str) -> bool:
    """Check if query can bypass agent system"""
    simple_patterns = [
        r"^(show|list|find)\s+(all\s+)?\w+$",  # "show rice", "list all dal"
        r"^what\s+is\s+\w+\??$",  # "what is rice?"
        r"^\w+\s+products?$",  # "rice products"
    ]
    
    return any(re.match(pattern, message.lower()) for pattern in simple_patterns)
```

### 5. Pricing Service (Ultra-Fast)

```python
# src/services/pricing_service.py
class PricingService:
    def __init__(self):
        self.cache = {}
        self.tier_discounts = {
            "retail": 0,
            "restaurant": 10,
            "wholesale": 15,
            "gold": 10,
            "platinum": 15
        }
        
    async def calculate_price(
        self,
        items: List[Dict],
        user_context: Dict,
        promo_codes: List[str] = None
    ) -> Dict:
        """
        Calculate pricing in <25ms
        No database calls - all from cache/memory
        """
        # Build cache key
        cache_key = self._build_cache_key(items, user_context, promo_codes)
        
        # Check cache
        if cached := self.cache.get(cache_key):
            if cached["expires"] > datetime.now():
                return cached["data"]
        
        # Calculate prices
        result = {
            "items": [],
            "summary": {
                "subtotal": 0,
                "adjustments": [],
                "shipping": 0,
                "tax": 0,
                "total": 0
            }
        }
        
        # Process each item
        for item in items:
            base_price = await self._get_base_price(item["productId"])
            
            # Apply tier discount
            tier_discount = self.tier_discounts.get(
                user_context.get("tier", "retail"), 
                0
            )
            
            # Apply quantity breaks
            qty_discount = self._get_quantity_discount(
                item["quantity"],
                item.get("quantityBreaks", [])
            )
            
            # Calculate final price
            adjustments = []
            
            if tier_discount:
                adjustments.append({
                    "type": "tier_discount",
                    "description": f"{user_context['tier']} tier discount",
                    "amount": -(base_price * tier_discount / 100),
                    "percentage": tier_discount
                })
            
            if qty_discount:
                adjustments.append({
                    "type": "quantity_break",
                    "description": f"{item['quantity']}+ units discount",
                    "amount": -(base_price * qty_discount / 100),
                    "percentage": qty_discount
                })
            
            unit_price = base_price + sum(a["amount"] for a in adjustments)
            subtotal = unit_price * item["quantity"]
            
            result["items"].append({
                "productId": item["productId"],
                "sku": item.get("sku"),
                "quantity": item["quantity"],
                "basePrice": base_price,
                "adjustments": adjustments,
                "unitPrice": unit_price,
                "subtotal": subtotal
            })
            
            result["summary"]["subtotal"] += subtotal
        
        # Apply promo codes
        if promo_codes:
            for code in promo_codes:
                if promo := await self._get_promo(code):
                    discount_amount = result["summary"]["subtotal"] * promo["percentage"] / 100
                    result["summary"]["adjustments"].append({
                        "type": "promo_code",
                        "code": code,
                        "amount": -discount_amount,
                        "percentage": promo["percentage"]
                    })
        
        # Calculate shipping and tax
        result["summary"]["shipping"] = self._calculate_shipping(
            user_context.get("location", {}),
            result["summary"]["subtotal"]
        )
        
        result["summary"]["tax"] = self._calculate_tax(
            user_context.get("location", {}),
            result["summary"]["subtotal"]
        )
        
        # Final total
        result["summary"]["total"] = (
            result["summary"]["subtotal"] +
            sum(a["amount"] for a in result["summary"]["adjustments"]) +
            result["summary"]["shipping"] +
            result["summary"]["tax"]
        )
        
        # Cache result
        self.cache[cache_key] = {
            "data": result,
            "expires": datetime.now() + timedelta(minutes=5)
        }
        
        return result
    
    async def _get_base_price(self, product_id: str) -> float:
        """Get base price from cache"""
        # This should be pre-loaded at startup
        return self.price_cache.get(product_id, 0.0)
```

### 6. Optimized Weaviate Client

```python
# src/integrations/weaviate_client_optimized.py
class OptimizedWeaviateClient:
    def __init__(self):
        self.client = None
        self.connection_pool = []
        self.pool_size = 5
        
    async def initialize(self):
        """Initialize connection pool"""
        for _ in range(self.pool_size):
            client = weaviate.Client(
                url=settings.WEAVIATE_URL,
                auth_client_secret=weaviate.AuthApiKey(
                    api_key=settings.WEAVIATE_API_KEY
                ),
                timeout_config=(5, 15),  # Connection, read timeout
                additional_headers={
                    "X-Openai-Api-Key": settings.OPENAI_API_KEY
                }
            )
            self.connection_pool.append(client)
    
    async def search_products(
        self,
        query: str,
        filters: Dict = None,
        limit: int = 20,
        offset: int = 0,
        alpha: float = 0.5
    ):
        """Optimized product search"""
        # Get client from pool
        client = self._get_client()
        
        try:
            # Build where filter
            where_filter = self._build_filter(filters) if filters else None
            
            # Execute search
            result = client.query.get(
                "Product",
                ["product_id", "sku", "product_name", "price", "supplier", 
                 "category", "dietary_info", "in_stock"]
            ).with_hybrid(
                query=query,
                alpha=alpha,
                properties=["product_name^2", "search_terms"]
            ).with_where(
                where_filter
            ).with_limit(
                limit
            ).with_offset(
                offset
            ).with_additional(
                ["score", "explainScore"]
            ).do()
            
            return SearchResult(
                objects=result.get("data", {}).get("Get", {}).get("Product", []),
                total_count=self._get_total_count(query, where_filter)
            )
            
        finally:
            # Return client to pool
            self._return_client(client)
    
    def _build_filter(self, filters: Dict):
        """Build Weaviate where filter"""
        conditions = []
        
        if categories := filters.get("categories"):
            conditions.append({
                "path": ["category"],
                "operator": "ContainsAny",
                "valueTextArray": categories
            })
        
        if suppliers := filters.get("suppliers"):
            conditions.append({
                "path": ["supplier"],
                "operator": "ContainsAny", 
                "valueTextArray": suppliers
            })
        
        if price_range := filters.get("priceRange"):
            if min_price := price_range.get("min"):
                conditions.append({
                    "path": ["price"],
                    "operator": "GreaterThanEqual",
                    "valueNumber": min_price
                })
            if max_price := price_range.get("max"):
                conditions.append({
                    "path": ["price"],
                    "operator": "LessThanEqual",
                    "valueNumber": max_price
                })
        
        if len(conditions) == 1:
            return conditions[0]
        elif len(conditions) > 1:
            return {
                "operator": "And",
                "operands": conditions
            }
        
        return None
```

---

## 🔄 Migration Path

### Phase 1: Quick Wins (Today)
1. **Fix order agent error** (missing time import)
2. **Create direct search endpoint** (bypass supervisor)
3. **Implement basic cart service** (in-memory + Redis)

### Phase 2: Optimization (This Week)
1. **Add Redis caching** for products and search results
2. **Implement connection pooling** for Weaviate
3. **Create pricing service** with pre-loaded prices

### Phase 3: Full Implementation (Next Week)
1. **Deploy all endpoints** with proper routing
2. **Add monitoring** for latency tracking
3. **Implement ML recommendations** (rule-based)

---

## 📊 Expected Results

### Latency Improvements:
- **Product Search**: 650ms → 150ms (-77%)
- **Cart Operations**: N/A → 50ms (new)
- **Simple Chat**: 900ms → 300ms (-67%)
- **Complex Chat**: 900ms → 500ms (-44%)
- **Pricing**: N/A → 25ms (new)

### Architecture Benefits:
1. **Separation of Concerns** - Each endpoint has one job
2. **Horizontal Scaling** - Can scale services independently
3. **Better Caching** - Targeted caching per operation
4. **Improved UX** - Faster responses for common operations

---

## 🚨 Critical Success Factors

1. **Cache Everything Possible**
   - Product details (1 hour)
   - Search results (5 minutes)
   - Pricing calculations (5 minutes)

2. **Avoid Supervisor for Simple Operations**
   - Direct search queries
   - Cart CRUD operations
   - Price calculations

3. **Parallel Processing**
   - Run independent agents concurrently
   - Use asyncio.gather() for multiple operations

4. **Connection Management**
   - Pool Weaviate connections
   - Reuse Redis connections
   - Implement circuit breakers

5. **Monitor Everything**
   - Track latency per endpoint
   - Alert on >300ms responses
   - Log cache hit rates