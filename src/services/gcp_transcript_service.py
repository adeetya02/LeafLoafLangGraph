"""
GCP-native transcript processing service
Handles voice transcripts with Cloud Storage, Pub/Sub, and BigQuery
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
import structlog
from google.cloud import storage, pubsub_v1, bigquery
from google.cloud.exceptions import NotFound
import os

logger = structlog.get_logger()

class GCPTranscriptService:
    """Production-ready transcript service for GCP"""
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "leafloaf-prod")
        
        # GCP clients (lazy initialization)
        self._storage_client = None
        self._pubsub_publisher = None
        self._bigquery_client = None
        
        # Configuration
        self.bucket_name = os.getenv("VOICE_BUCKET", "leafloaf-voice")
        self.topic_name = os.getenv("VOICE_TOPIC", "voice-transcripts")
        self.dataset_id = "leafloaf_analytics"
        self.table_id = "voice_conversations"
        
        # Local queue for batching (optional)
        self.batch_queue = []
        self.batch_size = 10
        self.batch_interval = 5.0  # seconds
        
    @property
    def storage_client(self):
        """Lazy load Cloud Storage client"""
        if not self._storage_client:
            self._storage_client = storage.Client(project=self.project_id)
        return self._storage_client
    
    @property
    def pubsub_publisher(self):
        """Lazy load Pub/Sub publisher"""
        if not self._pubsub_publisher:
            self._pubsub_publisher = pubsub_v1.PublisherClient()
        return self._pubsub_publisher
    
    @property
    def bigquery_client(self):
        """Lazy load BigQuery client"""
        if not self._bigquery_client:
            self._bigquery_client = bigquery.Client(project=self.project_id)
        return self._bigquery_client
    
    async def capture_transcript(self, user_id: str, session_id: str, 
                               transcript: str, response: str, 
                               metadata: Optional[Dict] = None) -> str:
        """Capture transcript and store in Cloud Storage"""
        try:
            # Create transcript document
            transcript_id = f"{session_id}_{datetime.utcnow().timestamp()}"
            transcript_doc = {
                "transcript_id": transcript_id,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "session_id": session_id,
                "transcript": transcript,
                "response": response,
                "metadata": metadata or {},
                "processing_status": "pending"
            }
            
            # Save to Cloud Storage
            blob_path = f"transcripts/{datetime.utcnow().strftime('%Y-%m-%d')}/{transcript_id}.json"
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(blob_path)
            
            blob.upload_from_string(
                json.dumps(transcript_doc, indent=2),
                content_type="application/json"
            )
            
            logger.info(f"Stored transcript in GCS", 
                       bucket=self.bucket_name, 
                       path=blob_path)
            
            # Publish to Pub/Sub for async processing
            topic_path = self.pubsub_publisher.topic_path(
                self.project_id, 
                self.topic_name
            )
            
            message = {
                "transcript_id": transcript_id,
                "user_id": user_id,
                "session_id": session_id,
                "gcs_path": f"gs://{self.bucket_name}/{blob_path}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            future = self.pubsub_publisher.publish(
                topic_path,
                json.dumps(message).encode("utf-8")
            )
            
            # Don't wait for publish confirmation (fire-and-forget)
            logger.info(f"Published to Pub/Sub", topic=self.topic_name)
            
            # Add to batch queue for BigQuery
            self.batch_queue.append({
                "transcript_id": transcript_id,
                "user_id": user_id,
                "session_id": session_id,
                "transcript_text": transcript,
                "response_text": response,
                "timestamp": datetime.utcnow(),
                "is_product_search": metadata.get("is_product_search", False),
                "product_count": metadata.get("product_count", 0)
            })
            
            # Check if we should flush batch
            if len(self.batch_queue) >= self.batch_size:
                await self._flush_to_bigquery()
            
            return transcript_id
            
        except Exception as e:
            logger.error(f"Error capturing transcript: {e}")
            # Don't fail the voice conversation
            return f"error_{datetime.utcnow().timestamp()}"
    
    async def _flush_to_bigquery(self):
        """Flush batch to BigQuery"""
        if not self.batch_queue:
            return
            
        try:
            table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
            table = self.bigquery_client.get_table(table_ref)
            
            errors = self.bigquery_client.insert_rows_json(
                table, 
                self.batch_queue
            )
            
            if errors:
                logger.error(f"BigQuery insert errors: {errors}")
            else:
                logger.info(f"Flushed {len(self.batch_queue)} transcripts to BigQuery")
                
            # Clear queue
            self.batch_queue = []
            
        except NotFound:
            logger.error(f"BigQuery table not found: {table_ref}")
        except Exception as e:
            logger.error(f"Error flushing to BigQuery: {e}")
    
    async def get_user_voice_insights(self, user_id: str) -> Dict[str, Any]:
        """Get voice insights from BigQuery"""
        try:
            query = f"""
            SELECT 
                COUNT(*) as total_conversations,
                AVG(CASE WHEN sentiment_score IS NOT NULL THEN sentiment_score ELSE 0 END) as avg_sentiment,
                ARRAY_AGG(DISTINCT intent IGNORE NULLS) as intents,
                ARRAY_AGG(DISTINCT topic IGNORE NULLS) as topics,
                MAX(timestamp) as last_conversation
            FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
            WHERE user_id = @user_id
                AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id)
                ]
            )
            
            query_job = self.bigquery_client.query(query, job_config=job_config)
            results = list(query_job.result())
            
            if results:
                row = results[0]
                return {
                    "total_conversations": row.total_conversations,
                    "avg_sentiment": float(row.avg_sentiment) if row.avg_sentiment else 0,
                    "common_intents": list(row.intents) if row.intents else [],
                    "favorite_topics": list(row.topics) if row.topics else [],
                    "last_conversation": row.last_conversation.isoformat() if row.last_conversation else None
                }
            
            return {
                "total_conversations": 0,
                "avg_sentiment": 0,
                "common_intents": [],
                "favorite_topics": [],
                "last_conversation": None
            }
            
        except Exception as e:
            logger.error(f"Error getting voice insights: {e}")
            return {}
    
    async def start_batch_processor(self):
        """Start background task to flush batches periodically"""
        while True:
            await asyncio.sleep(self.batch_interval)
            if self.batch_queue:
                await self._flush_to_bigquery()


# Singleton instance
_gcp_service: Optional[GCPTranscriptService] = None

def get_gcp_transcript_service() -> GCPTranscriptService:
    """Get or create the GCP transcript service singleton"""
    global _gcp_service
    if _gcp_service is None:
        _gcp_service = GCPTranscriptService()
    return _gcp_service