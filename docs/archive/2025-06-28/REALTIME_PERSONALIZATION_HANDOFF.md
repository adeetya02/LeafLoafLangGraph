# Real-Time Personalization Implementation Handoff

## Critical Context
You are continuing work on LeafLoaf after a failed demo. The generic flow wasn't appreciated by stakeholders, especially after talking up the AI/personalization capabilities. We need a production-grade personalization system in 2 days (not 4 weeks).

## User's Frustration (Direct Quotes)
- "yesterday was not good. i had a demo with a few folks and u got me a generic flow which was not appreciated"
- "sorry, i met a few folks yesterday.. they wer not happy"
- "yes, epecially when we have talked this up so much"
- "i dont have 4 weeks.. i have 2 days"
- "stakes are high now"

## Architecture Decided
```
User Action → Real-Time Processing → Instant UI Update (<10ms)
     ↓              ↓                          ↑
     └──→ BigQuery (Raw Events) ──→ ML Pipeline (Batch)
```

## Key Technical Decisions
1. **Real-time feedback loop**: User gets response in <10ms
2. **Fire-and-forget to BigQuery**: Analytics without blocking
3. **In-memory preference cache**: Instant personalization
4. **Configurable rules**: YAML-based for easy tuning
5. **React + Tailwind UI**: NOT HTML (user was specific)
6. **Cloud SQL**: For session/cart persistence across servers

## Implementation Plan (48 Hours)

### Hour 0-8: Backend Core
```bash
# 1. Create BigQuery schema
cd /Users/adi/Desktop/LeafLoafLangGraph
cat > bigquery_schema.json << 'EOF'
[
  {
    "name": "event_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "event_timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  },
  {
    "name": "event_type",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "user_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "session_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "product_id",
    "type": "STRING",
    "mode": "NULLABLE"
  },
  {
    "name": "interaction_strength",
    "type": "FLOAT64",
    "mode": "NULLABLE"
  },
  {
    "name": "raw_event_data",
    "type": "JSON",
    "mode": "NULLABLE"
  }
]
EOF

# Create dataset and table
bq mk --dataset --location=US leafloafai:leafloaf_events
bq mk --table leafloafai:leafloaf_events.raw_user_actions ./bigquery_schema.json
```

### 2. Create Event Streamer
Create `src/analytics/event_streamer.py`:
```python
import asyncio
from google.cloud import bigquery
from datetime import datetime
import uuid
import json

class EventStreamer:
    def __init__(self):
        self.client = bigquery.Client(project="leafloafai")
        self.table_id = "leafloafai.leafloaf_events.raw_user_actions"
        self.batch = []
        self.batch_size = 100
        self._background_task = None
        
    async def stream_event(self, event_type: str, user_id: str, data: dict):
        """Fire-and-forget event streaming - NEVER blocks user"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "session_id": data.get("session_id", "default"),
            "product_id": data.get("product_id"),
            "interaction_strength": self._calculate_strength(event_type),
            "raw_event_data": json.dumps(data)
        }
        
        # Add to batch (non-blocking)
        self.batch.append(event)
        
        # Start background flush if not running
        if not self._background_task:
            self._background_task = asyncio.create_task(self._flush_loop())
            
    def _calculate_strength(self, event_type: str) -> float:
        """Calculate signal strength based on event type"""
        strengths = {
            "purchase": 1.0,
            "add_to_cart": 0.5,
            "click_product": 0.2,
            "search": 0.1,
            "displayed_but_scrolled": -0.05
        }
        return strengths.get(event_type, 0.1)
        
    async def _flush_loop(self):
        """Background task to flush events to BigQuery"""
        while True:
            await asyncio.sleep(1)  # Flush every second
            if self.batch:
                await self._flush_batch()
                
    async def _flush_batch(self):
        """Flush current batch to BigQuery"""
        if not self.batch:
            return
            
        # Copy and clear batch
        to_insert = self.batch[:self.batch_size]
        self.batch = self.batch[self.batch_size:]
        
        # Insert asynchronously (fire-and-forget)
        try:
            errors = self.client.insert_rows_json(self.table_id, to_insert)
            if errors:
                print(f"BigQuery insert errors: {errors}")
        except Exception as e:
            print(f"BigQuery streaming failed: {e}")
            # Don't retry - this is fire-and-forget
```

### 3. Real-Time Preference Engine
Create `src/personalization/realtime_engine.py`:
```python
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime, timedelta

class RealtimePreferenceEngine:
    def __init__(self):
        # In-memory cache for instant updates
        self.user_preferences = {}
        self.signal_weights = {
            "purchase": {"first_time": 0.8, "repeat": 1.0},
            "cart": {"add_to_cart": 0.5, "remove_from_cart": -0.4},
            "browse": {"click_product": 0.2, "displayed_but_scrolled": -0.05}
        }
        
    async def process_interaction(
        self, 
        user_id: str, 
        interaction_type: str,
        product_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process interaction and update preferences in <5ms"""
        start = datetime.now()
        
        # Get or create user preferences
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                "categories": {},
                "brands": {},
                "attributes": {},
                "last_updated": datetime.now()
            }
            
        prefs = self.user_preferences[user_id]
        
        # Update preferences based on interaction
        weight = self._get_signal_weight(interaction_type)
        
        # Update category preference
        category = product_data.get("category", "")
        if category:
            current = prefs["categories"].get(category, 0)
            prefs["categories"][category] = min(1.0, current + weight * 0.1)
            
        # Update brand preference
        brand = product_data.get("brand", "")
        if brand:
            current = prefs["brands"].get(brand, 0)
            prefs["brands"][brand] = min(1.0, current + weight * 0.15)
            
        # Update attribute preferences
        if product_data.get("is_organic"):
            current = prefs["attributes"].get("organic", 0)
            prefs["attributes"]["organic"] = min(1.0, current + weight * 0.05)
            
        prefs["last_updated"] = datetime.now()
        
        # Calculate response time
        elapsed = (datetime.now() - start).total_seconds() * 1000
        
        return {
            "preferences_updated": True,
            "response_time_ms": elapsed,
            "current_preferences": prefs
        }
        
    def _get_signal_weight(self, interaction_type: str) -> float:
        """Get weight for interaction type from config"""
        if interaction_type == "purchase":
            return 1.0
        elif interaction_type == "add_to_cart":
            return 0.5
        elif interaction_type == "click_product":
            return 0.2
        elif interaction_type == "displayed_but_scrolled":
            return -0.05
        return 0.1
        
    async def get_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get current preferences for user"""
        return self.user_preferences.get(user_id, {
            "categories": {},
            "brands": {},
            "attributes": {}
        })
```

### 4. API Endpoints
Update `src/api/main.py`:
```python
# Add these endpoints

@app.post("/api/interactions/track")
async def track_interaction(
    event_type: str,
    user_id: str,
    product_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
):
    """Track user interaction - returns instantly"""
    # Update preferences in memory (< 5ms)
    if product_id:
        product = await get_product_data(product_id)
        prefs = await realtime_engine.process_interaction(
            user_id, event_type, product
        )
    
    # Stream to BigQuery (fire-and-forget)
    asyncio.create_task(
        event_streamer.stream_event(event_type, user_id, {
            "product_id": product_id,
            "context": context
        })
    )
    
    return {"status": "tracked", "response_time_ms": prefs.get("response_time_ms", 0)}

@app.post("/api/search/personalized")
async def personalized_search(
    query: str,
    user_id: str,
    limit: int = 10
):
    """Real-time personalized search"""
    # Get user preferences (instant from memory)
    preferences = await realtime_engine.get_preferences(user_id)
    
    # Search with personalization
    results = await search_products(query, limit=limit)
    
    # Rerank based on preferences
    personalized_results = await personalized_ranker.rerank_products(
        results,
        user_preferences=preferences,
        user_id=user_id
    )
    
    return {
        "results": personalized_results,
        "personalization_applied": True,
        "user_id": user_id
    }
```

## Performance Fixes

### Weaviate Optimization (699ms → <300ms)
1. **Reduce result limit**: 30 → 10 products
2. **Connection pooling**: Already implemented
3. **Pre-warm connections**: On startup
4. **Cache common queries**: Redis with 5min TTL

```python
# In product_search.py
async def search_products(query: str, limit: int = 10):  # Changed from 30
    # Check cache first
    cache_key = f"search:{query}:{limit}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Search Weaviate
    results = await weaviate_search(query, limit=limit)
    
    # Cache for 5 minutes
    await redis.setex(cache_key, 300, json.dumps(results))
    
    return results
```

## UI Development (Day 2)

### React + Tailwind Setup
```bash
npx create-next-app@latest leafloaf-ui --typescript --tailwind --app
cd leafloaf-ui

# Install additional dependencies
npm install zustand react-query axios framer-motion
npm install -D @types/node
```

### Key Components
1. **SearchBar**: Instant search with personalization indicators
2. **ProductCard**: Shows "Your usual" badge, personalization score
3. **PersonalizationIndicator**: Visual feedback when learning
4. **QuantitySelector**: Pre-filled with usual quantities

## Testing Scenarios

### 1. Instant Learning Demo
```python
# User searches "milk"
# Clicks "Oat Milk" 
# Next search for "yogurt" shows plant-based first
# Total time: <2 seconds
```

### 2. Negative Signal Demo
```python
# Show spicy chips in results
# User scrolls past without clicking
# Next snack search deprioritizes spicy
```

### 3. Bulk Pattern Demo
```python
# User adds 2 gallons of milk to cart
# Next time, quantity defaults to 2
# System learns bulk buying preference
```

## Deployment Commands

```bash
# Deploy backend
gcloud builds submit --config cloudbuild-enhanced.yaml

# Deploy with personalization enabled
gcloud run deploy leafloaf \
  --image gcr.io/leafloafai/leafloaf \
  --set-env-vars ENABLE_PERSONALIZATION=true \
  --set-env-vars BIGQUERY_DATASET=leafloaf_events

# Check logs
gcloud run logs read --service=leafloaf --limit=50
```

## Critical Success Factors
1. **Response time <10ms**: User doesn't wait
2. **Visual feedback**: Show when personalization is applied
3. **Configurable rules**: Can tune without code changes
4. **Works on first click**: Instant gratification
5. **Production-grade**: No shortcuts or hacks

## Remember
- User had a bad demo and stakeholders weren't happy
- We oversold the AI capabilities, now must deliver
- 2 days only - no time for perfect, need working
- Backend first, then UI
- Real personalization that actually works