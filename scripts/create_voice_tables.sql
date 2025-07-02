-- BigQuery schema for voice conversations and analysis
-- Run this in BigQuery console for project: leafloaf-prod

-- Create dataset if not exists
CREATE SCHEMA IF NOT EXISTS `leafloaf-prod.leafloaf_analytics`
OPTIONS(
  description="Analytics data for LeafLoaf voice conversations",
  location="us-central1"
);

-- Main voice conversations table
CREATE OR REPLACE TABLE `leafloaf-prod.leafloaf_analytics.voice_conversations` (
  transcript_id STRING NOT NULL,
  user_id STRING NOT NULL,
  session_id STRING NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  
  -- Conversation content
  transcript_text STRING NOT NULL,
  response_text STRING NOT NULL,
  
  -- Metadata
  is_product_search BOOLEAN,
  product_count INTEGER,
  conversation_duration_ms INTEGER,
  
  -- Analysis results (populated by Cloud Function)
  sentiment STRING,
  sentiment_score FLOAT64,
  intent STRING,
  intent_confidence FLOAT64,
  topics ARRAY<STRING>,
  entities ARRAY<STRUCT<
    entity STRING,
    type STRING,
    confidence FLOAT64
  >>,
  summary STRING,
  
  -- Processing metadata
  processing_status STRING DEFAULT 'pending',
  processed_at TIMESTAMP,
  deepgram_request_id STRING,
  
  -- Partitioning for performance
  _PARTITIONTIME TIMESTAMP
)
PARTITION BY DATE(_PARTITIONTIME)
CLUSTER BY user_id, session_id;

-- Create view for user insights
CREATE OR REPLACE VIEW `leafloaf-prod.leafloaf_analytics.user_voice_insights` AS
SELECT 
  user_id,
  COUNT(DISTINCT session_id) as total_sessions,
  COUNT(*) as total_conversations,
  AVG(sentiment_score) as avg_sentiment,
  
  -- Most common intents
  ARRAY_AGG(DISTINCT intent IGNORE NULLS) as all_intents,
  
  -- Product search behavior
  COUNTIF(is_product_search) as product_searches,
  AVG(IF(is_product_search, product_count, NULL)) as avg_products_per_search,
  
  -- Engagement metrics
  MIN(timestamp) as first_conversation,
  MAX(timestamp) as last_conversation,
  
  -- Topics of interest
  ARRAY(
    SELECT AS STRUCT topic, COUNT(*) as count
    FROM UNNEST(topics) as topic
    GROUP BY topic
    ORDER BY count DESC
    LIMIT 10
  ) as top_topics,
  
  -- Common entities
  ARRAY(
    SELECT AS STRUCT entity, type, COUNT(*) as count
    FROM UNNEST(entities)
    GROUP BY entity, type
    ORDER BY count DESC
    LIMIT 20
  ) as common_entities

FROM `leafloaf-prod.leafloaf_analytics.voice_conversations`
WHERE timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
GROUP BY user_id;

-- Real-time streaming view (last 24 hours)
CREATE OR REPLACE VIEW `leafloaf-prod.leafloaf_analytics.voice_conversations_today` AS
SELECT *
FROM `leafloaf-prod.leafloaf_analytics.voice_conversations`
WHERE DATE(timestamp) = CURRENT_DATE()
ORDER BY timestamp DESC;