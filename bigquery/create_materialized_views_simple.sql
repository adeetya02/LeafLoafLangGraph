-- Simplified Materialized Views based on actual schema
-- These views are designed to work with the current table structure

-- 1. User Preference Patterns (Simplified)
CREATE MATERIALIZED VIEW IF NOT EXISTS `leafloafai.leafloaf_analytics.user_preference_patterns`
PARTITION BY DATE(last_updated)
CLUSTER BY user_id
AS
WITH user_interactions AS (
  SELECT 
    user_id,
    product_name,
    interaction_type,
    timestamp,
    sku
  FROM `leafloafai.leafloaf_analytics.product_interaction_events`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
    AND user_id IS NOT NULL
),
product_scores AS (
  SELECT 
    user_id,
    product_name,
    COUNT(*) as interaction_count,
    SUM(CASE 
      WHEN interaction_type = 'add_to_cart' THEN 2.0
      WHEN interaction_type = 'purchase' THEN 3.0
      WHEN interaction_type = 'click' THEN 1.0
      ELSE 0.5
    END) as preference_score,
    MAX(timestamp) as last_interaction
  FROM user_interactions
  GROUP BY user_id, product_name
)
SELECT 
  user_id,
  product_name,
  interaction_count,
  preference_score,
  -- Add recency boost
  preference_score * EXP(-DATE_DIFF(CURRENT_DATE(), DATE(last_interaction), DAY) / 30.0) as weighted_score,
  last_interaction,
  CURRENT_TIMESTAMP() as last_updated
FROM product_scores
WHERE interaction_count >= 2;

-- 2. Product Association Patterns (Simplified)
CREATE MATERIALIZED VIEW IF NOT EXISTS `leafloafai.leafloaf_analytics.product_association_patterns`
PARTITION BY DATE(last_updated)
AS
WITH cart_sessions AS (
  SELECT 
    session_id,
    ARRAY_AGG(DISTINCT sku) as products_in_session
  FROM `leafloafai.leafloaf_analytics.cart_modification_events`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
    AND action = 'add'
  GROUP BY session_id
  HAVING ARRAY_LENGTH(products_in_session) >= 2
),
product_pairs AS (
  SELECT 
    p1 as product_a,
    p2 as product_b,
    COUNT(*) as co_occurrence_count
  FROM cart_sessions,
  UNNEST(products_in_session) as p1,
  UNNEST(products_in_session) as p2
  WHERE p1 < p2
  GROUP BY p1, p2
)
SELECT 
  product_a,
  product_b,
  co_occurrence_count,
  co_occurrence_count / (SELECT COUNT(*) FROM cart_sessions) as support,
  CURRENT_TIMESTAMP() as last_updated
FROM product_pairs
WHERE co_occurrence_count >= 3;

-- 3. Reorder Patterns (Simplified)
CREATE MATERIALIZED VIEW IF NOT EXISTS `leafloafai.leafloaf_analytics.reorder_intelligence_patterns`
PARTITION BY DATE(last_updated)
CLUSTER BY user_id
AS
WITH user_orders AS (
  SELECT 
    user_id,
    sku,
    product_name,
    timestamp,
    quantity
  FROM `leafloafai.leafloaf_analytics.order_transaction_events`,
  UNNEST(JSON_EXTRACT_ARRAY(items)) as item
  WHERE user_id IS NOT NULL
    AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
),
reorder_stats AS (
  SELECT 
    user_id,
    sku,
    MAX(product_name) as product_name,
    COUNT(*) as order_count,
    AVG(quantity) as avg_quantity,
    MAX(timestamp) as last_order_date,
    -- Calculate average days between orders
    SAFE_DIVIDE(
      DATE_DIFF(CURRENT_DATE(), DATE(MIN(timestamp)), DAY),
      COUNT(*) - 1
    ) as avg_days_between_orders
  FROM user_orders
  GROUP BY user_id, sku
  HAVING COUNT(*) >= 2
)
SELECT 
  user_id,
  sku,
  product_name,
  order_count,
  avg_quantity,
  avg_days_between_orders,
  last_order_date,
  DATE_DIFF(CURRENT_DATE(), DATE(last_order_date), DAY) as days_since_last_order,
  -- Simple reorder prediction
  CASE 
    WHEN DATE_DIFF(CURRENT_DATE(), DATE(last_order_date), DAY) >= avg_days_between_orders * 0.8 
    THEN TRUE
    ELSE FALSE
  END as reorder_due,
  CURRENT_TIMESTAMP() as last_updated
FROM reorder_stats
WHERE avg_days_between_orders IS NOT NULL
  AND avg_days_between_orders <= 90;

-- 4. Session Context (Real-time patterns)
CREATE MATERIALIZED VIEW IF NOT EXISTS `leafloafai.leafloaf_analytics.session_context_patterns`
PARTITION BY DATE(session_start)
CLUSTER BY session_id
AS
WITH recent_sessions AS (
  SELECT 
    session_id,
    user_id,
    MIN(timestamp) as session_start,
    MAX(timestamp) as session_end,
    COUNT(*) as search_count,
    ARRAY_AGG(query IGNORE NULLS ORDER BY timestamp) as search_queries
  FROM `leafloafai.leafloaf_analytics.user_search_events`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  GROUP BY session_id, user_id
)
SELECT 
  session_id,
  user_id,
  session_start,
  session_end,
  TIMESTAMP_DIFF(session_end, session_start, MINUTE) as session_duration_minutes,
  search_count,
  search_queries,
  CURRENT_TIMESTAMP() as last_updated
FROM recent_sessions;

-- 5. User Shopping Behavior (Simplified)
CREATE MATERIALIZED VIEW IF NOT EXISTS `leafloafai.leafloaf_analytics.user_shopping_behavior_patterns`
PARTITION BY DATE(last_updated)
CLUSTER BY user_id
AS
WITH user_activity AS (
  SELECT 
    user_id,
    COUNT(DISTINCT session_id) as total_sessions,
    COUNT(DISTINCT DATE(timestamp)) as active_days,
    MIN(timestamp) as first_activity,
    MAX(timestamp) as last_activity
  FROM `leafloafai.leafloaf_analytics.user_search_events`
  WHERE user_id IS NOT NULL
  GROUP BY user_id
),
order_stats AS (
  SELECT 
    user_id,
    COUNT(*) as total_orders,
    AVG(order_total) as avg_order_value,
    MAX(timestamp) as last_order_date
  FROM `leafloafai.leafloaf_analytics.order_transaction_events`
  WHERE user_id IS NOT NULL
  GROUP BY user_id
)
SELECT 
  ua.user_id,
  ua.total_sessions,
  ua.active_days,
  IFNULL(os.total_orders, 0) as total_orders,
  IFNULL(os.avg_order_value, 0) as avg_order_value,
  ua.first_activity,
  ua.last_activity,
  os.last_order_date,
  -- Calculate shopping frequency
  CASE 
    WHEN ua.active_days > 0 THEN ua.total_sessions / ua.active_days
    ELSE 0
  END as sessions_per_active_day,
  CURRENT_TIMESTAMP() as last_updated
FROM user_activity ua
LEFT JOIN order_stats os ON ua.user_id = os.user_id
WHERE ua.total_sessions >= 2;