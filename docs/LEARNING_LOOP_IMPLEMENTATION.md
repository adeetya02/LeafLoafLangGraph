# Learning Loop Implementation Guide

**Goal**: Close the feedback loop - every user action improves future experiences  
**Current State**: One-way flow (Search → Results → User)  
**Target State**: Continuous learning (Search → Results → Actions → Learn → Better Search)

## 🎯 Success Criteria

1. **Real-time Learning**: User actions immediately affect next search
2. **Batch Processing**: Daily/weekly pattern analysis
3. **Multi-signal Learning**: Clicks, cart, orders all contribute
4. **Privacy First**: Users control what's learned
5. **Performance**: <100ms for event tracking

## 📊 Current State Analysis

### What Exists

```python
# Components that could support learning:
1. BigQueryClient - Ready for analytics
2. GraphitiMemorySpanner - Can store relationships
3. Analytics Service - Tracks some events
4. Personalization Engine - Uses learned data
```

### What's Missing

1. **No Click Tracking**: Search results aren't tracked
2. **No Feedback Loop**: User actions don't update preferences
3. **No Pattern Analysis**: Purchase patterns aren't extracted
4. **No A/B Testing**: Can't measure improvements

## 🔄 Learning Loop Architecture

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│ Personalized    │◀────│   Learned    │
│    Search       │     │  Preferences │
└────────┬────────┘     └──────────────┘
         │                      ▲
         ▼                      │
┌─────────────────┐            │
│    Results      │            │
└────────┬────────┘            │
         │                      │
         ▼                      │
┌─────────────────┐            │
│  User Actions   │            │
│ • Click         │            │
│ • Add to Cart   │            │
│ • Purchase      │            │
└────────┬────────┘            │
         │                      │
         ▼                      │
┌─────────────────┐            │
│ Event Tracking  │            │
└────────┬────────┘            │
         │                      │
         ▼                      │
┌─────────────────┐            │
│   Learning      │────────────┘
│ • Real-time     │
│ • Batch         │
└─────────────────┘
```

## 🏗️ Implementation Components

### 1. Event Tracking Layer

```python
# src/services/event_tracking_service.py
from enum import Enum
from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
import json

class EventType(Enum):
    SEARCH_PERFORMED = "search_performed"
    SEARCH_RESULT_CLICKED = "search_result_clicked"
    PRODUCT_VIEWED = "product_viewed"
    CART_ITEM_ADDED = "cart_item_added"
    CART_ITEM_REMOVED = "cart_item_removed"
    CART_ITEM_UPDATED = "cart_item_updated"
    ORDER_COMPLETED = "order_completed"
    PREFERENCE_UPDATED = "preference_updated"

class EventTracker:
    """Central event tracking for learning loop"""
    
    def __init__(self):
        self.bigquery = BigQueryClient()
        self.unified_memory = unified_memory
        self.batch_queue = asyncio.Queue(maxsize=1000)
        self.batch_size = 100
        self.batch_interval = 5.0
        
        # Start background processor
        asyncio.create_task(self._batch_processor())
    
    async def track_event(
        self,
        event_type: EventType,
        user_id: str,
        session_id: str,
        data: Dict[str, Any]
    ):
        """Track any user event"""
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type.value,
            "user_id": user_id,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # Queue for batch processing
        try:
            self.batch_queue.put_nowait(event)
        except asyncio.QueueFull:
            # Emergency flush
            await self._flush_batch()
            await self.batch_queue.put(event)
        
        # Real-time learning for critical events
        if event_type in [EventType.CART_ITEM_ADDED, EventType.ORDER_COMPLETED]:
            await self._real_time_learn(event)
    
    async def track_search(
        self,
        user_id: str,
        session_id: str,
        query: str,
        results: List[Dict],
        filters_applied: Dict[str, Any],
        personalization_applied: bool
    ):
        """Track search performed"""
        
        await self.track_event(
            EventType.SEARCH_PERFORMED,
            user_id,
            session_id,
            {
                "query": query,
                "results_count": len(results),
                "result_ids": [r.get("sku") for r in results[:20]],
                "filters": filters_applied,
                "personalized": personalization_applied,
                "top_categories": self._extract_categories(results[:10])
            }
        )
    
    async def track_click(
        self,
        user_id: str,
        session_id: str,
        query: str,
        product: Dict,
        position: int,
        search_session_id: str
    ):
        """Track click on search result"""
        
        await self.track_event(
            EventType.SEARCH_RESULT_CLICKED,
            user_id,
            session_id,
            {
                "query": query,
                "product_sku": product.get("sku"),
                "product_name": product.get("name"),
                "position": position,
                "search_session_id": search_session_id,
                "category": product.get("category"),
                "price": product.get("price"),
                "brand": product.get("supplier")
            }
        )
        
        # Update click-through rate in real-time
        await self._update_ctr(query, position)
    
    async def track_cart_action(
        self,
        user_id: str,
        session_id: str,
        action: str,  # add, remove, update
        product: Dict,
        quantity: int,
        cart_value_after: float
    ):
        """Track cart modifications"""
        
        event_type_map = {
            "add": EventType.CART_ITEM_ADDED,
            "remove": EventType.CART_ITEM_REMOVED,
            "update": EventType.CART_ITEM_UPDATED
        }
        
        await self.track_event(
            event_type_map[action],
            user_id,
            session_id,
            {
                "product_sku": product.get("sku"),
                "product_name": product.get("name"),
                "quantity": quantity,
                "price": product.get("price"),
                "category": product.get("category"),
                "brand": product.get("supplier"),
                "cart_value_after": cart_value_after
            }
        )
    
    async def track_order(
        self,
        user_id: str,
        session_id: str,
        order: Dict
    ):
        """Track completed order"""
        
        await self.track_event(
            EventType.ORDER_COMPLETED,
            user_id,
            session_id,
            {
                "order_id": order.get("id"),
                "total_value": order.get("total"),
                "item_count": len(order.get("items", [])),
                "items": [
                    {
                        "sku": item["sku"],
                        "name": item["name"],
                        "quantity": item["quantity"],
                        "price": item["price"],
                        "category": item["category"]
                    }
                    for item in order.get("items", [])
                ],
                "delivery_date": order.get("delivery_date"),
                "applied_promotions": order.get("promotions", [])
            }
        )
    
    async def _real_time_learn(self, event: Dict):
        """Apply immediate learning from event"""
        
        user_id = event["user_id"]
        session_id = event["session_id"]
        event_type = EventType(event["event_type"])
        data = event["data"]
        
        # Get user context
        context = await self.unified_memory.get_user_context(user_id, session_id)
        
        if event_type == EventType.CART_ITEM_ADDED:
            # Learn product preference
            product_sku = data["product_sku"]
            brand = data["brand"]
            category = data["category"]
            
            # Update Graphiti relationships
            if context.graphiti_instance:
                # Product affinity
                await context.graphiti_instance.add_relationship(
                    user_id,
                    product_sku,
                    "SHOWS_INTEREST",
                    confidence=0.7,
                    metadata={"action": "cart_add", "timestamp": event["timestamp"]}
                )
                
                # Brand affinity
                if brand:
                    await context.graphiti_instance.add_relationship(
                        user_id,
                        brand,
                        "CONSIDERS_BRAND",
                        confidence=0.6
                    )
                
                # Category preference
                await context.graphiti_instance.add_relationship(
                    user_id,
                    category,
                    "BROWSES_CATEGORY",
                    confidence=0.5
                )
        
        elif event_type == EventType.ORDER_COMPLETED:
            # Strongest signals - actual purchases
            for item in data["items"]:
                if context.graphiti_instance:
                    # Strong product preference
                    await context.graphiti_instance.add_relationship(
                        user_id,
                        item["sku"],
                        "REGULARLY_BUYS",
                        confidence=0.9,
                        metadata={
                            "last_purchased": event["timestamp"],
                            "quantity": item["quantity"]
                        }
                    )
                    
                    # Update reorder patterns
                    await self._update_reorder_pattern(user_id, item)
    
    async def _batch_processor(self):
        """Background task to batch process events"""
        
        while True:
            batch = []
            deadline = asyncio.get_event_loop().time() + self.batch_interval
            
            # Collect events for batch
            while len(batch) < self.batch_size:
                timeout = deadline - asyncio.get_event_loop().time()
                if timeout <= 0:
                    break
                    
                try:
                    event = await asyncio.wait_for(
                        self.batch_queue.get(),
                        timeout=timeout
                    )
                    batch.append(event)
                except asyncio.TimeoutError:
                    break
            
            # Process batch
            if batch:
                await self._process_batch(batch)
    
    async def _process_batch(self, events: List[Dict]):
        """Send batch to BigQuery"""
        
        try:
            # Group by event type for efficient insertion
            by_type = {}
            for event in events:
                event_type = event["event_type"]
                if event_type not in by_type:
                    by_type[event_type] = []
                by_type[event_type].append(event)
            
            # Insert each type
            for event_type, type_events in by_type.items():
                table_name = f"user_events.{event_type}"
                await self.bigquery.insert_rows(table_name, type_events)
            
            logger.info(f"Processed batch of {len(events)} events")
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            # Could implement retry logic here

# Global instance
event_tracker = EventTracker()
```

### 2. Pattern Analysis Engine

```python
# src/services/pattern_analysis_service.py
from typing import Dict, List, Tuple, Optional
import pandas as pd
from datetime import datetime, timedelta

class PatternAnalyzer:
    """Analyze user patterns from events"""
    
    def __init__(self):
        self.bigquery = BigQueryClient()
        self.min_confidence = 0.6
    
    async def analyze_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Complete pattern analysis for a user"""
        
        patterns = {
            "purchase_patterns": await self._analyze_purchase_patterns(user_id),
            "brand_preferences": await self._analyze_brand_preferences(user_id),
            "category_preferences": await self._analyze_category_preferences(user_id),
            "price_sensitivity": await self._analyze_price_sensitivity(user_id),
            "shopping_schedule": await self._analyze_shopping_schedule(user_id),
            "dietary_patterns": await self._analyze_dietary_patterns(user_id),
            "complementary_products": await self._analyze_complementary_products(user_id)
        }
        
        return patterns
    
    async def _analyze_purchase_patterns(self, user_id: str) -> Dict[str, Any]:
        """Identify what user regularly buys"""
        
        query = """
        WITH purchase_data AS (
            SELECT 
                product_sku,
                product_name,
                category,
                COUNT(*) as purchase_count,
                AVG(quantity) as avg_quantity,
                ARRAY_AGG(timestamp ORDER BY timestamp) as purchase_dates,
                MAX(timestamp) as last_purchased
            FROM user_events.order_completed,
                UNNEST(data.items) as item
            WHERE user_id = @user_id
                AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 MONTH)
            GROUP BY product_sku, product_name, category
        )
        SELECT *,
            -- Calculate average days between purchases
            CASE 
                WHEN purchase_count > 1 THEN
                    TIMESTAMP_DIFF(last_purchased, purchase_dates[0], DAY) / (purchase_count - 1)
                ELSE 30  -- Default to monthly
            END as avg_days_between
        FROM purchase_data
        WHERE purchase_count >= 2  -- At least 2 purchases to be "regular"
        ORDER BY purchase_count DESC
        """
        
        results = await self.bigquery.query(query, {"user_id": user_id})
        
        patterns = []
        for row in results:
            pattern = {
                "sku": row.product_sku,
                "name": row.product_name,
                "category": row.category,
                "frequency": self._classify_frequency(row.avg_days_between),
                "avg_days_between": row.avg_days_between,
                "usual_quantity": row.avg_quantity,
                "confidence": min(0.9, row.purchase_count / 10),  # Max at 10 purchases
                "last_purchased": row.last_purchased,
                "is_due": self._is_due_for_reorder(row.last_purchased, row.avg_days_between)
            }
            patterns.append(pattern)
        
        return {
            "regular_items": patterns[:20],  # Top 20
            "total_regular_items": len(patterns)
        }
    
    async def _analyze_brand_preferences(self, user_id: str) -> List[Dict]:
        """Identify preferred brands"""
        
        query = """
        WITH brand_interactions AS (
            -- Purchases (strongest signal)
            SELECT 
                item.brand as brand,
                'purchase' as signal_type,
                0.9 as signal_strength,
                COUNT(*) as interaction_count
            FROM user_events.order_completed,
                UNNEST(data.items) as item
            WHERE user_id = @user_id
                AND item.brand IS NOT NULL
            GROUP BY item.brand
            
            UNION ALL
            
            -- Cart adds (medium signal)
            SELECT 
                data.brand as brand,
                'cart_add' as signal_type,
                0.6 as signal_strength,
                COUNT(*) as interaction_count
            FROM user_events.cart_item_added
            WHERE user_id = @user_id
                AND data.brand IS NOT NULL
            GROUP BY data.brand
            
            UNION ALL
            
            -- Clicks (weak signal)
            SELECT 
                data.brand as brand,
                'click' as signal_type,
                0.3 as signal_strength,
                COUNT(*) as interaction_count
            FROM user_events.search_result_clicked
            WHERE user_id = @user_id
                AND data.brand IS NOT NULL
            GROUP BY data.brand
        )
        SELECT 
            brand,
            SUM(interaction_count * signal_strength) as preference_score,
            ARRAY_AGG(STRUCT(
                signal_type,
                interaction_count
            )) as signals
        FROM brand_interactions
        GROUP BY brand
        HAVING preference_score >= 2.0  -- Threshold
        ORDER BY preference_score DESC
        LIMIT 10
        """
        
        results = await self.bigquery.query(query, {"user_id": user_id})
        
        preferences = []
        for row in results:
            preferences.append({
                "brand": row.brand,
                "preference_score": row.preference_score,
                "confidence": min(0.9, row.preference_score / 10),
                "signals": row.signals
            })
        
        return preferences
    
    async def _analyze_complementary_products(self, user_id: str) -> List[Dict]:
        """Find products often bought together"""
        
        query = """
        WITH user_baskets AS (
            SELECT 
                order_id,
                ARRAY_AGG(STRUCT(
                    item.sku as sku,
                    item.name as name,
                    item.category as category
                )) as basket
            FROM user_events.order_completed,
                UNNEST(data.items) as item
            WHERE user_id = @user_id
            GROUP BY order_id
        ),
        product_pairs AS (
            SELECT 
                p1.sku as product1_sku,
                p1.name as product1_name,
                p2.sku as product2_sku,
                p2.name as product2_name,
                COUNT(*) as times_bought_together
            FROM user_baskets,
                UNNEST(basket) as p1,
                UNNEST(basket) as p2
            WHERE p1.sku < p2.sku  -- Avoid duplicates
            GROUP BY p1.sku, p1.name, p2.sku, p2.name
            HAVING times_bought_together >= 2
        )
        SELECT *,
            times_bought_together / (
                SELECT COUNT(DISTINCT order_id) 
                FROM user_events.order_completed 
                WHERE user_id = @user_id
            ) as support
        FROM product_pairs
        ORDER BY times_bought_together DESC
        LIMIT 20
        """
        
        results = await self.bigquery.query(query, {"user_id": user_id})
        
        pairs = []
        for row in results:
            pairs.append({
                "product1": {"sku": row.product1_sku, "name": row.product1_name},
                "product2": {"sku": row.product2_sku, "name": row.product2_name},
                "frequency": row.times_bought_together,
                "confidence": row.support
            })
        
        return pairs
    
    def _classify_frequency(self, days: float) -> str:
        """Classify purchase frequency"""
        if days <= 7:
            return "weekly"
        elif days <= 14:
            return "bi-weekly"
        elif days <= 30:
            return "monthly"
        elif days <= 90:
            return "quarterly"
        else:
            return "occasional"
    
    def _is_due_for_reorder(self, last_purchased: datetime, avg_days: float) -> bool:
        """Check if item is due for reorder"""
        days_since = (datetime.now() - last_purchased).days
        return days_since >= avg_days * 0.9  # 90% of average

# Global instance
pattern_analyzer = PatternAnalyzer()
```

### 3. Learning Orchestrator

```python
# src/services/learning_orchestrator.py
class LearningOrchestrator:
    """Orchestrate the complete learning loop"""
    
    def __init__(self):
        self.event_tracker = event_tracker
        self.pattern_analyzer = pattern_analyzer
        self.unified_memory = unified_memory
        self.update_interval = 300  # 5 minutes for real-time
        self.batch_interval = 3600  # 1 hour for batch
    
    async def start(self):
        """Start learning loops"""
        # Real-time learning loop
        asyncio.create_task(self._real_time_loop())
        
        # Batch learning loop
        asyncio.create_task(self._batch_loop())
        
        logger.info("Learning loops started")
    
    async def _real_time_loop(self):
        """Process recent events in near real-time"""
        
        while True:
            try:
                # Get users with recent activity
                active_users = await self._get_recently_active_users()
                
                for user_id in active_users:
                    try:
                        # Quick pattern updates
                        await self._update_user_patterns_quick(user_id)
                    except Exception as e:
                        logger.error(f"Real-time update failed for {user_id}: {e}")
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Real-time loop error: {e}")
                await asyncio.sleep(60)  # Back off on error
    
    async def _batch_loop(self):
        """Deep pattern analysis in batches"""
        
        while True:
            try:
                # Get all users needing updates
                users_to_update = await self._get_users_for_batch_update()
                
                for user_id in users_to_update:
                    try:
                        # Full pattern analysis
                        patterns = await self.pattern_analyzer.analyze_user_patterns(user_id)
                        
                        # Update memory systems
                        await self._update_all_memory_systems(user_id, patterns)
                        
                    except Exception as e:
                        logger.error(f"Batch update failed for {user_id}: {e}")
                
                await asyncio.sleep(self.batch_interval)
                
            except Exception as e:
                logger.error(f"Batch loop error: {e}")
                await asyncio.sleep(300)  # Back off on error
    
    async def _update_user_patterns_quick(self, user_id: str):
        """Quick updates based on recent actions"""
        
        # Get last 10 events
        query = """
        SELECT event_type, data
        FROM user_events.all_events
        WHERE user_id = @user_id
            AND timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
        ORDER BY timestamp DESC
        LIMIT 10
        """
        
        events = await self.bigquery.query(query, {"user_id": user_id})
        
        # Extract quick signals
        clicked_brands = set()
        added_categories = set()
        
        for event in events:
            if event.event_type == "search_result_clicked":
                if brand := event.data.get("brand"):
                    clicked_brands.add(brand)
            elif event.event_type == "cart_item_added":
                if category := event.data.get("category"):
                    added_categories.add(category)
        
        # Update context if patterns found
        if clicked_brands or added_categories:
            context = await self.unified_memory.get_user_context(user_id, "")
            
            # Update preferences
            updates = {}
            if clicked_brands:
                updates["recent_brand_interests"] = list(clicked_brands)
            if added_categories:
                updates["recent_category_interests"] = list(added_categories)
            
            await self.unified_memory.update_context(user_id, "", updates)
    
    async def _update_all_memory_systems(self, user_id: str, patterns: Dict):
        """Update all memory systems with learned patterns"""
        
        # Update Graphiti with relationships
        await self._update_graphiti_patterns(user_id, patterns)
        
        # Update user preferences
        await self._update_user_preferences(user_id, patterns)
        
        # Cache computed patterns
        await self._cache_patterns(user_id, patterns)
    
    async def _update_graphiti_patterns(self, user_id: str, patterns: Dict):
        """Update Graphiti with learned relationships"""
        
        try:
            graphiti = GraphitiMemorySpanner(user_id, "system")
            await graphiti.initialize()
            
            # Regular purchase patterns
            for item in patterns["purchase_patterns"]["regular_items"]:
                await graphiti.add_entity(
                    f"pattern_{user_id}_{item['sku']}",
                    "PURCHASE_PATTERN",
                    {
                        "sku": item["sku"],
                        "frequency": item["frequency"],
                        "usual_quantity": item["usual_quantity"],
                        "confidence": item["confidence"]
                    }
                )
                
                await graphiti.add_relationship(
                    user_id,
                    item["sku"],
                    "HAS_PATTERN",
                    confidence=item["confidence"]
                )
            
            # Brand preferences
            for brand_pref in patterns["brand_preferences"]:
                await graphiti.add_relationship(
                    user_id,
                    brand_pref["brand"],
                    "PREFERS_BRAND",
                    confidence=brand_pref["confidence"]
                )
            
            # Complementary products
            for pair in patterns["complementary_products"]:
                await graphiti.add_relationship(
                    pair["product1"]["sku"],
                    pair["product2"]["sku"],
                    "BOUGHT_WITH",
                    confidence=pair["confidence"],
                    metadata={"user_specific": user_id}
                )
                
        except Exception as e:
            logger.error(f"Graphiti update failed: {e}")

# Global orchestrator
learning_orchestrator = LearningOrchestrator()
```

### 4. Integration Points

#### Frontend - Click Tracking

```typescript
// frontend/src/hooks/useAnalytics.ts
export const useAnalytics = () => {
  const trackProductClick = async (
    product: Product,
    position: number,
    query: string,
    searchSessionId: string
  ) => {
    try {
      await api.post('/api/v1/events/click', {
        query,
        product,
        position,
        search_session_id: searchSessionId
      });
    } catch (error) {
      console.error('Failed to track click:', error);
    }
  };
  
  const trackAddToCart = async (
    product: Product,
    quantity: number
  ) => {
    try {
      await api.post('/api/v1/events/cart-add', {
        product,
        quantity
      });
    } catch (error) {
      console.error('Failed to track cart add:', error);
    }
  };
  
  return {
    trackProductClick,
    trackAddToCart
  };
};

// In ProductCard component
const ProductCard: React.FC<ProductCardProps> = ({ product, position, query }) => {
  const { trackProductClick } = useAnalytics();
  
  const handleClick = () => {
    trackProductClick(product, position, query, searchSessionId);
    // Navigate to product details
  };
  
  return (
    <div onClick={handleClick} className="cursor-pointer">
      {/* Product display */}
    </div>
  );
};
```

#### API - Event Endpoints

```python
# src/api/event_endpoints.py
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/events")

class ClickEvent(BaseModel):
    query: str
    product: Dict[str, Any]
    position: int
    search_session_id: str

@router.post("/click")
async def track_click(event: ClickEvent, request: Request):
    """Track product click"""
    
    user_id = request.state.user_id
    session_id = request.state.session_id
    
    await event_tracker.track_click(
        user_id=user_id,
        session_id=session_id,
        query=event.query,
        product=event.product,
        position=event.position,
        search_session_id=event.search_session_id
    )
    
    return {"success": True}

@router.post("/cart-add")
async def track_cart_add(event: CartAddEvent, request: Request):
    """Track add to cart"""
    
    user_id = request.state.user_id
    session_id = request.state.session_id
    
    # Get current cart value
    cart = await session_memory.get_current_order(session_id)
    cart_value = sum(item["price"] * item["quantity"] 
                    for item in cart.get("items", []))
    
    await event_tracker.track_cart_action(
        user_id=user_id,
        session_id=session_id,
        action="add",
        product=event.product,
        quantity=event.quantity,
        cart_value_after=cart_value + (event.product["price"] * event.quantity)
    )
    
    return {"success": True}

@router.get("/learning-status/{user_id}")
async def get_learning_status(user_id: str):
    """Get learning status for a user"""
    
    # Get recent patterns
    patterns = await pattern_analyzer.analyze_user_patterns(user_id)
    
    return {
        "user_id": user_id,
        "regular_items_count": len(patterns["purchase_patterns"]["regular_items"]),
        "preferred_brands": [b["brand"] for b in patterns["brand_preferences"][:5]],
        "learning_confidence": _calculate_overall_confidence(patterns),
        "last_updated": datetime.utcnow().isoformat()
    }
```

#### Search Integration

```python
# In src/agents/product_search.py
async def _run(self, state: SearchState) -> SearchState:
    """Enhanced search with event tracking"""
    
    # Generate search session ID
    search_session_id = str(uuid.uuid4())
    state["search_session_id"] = search_session_id
    
    # Perform search
    products = await self.search_tool.run(
        query=state["query"],
        limit=50,
        alpha=state.get("alpha_value", 0.5)
    )
    
    # Apply personalization
    memory_context = state.get("memory_context")
    personalization_applied = False
    
    if memory_context and products:
        products = await self._apply_personalization(
            products, memory_context, state["query"]
        )
        personalization_applied = True
    
    # Track search event
    if state.get("user_id"):
        await event_tracker.track_search(
            user_id=state["user_id"],
            session_id=state["session_id"],
            query=state["query"],
            results=products[:20],
            filters_applied=state.get("filters", {}),
            personalization_applied=personalization_applied
        )
    
    state["search_results"] = products[:15]
    return state
```

## 📋 Implementation Plan

### Phase 1: Event Infrastructure (3 hours)
1. [ ] Create event tracking service
2. [ ] Set up BigQuery tables
3. [ ] Add event endpoints to API
4. [ ] Implement frontend tracking hooks

### Phase 2: Real-time Learning (2 hours)
1. [ ] Implement real-time event processing
2. [ ] Add immediate preference updates
3. [ ] Create Graphiti relationship updates
4. [ ] Test with sample events

### Phase 3: Batch Analysis (3 hours)
1. [ ] Create pattern analyzer
2. [ ] Implement batch SQL queries
3. [ ] Build learning orchestrator
4. [ ] Schedule batch jobs

### Phase 4: Integration (2 hours)
1. [ ] Wire tracking into all agents
2. [ ] Connect learning to memory service
3. [ ] Add monitoring/metrics
4. [ ] Create admin dashboard

## 🎯 Success Metrics

### Event Tracking
- **Coverage**: >95% of user actions tracked
- **Latency**: <100ms for event logging
- **Reliability**: <0.1% event loss

### Learning Effectiveness
- **CTR Improvement**: +20% after 1 week
- **Reorder Accuracy**: >80% for regular items
- **Brand Preference**: >70% accuracy

### System Performance
- **Real-time Updates**: <5 minute lag
- **Batch Processing**: <1 hour for all users
- **Memory Updates**: <50ms propagation

## 🚨 Privacy & Control

### User Controls

```python
# src/models/user_privacy_settings.py
class PrivacySettings(BaseModel):
    track_searches: bool = True
    track_clicks: bool = True
    track_purchases: bool = True
    learn_preferences: bool = True
    share_patterns: bool = False  # For collaborative filtering
    retention_days: int = 365
    
    # Granular controls
    learn_dietary: bool = True
    learn_brands: bool = True
    learn_price: bool = True
    learn_schedule: bool = True

# Check before tracking
async def should_track_event(
    user_id: str,
    event_type: EventType
) -> bool:
    settings = await get_user_privacy_settings(user_id)
    
    if event_type == EventType.SEARCH_PERFORMED:
        return settings.track_searches
    elif event_type == EventType.SEARCH_RESULT_CLICKED:
        return settings.track_clicks
    elif event_type == EventType.ORDER_COMPLETED:
        return settings.track_purchases
    
    return True  # Default allow
```

### Data Deletion

```python
@router.delete("/api/v1/user/{user_id}/learning-data")
async def delete_user_learning_data(user_id: str):
    """Complete data deletion for GDPR"""
    
    # Delete from BigQuery
    await bigquery.delete_user_events(user_id)
    
    # Delete from Graphiti
    graphiti = GraphitiMemorySpanner(user_id, "system")
    await graphiti.delete_all_user_data()
    
    # Clear caches
    await unified_memory.clear_user_cache(user_id)
    
    return {"success": True, "message": "All learning data deleted"}
```

## 🔄 Feedback Loop Metrics

```python
# src/metrics/learning_metrics.py
class LearningMetrics:
    def __init__(self):
        self.prometheus = PrometheusClient()
    
    async def track_learning_effectiveness(self):
        """Measure how well learning improves results"""
        
        metrics = {
            # Click-through rate by personalization
            "ctr_personalized": await self._calculate_ctr(personalized=True),
            "ctr_not_personalized": await self._calculate_ctr(personalized=False),
            
            # Reorder prediction accuracy
            "reorder_precision": await self._calculate_reorder_precision(),
            "reorder_recall": await self._calculate_reorder_recall(),
            
            # User satisfaction
            "cart_abandonment_rate": await self._calculate_abandonment_rate(),
            "avg_cart_value_change": await self._calculate_cart_value_trend()
        }
        
        # Push to monitoring
        for metric, value in metrics.items():
            self.prometheus.gauge(f"learning_{metric}", value)
        
        return metrics
```

The learning loop transforms the system from static search to dynamic personalization that improves with every interaction.