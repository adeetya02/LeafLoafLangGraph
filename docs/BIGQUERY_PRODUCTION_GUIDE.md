# BigQuery Production Setup Guide

## ✅ Production Status: READY

All BigQuery integrations have been verified and are production-ready.

## 🏗️ Architecture Overview

### Dual Implementation Strategy
LeafLoaf uses two BigQuery clients for different purposes:

1. **`bigquery_client.py`** - ML & Analytics Pipeline
   - User search events
   - Product interactions
   - Cart modifications
   - Order transactions
   - Recommendation impressions

2. **`analytics_service.py`** - Business Intelligence
   - User behavior events
   - Intent analysis tracking
   - Agent execution metrics
   - Promotion usage analytics

### Fire-and-Forget Pattern
- **Zero latency impact** on user requests
- Async streaming inserts
- Non-blocking error handling
- Graceful degradation

## 📊 Table Structure

```
leafloaf_analytics/
├── ML Pipeline Tables (bigquery_client.py)
│   ├── user_search_events         # Search queries and results
│   ├── product_interaction_events # Clicks, views, cart adds
│   ├── cart_modification_events   # Cart changes
│   ├── order_transaction_events   # Completed orders
│   └── recommendation_impression_events # ML recommendations shown
│
└── Analytics Tables (analytics_service.py)
    ├── user_events      # Generic user events with flexible schema
    ├── search_events    # Detailed search analytics
    ├── cart_events      # Cart-specific events
    ├── order_events     # Order completion with product details
    └── promotion_usage  # Promotion effectiveness tracking
```

## 🚀 Production Deployment Checklist

### 1. GCP Setup
- [x] BigQuery API enabled
- [x] Service account with BigQuery Data Editor role
- [x] Dataset created: `leafloaf_analytics`
- [x] All tables created with correct schemas

### 2. Schema Validations
- [x] All latency fields use INTEGER type
- [x] TIMESTAMP fields properly formatted
- [x] RECORD types for nested data (order products)
- [x] STRING fields for JSON data

### 3. Data Type Fixes Applied
- [x] `response_time_ms` → INTEGER conversion
- [x] `search_latency_ms` → INTEGER conversion
- [x] `total_latency_ms` → INTEGER conversion
- [x] Removed problematic `event_properties` field
- [x] Added event-specific fields to `user_events`

### 4. Production Verification
```bash
# Verify all tables and schemas
python3 scripts/verify_bigquery_production.py

# Monitor production health
python3 scripts/monitor_bigquery_production.py

# Continuous monitoring (every 5 minutes)
python3 scripts/monitor_bigquery_production.py --continuous 5
```

## 📈 Key Metrics to Monitor

### Real-time Metrics
1. **Ingestion Rate**: Events per minute per table
2. **Error Rate**: Failed inserts percentage
3. **Latency**: P50, P95, P99 response times
4. **Data Quality**: NULL values, invalid data

### Daily Metrics
1. **Table Growth**: GB per day
2. **Query Performance**: Average query time
3. **Cost**: Storage + streaming insert costs
4. **User Engagement**: Active users, searches, orders

## 💰 Cost Management

### Estimated Costs
- **Streaming Inserts**: $0.01 per 200MB
- **Storage**: $0.02 per GB per month
- **Queries**: $5 per TB processed

### Cost Optimization
1. Set table expiration for old data (90 days)
2. Use partitioning by date
3. Cluster frequently queried columns
4. Archive to Cloud Storage after 30 days

## 🔧 Maintenance Tasks

### Daily
- Check error logs for failed inserts
- Monitor table growth rates
- Verify data quality

### Weekly
- Review query performance
- Check cost trends
- Update ML feature queries

### Monthly
- Archive old data
- Optimize slow queries
- Review schema for new fields

## 🚨 Alerting Setup

### Critical Alerts
1. **No data ingestion** for 15 minutes
2. **Error rate** > 1%
3. **Table size** > 1TB
4. **Query timeout** > 30 seconds

### Warning Alerts
1. **Latency P95** > 500ms
2. **Daily cost** > $50
3. **NULL rate** > 5%
4. **Streaming quota** > 80%

## 🔄 Disaster Recovery

### Backup Strategy
1. Daily exports to Cloud Storage
2. Cross-region dataset replication
3. Point-in-time recovery (7 days)

### Recovery Procedures
1. **Data Loss**: Restore from Cloud Storage backup
2. **Schema Corruption**: Recreate from scripts
3. **Performance Issues**: Switch to backup dataset
4. **Quota Exceeded**: Implement rate limiting

## 📚 Useful Queries

### Check Recent Activity
```sql
SELECT 
    COUNT(*) as event_count,
    MAX(timestamp) as latest_event
FROM `leafloafai.leafloaf_analytics.user_search_events`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
```

### User Engagement Metrics
```sql
SELECT 
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_searches,
    AVG(result_count) as avg_results
FROM `leafloafai.leafloaf_analytics.user_search_events`
WHERE DATE(timestamp) = CURRENT_DATE()
```

### Popular Products
```sql
SELECT 
    product_name,
    COUNT(*) as interaction_count,
    SUM(CASE WHEN interaction_type = 'add_to_cart' THEN 1 ELSE 0 END) as cart_adds
FROM `leafloafai.leafloaf_analytics.product_interaction_events`
WHERE DATE(timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY product_name
ORDER BY interaction_count DESC
LIMIT 20
```

## 🎯 Success Metrics

### Technical Success
- ✅ 100% schema compliance
- ✅ < 1% error rate
- ✅ < 100ms streaming latency
- ✅ Zero impact on user experience

### Business Success
- Search-to-order conversion tracking
- User behavior insights
- ML model training data
- Personalization effectiveness

## 📞 Support

### Issues?
1. Check `scripts/verify_bigquery_production.py`
2. Run `scripts/monitor_bigquery_production.py`
3. Review Cloud Logging for errors
4. Check BigQuery UI for table status

### Contacts
- **Technical**: Check BigQuery logs and monitoring
- **Billing**: Review GCP billing dashboard
- **Schema**: See `scripts/create_bigquery_tables.py`