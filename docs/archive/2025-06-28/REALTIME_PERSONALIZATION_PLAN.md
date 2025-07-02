# Real-Time Personalization Implementation Plan

## Overview
Production-grade real-time personalization system with instant feedback loop and BigQuery analytics pipeline.

## Architecture

```
User Action → Real-Time Processing → Instant UI Update (<10ms)
     ↓              ↓                          ↑
     └──→ BigQuery (Raw Events) ──→ ML Pipeline (Batch)
```

## 1. Core Components

### 1.1 Real-Time Feedback Loop
- **In-memory preference cache**: <5ms updates
- **Graphiti async updates**: 50ms (non-blocking)
- **BigQuery streaming**: 100ms (fire-and-forget)
- **User wait time**: <10ms total

### 1.2 Signal Weights (Configurable)
```yaml
# config/personalization_rules.yaml
signal_weights:
  purchase:
    first_time: 0.8
    repeat: 1.0
    bulk_purchase: 1.2
    subscription: 1.5
  
  cart:
    add_to_cart: 0.5
    quantity_increase: 0.6
    save_for_later: 0.4
    remove_from_cart: -0.4
  
  browse:
    click_product: 0.2
    view_details: 0.15
    time_on_product:
      10_seconds: 0.1
      30_seconds: 0.25
      60_seconds: 0.3
    
  negative:
    displayed_but_scrolled: -0.05
    viewed_never_bought: -0.2
    returned: -0.8
```

## 2. Implementation Steps

### Day 1: Backend Implementation

#### Morning (4 hours)
1. **Create BigQuery Schema**
   ```sql
   CREATE TABLE leafloaf_events.raw_user_actions (
       event_id STRING NOT NULL,
       event_timestamp TIMESTAMP NOT NULL,
       event_type STRING NOT NULL,
       user_id STRING NOT NULL,
       session_id STRING NOT NULL,
       product_id STRING,
       product_category STRING,
       product_attributes JSON,
       interaction_strength FLOAT64,
       interaction_context JSON,
       search_query STRING,
       search_results_shown JSON,
       result_position INT64,
       raw_event_data JSON
   )
   PARTITION BY DATE(event_timestamp)
   CLUSTER BY user_id, event_type;
   ```

2. **Implement Event Streamer**
   - Create `src/analytics/event_streamer.py`
   - Batch events for efficiency
   - Fire-and-forget pattern
   - Error handling without blocking

3. **Build Real-Time Engine**
   - Create `src/personalization/realtime_engine.py`
   - In-memory preference cache
   - Instant score updates
   - Async Graphiti updates

4. **Update API Endpoints**
   - `/api/interactions/track` - Track all interactions
   - `/api/search/personalized` - Real-time personalized search
   - `/api/preferences/live` - Get current preferences

#### Afternoon (4 hours)
1. **Preference Learning System**
   - Category inference from interactions
   - Attribute preference detection
   - Negative signal processing
   - Pattern recognition

2. **Context Engine**
   - Time-based personalization
   - Seasonal adjustments
   - Meal planning context
   - Weather-based suggestions

3. **Recommendation Engine**
   - Complementary products
   - Reorder suggestions
   - Quantity prediction
   - Discovery items

4. **Testing & Optimization**
   - Load testing for <10ms response
   - Cache warming strategies
   - Connection pooling verification

### Day 2: UI & Integration

#### Morning (4 hours)
1. **React + Tailwind Setup**
   ```bash
   npx create-next-app@latest leafloaf-ui --typescript --tailwind --app
   ```

2. **Core Components**
   - SearchBar with instant suggestions
   - ProductCard with personalization badges
   - QuantitySelector with smart defaults
   - PersonalizationIndicator

3. **State Management**
   - Zustand for cart state
   - React Query for server state
   - Optimistic updates for instant feedback

4. **Real-Time Updates**
   - WebSocket connection for live updates
   - Event tracking hooks
   - Visual feedback system

#### Afternoon (4 hours)
1. **Integration Testing**
   - First-time user flow
   - Returning user personalization
   - Dietary preference detection
   - Bulk buying patterns
   - Cultural context understanding

2. **Performance Optimization**
   - Pre-cache common searches
   - Lazy load components
   - Image optimization
   - Bundle size reduction

3. **Demo Preparation**
   - Create demo accounts
   - Pre-warm caches
   - Test all use cases
   - Performance metrics dashboard

## 3. Key APIs

### 3.1 Track Interaction
```python
POST /api/interactions/track
{
    "type": "click|add_to_cart|purchase|scroll",
    "user_id": "uuid",
    "product_id": "sku",
    "context": {
        "search_query": "milk",
        "position": 3,
        "time_on_page": 45
    }
}
```

### 3.2 Personalized Search
```python
POST /api/search/personalized
{
    "query": "milk",
    "user_id": "uuid",
    "context": {
        "time_of_day": "morning",
        "recent_views": ["oat_milk", "almond_milk"]
    }
}
```

### 3.3 Live Preferences
```python
GET /api/users/{user_id}/preferences/live

Response:
{
    "categories": {
        "dairy_alternatives": 0.8,
        "organic": 0.6
    },
    "attributes": {
        "vegan": 0.7,
        "local": 0.5
    },
    "brands": {
        "oatly": 0.9
    }
}
```

## 4. BigQuery ML Pipeline (Batch)

### Hourly Jobs
- User segmentation
- Product associations
- Time pattern analysis
- Preference evolution

### Daily Jobs
- Collaborative filtering updates
- Category relationship mining
- Price sensitivity analysis
- Seasonal pattern detection

## 5. Success Metrics

### Performance
- Search latency: <300ms (including personalization)
- Preference update: <10ms
- UI responsiveness: Instant (<16ms)

### Business
- Click-through rate: >40% improvement
- Cart conversion: >25% increase
- User satisfaction: >4.5/5

### Technical
- System uptime: 99.9%
- BigQuery streaming success: >99%
- Cache hit rate: >80%

## 6. Testing Scenarios

### Scenario 1: Instant Learning
1. New user searches "milk"
2. Clicks "Oat Milk"
3. Searches "yogurt"
4. Sees plant-based yogurt first

### Scenario 2: Negative Learning
1. User searches "chips"
2. Scrolls past all spicy options
3. Clicks "Original"
4. Future searches deprioritize spicy

### Scenario 3: Bulk Pattern
1. User buys 2 gallons of milk
2. System learns quantity preference
3. Next time suggests 2 by default

## 7. Deployment

### Cloud SQL Setup
```sql
-- Users and sessions
CREATE TABLE users (
    id UUID PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    token VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP
);

-- Carts (persistent)
CREATE TABLE carts (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'active'
);

-- Preferences (cached from Graphiti)
CREATE TABLE user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    preferences JSONB,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Environment Variables
```yaml
# BigQuery
BIGQUERY_PROJECT_ID: leafloafai
BIGQUERY_DATASET: leafloaf_events

# Cloud SQL
CLOUDSQL_CONNECTION_NAME: leafloafai:us-central1:leafloaf-db
CLOUDSQL_DATABASE: leafloaf
CLOUDSQL_USER: leafloaf_app

# Redis (for caching)
REDIS_URL: redis://10.x.x.x:6379

# Existing
WEAVIATE_URL: https://7cijosfpsryfteazzawhjw.c0.us-east1.gcp.weaviate.cloud
SPANNER_INSTANCE_ID: leafloaf-graph
```

## 8. Critical Path (48 hours)

**Hour 0-8**: Backend core
- Event streaming to BigQuery ✓
- Real-time preference engine ✓
- API endpoints ✓

**Hour 8-16**: Advanced features
- Context engine ✓
- Recommendation system ✓
- Performance optimization ✓

**Hour 16-24**: UI development
- React setup ✓
- Core components ✓
- State management ✓

**Hour 24-32**: Integration
- Connect UI to API ✓
- Test all flows ✓
- Fix issues ✓

**Hour 32-40**: Polish
- Performance tuning ✓
- Demo scenarios ✓
- Documentation ✓

**Hour 40-48**: Deploy
- GKE deployment ✓
- Production testing ✓
- Final demo prep ✓

## Next Steps
1. Start with BigQuery schema creation
2. Implement event streamer
3. Build real-time engine
4. Test with mock data
5. Move to UI development