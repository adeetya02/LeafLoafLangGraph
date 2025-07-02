# Search Improvement Plan

**Timeline**: 24 Hours  
**Goal**: Transform broken search into intelligent, personalized system  
**Approach**: Iterative - Fix basics first, add intelligence incrementally

## 🎯 Success Criteria

1. **Phase 1 Success**: Search returns products (any products)
2. **Phase 2 Success**: Search uses fallbacks gracefully  
3. **Phase 3 Success**: Search is personalized per user
4. **Phase 4 Success**: Search learns from behavior
5. **Phase 5 Success**: Search is fast and reliable

## 📋 Phase 1: Make Search Work (2-3 hours)

**Goal**: Users can search and see products

### 1.1 Debug Weaviate Connection

```python
# Check from Cloud Run environment
curl https://leafloaf-24zrqqjo.weaviate.network/v1/.well-known/ready

# Test with API key
curl -H "Authorization: Bearer YOUR_KEY" https://leafloaf-24zrqqjo.weaviate.network/v1/objects

# Common issues:
- Network/firewall blocking from GCP
- API key expired or wrong
- URL not accessible from region
```

### 1.2 Implement Immediate Fallback

```python
# In src/tools/search_tools.py
async def run(self, query: str, limit: int = 10, alpha: Optional[float] = None) -> Dict[str, Any]:
    """Execute product search with fallbacks"""
    
    # Try 1: Full Weaviate search
    try:
        if not self.test_mode:
            return await self._weaviate_search(query, limit, alpha)
    except Exception as e:
        logger.warning(f"Weaviate search failed: {e}")
    
    # Try 2: BM25 only (no vectors)
    try:
        return await self._bm25_only_search(query, limit)
    except Exception as e:
        logger.warning(f"BM25 search failed: {e}")
    
    # Try 3: Return mock data
    logger.warning("All search methods failed, returning mock data")
    return self._get_mock_products(query, limit)

async def _bm25_only_search(self, query: str, limit: int) -> Dict[str, Any]:
    """Keyword search without vectors"""
    collection = self.client.collections.get(self.collection_name)
    response = collection.query.bm25(
        query=query,
        limit=limit,
        return_properties=["product_name", "price", "category", ...]
    )
    return self._format_response(response)
```

### 1.3 Enhance Mock Data

```python
# Expand mock products to cover common queries
MOCK_PRODUCTS = [
    # Milk products (most common search)
    {"product_name": "Organic Whole Milk", "category": "Dairy", "price": 4.99},
    {"product_name": "Oat Milk - Oatly", "category": "Dairy", "price": 5.49},
    {"product_name": "Almond Milk", "category": "Dairy", "price": 4.49},
    
    # Add 50+ common products covering all categories
    # Ensure mock data can satisfy basic searches
]
```

### 1.4 Fix API Response Format

```python
# Ensure consistent response format
def _format_response(self, products: List[Dict]) -> Dict[str, Any]:
    return {
        "success": True,
        "query": self.query,
        "count": len(products),
        "products": [self._format_product(p) for p in products],
        "search_config": {
            "method": "weaviate" if not self.test_mode else "mock",
            "alpha": self.alpha,
            "fallback_used": self.fallback_used
        }
    }
```

### Phase 1 Validation
- [ ] Search for "milk" returns products
- [ ] Search for "bread" returns products  
- [ ] Health check shows search status
- [ ] Logs show which method was used

## 📋 Phase 2: Add Graceful Degradation (2 hours)

**Goal**: System works even when components fail

### 2.1 Create Service Health Monitor

```python
# src/utils/health_monitor.py
class ServiceHealth:
    def __init__(self):
        self.services = {
            "weaviate": {"healthy": True, "last_check": None},
            "spanner": {"healthy": True, "last_check": None},
            "redis": {"healthy": True, "last_check": None},
            "graphiti": {"healthy": True, "last_check": None}
        }
    
    async def check_weaviate(self):
        try:
            # Quick health check
            await self.weaviate_client.collections.list_all()
            self.mark_healthy("weaviate")
        except:
            self.mark_unhealthy("weaviate")
    
    def should_use_service(self, service: str) -> bool:
        return self.services[service]["healthy"]
```

### 2.2 Implement Circuit Breaker

```python
# Prevent hammering failed services
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.last_failure_time = None
        self.is_open = False
    
    async def call(self, func, *args, **kwargs):
        if self.is_open:
            if time.time() - self.last_failure_time > self.timeout:
                self.is_open = False  # Try again
            else:
                raise CircuitBreakerOpen()
        
        try:
            result = await func(*args, **kwargs)
            self.failure_count = 0  # Reset on success
            return result
        except Exception as e:
            self.failure_count += 1
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
                self.last_failure_time = time.time()
            raise
```

### 2.3 Implement Fallback Chain

```python
# src/services/search_service.py
class SearchService:
    def __init__(self):
        self.weaviate_breaker = CircuitBreaker()
        self.health_monitor = ServiceHealth()
    
    async def search(self, query: str, user_id: str = None) -> List[Dict]:
        methods = [
            ("weaviate_vector", self._search_weaviate_vector),
            ("weaviate_bm25", self._search_weaviate_bm25),
            ("elasticsearch", self._search_elasticsearch),  # If available
            ("mock_data", self._search_mock_data)
        ]
        
        for method_name, method_func in methods:
            try:
                if method_name == "weaviate_vector" and not self.health_monitor.should_use_service("weaviate"):
                    continue
                    
                results = await method_func(query)
                logger.info(f"Search succeeded with {method_name}")
                return results
            except Exception as e:
                logger.warning(f"Search failed with {method_name}: {e}")
                continue
        
        # Absolute fallback
        return self._get_default_products()
```

### Phase 2 Validation
- [ ] Disable Weaviate - search still works
- [ ] Circuit breaker prevents repeated failures
- [ ] Health monitor tracks service status
- [ ] Fallback chain documented in logs

## 📋 Phase 3: Add User Context (4 hours)

**Goal**: Personalized search based on user preferences

### 3.1 Create Unified UserContext Service

```python
# src/services/user_context_service.py
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class UserContext:
    user_id: str
    preferences: Dict[str, Any]
    dietary_restrictions: List[str]
    preferred_brands: List[str]
    avoided_ingredients: List[str]
    price_sensitivity: float  # 0.0 (price insensitive) to 1.0 (very sensitive)
    cultural_context: Optional[str]
    shopping_patterns: Dict[str, Any]
    graphiti_instance: Optional[Any]

class UserContextService:
    def __init__(self):
        self.redis_client = RedisClient()
        self.spanner_client = SpannerClient()
        self.cache_ttl = 3600  # 1 hour
    
    async def get_user_context(self, user_id: str) -> UserContext:
        # Try cache first
        cached = await self._get_from_cache(user_id)
        if cached:
            return cached
        
        # Load from Spanner/Graphiti
        context = await self._load_from_storage(user_id)
        
        # Cache for next time
        await self._cache_context(user_id, context)
        
        return context
    
    async def _load_from_storage(self, user_id: str) -> UserContext:
        # Initialize Graphiti
        graphiti = GraphitiMemorySpanner(user_id, "session")
        await graphiti.initialize()
        
        # Get user data
        prefs = await graphiti.get_preferences()
        dietary = await graphiti.get_dietary_restrictions()
        brands = await graphiti.get_preferred_brands()
        
        return UserContext(
            user_id=user_id,
            preferences=prefs,
            dietary_restrictions=dietary,
            preferred_brands=brands,
            avoided_ingredients=await graphiti.get_avoided_ingredients(),
            price_sensitivity=await graphiti.get_price_sensitivity(),
            cultural_context=await graphiti.get_cultural_context(),
            shopping_patterns=await graphiti.get_shopping_patterns(),
            graphiti_instance=graphiti
        )
```

### 3.2 Inject Context into State

```python
# In src/api/main.py
@app.post("/api/v1/search")
async def search(request: SearchRequest):
    # Load user context ONCE at the beginning
    user_context = None
    if request.user_id:
        try:
            context_service = UserContextService()
            user_context = await context_service.get_user_context(request.user_id)
        except Exception as e:
            logger.warning(f"Failed to load user context: {e}")
    
    # Create initial state with context
    initial_state = create_initial_state(request, calculated_alpha)
    initial_state["user_context"] = user_context  # Now available to ALL agents
    
    # Run the graph
    result = await search_graph.ainvoke(initial_state)
```

### 3.3 Update Agents to Use Context

```python
# In src/agents/supervisor_optimized.py
async def _run(self, state: SearchState) -> SearchState:
    user_context = state.get("user_context")
    
    if user_context:
        # Use context for better routing
        if "organic" in query and "vegan" in user_context.dietary_restrictions:
            # User cares about dietary, route to specialized search
            state["routing_decision"] = "dietary_search"
        
        # Adjust alpha based on user patterns
        if user_context.shopping_patterns.get("explores_new", False):
            state["alpha_value"] *= 1.2  # More semantic
        else:
            state["alpha_value"] *= 0.8  # More specific

# In src/agents/product_search.py
async def _run(self, state: SearchState) -> SearchState:
    user_context = state.get("user_context")
    
    # Get base results
    products = await self.search_tool.run(query, alpha=alpha)
    
    if user_context and products:
        # Apply user filters
        products = self._filter_dietary(products, user_context.dietary_restrictions)
        products = self._boost_preferred_brands(products, user_context.preferred_brands)
        products = self._apply_price_filter(products, user_context.price_sensitivity)
        
        # Rerank based on user preferences
        products = await self.personalized_ranker.rerank(
            products, 
            user_context.preferences
        )
```

### Phase 3 Validation
- [ ] User context loaded once per request
- [ ] Different users get different results
- [ ] Dietary restrictions applied
- [ ] Preferred brands boosted
- [ ] Context available to all agents

## 📋 Phase 4: Implement Learning Loop (4 hours)

**Goal**: System learns from every interaction

### 4.1 Create Event Tracking System

```python
# src/services/learning_service.py
class LearningService:
    def __init__(self):
        self.bigquery = BigQueryClient()
        self.graphiti = GraphitiMemorySpanner()
    
    async def track_search_interaction(
        self,
        user_id: str,
        query: str,
        results: List[Dict],
        clicked_items: List[str],
        timestamp: datetime
    ):
        # 1. Send to BigQuery for analytics
        await self.bigquery.insert_rows([{
            "user_id": user_id,
            "query": query,
            "results_shown": [r["id"] for r in results[:10]],
            "items_clicked": clicked_items,
            "timestamp": timestamp,
            "click_through_rate": len(clicked_items) / min(len(results), 10)
        }])
        
        # 2. Update Graphiti immediately
        for item_id in clicked_items:
            item = next((r for r in results if r["id"] == item_id), None)
            if item:
                # User showed interest in this category
                await self.graphiti.add_relationship(
                    user_id,
                    item["category"],
                    "SHOWS_INTEREST",
                    confidence=0.6
                )
                
                # User interested in this brand
                await self.graphiti.add_relationship(
                    user_id,
                    item["brand"],
                    "CONSIDERS_BRAND",
                    confidence=0.5
                )
    
    async def track_cart_action(
        self,
        user_id: str,
        action: str,  # "add", "remove", "update"
        item: Dict,
        quantity: int
    ):
        # Strong preference signal
        if action == "add":
            await self.graphiti.add_relationship(
                user_id,
                item["id"],
                "PREFERS_PRODUCT",
                confidence=0.8
            )
            
            # Learn quantity preferences
            await self.graphiti.add_entity(
                f"quantity_pref_{user_id}_{item['category']}",
                "QUANTITY_PREFERENCE",
                {"typical_quantity": quantity}
            )
        
        elif action == "remove":
            # Negative signal
            await self.graphiti.add_relationship(
                user_id,
                item["id"],
                "AVOIDED",
                confidence=0.7
            )
    
    async def track_order_completion(
        self,
        user_id: str,
        order_items: List[Dict]
    ):
        # Strongest preference signals
        for item in order_items:
            # This is what they actually buy
            await self.graphiti.add_relationship(
                user_id,
                item["id"],
                "REGULARLY_BUYS",
                confidence=0.9
            )
            
            # Track reorder patterns
            await self.graphiti.add_entity(
                f"reorder_{user_id}_{item['id']}",
                "REORDER_PATTERN",
                {
                    "last_ordered": datetime.now(),
                    "quantity": item["quantity"],
                    "frequency_days": 14  # Will be calculated
                }
            )
```

### 4.2 Add Learning Hooks

```python
# In src/api/main.py - after search
@app.post("/api/v1/track/search-click")
async def track_search_click(
    user_id: str,
    query: str,
    clicked_item_id: str,
    position: int
):
    learning_service = LearningService()
    await learning_service.track_search_interaction(
        user_id=user_id,
        query=query,
        clicked_items=[clicked_item_id],
        timestamp=datetime.now()
    )

# In frontend - track clicks
async function trackProductClick(productId, position) {
    await api.post('/api/v1/track/search-click', {
        user_id: currentUser,
        query: lastQuery,
        clicked_item_id: productId,
        position: position
    });
}
```

### 4.3 Implement Batch Learning

```python
# src/jobs/batch_learning_job.py
async def process_daily_learning():
    """Run daily to update long-term patterns"""
    
    # 1. Aggregate patterns from BigQuery
    query = """
    SELECT 
        user_id,
        category,
        COUNT(*) as purchase_count,
        AVG(quantity) as avg_quantity,
        ARRAY_AGG(DISTINCT brand) as brands
    FROM orders
    WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY user_id, category
    """
    
    results = await bigquery.query(query)
    
    # 2. Update Graphiti with patterns
    for row in results:
        if row.purchase_count > 3:
            # Regular purchase pattern
            await graphiti.add_relationship(
                row.user_id,
                row.category,
                "REGULARLY_BUYS_CATEGORY",
                confidence=min(0.9, row.purchase_count / 10)
            )
```

### Phase 4 Validation
- [ ] Click tracking works
- [ ] Cart actions update preferences
- [ ] Orders create strong signals
- [ ] Batch job processes patterns
- [ ] Second search better than first

## 📋 Phase 5: Performance & Reliability (2 hours)

**Goal**: Fast, stable system

### 5.1 Optimize User Context Loading

```python
# Pre-load in parallel
async def load_request_context(request: SearchRequest):
    tasks = []
    
    # Load user context
    if request.user_id:
        tasks.append(load_user_context(request.user_id))
    
    # Warm up caches
    tasks.append(warm_product_cache())
    
    # Pre-connect to services
    tasks.append(ensure_service_connections())
    
    # Execute in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        "user_context": results[0] if not isinstance(results[0], Exception) else None,
        "cache_warmed": results[1],
        "services_ready": results[2]
    }
```

### 5.2 Implement Smart Caching

```python
# Cache personalized results
class PersonalizedSearchCache:
    def get_cache_key(self, user_id: str, query: str) -> str:
        # Include user preferences in cache key
        user_hash = hashlib.md5(f"{user_id}:{query}".encode()).hexdigest()
        return f"search:v2:{user_hash}"
    
    async def get(self, user_id: str, query: str) -> Optional[List[Dict]]:
        key = self.get_cache_key(user_id, query)
        cached = await redis.get(key)
        
        if cached:
            # Check if preferences changed
            pref_version = await redis.get(f"pref_version:{user_id}")
            if cached["pref_version"] == pref_version:
                return cached["results"]
        
        return None
```

### 5.3 Add Comprehensive Monitoring

```python
# Track everything
class SearchMetrics:
    def __init__(self):
        self.metrics = {
            "search_latency": Histogram("search_latency_ms"),
            "personalization_applied": Counter("personalization_applied"),
            "fallback_used": Counter("fallback_used"),
            "cache_hit_rate": Counter("cache_hits"),
            "learning_events": Counter("learning_events")
        }
    
    async def track_search(self, metadata: Dict):
        self.metrics["search_latency"].observe(metadata["latency_ms"])
        
        if metadata.get("personalization_applied"):
            self.metrics["personalization_applied"].inc()
        
        if metadata.get("fallback_used"):
            self.metrics["fallback_used"].inc({"method": metadata["fallback_method"]})
```

### Phase 5 Validation
- [ ] Response time < 300ms (p95)
- [ ] Cache hit rate > 30%
- [ ] No memory leaks
- [ ] Graceful degradation works
- [ ] Metrics dashboard available

## 🚀 Rollout Strategy

### Day 1 Morning
1. Deploy Phase 1 fixes
2. Verify basic search works
3. Monitor error rates

### Day 1 Afternoon  
1. Deploy Phase 2 & 3
2. Test with sample users
3. Verify personalization

### Day 1 Evening
1. Deploy Phase 4
2. Enable learning hooks
3. Monitor overnight

### Day 2 Morning
1. Deploy Phase 5
2. Full production rollout
3. Monitor and iterate

## 📊 Success Metrics

1. **Search Success Rate**: >99% (from 0%)
2. **Personalization Coverage**: >80% of searches
3. **Click-Through Rate**: >30% improvement
4. **Response Time**: <300ms p95
5. **User Satisfaction**: Measure via feedback

## 🚨 Rollback Plan

Each phase can be rolled back independently:
- Feature flags for each phase
- Previous version kept warm
- One-click rollback
- Monitoring alerts for issues

The key is iterative improvement - fix the basics first, then layer on intelligence.