-- BigQuery tables for LeafLoaf analytics
-- Dataset: leafloaf_analytics

-- 1. User search events
CREATE TABLE IF NOT EXISTS `leafloafai.leafloaf_analytics.user_search_events` (
  event_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  user_id STRING,
  session_id STRING NOT NULL,
  query STRING NOT NULL,
  alpha_value FLOAT64,
  search_type STRING,
  result_count INT64,
  response_time_ms FLOAT64,
  routing_decision STRING,
  agent_timings STRUCT<
    supervisor_ms FLOAT64,
    product_search_ms FLOAT64,
    order_agent_ms FLOAT64,
    response_compiler_ms FLOAT64
  >,
  metadata JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id, session_id;

-- 2. Product interaction events
CREATE TABLE IF NOT EXISTS `leafloafai.leafloaf_analytics.product_interaction_events` (
  event_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  user_id STRING,
  session_id STRING NOT NULL,
  product_sku STRING NOT NULL,
  product_name STRING,
  interaction_type STRING, -- 'view', 'click', 'add_to_cart', 'remove_from_cart'
  position INT64, -- position in search results
  price FLOAT64,
  supplier STRING,
  category STRING,
  metadata JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id, product_sku;

-- 3. Cart modification events
CREATE TABLE IF NOT EXISTS `leafloafai.leafloaf_analytics.cart_modification_events` (
  event_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  user_id STRING,
  session_id STRING NOT NULL,
  action STRING, -- 'add', 'remove', 'update_quantity', 'clear'
  product_sku STRING,
  product_name STRING,
  quantity INT64,
  unit_price FLOAT64,
  total_price FLOAT64,
  cart_total_after FLOAT64,
  cart_item_count_after INT64,
  metadata JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id, session_id;

-- 4. Order transaction events
CREATE TABLE IF NOT EXISTS `leafloafai.leafloaf_analytics.order_transaction_events` (
  order_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  user_id STRING,
  session_id STRING NOT NULL,
  order_total FLOAT64,
  item_count INT64,
  items ARRAY<STRUCT<
    sku STRING,
    name STRING,
    quantity INT64,
    unit_price FLOAT64,
    total_price FLOAT64
  >>,
  delivery_date DATE,
  payment_method STRING,
  metadata JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id;

-- 5. ML recommendation impressions
CREATE TABLE IF NOT EXISTS `leafloafai.leafloaf_analytics.recommendation_impression_events` (
  event_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  user_id STRING,
  session_id STRING NOT NULL,
  recommendation_type STRING, -- 'reorder', 'complementary', 'trending', 'personalized'
  recommendation_source STRING, -- 'ml_model', 'rule_based', 'collaborative'
  products ARRAY<STRUCT<
    sku STRING,
    name STRING,
    position INT64,
    score FLOAT64,
    clicked BOOL
  >>,
  context_query STRING,
  metadata JSON
)
PARTITION BY DATE(timestamp)
CLUSTER BY user_id, recommendation_type;

-- Views for analytics

-- Daily user activity
CREATE OR REPLACE VIEW `leafloafai.leafloaf_analytics.daily_user_activity` AS
SELECT
  DATE(timestamp) as date,
  user_id,
  COUNT(DISTINCT session_id) as sessions,
  COUNT(*) as searches,
  AVG(response_time_ms) as avg_response_time,
  SUM(result_count) as total_results_shown
FROM `leafloafai.leafloaf_analytics.user_search_events`
GROUP BY date, user_id;

-- Product performance
CREATE OR REPLACE VIEW `leafloafai.leafloaf_analytics.product_performance` AS
SELECT
  p.product_sku,
  p.product_name,
  p.supplier,
  p.category,
  COUNT(DISTINCT p.session_id) as unique_sessions,
  SUM(CASE WHEN p.interaction_type = 'view' THEN 1 ELSE 0 END) as views,
  SUM(CASE WHEN p.interaction_type = 'click' THEN 1 ELSE 0 END) as clicks,
  SUM(CASE WHEN p.interaction_type = 'add_to_cart' THEN 1 ELSE 0 END) as adds_to_cart,
  SAFE_DIVIDE(
    SUM(CASE WHEN p.interaction_type = 'click' THEN 1 ELSE 0 END),
    SUM(CASE WHEN p.interaction_type = 'view' THEN 1 ELSE 0 END)
  ) as click_through_rate,
  SAFE_DIVIDE(
    SUM(CASE WHEN p.interaction_type = 'add_to_cart' THEN 1 ELSE 0 END),
    SUM(CASE WHEN p.interaction_type = 'view' THEN 1 ELSE 0 END)
  ) as add_to_cart_rate
FROM `leafloafai.leafloaf_analytics.product_interaction_events` p
GROUP BY 1,2,3,4;