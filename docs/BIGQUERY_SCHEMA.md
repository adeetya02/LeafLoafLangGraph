# BigQuery Schema Design for LeafLoaf

## Implementation Decision: Streaming Inserts
**Decision Date: 2025-01-24**
- Skipping batch processing, going directly to streaming inserts
- Cost is negligible (~$5/month for expected volume)
- Provides real-time data availability for ML and analytics
- Simpler architecture without batch/streaming transition

## Dataset Structure

```
leafloaf_analytics/
├── raw_events/           # Raw event stream
│   ├── search_events
│   ├── order_events
│   └── interaction_events
├── processed/            # Cleaned and enriched
│   ├── user_searches
│   ├── user_orders
│   ├── product_performance
│   └── session_analytics
├── ml_features/          # ML-ready features
│   ├── user_profiles
│   ├── product_embeddings
│   └── reorder_predictions
└── aggregated/          # Business metrics
    ├── daily_metrics
    ├── user_cohorts
    └── demand_forecast
```

## 1. Raw Events Tables

### search_events
```sql
CREATE TABLE `leafloaf_analytics.raw_events.search_events` (
  -- Event Identifiers
  event_id STRING NOT NULL,
  event_timestamp TIMESTAMP NOT NULL,
  ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  
  -- User Information
  user_id STRING NOT NULL,
  user_uuid STRING,
  session_id STRING NOT NULL,
  device_type STRING,  -- mobile, desktop, tablet
  
  -- Search Details
  query STRING NOT NULL,
  query_normalized STRING,  -- cleaned, lowercase
  query_tokens ARRAY<STRING>,  -- tokenized for analysis
  query_length INT64,
  
  -- Intent Classification
  intent STRING,  -- product_search, reorder, explore, etc.
  intent_confidence FLOAT64,
  intent_signals ARRAY<STRING>,  -- signals used for classification
  
  -- Search Configuration
  search_alpha FLOAT64,
  search_strategy STRING,  -- hybrid, keyword, semantic
  filters_applied STRUCT<
    categories ARRAY<STRING>,
    brands ARRAY<STRING>,
    dietary ARRAY<STRING>,
    price_range STRUCT<min FLOAT64, max FLOAT64>
  >,
  
  -- Results
  results_count INT64,
  results_shown ARRAY<STRUCT<
    product_id STRING,
    position INT64,
    score FLOAT64,
    price FLOAT64,
    in_stock BOOLEAN
  >>,
  
  -- Performance
  response_time_ms FLOAT64,
  cache_hit BOOLEAN,
  
  -- Context
  cart_value_before FLOAT64,
  items_in_cart_before INT64,
  time_since_last_order_hours FLOAT64,
  
  -- Outcome
  clicked_results ARRAY<STRUCT<
    product_id STRING,
    position INT64,
    time_to_click_seconds FLOAT64
  >>,
  added_to_cart ARRAY<STRING>,  -- product_ids
  
  -- Metadata
  app_version STRING,
  experiment_ids ARRAY<STRING>
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY user_id, intent;
```

### order_events
```sql
CREATE TABLE `leafloaf_analytics.raw_events.order_events` (
  -- Event Identifiers
  event_id STRING NOT NULL,
  event_timestamp TIMESTAMP NOT NULL,
  event_type STRING NOT NULL,  -- created, confirmed, delivered, cancelled
  
  -- Order Information
  order_id STRING NOT NULL,
  user_id STRING NOT NULL,
  session_id STRING,
  
  -- Order Details
  items ARRAY<STRUCT<
    product_id STRING,
    product_name STRING,
    quantity INT64,
    unit_price FLOAT64,
    total_price FLOAT64,
    discount_applied FLOAT64,
    -- Product Attributes
    category STRING,
    brand STRING,
    supplier STRING,
    size STRING,
    dietary_flags ARRAY<STRING>
  >>,
  
  -- Order Metrics
  subtotal FLOAT64,
  discount_total FLOAT64,
  delivery_fee FLOAT64,
  total_amount FLOAT64,
  item_count INT64,
  unique_item_count INT64,
  
  -- Delivery Information
  delivery_type STRING,  -- standard, express, pickup
  delivery_slot STRUCT<
    date DATE,
    start_time TIME,
    end_time TIME
  >,
  delivery_address_zip STRING,
  
  -- User Context
  is_first_order BOOLEAN,
  days_since_last_order INT64,
  order_number_for_user INT64,
  
  -- Cart Journey
  cart_created_timestamp TIMESTAMP,
  cart_abandoned_count INT64,  -- before this order
  minutes_to_checkout FLOAT64,
  search_queries_before_order ARRAY<STRING>,
  
  -- Payment
  payment_method STRING,
  used_loyalty_points BOOLEAN,
  
  -- Source Attribution
  order_source STRING,  -- web, app, voice, reorder
  marketing_channel STRING,
  referral_code STRING
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY user_id, order_id;
```

### interaction_events
```sql
CREATE TABLE `leafloaf_analytics.raw_events.interaction_events` (
  event_id STRING NOT NULL,
  event_timestamp TIMESTAMP NOT NULL,
  
  user_id STRING NOT NULL,
  session_id STRING NOT NULL,
  
  interaction_type STRING NOT NULL,  -- view, click, add_cart, remove_cart, etc.
  
  -- Target of interaction
  target_type STRING,  -- product, category, brand, banner
  target_id STRING,
  target_details STRUCT<
    name STRING,
    category STRING,
    brand STRING,
    price FLOAT64,
    position INT64,  -- where shown in UI
    context STRING   -- search_results, recommendations, etc.
  >,
  
  -- Interaction Details
  action_details STRUCT<
    quantity INT64,  -- for cart actions
    old_quantity INT64,  -- for updates
    time_on_page_seconds FLOAT64,
    scroll_depth_percent FLOAT64,
    clicks_before_action INT64
  >,
  
  -- Source
  referrer_type STRING,  -- search, browse, recommendation, reorder
  referrer_id STRING,    -- search_id or recommendation_id
  
  -- Device Context
  device_type STRING,
  viewport_size STRING,
  connection_speed STRING
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY user_id, interaction_type;
```

## 2. Processed Tables

### user_searches (Daily ETL)
```sql
CREATE TABLE `leafloaf_analytics.processed.user_searches` (
  date DATE NOT NULL,
  user_id STRING NOT NULL,
  
  -- Search Behavior Metrics
  total_searches INT64,
  unique_queries INT64,
  avg_query_length FLOAT64,
  
  -- Intent Distribution
  intent_counts STRUCT<
    product_search INT64,
    reorder INT64,
    browse INT64,
    meal_planning INT64,
    price_check INT64
  >,
  
  -- Query Patterns
  most_common_queries ARRAY<STRUCT<query STRING, count INT64>>,
  query_refinements INT64,  -- searches that refined previous
  
  -- Search Success Metrics
  searches_with_clicks INT64,
  searches_with_cart_adds INT64,
  avg_clicks_per_search FLOAT64,
  avg_time_to_click FLOAT64,
  zero_result_searches INT64,
  
  -- Category Preferences (from searches)
  category_search_counts ARRAY<STRUCT<
    category STRING,
    search_count INT64,
    click_count INT64,
    add_to_cart_count INT64
  >>,
  
  -- Brand Affinity
  brand_search_counts ARRAY<STRUCT<
    brand STRING,
    search_count INT64,
    click_count INT64,
    purchase_count INT64
  >>,
  
  -- Time Patterns
  searches_by_hour ARRAY<STRUCT<hour INT64, count INT64>>,
  most_active_hour INT64,
  
  -- Device Usage
  device_distribution STRUCT<
    mobile_percent FLOAT64,
    desktop_percent FLOAT64,
    tablet_percent FLOAT64
  >
)
PARTITION BY date
CLUSTER BY user_id;
```

### product_performance
```sql
CREATE TABLE `leafloaf_analytics.processed.product_performance` (
  date DATE NOT NULL,
  product_id STRING NOT NULL,
  
  -- Product Details (denormalized)
  product_name STRING,
  category STRING,
  brand STRING,
  supplier STRING,
  price FLOAT64,
  
  -- Search Performance
  appearances_in_search INT64,
  total_impressions INT64,
  clicks INT64,
  click_through_rate FLOAT64,
  avg_position FLOAT64,
  
  -- Conversion Metrics
  add_to_cart_count INT64,
  purchase_count INT64,
  conversion_rate FLOAT64,
  
  -- Revenue Metrics
  revenue FLOAT64,
  units_sold INT64,
  avg_order_quantity FLOAT64,
  
  -- User Metrics
  unique_viewers INT64,
  unique_purchasers INT64,
  repeat_purchase_rate FLOAT64,
  
  -- Reorder Behavior
  reorder_count INT64,
  avg_days_between_orders FLOAT64,
  
  -- Search Context
  top_search_queries ARRAY<STRUCT<query STRING, count INT64>>,
  found_via_brand_search_percent FLOAT64,
  found_via_category_search_percent FLOAT64,
  
  -- Competitive Metrics
  shown_with_products ARRAY<STRUCT<product_id STRING, count INT64>>,
  lost_clicks_to ARRAY<STRUCT<product_id STRING, count INT64>>
)
PARTITION BY date
CLUSTER BY product_id, category;
```

## 3. ML Feature Tables

### user_profiles
```sql
CREATE OR REPLACE TABLE `leafloaf_analytics.ml_features.user_profiles` (
  user_id STRING NOT NULL,
  profile_date DATE NOT NULL,
  
  -- Demographics (inferred)
  inferred_household_size INT64,
  inferred_income_bracket STRING,
  inferred_life_stage STRING,  -- single, couple, family_young, family_teen, empty_nest
  
  -- Shopping Behavior
  customer_lifetime_value FLOAT64,
  total_orders INT64,
  total_spend FLOAT64,
  avg_order_value FLOAT64,
  avg_days_between_orders FLOAT64,
  order_frequency_variance FLOAT64,  -- how regular
  
  -- Category Preferences (0-1 scores)
  category_preferences ARRAY<STRUCT<
    category STRING,
    preference_score FLOAT64,
    purchase_frequency FLOAT64,
    avg_spend FLOAT64
  >>,
  
  -- Brand Loyalty (0-1 scores)
  brand_loyalty_scores ARRAY<STRUCT<
    brand STRING,
    loyalty_score FLOAT64,
    switch_probability FLOAT64
  >>,
  
  -- Price Sensitivity
  price_sensitivity_score FLOAT64,
  discount_usage_rate FLOAT64,
  premium_product_ratio FLOAT64,
  
  -- Dietary Preferences
  dietary_preferences STRUCT<
    organic_score FLOAT64,
    gluten_free_score FLOAT64,
    vegan_score FLOAT64,
    low_sugar_score FLOAT64,
    non_gmo_score FLOAT64
  >,
  
  -- Shopping Patterns
  preferred_shopping_day STRING,
  preferred_shopping_hour INT64,
  weekend_shopper BOOLEAN,
  bulk_buyer_score FLOAT64,
  variety_seeker_score FLOAT64,
  
  -- Search Behavior
  avg_searches_per_session FLOAT64,
  search_before_purchase_rate FLOAT64,
  browse_to_buy_ratio FLOAT64,
  uses_search_filters_rate FLOAT64,
  
  -- ML Scores
  churn_risk_score FLOAT64,
  predicted_next_order_date DATE,
  predicted_next_order_value FLOAT64,
  recommendation_responsiveness FLOAT64,
  
  -- Engagement
  days_since_last_order INT64,
  days_since_last_visit INT64,
  email_open_rate FLOAT64,
  push_notification_enabled BOOLEAN,
  
  -- Location
  delivery_zip STRING,
  urban_rural_classification STRING,
  
  -- Vectors for ML
  user_embedding ARRAY<FLOAT64>,  -- 128-dim embedding
  
  last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY profile_date
CLUSTER BY user_id;
```

### reorder_predictions
```sql
CREATE TABLE `leafloaf_analytics.ml_features.reorder_predictions` (
  prediction_date DATE NOT NULL,
  user_id STRING NOT NULL,
  product_id STRING NOT NULL,
  
  -- Prediction
  predicted_reorder_date DATE,
  days_until_reorder INT64,
  reorder_probability FLOAT64,
  confidence_score FLOAT64,
  
  -- Historical Pattern
  previous_order_dates ARRAY<DATE>,
  avg_reorder_interval_days FLOAT64,
  reorder_interval_std_dev FLOAT64,
  
  -- Context
  current_inventory_estimate FLOAT64,  -- based on consumption rate
  seasonality_factor FLOAT64,
  price_change_impact FLOAT64,
  
  -- Model Info
  model_version STRING,
  feature_importance STRUCT<
    recency FLOAT64,
    frequency FLOAT64,
    regularity FLOAT64,
    seasonality FLOAT64,
    price_sensitivity FLOAT64
  >
)
PARTITION BY prediction_date
CLUSTER BY user_id, predicted_reorder_date;
```

## 4. Aggregated Business Tables

### daily_metrics
```sql
CREATE TABLE `leafloaf_analytics.aggregated.daily_metrics` (
  date DATE NOT NULL,
  
  -- User Metrics
  active_users INT64,
  new_users INT64,
  returning_users INT64,
  
  -- Search Metrics
  total_searches INT64,
  unique_search_users INT64,
  searches_per_user FLOAT64,
  zero_result_rate FLOAT64,
  
  -- Order Metrics
  total_orders INT64,
  total_revenue FLOAT64,
  avg_order_value FLOAT64,
  
  -- Conversion
  search_to_order_rate FLOAT64,
  cart_abandonment_rate FLOAT64,
  
  -- Product Metrics
  unique_products_sold INT64,
  top_products ARRAY<STRUCT<
    product_id STRING,
    units_sold INT64,
    revenue FLOAT64
  >>,
  
  -- Category Performance
  category_revenue ARRAY<STRUCT<
    category STRING,
    revenue FLOAT64,
    order_count INT64
  >>
)
PARTITION BY date;
```

### user_cohorts
```sql
CREATE TABLE `leafloaf_analytics.aggregated.user_cohorts` (
  cohort_month DATE NOT NULL,
  user_count INT64,
  
  -- Retention by month
  retention_months ARRAY<STRUCT<
    month_number INT64,
    retained_users INT64,
    retention_rate FLOAT64,
    avg_orders_per_user FLOAT64,
    avg_revenue_per_user FLOAT64
  >>,
  
  -- Cohort Characteristics
  avg_first_order_value FLOAT64,
  most_common_first_category STRING,
  acquisition_channels ARRAY<STRUCT<
    channel STRING,
    user_count INT64
  >>
)
PARTITION BY cohort_month;
```

## 5. Views for Easy Analysis

### v_user_360
```sql
CREATE VIEW `leafloaf_analytics.views.v_user_360` AS
SELECT
  u.user_id,
  u.total_orders,
  u.customer_lifetime_value,
  u.avg_order_value,
  u.preferred_shopping_day,
  u.price_sensitivity_score,
  
  -- Recent Activity
  ARRAY(
    SELECT AS STRUCT 
      query, 
      intent, 
      event_timestamp
    FROM `raw_events.search_events`
    WHERE user_id = u.user_id
    ORDER BY event_timestamp DESC
    LIMIT 10
  ) as recent_searches,
  
  -- Favorite Products
  ARRAY(
    SELECT AS STRUCT
      product_id,
      COUNT(*) as purchase_count
    FROM `raw_events.order_events`, UNNEST(items) as item
    WHERE user_id = u.user_id
    GROUP BY product_id
    ORDER BY purchase_count DESC
    LIMIT 10
  ) as favorite_products
  
FROM `ml_features.user_profiles` u
WHERE profile_date = CURRENT_DATE();
```

## Schema Management

### Create Tables Script
```bash
# Create dataset
bq mk --dataset --location=US leafloafai:leafloaf_analytics

# Create tables
bq mk --table leafloafai:leafloaf_analytics.search_events ./schemas/search_events.json
bq mk --table leafloafai:leafloaf_analytics.order_events ./schemas/order_events.json
```

### Partitioning Strategy
- All event tables partitioned by DATE(event_timestamp)
- 90-day partition expiration for raw events
- Clustered by user_id for efficient user queries
- Secondary clustering by important dimensions

### Cost Optimization
- Use materialized views for frequent queries
- Schedule batch jobs during off-peak
- Use BI Engine for dashboard queries
- Archive old partitions to Cloud Storage