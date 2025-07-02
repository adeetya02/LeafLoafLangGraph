# Memory Integration Guide

**Goal**: Make all agents memory-aware for true personalization  
**Current State**: Fragmented - some agents use memory, others don't  
**Target State**: Unified memory service accessible to all agents

## 🎯 Success Criteria

1. **Unified Access**: All agents use same memory pattern
2. **User Context**: Loaded once, available everywhere
3. **Real-time Updates**: User actions immediately affect future searches
4. **Graceful Degradation**: Works even if memory systems fail
5. **Performance**: <50ms overhead for memory operations

## 📊 Current Memory Architecture Analysis

### What Exists

```python
# Multiple memory systems:
1. GraphitiMemorySpanner - Graph-based memory with Spanner backend
2. RedisMemory - Session and cache storage
3. InMemoryFallback - When Redis unavailable
4. MemoryRegistry - Supposed to unify access
```

### Problems

1. **No Consistent Usage**
   - Supervisor: Doesn't load user context
   - Product Search: Has personalization code but no memory
   - Order Agent: Only agent that uses Graphiti properly
   - Response Compiler: No memory access

2. **Multiple Initialization Points**
   ```python
   # Each agent does its own thing:
   # Order Agent:
   graphiti_memory = GraphitiMemorySpanner(user_id, session_id)
   await graphiti_memory.initialize()
   
   # Product Search:
   # Has personalization engine but doesn't use it
   
   # Supervisor:
   # No memory initialization at all
   ```

3. **Context Not Flowing**
   - User context loaded in API but not passed properly
   - Each agent would need to reload context
   - No shared state for user preferences

## 🏗️ Unified Memory Architecture

### 1. Memory Service Layer

```python
# src/services/unified_memory_service.py
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime

@dataclass
class UserMemoryContext:
    """Unified memory context for a user"""
    user_id: str
    session_id: str
    
    # Preferences
    dietary_restrictions: List[str] = None
    preferred_brands: List[str] = None
    avoided_ingredients: List[str] = None
    price_sensitivity: float = 0.5
    
    # Behavioral patterns
    usual_items: List[Dict] = None
    reorder_patterns: List[Dict] = None
    purchase_history: List[Dict] = None
    search_history: List[Dict] = None
    
    # Session state
    current_cart: Dict = None
    recent_searches: List[str] = None
    last_intent: str = None
    
    # Graphiti references
    graphiti_instance: Any = None
    entity_cache: List[Dict] = None
    relationship_cache: List[Dict] = None
    
    # Metadata
    loaded_at: datetime = None
    last_updated: datetime = None
    data_quality_score: float = 0.0

class UnifiedMemoryService:
    """Single source of truth for all memory operations"""
    
    def __init__(self):
        self._cache = {}  # In-memory cache
        self._loading_locks = {}  # Prevent duplicate loads
    
    async def get_user_context(
        self, 
        user_id: str, 
        session_id: str,
        force_refresh: bool = False
    ) -> UserMemoryContext:
        """Get or load user context with caching"""
        
        cache_key = f"{user_id}:{session_id}"
        
        # Return cached if available and fresh
        if not force_refresh and cache_key in self._cache:
            context = self._cache[cache_key]
            if (datetime.now() - context.loaded_at).seconds < 300:  # 5 min cache
                return context
        
        # Prevent duplicate loading
        if cache_key not in self._loading_locks:
            self._loading_locks[cache_key] = asyncio.Lock()
        
        async with self._loading_locks[cache_key]:
            # Check again after acquiring lock
            if not force_refresh and cache_key in self._cache:
                return self._cache[cache_key]
            
            # Load fresh context
            context = await self._load_full_context(user_id, session_id)
            self._cache[cache_key] = context
            
            return context
    
    async def _load_full_context(self, user_id: str, session_id: str) -> UserMemoryContext:
        """Load complete user context from all sources"""
        
        # Initialize context
        context = UserMemoryContext(
            user_id=user_id,
            session_id=session_id,
            loaded_at=datetime.now()
        )
        
        # Parallel load from all sources
        tasks = [
            self._load_graphiti_data(context),
            self._load_redis_session(context),
            self._load_user_preferences(context),
            self._load_purchase_history(context)
        ]
        
        # Wait for all with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=2.0  # 2 second timeout
            )
        except asyncio.TimeoutError:
            logger.warning("Memory loading timeout, using partial data")
        
        # Calculate data quality
        context.data_quality_score = self._calculate_quality_score(context)
        
        return context
    
    async def _load_graphiti_data(self, context: UserMemoryContext):
        """Load Graphiti graph data"""
        try:
            from src.memory.graphiti_memory_spanner import GraphitiMemorySpanner
            
            graphiti = GraphitiMemorySpanner(
                user_id=context.user_id,
                session_id=context.session_id
            )
            await graphiti.initialize()
            
            # Get user patterns
            graphiti_context = await graphiti.get_context("")
            
            # Extract key data
            context.usual_items = graphiti_context.get("usual_items", [])
            context.reorder_patterns = graphiti_context.get("reorder_patterns", [])
            context.entity_cache = graphiti_context.get("entities", [])[:50]
            context.relationship_cache = graphiti_context.get("relationships", [])[:50]
            
            # Extract preferences from relationships
            for rel in context.relationship_cache:
                if rel.get("type") == "AVOIDS":
                    if context.avoided_ingredients is None:
                        context.avoided_ingredients = []
                    context.avoided_ingredients.append(rel.get("target"))
                elif rel.get("type") == "PREFERS_BRAND":
                    if context.preferred_brands is None:
                        context.preferred_brands = []
                    context.preferred_brands.append(rel.get("target"))
            
            context.graphiti_instance = graphiti
            
        except Exception as e:
            logger.error(f"Failed to load Graphiti data: {e}")
    
    async def _load_redis_session(self, context: UserMemoryContext):
        """Load session data from Redis"""
        try:
            from src.memory.session_memory import SessionMemory
            
            session_memory = SessionMemory()
            
            # Get current cart
            context.current_cart = await session_memory.get_current_order(
                context.session_id
            )
            
            # Get recent searches
            context.recent_searches = await session_memory.get_search_history(
                context.session_id
            )
            
        except Exception as e:
            logger.error(f"Failed to load Redis session: {e}")
    
    async def update_context(
        self,
        user_id: str,
        session_id: str,
        updates: Dict[str, Any]
    ):
        """Update user context and propagate to storage"""
        
        context = await self.get_user_context(user_id, session_id)
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(context, key):
                setattr(context, key, value)
        
        context.last_updated = datetime.now()
        
        # Propagate to storage systems
        await self._propagate_updates(context, updates)
        
        return context
    
    def _calculate_quality_score(self, context: UserMemoryContext) -> float:
        """Calculate how complete/reliable the user data is"""
        
        score = 0.0
        factors = 0
        
        # Check data completeness
        if context.usual_items:
            score += 0.2
            factors += 1
        
        if context.purchase_history:
            score += 0.3
            factors += 1
        
        if context.dietary_restrictions:
            score += 0.2
            factors += 1
        
        if context.reorder_patterns:
            score += 0.3
            factors += 1
        
        return score if factors > 0 else 0.0

# Global instance
unified_memory = UnifiedMemoryService()
```

### 2. Integration Points

#### API Level - Load Once

```python
# src/api/main.py - Modified search endpoint
@app.post("/api/v1/search")
async def search_products(request: SearchRequest, req: Request):
    start_time = time.perf_counter()
    
    # Get user identifiers
    user_id = request.user_id or 'anonymous'
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        # Load user context ONCE at the beginning
        user_context = None
        if user_id != 'anonymous':
            try:
                user_context = await unified_memory.get_user_context(
                    user_id, session_id
                )
                logger.info(
                    "User context loaded",
                    quality_score=user_context.data_quality_score
                )
            except Exception as e:
                logger.warning(f"Failed to load user context: {e}")
        
        # Create initial state WITH context
        initial_state = create_initial_state(request, calculated_alpha)
        initial_state["memory_context"] = user_context  # Pass the full context
        initial_state["user_id"] = user_id
        initial_state["session_id"] = session_id
        
        # Execute graph - context flows to ALL agents
        final_state = await search_graph.ainvoke(initial_state)
        
        # Update memory with results
        if user_context and final_state.get("search_results"):
            await unified_memory.update_context(
                user_id, 
                session_id,
                {
                    "recent_searches": [request.query],
                    "last_intent": final_state.get("intent")
                }
            )
```

#### Supervisor - Use Context for Routing

```python
# src/agents/supervisor_optimized.py
async def _run(self, state: SearchState) -> SearchState:
    """Route queries with user context awareness"""
    
    # Get user context from state
    memory_context = state.get("memory_context")
    
    # Enhance routing with user patterns
    if memory_context:
        # User who frequently orders milk → route "need milk" to order agent
        if self._is_reorder_intent(state["query"], memory_context):
            state["routing_decision"] = "order_agent"
            state["intent"] = "usual_order"
            state["reasoning"].append(
                "User frequently orders this item - routing to order agent"
            )
            return state
        
        # Adjust alpha based on user behavior
        alpha = self._calculate_user_alpha(state["query"], memory_context)
        state["alpha_value"] = alpha
    
    # Continue with normal routing...

def _is_reorder_intent(self, query: str, context: UserMemoryContext) -> bool:
    """Check if user wants to reorder usual items"""
    
    if not context.usual_items:
        return False
    
    query_lower = query.lower()
    
    # Direct reorder signals
    if any(word in query_lower for word in ["usual", "regular", "again", "reorder"]):
        return True
    
    # Check if query matches usual items
    for item in context.usual_items[:10]:
        item_name = item.get("name", "").lower()
        if item_name in query_lower or query_lower in item_name:
            # User just said "milk" and regularly buys milk
            return True
    
    return False

def _calculate_user_alpha(self, query: str, context: UserMemoryContext) -> float:
    """Personalize alpha based on user behavior"""
    
    base_alpha = 0.5  # Default
    
    # Users who explore new products prefer semantic search
    if context.search_history:
        unique_categories = len(set(s.get("category") for s in context.search_history))
        if unique_categories > 10:
            base_alpha += 0.2  # More semantic
    
    # Users with strong preferences prefer exact matches
    if context.preferred_brands and len(context.preferred_brands) > 3:
        base_alpha -= 0.1  # More keyword-focused
    
    # Dietary restrictions = exact matching important
    if context.dietary_restrictions:
        base_alpha -= 0.15
    
    return max(0.2, min(0.8, base_alpha))
```

#### Product Search - Apply Personalization

```python
# src/agents/product_search.py
async def _run(self, state: SearchState) -> SearchState:
    """Search with full personalization"""
    
    # Get memory context
    memory_context = state.get("memory_context")
    
    # Base search
    products = await self.search_tool.run(
        query=state["query"],
        limit=50,  # Get more for filtering
        alpha=state.get("alpha_value", 0.5)
    )
    
    if memory_context and products:
        # Apply user filters
        products = await self._apply_personalization(
            products, 
            memory_context,
            state["query"]
        )
    
    # Store top 15 results
    state["search_results"] = products[:15]
    
    return state

async def _apply_personalization(
    self, 
    products: List[Dict],
    context: UserMemoryContext,
    query: str
) -> List[Dict]:
    """Apply all personalization features"""
    
    # 1. Filter dietary restrictions
    if context.dietary_restrictions:
        products = self._filter_dietary(products, context.dietary_restrictions)
    
    # 2. Filter avoided ingredients
    if context.avoided_ingredients:
        products = self._filter_avoided(products, context.avoided_ingredients)
    
    # 3. Boost preferred brands
    if context.preferred_brands:
        products = self._boost_brands(products, context.preferred_brands)
    
    # 4. Apply price sensitivity
    products = self._apply_price_filter(products, context.price_sensitivity)
    
    # 5. Smart ranking based on purchase history
    if context.purchase_history:
        products = self._rank_by_history(products, context.purchase_history)
    
    # 6. Highlight usual items
    if context.usual_items:
        products = self._mark_usual_items(products, context.usual_items)
    
    return products

def _filter_dietary(self, products: List[Dict], restrictions: List[str]) -> List[Dict]:
    """Remove products that don't meet dietary requirements"""
    
    filtered = []
    for product in products:
        # Check product attributes
        attributes = product.get("dietary_info", [])
        
        # Skip if has restricted ingredients
        if "vegan" in restrictions and "dairy" in attributes:
            continue
        if "gluten-free" in restrictions and "gluten" in attributes:
            continue
        if "vegetarian" in restrictions and "meat" in attributes:
            continue
        
        filtered.append(product)
    
    return filtered

def _boost_brands(self, products: List[Dict], preferred: List[str]) -> List[Dict]:
    """Boost scores for preferred brands"""
    
    for product in products:
        if product.get("supplier") in preferred:
            # Boost score by 20%
            product["_score"] = product.get("_score", 1.0) * 1.2
            product["is_preferred_brand"] = True
    
    # Re-sort by score
    return sorted(products, key=lambda p: p.get("_score", 0), reverse=True)
```

#### Order Agent - Use Purchase Patterns

```python
# src/agents/order_agent.py - Enhanced
async def _run(self, state: SearchState) -> SearchState:
    """Order management with memory awareness"""
    
    memory_context = state.get("memory_context")
    
    # Handle memory-based intents
    if state.get("intent") == "usual_order" and memory_context:
        await self._handle_usual_order(state, memory_context)
    elif state.get("intent") == "reorder" and memory_context:
        await self._handle_reorder(state, memory_context)
    else:
        # Normal order processing
        await self._process_order(state)
    
    return state

async def _handle_usual_order(
    self, 
    state: SearchState, 
    context: UserMemoryContext
):
    """Add user's usual items to cart"""
    
    if not context.usual_items:
        state["messages"].append({
            "role": "assistant",
            "content": "I don't have your usual order on file yet. What would you like to add?"
        })
        return
    
    # Group by readiness
    due_now = []
    due_soon = []
    not_due = []
    
    for item in context.usual_items:
        days_since = item.get("days_since_last_order", 0)
        avg_frequency = item.get("avg_days_between_orders", 30)
        
        if days_since >= avg_frequency:
            due_now.append(item)
        elif days_since >= avg_frequency * 0.8:
            due_soon.append(item)
        else:
            not_due.append(item)
    
    # Add due items to cart
    items_to_add = []
    
    for item in due_now:
        items_to_add.append({
            "sku": item["sku"],
            "name": item["name"],
            "quantity": item.get("usual_quantity", 1),
            "auto_added": True,
            "reason": "usually_ordered"
        })
    
    # Execute add to cart
    tool_call = {
        "id": "usual_order_add",
        "name": "add_to_cart",
        "args": {
            "items": items_to_add,
            "current_order": state.get("current_order", {})
        }
    }
    
    result = await self.tool_executor.execute_tool_call(tool_call)
    
    # Inform about items
    message = f"Added {len(due_now)} items from your usual order."
    if due_soon:
        message += f" {len(due_soon)} items will be due soon."
    
    state["messages"].append({
        "role": "assistant",
        "content": message
    })
```

#### Response Compiler - Include Personalization

```python
# src/agents/response_compiler.py - Enhanced
async def _run(self, state: SearchState) -> SearchState:
    """Compile response with personalization insights"""
    
    memory_context = state.get("memory_context")
    
    # Build base response
    response = await self._build_base_response(state)
    
    # Add personalization layer
    if memory_context and memory_context.data_quality_score > 0.3:
        response["personalization"] = {
            "applied": True,
            "confidence": memory_context.data_quality_score,
            "features_used": self._get_applied_features(state, memory_context),
            "insights": self._generate_insights(state, memory_context)
        }
    
    state["final_response"] = response
    return state

def _get_applied_features(self, state: SearchState, context: UserMemoryContext) -> List[str]:
    """List which personalization features were used"""
    
    features = []
    
    if context.dietary_restrictions:
        features.append("dietary_filtering")
    
    if context.preferred_brands:
        features.append("brand_preference")
    
    if context.usual_items and state.get("intent") == "usual_order":
        features.append("usual_order")
    
    if context.price_sensitivity != 0.5:
        features.append("price_awareness")
    
    return features

def _generate_insights(self, state: SearchState, context: UserMemoryContext) -> Dict:
    """Generate user insights for transparency"""
    
    insights = {}
    
    # Search personalization
    if state.get("routing_decision") == "product_search":
        insights["search"] = {
            "filtered_count": state.get("filtered_product_count", 0),
            "boosted_brands": [b for b in context.preferred_brands 
                               if any(p.get("supplier") == b 
                                     for p in state.get("search_results", []))]
        }
    
    # Order insights
    if state.get("routing_decision") == "order_agent":
        insights["order"] = {
            "usual_items_added": len([i for i in state.get("current_order", {}).get("items", [])
                                      if i.get("auto_added")]),
            "saved_time": True
        }
    
    return insights
```

### 3. Memory Update Patterns

#### Real-time Learning

```python
# src/services/memory_update_service.py
class MemoryUpdateService:
    """Handle real-time memory updates from user actions"""
    
    def __init__(self):
        self.unified_memory = unified_memory
        self.update_queue = asyncio.Queue()
        self.batch_size = 10
        self.batch_interval = 5.0  # seconds
    
    async def track_search_click(
        self,
        user_id: str,
        session_id: str,
        query: str,
        clicked_product: Dict,
        position: int
    ):
        """User clicked on a search result"""
        
        update = {
            "type": "search_click",
            "user_id": user_id,
            "session_id": session_id,
            "query": query,
            "product": clicked_product,
            "position": position,
            "timestamp": datetime.now()
        }
        
        await self.update_queue.put(update)
        
        # Immediate context update for session
        context = await self.unified_memory.get_user_context(user_id, session_id)
        
        # Update search history
        if context.search_history is None:
            context.search_history = []
        
        context.search_history.append({
            "query": query,
            "clicked": clicked_product["name"],
            "category": clicked_product["category"],
            "timestamp": datetime.now().isoformat()
        })
        
        # Learn brand preference
        brand = clicked_product.get("supplier")
        if brand and brand not in (context.preferred_brands or []):
            if context.preferred_brands is None:
                context.preferred_brands = []
            
            # Count brand clicks
            brand_clicks = sum(1 for s in context.search_history 
                              if s.get("clicked", "").startswith(brand))
            
            if brand_clicks >= 3:  # 3 clicks = preference
                context.preferred_brands.append(brand)
                
                # Update Graphiti
                if context.graphiti_instance:
                    await context.graphiti_instance.add_relationship(
                        context.user_id,
                        brand,
                        "PREFERS_BRAND",
                        confidence=0.7
                    )
    
    async def track_cart_action(
        self,
        user_id: str,
        session_id: str,
        action: str,
        product: Dict,
        quantity: int
    ):
        """Track cart modifications"""
        
        context = await self.unified_memory.get_user_context(user_id, session_id)
        
        if action == "add":
            # Strong preference signal
            if context.graphiti_instance:
                # Product preference
                await context.graphiti_instance.add_relationship(
                    user_id,
                    product["sku"],
                    "PREFERS_PRODUCT",
                    confidence=0.8
                )
                
                # Quantity preference
                await context.graphiti_instance.add_entity(
                    f"qty_pref_{user_id}_{product['category']}",
                    "QUANTITY_PREFERENCE",
                    {
                        "category": product["category"],
                        "typical_quantity": quantity,
                        "last_updated": datetime.now().isoformat()
                    }
                )
        
        elif action == "remove":
            # Negative signal
            if context.graphiti_instance:
                await context.graphiti_instance.add_relationship(
                    user_id,
                    product["sku"],
                    "REMOVED_FROM_CART",
                    confidence=0.6
                )
    
    async def track_order_completion(
        self,
        user_id: str,
        session_id: str,
        order: Dict
    ):
        """Track completed orders - strongest signal"""
        
        context = await self.unified_memory.get_user_context(user_id, session_id)
        
        for item in order.get("items", []):
            # Update usual items
            if context.usual_items is None:
                context.usual_items = []
            
            # Find or create usual item entry
            usual_item = next(
                (ui for ui in context.usual_items if ui["sku"] == item["sku"]),
                None
            )
            
            if usual_item:
                # Update existing pattern
                usual_item["order_count"] += 1
                usual_item["last_ordered"] = datetime.now().isoformat()
                usual_item["usual_quantity"] = (
                    usual_item["usual_quantity"] * 0.7 + 
                    item["quantity"] * 0.3  # Weighted average
                )
            else:
                # New usual item
                context.usual_items.append({
                    "sku": item["sku"],
                    "name": item["name"],
                    "usual_quantity": item["quantity"],
                    "order_count": 1,
                    "last_ordered": datetime.now().isoformat(),
                    "category": item["category"]
                })
            
            # Update Graphiti
            if context.graphiti_instance:
                await context.graphiti_instance.add_relationship(
                    user_id,
                    item["sku"],
                    "REGULARLY_BUYS",
                    confidence=0.9
                )

# Global instance
memory_updater = MemoryUpdateService()
```

### 4. Fallback Patterns

```python
# src/memory/fallback_memory.py
class FallbackMemoryContext:
    """Minimal memory when systems are down"""
    
    def __init__(self, user_id: str, session_id: str):
        self.user_id = user_id
        self.session_id = session_id
        self.current_cart = {"items": []}
        self.recent_searches = []
    
    @classmethod
    def from_request(cls, request: Dict) -> 'FallbackMemoryContext':
        """Create from request data when memory systems fail"""
        
        context = cls(
            user_id=request.get("user_id", "anonymous"),
            session_id=request.get("session_id", str(uuid.uuid4()))
        )
        
        # Extract any preferences from request
        if "preferences" in request:
            prefs = request["preferences"]
            context.dietary_restrictions = prefs.get("dietary", [])
            context.preferred_brands = prefs.get("brands", [])
        
        return context

# In UnifiedMemoryService
async def get_user_context(self, user_id: str, session_id: str) -> UserMemoryContext:
    try:
        # Normal loading...
        return await self._load_full_context(user_id, session_id)
    except Exception as e:
        logger.error(f"Memory system failure: {e}")
        
        # Return minimal context
        fallback = FallbackMemoryContext(user_id, session_id)
        
        # Convert to full context format
        return UserMemoryContext(
            user_id=user_id,
            session_id=session_id,
            current_cart=fallback.current_cart,
            recent_searches=fallback.recent_searches,
            loaded_at=datetime.now(),
            data_quality_score=0.1  # Low quality indicator
        )
```

## 📋 Implementation Plan

### Phase 1: Create Unified Service (2 hours)
1. [ ] Implement UnifiedMemoryService
2. [ ] Add fallback patterns
3. [ ] Create memory update service
4. [ ] Add monitoring/metrics

### Phase 2: Update API Layer (1 hour)
1. [ ] Modify search endpoint to load context once
2. [ ] Pass context in initial state
3. [ ] Add memory update endpoints
4. [ ] Handle anonymous users

### Phase 3: Update Agents (3 hours)
1. [ ] Supervisor: Use context for routing & alpha
2. [ ] Product Search: Apply all personalization
3. [ ] Order Agent: Handle usual orders
4. [ ] Response Compiler: Add insights

### Phase 4: Testing (2 hours)
1. [ ] Test with memory systems up
2. [ ] Test with Graphiti down
3. [ ] Test with Redis down
4. [ ] Test with all systems down
5. [ ] Load test memory service

## 🎯 Success Metrics

1. **Unified Access**: 100% of agents use same pattern
2. **Load Time**: <50ms for context loading
3. **Cache Hit Rate**: >80% for active users
4. **Fallback Success**: 100% requests complete even with failures
5. **Memory Updates**: <100ms for update propagation

## 🚨 Common Pitfalls to Avoid

1. **Loading Multiple Times**
   ```python
   # BAD: Each agent loads separately
   context1 = await load_user_context()  # Supervisor
   context2 = await load_user_context()  # Product Search
   context3 = await load_user_context()  # Order Agent
   
   # GOOD: Load once, pass through state
   context = await unified_memory.get_user_context()
   state["memory_context"] = context
   ```

2. **Blocking on Memory Load**
   ```python
   # BAD: Wait forever for memory
   context = await load_all_user_data()  # Could timeout
   
   # GOOD: Timeout and use partial data
   try:
       context = await asyncio.wait_for(load_data(), timeout=2.0)
   except TimeoutError:
       context = FallbackMemoryContext()
   ```

3. **Not Handling Failures**
   ```python
   # BAD: Crash if Graphiti unavailable
   graphiti_data = await graphiti.get_context()  # Could fail
   
   # GOOD: Graceful degradation
   try:
       graphiti_data = await graphiti.get_context()
   except:
       graphiti_data = {}  # Continue without
   ```

## 🔄 Migration Strategy

1. **Add New Service**: Deploy UnifiedMemoryService alongside existing
2. **Update One Agent**: Start with Response Compiler (least critical)
3. **Measure Impact**: Compare performance metrics
4. **Roll Out**: Update remaining agents one by one
5. **Remove Old Code**: Clean up fragmented memory access

The key is making memory a first-class citizen in the architecture, not an afterthought.

## 📊 Memory Data Flow Diagram

```
┌─────────────┐
│   Request   │
│ (user_id,   │
│ session_id) │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│      API Layer          │
│ Load Context ONCE       │◀─────┐
│ unified_memory.get()    │      │
└──────┬──────────────────┘      │
       │                         │
       ▼                         │
┌─────────────────────────┐      │ Memory
│    Initial State        │      │ Context
│ state["memory_context"] │      │ Flows
└──────┬──────────────────┘      │ Through
       │                         │ State
       ▼                         │
┌─────────────────────────┐      │
│     Supervisor          │      │
│ - Routing decisions     │──────┤
│ - Alpha calculation     │      │
└──────┬──────────────────┘      │
       │                         │
       ▼                         │
┌─────────────────────────┐      │
│   Product Search        │      │
│ - Apply filters         │──────┤
│ - Boost preferences     │      │
│ - Rank by history       │      │
└──────┬──────────────────┘      │
       │                         │
       ▼                         │
┌─────────────────────────┐      │
│    Order Agent          │      │
│ - Usual orders          │──────┤
│ - Reorder patterns      │      │
└──────┬──────────────────┘      │
       │                         │
       ▼                         │
┌─────────────────────────┐      │
│  Response Compiler      │      │
│ - Add insights          │──────┘
│ - Show personalization  │
└─────────────────────────┘

       ⬇️ User Actions ⬇️

┌─────────────────────────┐
│   Memory Updates        │
│ - Search clicks         │
│ - Cart actions          │
│ - Order completion      │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│   Update Propagation    │
├─────────────────────────┤
│ • Graphiti (permanent)  │
│ • Redis (session)       │
│ • Cache (temporary)     │
└─────────────────────────┘
```