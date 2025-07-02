# Data Pipeline Architecture Decisions

## Key Decisions Log

### 1. BigQuery Streaming vs Batch (2025-01-24)
**Decision**: Go directly to streaming inserts, skip batch processing
**Rationale**:
- Cost is negligible (~$5/month for 20-50 users)
- Simpler architecture (no batch-to-streaming migration needed)
- Real-time data availability for ML features
- User explicitly approved: "let us do a streaming insert.. we have all the things and costs are negligible too"

### 2. Redis Feature Flag (Implemented)
**Decision**: Redis can be completely disabled via environment variable
**Implementation**: `REDIS_ENABLED=false` (currently disabled)
**Rationale**:
- System works without Redis
- Can enable when ready without code changes
- Allows testing core functionality first

### 3. Data Capture Strategy
**Current Implementation**:
- Multi-backend approach (Redis, Cloud Storage, BigQuery)
- Each backend can be independently enabled/disabled
- Async capture doesn't block main search flow
- Graceful degradation if any backend fails

### 4. ML Data Collection Scope
**What We're Capturing**:
- Every search query with intent classification
- All product interactions (views, clicks, cart adds)
- Complete order history with item details
- User behavior patterns for profiling
- Session tracking for journey analysis
- Future: 11Labs voice interactions

### 5. Privacy & Retention
**Decisions**:
- 90-day retention for raw events
- No PII beyond user_id
- Queries anonymized in aggregated tables
- Service accounts with least privilege

## Next Implementation Steps

1. **BigQuery Streaming Insert** (Priority: HIGH)
   - Create BigQuery dataset and tables
   - Implement streaming insert client
   - Add to data capture pipeline
   - Test with real events

2. **Real-time ML Features** (After streaming works)
   - User profile generation
   - Reorder predictions
   - Personalized recommendations

3. **Monitoring & Observability**
   - Event capture metrics
   - Streaming insert success rates
   - Data quality checks

## Architecture Evolution

### Phase 1 (Current)
- Cloud Storage capture only
- No personalization
- Basic search functionality

### Phase 2 (Next)
- BigQuery streaming enabled
- Start collecting ML training data
- Basic analytics dashboards

### Phase 3 (Future)
- Redis enabled for caching
- Real-time personalization
- Advanced ML models
- 11Labs voice integration

## Cost Considerations

### Streaming Costs (Approved)
- ~$5/month for 20-50 users
- Scales linearly with usage
- Monitoring in place for cost alerts

### Storage Costs
- BigQuery: $0.02/GB/month
- 90-day retention keeps costs low
- Partitioning by date for efficient queries

## Technical Notes

### Why Streaming Over Batch?
1. **Simplicity**: One code path instead of two
2. **Real-time**: Data available immediately
3. **Cost**: Negligible difference at our scale
4. **Future-proof**: No migration needed later

### Implementation Considerations
- Use BigQuery streaming API directly
- Batch multiple events per request (up to 500)
- Implement retry logic with exponential backoff
- Monitor quota usage (100,000 rows/second limit)