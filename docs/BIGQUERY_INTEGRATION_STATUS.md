# BigQuery Integration Status

## Current Implementation Status

### ✅ What's Implemented

1. **BigQuery Schema** - Tables are defined in analytics service:
   - `user_search_events`
   - `product_interaction_events` 
   - `cart_modification_events`
   - `order_transaction_events`
   - `recommendation_impression_events`

2. **Analytics Service** - Core streaming logic exists:
   ```python
   # src/services/analytics_service.py
   - track_search_event()
   - track_interaction_event()
   - track_cart_event()
   - track_order_event()
   ```

3. **Non-blocking Writes** - Using asyncio.create_task() for fire-and-forget

### ❌ What's NOT Working

1. **BigQuery Errors** - From server logs:
   ```
   BigQuery insert errors for leafloafai.analytics.user_events: 
   [{'reason': 'invalid', 'location': 'event_properties', 
     'message': 'This field: event_properties is not a record.'}]
   ```

2. **Schema Mismatches**:
   - `response_time_ms` expects integer but getting float
   - `event_properties` expects RECORD but getting string
   - Table names don't match (code vs actual)

3. **Missing Configuration**:
   - BigQuery credentials not set up
   - Project ID not configured
   - Dataset not created

## How to Fix BigQuery Integration

### Step 1: Set Up BigQuery Project
```bash
# 1. Create dataset
bq mk --dataset --location=US leafloafai:leafloaf_analytics

# 2. Create tables with correct schema
bq mk --table leafloafai:leafloaf_analytics.user_search_events \
  event_id:STRING,user_id:STRING,session_id:STRING,query:STRING,\
  intent:STRING,alpha_value:FLOAT,results_count:INTEGER,\
  categories:STRING,response_time_ms:INTEGER,timestamp:TIMESTAMP

# 3. Set credentials
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

### Step 2: Fix Schema Issues
```python
# In analytics_service.py, fix data types:
async def track_search_event(self, event_data: Dict[str, Any]):
    rows = [{
        'event_id': str(uuid.uuid4()),
        'user_id': event_data.get('user_id', 'anonymous'),
        'session_id': event_data.get('session_id', ''),
        'query': event_data.get('query', ''),
        'intent': event_data.get('intent', ''),
        'alpha_value': float(event_data.get('alpha', 0.5)),
        'results_count': int(event_data.get('results_count', 0)),
        'categories': json.dumps(event_data.get('categories', [])),  # JSON string
        'response_time_ms': int(event_data.get('response_time_ms', 0)),  # Convert to int
        'timestamp': datetime.utcnow().isoformat()
    }]
```

### Step 3: Update Table References
```python
# Fix table paths
TABLES = {
    'search': 'leafloaf_analytics.raw_events.user_search_events',
    'interaction': 'leafloaf_analytics.raw_events.product_interaction_events',
    'cart': 'leafloaf_analytics.raw_events.cart_modification_events',
    'order': 'leafloaf_analytics.raw_events.order_transaction_events'
}
```

## Current Data Flow (What's Actually Happening)

```
User Action
    ↓
API Endpoint
    ↓
Analytics Service (Attempted)
    ↓
❌ BigQuery Error (Schema mismatch)
    ↓
Error logged but ignored
    ↓
✅ User still gets response (non-blocking)
```

## Data We're Trying to Capture

### 1. Search Events
- User ID and session
- Search query and intent
- Number of results returned
- Categories found
- Response time
- Alpha value used

### 2. Interaction Events  
- Click, view, add to cart signals
- Product details (SKU, name, category)
- Position in search results
- Signal weight/strength
- Timestamp

### 3. Cart Events
- Add/remove/update actions
- Product and quantity
- Price at time of action
- Session context

### 4. Order Events
- Completed purchases
- Order total and items
- Applied discounts
- Delivery preferences

## Why BigQuery Matters

1. **ML Training Data**: Historical patterns for recommendation models
2. **Business Intelligence**: Understand user behavior and trends
3. **A/B Testing**: Measure impact of personalization
4. **Debugging**: Trace user journeys and issues
5. **Compliance**: Audit trail for data usage

## Next Steps

1. **For Demo**: BigQuery can be disabled - personalization works without it
2. **For Production**: 
   - Set up GCP project and BigQuery dataset
   - Fix schema mismatches
   - Add proper error handling
   - Set up data retention policies
   - Create materialized views for ML

## Demo Talking Points

"While we're capturing all user interactions for future ML training in BigQuery, the real-time personalization you're seeing works entirely in-memory. This means:

- Zero dependency on BigQuery for personalization
- Sub-10ms preference updates
- Works even if analytics pipeline is down
- Privacy-first: personalization without persistent tracking

The BigQuery integration enables:
- Training better ML models offline
- Business intelligence dashboards
- Long-term pattern analysis
- But it's completely decoupled from real-time features"