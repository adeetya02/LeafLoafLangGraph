# BigQuery Schema Fixes Summary

## Issues Fixed

### 1. Data Type Mismatches
**Problem**: BigQuery tables expected INTEGER for latency fields but code was sending FLOAT values.

**Error Example**:
```
Cannot convert value to integer (bad value): 301.086709019728
```

**Fix Applied**: All latency and response time fields now convert to integer:
- `response_time_ms`: `int(search_data.get("response_time_ms", 0))`
- `gemma_latency_ms`: `int(latency_ms)`
- `search_latency_ms`: `int(search_data.get("response_time_ms", 0))`
- `weaviate_latency_ms`: `int(search_data.get("weaviate_latency_ms", 0))`
- `total_latency_ms`: `int(sum(state.get("agent_timings", {}).values()))`

### 2. RECORD Type Issues
**Problem**: The `event_properties` field was sending a dictionary but BigQuery expected a RECORD type.

**Error Example**:
```
This field: event_properties is not a record.
```

**Fix Applied**: Removed `event_properties` field and added individual fields based on event type:
- For `intent_analysis` events: Added `query`, `intent`, `confidence`, `alpha` fields
- For `search_executed` events: Added `query`, `results_count`, `search_latency_ms` fields

### 3. Table Name Mismatches
**Problem**: Different services were using different dataset names:
- `analytics_service.py`: Used `analytics` dataset
- `bigquery_client.py`: Used `leafloaf_analytics` dataset

**Fix Applied**: Standardized all table references to use `leafloaf_analytics` dataset:
- `leafloafai.analytics.user_events` → `leafloafai.leafloaf_analytics.user_events`
- `leafloafai.analytics.search_events` → `leafloafai.leafloaf_analytics.search_events`
- `leafloafai.analytics.cart_events` → `leafloafai.leafloaf_analytics.cart_events`
- `leafloafai.analytics.order_events` → `leafloafai.leafloaf_analytics.order_events`
- `leafloafai.promotions.promotion_usage` → `leafloafai.leafloaf_analytics.promotion_usage`

## Files Modified

### 1. `src/services/analytics_service.py`
- Fixed data type conversions for all latency fields
- Removed `event_properties` field
- Updated all table references to use correct dataset
- Added event-specific fields to user_events table

### 2. Created `scripts/create_additional_bigquery_tables.py`
- Script to create missing tables needed by analytics_service
- Includes proper schemas for:
  - `user_events`: Generic event tracking with event-specific fields
  - `search_events`: Search-specific tracking
  - `cart_events`: Cart modification tracking
  - `order_events`: Order completion tracking with RECORD type for products
  - `promotion_usage`: Promotion usage tracking

## Current Architecture

### Two BigQuery Implementations
1. **`src/services/analytics_service.py`** (Legacy)
   - Used by older parts of the system
   - Now fixed to match BigQuery schemas
   - Fire-and-forget pattern

2. **`src/analytics/bigquery_client.py`** (Recommended)
   - Newer implementation
   - Used by data capture strategy
   - Cleaner architecture
   - ML-focused tables

### Table Structure
```
leafloaf_analytics/
├── Raw Events (from bigquery_client.py)
│   ├── user_search_events
│   ├── product_interaction_events
│   ├── cart_modification_events
│   ├── order_transaction_events
│   └── recommendation_impression_events
│
└── Analytics Events (from analytics_service.py)
    ├── user_events (generic events)
    ├── search_events
    ├── cart_events
    ├── order_events
    └── promotion_usage
```

## Next Steps

### 1. Create Missing Tables
```bash
python3 scripts/create_additional_bigquery_tables.py
```

### 2. Verify Tables
```bash
python3 scripts/verify_bigquery_data.py
```

### 3. Long-term Recommendation
- Consolidate to use only `bigquery_client.py`
- Remove redundant analytics_service.py implementation
- Create unified event schema
- Implement proper error monitoring

## Impact on Demo

**None** - BigQuery is optional for the demo:
- Real-time personalization works without BigQuery
- Errors are logged but don't affect user experience
- Fire-and-forget pattern ensures zero latency impact

## Production Considerations

1. **Enable BigQuery API**: Ensure BigQuery API is enabled in GCP
2. **Service Account**: Verify service account has BigQuery Data Editor role
3. **Table Creation**: Run all table creation scripts before production
4. **Monitoring**: Set up alerts for BigQuery insertion errors
5. **Cost Management**: Enable streaming insert quotas to control costs