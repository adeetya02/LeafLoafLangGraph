# Real-time Personalization Demo Guide

## 🎯 Demo Overview

This demo showcases LeafLoaf's instant personalization capabilities, demonstrating how the system learns from user interactions in real-time and adapts search results within seconds.

## 🚀 Quick Start

### 1. Start the Server
```bash
# Make sure you're in the project directory
cd /Users/adi/Desktop/LeafLoafLangGraph

# Start the API server
PORT=8000 python3 run.py
```

### 2. Open the Demo UI
```bash
# Open in browser
open demo_realtime_personalization.html
```

## 📋 Demo Script

### Part 1: Baseline Experience (30 seconds)
1. **Initial Search**: The demo starts with "milk" pre-filled
   - Point out: "Notice these are generic results - no personalization yet"
   - Show the metrics: 0 interactions, 0% personalization strength

2. **Show Categories**: 
   - "We're getting milk products but also some irrelevant items"
   - Note the mix of Dairy and other categories

### Part 2: Instant Learning (1 minute)
1. **First Click**: Click on "Organic 2% Milk"
   - "Watch what happens when I click this organic milk"
   - Point to the activity log: "System tracked my click"
   - Wait 1 second for auto-refresh
   - "Notice how organic products now have the 'For You' badge!"

2. **Build Preferences**: Click 2-3 more organic/dairy items
   - Show the preferences sidebar building up
   - "The system is learning I prefer organic dairy products"
   - Point to metrics: "Personalization strength increasing"

3. **Demonstrate Reranking**:
   - "Notice how my preferred products are moving to the top"
   - "Products matching my preferences are highlighted"

### Part 3: Cross-Category Intelligence (30 seconds)
1. **New Search**: Search for "yogurt"
   - "Let's search for something different"
   - "Look! It already knows I prefer organic dairy"
   - "My preferred brands appear first"

2. **Search for "bread"**:
   - "Even in a different category, it remembers my organic preference"

### Part 4: Strong Signals (30 seconds)
1. **Add to Cart**: Add a few items to cart
   - "Adding to cart is a strong signal"
   - Show how preference scores jump
   - Cart slides out showing items

2. **Reset Demo**: Click "Reset Preferences"
   - "We can start fresh for the next person"
   - Everything resets to baseline

## 🔍 Key Points to Emphasize

1. **Speed**: "Updates happen in under 300ms"
2. **No Login Required**: "Works even for anonymous users"
3. **Privacy First**: "Users control their data with granular preferences"
4. **Category Filtering**: "Notice how produce items are filtered from dairy searches"
5. **Multi-signal Learning**: "Clicks, views, and cart additions have different weights"

## 📊 Metrics to Highlight

- **Response Time**: Always under 350ms (our target)
- **Personalization Strength**: Grows with each interaction
- **Products Personalized**: Shows how many items match preferences
- **User Interactions**: Total engagement count

## 🎨 Visual Features

1. **Green Borders**: Products matching preferences
2. **"For You" Badges**: Personalized recommendations
3. **Preference Scores**: Real-time percentage updates
4. **Activity Icons**: 
   - 👆 Click
   - 👁️ View
   - 🛒 Add to Cart
   - ✅ Purchase

## ⚡ Technical Highlights for Engineers

- **In-memory Personalization**: Instant updates without database calls
- **Parallel Scoring**: Products scored concurrently for speed
- **Category Filtering**: Removes irrelevant items (produce from dairy)
- **Configurable Weights**: Different actions have different impacts
- **Thread-safe Design**: Handles concurrent users

## 🔧 Troubleshooting

**Search fails?**
- Check server is running on port 8000
- Verify Weaviate connection in logs

**No personalization?**
- Ensure tracking endpoint is working
- Check browser console for errors

**Slow responses?**
- Check Weaviate performance
- Verify no blocking operations

## 📱 Mobile Demo

The UI is responsive and works on tablets/phones:
- Touch-friendly buttons
- Responsive grid layout
- Slide-out cart works with swipe

---

# 🗄️ Data Flow Architecture

## 1. Graphiti Memory Integration

### Current State
- **Location**: Agent-level integration (not API-level)
- **Supervisor Agent**: Creates Graphiti instance, extracts entities
- **Order Agent**: Uses Graphiti for reorder patterns
- **Backend**: Google Cloud Spanner for production-grade GraphRAG

### Data Flow
```
User Interaction
    ↓
API Endpoint (/api/personalization/track)
    ↓
Instant Personalization Engine (In-memory)
    ↓
Background Task → Graphiti Memory
    ↓
Spanner Graph Database
```

### What Gets Stored in Graphiti/Spanner

1. **User Entities**:
   ```json
   {
     "entity_type": "user",
     "entity_id": "demo_user_123",
     "attributes": {
       "preferred_categories": ["Dairy", "Organic"],
       "dietary_restrictions": ["lactose_intolerant"],
       "household_size": 4
     }
   }
   ```

2. **Product Relationships**:
   ```json
   {
     "source": "user:demo_user_123",
     "target": "product:organic_milk",
     "relationship": "frequently_purchases",
     "weight": 0.8,
     "last_interaction": "2025-06-28T10:30:00Z"
   }
   ```

3. **Temporal Patterns**:
   ```json
   {
     "pattern_type": "reorder_cycle",
     "product": "milk",
     "frequency_days": 7,
     "confidence": 0.85
   }
   ```

### Spanner Schema
```sql
-- Entities table
CREATE TABLE entities (
  entity_id STRING(64) NOT NULL,
  entity_type STRING(32) NOT NULL,
  attributes JSON,
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL,
) PRIMARY KEY (entity_id);

-- Relationships table  
CREATE TABLE relationships (
  relationship_id STRING(64) NOT NULL,
  source_id STRING(64) NOT NULL,
  target_id STRING(64) NOT NULL,
  relationship_type STRING(32) NOT NULL,
  weight FLOAT64,
  metadata JSON,
  created_at TIMESTAMP NOT NULL,
) PRIMARY KEY (relationship_id);

-- Indexes for fast lookups
CREATE INDEX idx_source ON relationships(source_id);
CREATE INDEX idx_target ON relationships(target_id);
```

## 2. BigQuery Analytics Pipeline

### Tables and Data Flow

#### Raw Events Layer
```sql
-- 1. user_search_events
INSERT INTO `leafloaf_analytics.raw_events.user_search_events` (
  event_id,
  user_id,
  session_id,
  query,
  intent,
  alpha_value,
  results_count,
  categories,
  response_time_ms,
  timestamp
) VALUES (
  'evt_123',
  'demo_user_123',
  'session_456',
  'organic milk',
  'product_search',
  0.5,
  15,
  ['Dairy', 'Beverages'],
  287,
  CURRENT_TIMESTAMP()
);

-- 2. product_interaction_events  
INSERT INTO `leafloaf_analytics.raw_events.product_interaction_events` (
  event_id,
  user_id,
  session_id,
  product_sku,
  product_name,
  category,
  interaction_type,  -- 'click', 'view', 'add_to_cart'
  interaction_weight,
  position_in_results,
  timestamp
) VALUES (
  'evt_124',
  'demo_user_123',
  'session_456',
  'MILK_ORG_2PCT',
  'Organic 2% Milk',
  'Dairy',
  'click',
  0.2,
  1,
  CURRENT_TIMESTAMP()
);

-- 3. cart_modification_events
INSERT INTO `leafloaf_analytics.raw_events.cart_modification_events` (
  event_id,
  user_id,
  session_id,
  product_sku,
  action,  -- 'add', 'remove', 'update_quantity'
  quantity,
  price,
  timestamp
) VALUES (
  'evt_125',
  'demo_user_123',
  'session_456',
  'MILK_ORG_2PCT',
  'add',
  2,
  4.99,
  CURRENT_TIMESTAMP()
);
```

#### Derived Tables (Materialized Views)
```sql
-- User purchase patterns (refreshed hourly)
CREATE OR REPLACE VIEW `leafloaf_analytics.user_behavior.user_purchase_patterns` AS
SELECT 
  user_id,
  category,
  COUNT(DISTINCT product_sku) as unique_products,
  COUNT(*) as total_interactions,
  SUM(CASE WHEN interaction_type = 'add_to_cart' THEN 1 ELSE 0 END) as cart_adds,
  AVG(interaction_weight) as avg_preference_score,
  MAX(timestamp) as last_interaction
FROM `leafloaf_analytics.raw_events.product_interaction_events`
GROUP BY user_id, category;

-- Product associations (for recommendations)
CREATE OR REPLACE VIEW `leafloaf_analytics.product_intelligence.product_associations` AS
WITH product_pairs AS (
  SELECT 
    a.product_sku as product_a,
    b.product_sku as product_b,
    COUNT(DISTINCT a.session_id) as co_occurrence_count
  FROM `leafloaf_analytics.raw_events.cart_modification_events` a
  JOIN `leafloaf_analytics.raw_events.cart_modification_events` b
    ON a.session_id = b.session_id 
    AND a.product_sku < b.product_sku
    AND a.action = 'add' 
    AND b.action = 'add'
  GROUP BY 1, 2
)
SELECT * FROM product_pairs WHERE co_occurrence_count > 5;
```

### Analytics Service Integration

The system writes to BigQuery through the Analytics Service:

```python
# In src/services/analytics_service.py
async def track_search_event(self, event_data: Dict[str, Any]):
    """Track search event to BigQuery"""
    # Stream insert for real-time analytics
    rows = [{
        'event_id': generate_event_id(),
        'user_id': event_data.get('user_id'),
        'session_id': event_data.get('session_id'),
        'query': event_data.get('query'),
        'intent': event_data.get('intent'),
        'alpha_value': event_data.get('alpha'),
        'results_count': event_data.get('results_count'),
        'categories': event_data.get('categories', []),
        'response_time_ms': int(event_data.get('response_time_ms', 0)),
        'timestamp': datetime.utcnow().isoformat()
    }]
    
    # Non-blocking stream insert
    asyncio.create_task(
        self._stream_insert('user_search_events', rows)
    )
```

### Data Pipeline Flow

```
User Action (Click/Search/Cart)
    ↓
API Endpoint
    ↓
Three Parallel Writes:
    ├─→ Instant Personalization (In-memory) - <10ms
    ├─→ Graphiti/Spanner (Background) - ~100ms  
    └─→ BigQuery Streaming (Background) - ~200ms
    
Response to User - <300ms total
```

### BigQuery Usage Patterns

1. **Real-time Dashboards**: 
   - Search volume by category
   - Popular products by time of day
   - User engagement metrics

2. **ML Feature Store**:
   - User embedding generation
   - Product popularity scores
   - Seasonal trend detection

3. **Business Intelligence**:
   - Conversion funnel analysis
   - Cart abandonment patterns
   - Category performance metrics

4. **Personalization Feedback Loop**:
   ```sql
   -- Daily job to update user preferences
   INSERT INTO `leafloaf_analytics.ml_features.user_preference_scores`
   SELECT 
     user_id,
     category,
     SUM(interaction_weight * POWER(0.95, DATE_DIFF(CURRENT_DATE(), DATE(timestamp), DAY))) as decayed_score
   FROM `leafloaf_analytics.raw_events.product_interaction_events`
   WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
   GROUP BY user_id, category
   HAVING decayed_score > 0.1;
   ```

## 🔄 Complete Data Flow

1. **User clicks "Organic 2% Milk"**

2. **Frontend** → POST /api/personalization/track

3. **API Layer**:
   - Updates instant personalization (in-memory)
   - Returns success immediately

4. **Background Tasks** (parallel):
   - **Graphiti**: Creates/updates user→product relationship
   - **Spanner**: Persists to graph database
   - **BigQuery**: Streams interaction event

5. **Next Search**:
   - Instant personalization applied from memory
   - Graphiti context fetched for deep insights
   - Results personalized in <300ms

6. **Offline Processing**:
   - BigQuery aggregates patterns nightly
   - ML models retrained weekly
   - Insights fed back to Graphiti

This architecture ensures:
- **Instant feedback**: <300ms response times
- **Durable memory**: Spanner for long-term patterns  
- **Analytics scale**: BigQuery for massive data processing
- **Privacy first**: User controls all data