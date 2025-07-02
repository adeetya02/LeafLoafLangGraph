# Flexible Data Capture & ML System

## Overview

A multi-tier data capture system that works with or without Redis, ensuring no data loss while enabling real-time ML features.

## Architecture

```
User Request
     │
     ├─> Main Search Flow (Blocking)
     │         │
     │         └─> Return Results (Fast)
     │
     └─> Async Data Pipeline (Non-blocking)
               │
               ├─> Redis (if enabled) ─> Real-time Cache
               │
               ├─> Cloud Storage ─> Batch Processing
               │
               └─> BigQuery ─> Analytics & ML Training
```

## Data Flow

### 1. Search Request

```python
# User searches for "organic milk"
POST /api/v1/search
{
  "query": "organic milk",
  "user_id": "user_123",
  "session_id": "session_abc"
}
```

### 2. Immediate Response (< 200ms)

```python
# Main search completes and returns
{
  "results": [...],
  "conversation": {"intent": "product_search"},
  "execution": {"total_time_ms": 145}
}
```

### 3. Async Data Capture (Background)

Multiple backends capture data simultaneously:

#### Redis (Real-time)
- User search history
- Cache for personalization
- Session state

#### Cloud Storage (Reliable)
- JSONL files batched every 60s or 100 events
- Format: `events/20240124_103000_100_events.jsonl`

#### BigQuery (Analytics)
- Structured tables for ML training
- User behavior analysis
- Demand forecasting

## Data Captured

### Search Events
```json
{
  "event_type": "search",
  "timestamp": "2024-01-24T10:30:00Z",
  "user_id": "user_123",
  "session_id": "session_abc",
  "query": "organic milk",
  "intent": "product_search",
  "results_count": 12,
  "response_time_ms": 145,
  "metadata": {
    "search_config": {"alpha": 0.3},
    "confidence": 0.95
  }
}
```

### Order Events
```json
{
  "event_type": "order",
  "timestamp": "2024-01-24T10:35:00Z",
  "user_id": "user_123",
  "order_id": "order_789",
  "items": [
    {
      "product_id": "OATLY_001",
      "quantity": 2,
      "price": 5.99,
      "category": "dairy_alternative"
    }
  ],
  "total_value": 67.89
}
```

### Interaction Events
```json
{
  "event_type": "interaction",
  "timestamp": "2024-01-24T10:31:00Z",
  "user_id": "user_123",
  "interaction_type": "product_click",
  "product_id": "OATLY_001",
  "position": 1,
  "context": {"from_search": "organic milk"}
}
```

## ML Features

### 1. Reorder Prediction
- Tracks purchase frequency
- Predicts when user needs items
- Confidence score based on regularity

### 2. Personalized Recommendations
- Based on search history
- Category preferences
- Brand affinity
- Price sensitivity

### 3. Complementary Products
- Items frequently bought together
- Category associations
- Meal planning suggestions

## Configuration

### Enable/Disable Backends

```python
# Environment variables
REDIS_ENABLED=false  # Currently disabled
ENABLE_BIGQUERY=true # Enable for analytics
CLOUD_STORAGE_BUCKET=leafloaf-user-data
```

### Timeouts

```python
# Recommendation timeout (won't block search)
RECOMMENDATION_TIMEOUT=0.5  # 500ms

# Data capture is fire-and-forget (no timeout)
```

## Usage Examples

### 1. Basic Search (No ML)
```python
# When Redis is disabled
- Search executes normally
- Results returned immediately
- Data captured to Cloud Storage only
- No personalization
```

### 2. Search with Redis
```python
# When Redis is enabled
- Check cache first (< 50ms)
- Get personalized recommendations (< 500ms)
- Return enriched results
- Background data capture to all backends
```

### 3. ML Timeout Handling
```python
# If recommendations timeout
- Return search results without recommendations
- Log timeout event
- Continue data capture in background
- User experience not affected
```

## Data Processing Pipeline

### Real-time (Redis)
- Immediate cache updates
- Session tracking
- Last 1000 searches per user

### Near Real-time (Cloud Storage)
- Batch upload every 60 seconds
- Processed by Cloud Functions
- Fed to ML training pipeline

### Batch (BigQuery)
- Daily aggregations
- ML model training
- Demand forecasting
- User segmentation

## Privacy & Security

### Data Minimization
- No PII beyond user_id
- Queries anonymized in analytics
- 90-day retention for raw events

### Access Control
- Service accounts for each backend
- Least privilege principle
- Audit logging enabled

## Monitoring

### Health Checks
```bash
# Check data capture status
curl /health
{
  "data_capture": {
    "redis": "disabled",
    "cloud_storage": "healthy",
    "bigquery": "healthy"
  }
}
```

### Metrics
- Events captured per minute
- Backend failure rates
- ML prediction latency
- Cache hit rates

## Future Enhancements

### 1. Real-time Streaming
- Pub/Sub for event streaming
- Dataflow for processing
- Real-time ML serving

### 2. Advanced ML
- Deep learning for intent
- Graph neural networks for recommendations
- Time-series for demand forecasting

### 3. Edge Computing
- Client-side personalization
- Offline recommendations
- Privacy-preserving ML

## Testing

### Without Any Backend
```bash
# All backends disabled
REDIS_ENABLED=false ENABLE_BIGQUERY=false
# System still works, just no data capture
```

### With Only Cloud Storage
```bash
# Minimal setup
REDIS_ENABLED=false
# Data captured to GCS for later processing
```

### Full ML Pipeline
```bash
# Everything enabled
REDIS_ENABLED=true ENABLE_BIGQUERY=true
# Real-time personalization + analytics
```