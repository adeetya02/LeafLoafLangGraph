-- BigQuery Materialized Views for Pattern Extraction
-- These views power the feedback loop from analytics to Graphiti
-- Dataset: leafloaf_analytics

-- 1. User Preference Patterns
-- Extracts brand and category preferences from user interactions
CREATE MATERIALIZED VIEW IF NOT EXISTS `leafloafai.leafloaf_analytics.user_preference_patterns`
PARTITION BY DATE(last_updated)
CLUSTER BY user_id
AS
WITH user_interactions AS (
  SELECT 
    user_id,
    IFNULL(supplier, 'Unknown') as brand,
    IFNULL(category, 'Unknown') as category,
    interaction_type,
    timestamp,
    product_sku
  FROM `leafloafai.leafloaf_analytics.product_interaction_events`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
    AND user_id IS NOT NULL
),
interaction_scores AS (
  SELECT 
    user_id,
    brand,
    category,
    COUNT(*) as total_interactions,
    SUM(CASE 
      WHEN interaction_type = 'add_to_cart' THEN 1.0
      WHEN interaction_type = 'click' THEN 0.5
      WHEN interaction_type = 'view' THEN 0.1
      ELSE 0
    END) as interaction_score,
    MAX(timestamp) as last_interaction,
    COUNT(DISTINCT DATE(timestamp)) as active_days,
    COUNT(DISTINCT product_sku) as product_variety
  FROM user_interactions
  GROUP BY user_id, brand, category
)
SELECT 
  user_id,
  brand,
  category,
  total_interactions,
  interaction_score,
  -- Calculate preference strength with recency factor
  interaction_score * 
    (1 + EXP(-DATE_DIFF(CURRENT_DATE(), DATE(last_interaction), DAY) / 30.0)) as preference_score,
  -- Confidence based on interaction count and consistency
  LEAST(1.0, 
    (total_interactions / 10.0) * 
    (active_days / 30.0) * 
    (product_variety / 5.0)
  ) as confidence,
  last_interaction,
  active_days,
  product_variety,
  CURRENT_TIMESTAMP() as last_updated
FROM interaction_scores
WHERE total_interactions >= 3;

-- 2. Product Association Patterns
-- Identifies products frequently bought together
CREATE MATERIALIZED VIEW IF NOT EXISTS `leafloafai.leafloaf_analytics.product_association_patterns`
PARTITION BY DATE(last_updated)
CLUSTER BY product_a, product_b
AS
WITH order_items_flattened AS (
  SELECT 
    order_id,
    user_id,
    timestamp,
    item.sku as product_sku,
    item.name as product_name
  FROM `leafloafai.leafloaf_analytics.order_transaction_events`,
  UNNEST(items) as item
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
),
product_pairs AS (
  SELECT 
    a.product_sku as product_a,
    b.product_sku as product_b,
    a.product_name as name_a,
    b.product_name as name_b,
    COUNT(DISTINCT a.order_id) as co_occurrence_count,
    COUNT(DISTINCT a.user_id) as unique_users
  FROM order_items_flattened a
  JOIN order_items_flattened b
    ON a.order_id = b.order_id 
    AND a.product_sku < b.product_sku  -- Avoid duplicates and self-joins
  GROUP BY 1, 2, 3, 4
),
total_orders AS (
  SELECT COUNT(DISTINCT order_id) as total_order_count
  FROM `leafloafai.leafloaf_analytics.order_transaction_events`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
)
SELECT 
  pp.product_a,
  pp.product_b,
  pp.name_a,
  pp.name_b,
  pp.co_occurrence_count,
  pp.unique_users,
  pp.co_occurrence_count / t.total_order_count as support,
  -- Confidence: P(B|A) = P(A,B) / P(A)
  pp.co_occurrence_count / 
    (SELECT COUNT(DISTINCT order_id) 
     FROM order_items_flattened 
     WHERE product_sku = pp.product_a) as confidence,
  -- Lift: P(A,B) / (P(A) * P(B))
  (pp.co_occurrence_count * t.total_order_count) / 
    ((SELECT COUNT(DISTINCT order_id) FROM order_items_flattened WHERE product_sku = pp.product_a) *
     (SELECT COUNT(DISTINCT order_id) FROM order_items_flattened WHERE product_sku = pp.product_b)) as lift,
  CURRENT_TIMESTAMP() as last_updated
FROM product_pairs pp
CROSS JOIN total_orders t
WHERE pp.co_occurrence_count >= 5
  AND pp.unique_users >= 3;

-- 3. Reorder Intelligence Patterns
-- Predicts when users will reorder specific products
CREATE MATERIALIZED VIEW IF NOT EXISTS `leafloafai.leafloaf_analytics.reorder_intelligence_patterns`
PARTITION BY DATE(last_updated)
CLUSTER BY user_id, product_sku
AS
WITH user_product_orders AS (
  SELECT 
    user_id,
    item.sku as product_sku,
    item.name as product_name,
    order_id,
    timestamp,
    item.quantity as quantity
  FROM `leafloafai.leafloaf_analytics.order_transaction_events`,
  UNNEST(items) as item
  WHERE user_id IS NOT NULL
    AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
),
order_intervals AS (
  SELECT 
    user_id,
    product_sku,
    product_name,
    timestamp,
    quantity,
    LAG(timestamp) OVER (PARTITION BY user_id, product_sku ORDER BY timestamp) as prev_order_time,
    DATE_DIFF(
      DATE(timestamp), 
      DATE(LAG(timestamp) OVER (PARTITION BY user_id, product_sku ORDER BY timestamp)), 
      DAY
    ) as days_between_orders
  FROM user_product_orders
),
reorder_stats AS (
  SELECT 
    user_id,
    product_sku,
    product_name,
    COUNT(*) as order_count,
    AVG(days_between_orders) as avg_reorder_days,
    STDDEV(days_between_orders) as reorder_variance,
    MIN(days_between_orders) as min_reorder_days,
    MAX(days_between_orders) as max_reorder_days,
    AVG(quantity) as avg_quantity,
    MAX(timestamp) as last_order_date,
    DATE_DIFF(CURRENT_DATE(), DATE(MAX(timestamp)), DAY) as days_since_last_order
  FROM order_intervals
  WHERE days_between_orders IS NOT NULL
  GROUP BY user_id, product_sku, product_name
  HAVING COUNT(*) >= 2  -- At least 3 orders to establish pattern
)
SELECT 
  user_id,
  product_sku,
  product_name,
  order_count,
  avg_reorder_days,
  reorder_variance,
  -- Coefficient of variation for consistency
  SAFE_DIVIDE(reorder_variance, avg_reorder_days) as reorder_consistency,
  avg_quantity,
  last_order_date,
  days_since_last_order,
  -- Predict if reorder is due
  CASE 
    WHEN days_since_last_order >= avg_reorder_days * 0.8 THEN TRUE
    ELSE FALSE
  END as reorder_due,
  -- Confidence based on order count and consistency
  LEAST(1.0, 
    (order_count / 10.0) * 
    (1.0 - LEAST(1.0, SAFE_DIVIDE(reorder_variance, avg_reorder_days)))
  ) as reorder_confidence,
  CURRENT_TIMESTAMP() as last_updated
FROM reorder_stats
WHERE avg_reorder_days IS NOT NULL
  AND avg_reorder_days <= 90;  -- Focus on regularly purchased items

-- 4. User Shopping Behavior Patterns
-- Captures overall shopping patterns and habits
CREATE MATERIALIZED VIEW IF NOT EXISTS `leafloafai.leafloaf_analytics.user_shopping_behavior_patterns`
PARTITION BY DATE(last_updated)
CLUSTER BY user_id
AS
WITH user_orders AS (
  SELECT 
    user_id,
    order_id,
    timestamp,
    EXTRACT(DAYOFWEEK FROM timestamp) as day_of_week,
    EXTRACT(HOUR FROM timestamp) as hour_of_day,
    order_total,
    item_count
  FROM `leafloafai.leafloaf_analytics.order_transaction_events`
  WHERE user_id IS NOT NULL
    AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
),
shopping_stats AS (
  SELECT 
    user_id,
    COUNT(DISTINCT order_id) as total_orders,
    COUNT(DISTINCT DATE(timestamp)) as shopping_days,
    AVG(order_total) as avg_order_value,
    STDDEV(order_total) as order_value_variance,
    AVG(item_count) as avg_items_per_order,
    -- Most common shopping day
    ARRAY_AGG(day_of_week ORDER BY COUNT(*) DESC LIMIT 1)[OFFSET(0)] as preferred_day_of_week,
    -- Most common shopping hour
    ARRAY_AGG(hour_of_day ORDER BY COUNT(*) DESC LIMIT 1)[OFFSET(0)] as preferred_hour,
    -- Shopping frequency
    DATE_DIFF(CURRENT_DATE(), DATE(MIN(timestamp)), DAY) / COUNT(DISTINCT order_id) as avg_days_between_orders,
    MAX(timestamp) as last_order_date
  FROM user_orders
  GROUP BY user_id
),
category_preferences AS (
  SELECT 
    p.user_id,
    p.category,
    COUNT(*) as category_purchase_count,
    SUM(CASE WHEN p.interaction_type = 'add_to_cart' THEN 1 ELSE 0 END) as category_cart_adds
  FROM `leafloafai.leafloaf_analytics.product_interaction_events` p
  WHERE p.user_id IS NOT NULL
    AND p.timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 180 DAY)
  GROUP BY 1, 2
),
top_categories AS (
  SELECT 
    user_id,
    ARRAY_AGG(
      STRUCT(category, category_purchase_count)
      ORDER BY category_purchase_count DESC
      LIMIT 5
    ) as top_categories
  FROM category_preferences
  GROUP BY user_id
)
SELECT 
  s.user_id,
  s.total_orders,
  s.shopping_days,
  s.avg_order_value,
  s.order_value_variance,
  s.avg_items_per_order,
  CASE s.preferred_day_of_week
    WHEN 1 THEN 'Sunday'
    WHEN 2 THEN 'Monday'
    WHEN 3 THEN 'Tuesday'
    WHEN 4 THEN 'Wednesday'
    WHEN 5 THEN 'Thursday'
    WHEN 6 THEN 'Friday'
    WHEN 7 THEN 'Saturday'
  END as preferred_shopping_day,
  s.preferred_hour as preferred_shopping_hour,
  s.avg_days_between_orders,
  CASE 
    WHEN s.avg_days_between_orders <= 7 THEN 'weekly'
    WHEN s.avg_days_between_orders <= 14 THEN 'bi-weekly'
    WHEN s.avg_days_between_orders <= 30 THEN 'monthly'
    ELSE 'occasional'
  END as shopping_frequency,
  s.last_order_date,
  tc.top_categories,
  CURRENT_TIMESTAMP() as last_updated
FROM shopping_stats s
LEFT JOIN top_categories tc ON s.user_id = tc.user_id
WHERE s.total_orders >= 3;

-- 5. Real-time Session Context (refreshed every hour)
-- Captures current session behavior for immediate personalization
CREATE MATERIALIZED VIEW IF NOT EXISTS `leafloafai.leafloaf_analytics.session_context_patterns`
PARTITION BY DATE(session_start)
CLUSTER BY session_id, user_id
AS
WITH session_events AS (
  SELECT 
    session_id,
    user_id,
    MIN(timestamp) as session_start,
    MAX(timestamp) as session_end,
    COUNT(DISTINCT query) as unique_queries,
    COUNT(*) as total_searches,
    ARRAY_AGG(DISTINCT query IGNORE NULLS) as search_queries
  FROM `leafloafai.leafloaf_analytics.user_search_events`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  GROUP BY session_id, user_id
),
session_interactions AS (
  SELECT 
    session_id,
    COUNT(DISTINCT product_sku) as products_viewed,
    SUM(CASE WHEN interaction_type = 'click' THEN 1 ELSE 0 END) as clicks,
    SUM(CASE WHEN interaction_type = 'add_to_cart' THEN 1 ELSE 0 END) as cart_adds,
    ARRAY_AGG(
      STRUCT(product_sku, product_name, category)
      ORDER BY timestamp DESC
      LIMIT 10
    ) as recent_products
  FROM `leafloafai.leafloaf_analytics.product_interaction_events`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  GROUP BY session_id
),
session_cart AS (
  SELECT 
    session_id,
    SUM(CASE WHEN action = 'add' THEN 1 ELSE 0 END) as items_added,
    SUM(CASE WHEN action = 'remove' THEN 1 ELSE 0 END) as items_removed,
    MAX(cart_total_after) as current_cart_total
  FROM `leafloafai.leafloaf_analytics.cart_modification_events`
  WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
  GROUP BY session_id
)
SELECT 
  se.session_id,
  se.user_id,
  se.session_start,
  se.session_end,
  TIMESTAMP_DIFF(se.session_end, se.session_start, MINUTE) as session_duration_minutes,
  se.unique_queries,
  se.total_searches,
  se.search_queries,
  IFNULL(si.products_viewed, 0) as products_viewed,
  IFNULL(si.clicks, 0) as clicks,
  IFNULL(si.cart_adds, 0) as cart_adds,
  si.recent_products,
  IFNULL(sc.items_added, 0) as items_added_to_cart,
  IFNULL(sc.items_removed, 0) as items_removed_from_cart,
  IFNULL(sc.current_cart_total, 0) as current_cart_total,
  -- Infer session intent
  CASE 
    WHEN si.cart_adds > 0 THEN 'shopping'
    WHEN si.clicks > 5 THEN 'browsing'
    WHEN se.unique_queries > 3 THEN 'exploring'
    ELSE 'searching'
  END as session_intent,
  CURRENT_TIMESTAMP() as last_updated
FROM session_events se
LEFT JOIN session_interactions si ON se.session_id = si.session_id
LEFT JOIN session_cart sc ON se.session_id = sc.session_id;

-- Create scheduled queries to refresh materialized views

-- Hourly refresh for session context and preferences
CREATE OR REPLACE SCHEDULED QUERY 
  `leafloafai.leafloaf_analytics.refresh_hourly_patterns`
OPTIONS (
  query = """
    REFRESH MATERIALIZED VIEW `leafloafai.leafloaf_analytics.user_preference_patterns`;
    REFRESH MATERIALIZED VIEW `leafloafai.leafloaf_analytics.session_context_patterns`;
  """,
  schedule = "every 1 hours",
  time_zone = "UTC"
);

-- 6-hour refresh for reorder patterns
CREATE OR REPLACE SCHEDULED QUERY 
  `leafloafai.leafloaf_analytics.refresh_reorder_patterns`
OPTIONS (
  query = """
    REFRESH MATERIALIZED VIEW `leafloafai.leafloaf_analytics.reorder_intelligence_patterns`;
  """,
  schedule = "every 6 hours",
  time_zone = "UTC"
);

-- Daily refresh for associations and behavior
CREATE OR REPLACE SCHEDULED QUERY 
  `leafloafai.leafloaf_analytics.refresh_daily_patterns`
OPTIONS (
  query = """
    REFRESH MATERIALIZED VIEW `leafloafai.leafloaf_analytics.product_association_patterns`;
    REFRESH MATERIALIZED VIEW `leafloafai.leafloaf_analytics.user_shopping_behavior_patterns`;
  """,
  schedule = "every 24 hours starts 2024-01-01 02:00:00 UTC",
  time_zone = "UTC"
);