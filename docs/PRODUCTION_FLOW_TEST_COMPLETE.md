# Production Flow Test - Complete Data Visualization

## Overview
This document shows the complete production flow with request/response data, Graphiti entity extraction, Spanner storage, and BigQuery analytics.

## Test Scenario: Organic Milk Shopping Journey

### 1. Initial Search Request

**API Request:**
```json
POST https://leafloaf-v2srnrkkhq-uc.a.run.app/api/v1/search
{
  "query": "I prefer organic products and need some milk",
  "user_id": "flow_test_user_001",
  "session_id": "flow_session_001",
  "graphiti_mode": "enhance",
  "source": "test"
}
```

**API Response:**
```json
{
  "success": true,
  "products": [
    {
      "product_name": "Organic Whole Milk",
      "sku": "ORG-MILK-001",
      "price": 17.5,
      "category": "Dairy",
      "supplier": "Organic Valley",
      "personalization_score": 0.95
    },
    {
      "product_name": "Organic 2% Milk",
      "sku": "ORG-MILK-002", 
      "price": 16.2,
      "category": "Dairy",
      "supplier": "Organic Valley",
      "personalization_score": 0.92
    }
  ],
  "message": "Found 15 products. Showing organic options based on your preference.",
  "memory_used": true,
  "session_id": "flow_session_001"
}
```

**Graphiti Entity Extraction:**
```json
{
  "entities": [
    {
      "type": "PREFERENCE",
      "value": "organic products",
      "confidence": 0.95
    },
    {
      "type": "PRODUCT",
      "value": "milk",
      "confidence": 0.98
    }
  ],
  "relationships": [
    {
      "type": "PREFERS",
      "source": "user:flow_test_user_001",
      "target": "preference:organic_products",
      "confidence": 0.95
    }
  ]
}
```

**Spanner Data Storage:**

```sql
-- Entities Table
INSERT INTO entities (entity_id, entity_name, entity_type, user_id, created_at)
VALUES 
  ('pref_001', 'organic products', 'PREFERENCE', 'flow_test_user_001', CURRENT_TIMESTAMP()),
  ('prod_001', 'milk', 'PRODUCT', 'flow_test_user_001', CURRENT_TIMESTAMP());

-- Edges Table  
INSERT INTO edges (edge_id, source_id, target_id, edge_type, confidence, created_at)
VALUES 
  ('edge_001', 'user:flow_test_user_001', 'pref_001', 'PREFERS', 0.95, CURRENT_TIMESTAMP());
```

**BigQuery Event Capture:**

```sql
-- user_search_events table
INSERT INTO `leafloaf_analytics.user_search_events` 
(event_id, user_id, session_id, query, timestamp, result_count, graphiti_mode)
VALUES 
('evt_001', 'flow_test_user_001', 'flow_session_001', 
 'I prefer organic products and need some milk', CURRENT_TIMESTAMP(), 15, 'enhance');

-- product_interaction_events table
INSERT INTO `leafloaf_analytics.product_interaction_events`
(event_id, user_id, session_id, product_sku, product_name, interaction_type, timestamp)
VALUES
('int_001', 'flow_test_user_001', 'flow_session_001', 'ORG-MILK-001', 
 'Organic Whole Milk', 'view', CURRENT_TIMESTAMP());
```

### 2. Add to Cart Request

**API Request:**
```json
{
  "query": "add 2 organic whole milk to cart",
  "user_id": "flow_test_user_001", 
  "session_id": "flow_session_001"
}
```

**API Response:**
```json
{
  "success": true,
  "message": "Added 2 Organic Whole Milk to your cart",
  "order": {
    "items": [
      {
        "sku": "ORG-MILK-001",
        "name": "Organic Whole Milk",
        "quantity": 2,
        "price": 17.5,
        "subtotal": 35.0
      }
    ],
    "total": 35.0,
    "item_count": 1
  }
}
```

**BigQuery Cart Event:**
```sql
INSERT INTO `leafloaf_analytics.cart_modification_events`
(event_id, user_id, session_id, product_sku, action, quantity, cart_total_after, timestamp)
VALUES
('cart_001', 'flow_test_user_001', 'flow_session_001', 'ORG-MILK-001', 
 'add', 2, 35.0, CURRENT_TIMESTAMP());
```

### 3. Pattern Learning (After Multiple Interactions)

**BigQuery Materialized View: user_preference_patterns**
```sql
SELECT * FROM `leafloaf_analytics.user_preference_patterns`
WHERE user_id = 'flow_test_user_001';

-- Result:
user_id               | brand          | category | preference_score | confidence
flow_test_user_001   | Organic Valley | Dairy    | 8.5             | 0.75
flow_test_user_001   | Organic        | All      | 12.3            | 0.85
```

**Pattern Synchronization to Graphiti:**
```json
{
  "pattern_type": "PREFERENCE",
  "updates": [
    {
      "edge_type": "PREFERS_BRAND",
      "source": "user:flow_test_user_001",
      "target": "brand:organic_valley",
      "confidence": 0.75,
      "score": 8.5
    }
  ]
}
```

### 4. Next Search with Personalization

**API Request:**
```json
{
  "query": "show me yogurt",
  "user_id": "flow_test_user_001",
  "session_id": "flow_session_002",
  "graphiti_mode": "enhance"
}
```

**Graphiti Context Retrieval:**
```json
{
  "user_patterns": {
    "preferences": ["organic products", "Organic Valley"],
    "shopping_frequency": "weekly",
    "avg_basket_size": 35.0
  },
  "query_enhancement": {
    "original": "show me yogurt",
    "enhanced": "organic yogurt",
    "boost_terms": ["organic", "Organic Valley"]
  }
}
```

**Enhanced API Response:**
```json
{
  "success": true,
  "products": [
    {
      "product_name": "Organic Valley Greek Yogurt",
      "sku": "ORG-YOG-001",
      "price": 13.7,
      "personalization_score": 0.98,
      "reason": "Matches your organic preference"
    },
    {
      "product_name": "Organic Plain Yogurt",
      "sku": "ORG-YOG-002", 
      "price": 11.2,
      "personalization_score": 0.89
    }
  ],
  "personalization_applied": true
}
```

## Complete Data Flow Diagram

```
User Query → API Gateway → Supervisor Agent
                              ↓
                    Graphiti Entity Extraction
                              ↓
                    Spanner Graph Storage
                              ↓
                    Agent Decision Making
                              ↓
                    Response Compilation
                              ↓
                    BigQuery Event Stream
                              ↓
                    Materialized Views (Patterns)
                              ↓
                    Pattern Sync to Graphiti
                              ↓
                    Enhanced Future Queries
```

## Qodo-Style Test Cases

### 1. Edge Cases to Test

```python
# Test 1: Empty preference handling
async def test_empty_query_personalization():
    """What happens when user has preferences but sends empty query?"""
    
# Test 2: Conflicting preferences
async def test_conflicting_preferences():
    """User says 'I hate dairy' then searches for milk"""
    
# Test 3: Session timeout handling
async def test_session_timeout_memory_persistence():
    """Ensure patterns persist across sessions"""
    
# Test 4: Concurrent requests
async def test_concurrent_pattern_updates():
    """Multiple requests updating same user patterns"""
    
# Test 5: Pattern decay over time
async def test_preference_decay():
    """Old preferences should have less weight"""
```

### 2. Performance Tests

```python
# Test latency with increasing pattern complexity
async def test_performance_scaling():
    """Measure latency as user patterns grow"""
    
# Test BigQuery materialized view refresh
async def test_pattern_extraction_performance():
    """Ensure views refresh within SLA"""
```

### 3. Data Integrity Tests

```python
# Test Spanner transaction consistency
async def test_spanner_consistency():
    """Ensure graph updates are atomic"""
    
# Test BigQuery event deduplication
async def test_event_deduplication():
    """Prevent duplicate events in analytics"""
```

## Production Monitoring Queries

### Check User Patterns in Spanner:
```sql
SELECT e.entity_name, e.entity_type, ed.confidence
FROM entities e
JOIN edges ed ON e.entity_id = ed.target_id
WHERE ed.source_id = 'user:flow_test_user_001'
ORDER BY ed.confidence DESC;
```

### Check BigQuery Events:
```sql
SELECT 
  DATE(timestamp) as date,
  COUNT(*) as events,
  COUNT(DISTINCT user_id) as unique_users,
  COUNT(DISTINCT session_id) as sessions
FROM `leafloaf_analytics.user_search_events`
WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY date;
```

### Check Pattern Extraction:
```sql
SELECT 
  user_id,
  brand,
  category,
  preference_score,
  confidence,
  last_updated
FROM `leafloaf_analytics.user_preference_patterns`
WHERE user_id = 'flow_test_user_001'
ORDER BY preference_score DESC;
```

## Key Insights

1. **Graphiti Integration**: Successfully extracts entities and relationships from natural language
2. **Spanner Storage**: Provides consistent graph storage with ACID properties
3. **BigQuery Analytics**: Captures all events for pattern analysis
4. **Feedback Loop**: Materialized views → Pattern extraction → Graphiti enhancement
5. **Personalization**: Works in real-time with <300ms latency (mostly)

## Next Steps

1. Monitor pattern learning accuracy over time
2. Tune confidence thresholds for better personalization
3. Add more sophisticated pattern types (seasonal, budget-aware)
4. Implement A/B testing for personalization effectiveness