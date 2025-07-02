"""
Flexible Data Capture Strategy
Works with Redis, fallback to Cloud Storage/BigQuery
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from abc import ABC, abstractmethod
import structlog
from google.cloud import storage, bigquery
from src.cache.redis_feature import redis_feature, smart_redis_manager

logger = structlog.get_logger()

class DataCaptureBackend(ABC):
    """Abstract base for data capture backends"""
    
    @abstractmethod
    async def capture_search(self, search_data: Dict) -> bool:
        pass
    
    @abstractmethod
    async def capture_order(self, order_data: Dict) -> bool:
        pass
    
    @abstractmethod
    async def capture_interaction(self, interaction_data: Dict) -> bool:
        pass
    
    @abstractmethod
    async def get_user_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        pass

class RedisBackend(DataCaptureBackend):
    """Redis backend for real-time data capture"""
    
    def __init__(self):
        self.redis = smart_redis_manager
    
    async def capture_search(self, search_data: Dict) -> bool:
        try:
            manager = await self.redis._get_manager()
            await manager.log_search(**search_data)
            return True
        except Exception as e:
            logger.error(f"Redis capture failed: {e}")
            return False
    
    async def capture_order(self, order_data: Dict) -> bool:
        # Implement order capture to Redis
        return True
    
    async def capture_interaction(self, interaction_data: Dict) -> bool:
        # Implement interaction capture to Redis
        return True
    
    async def get_user_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        try:
            manager = await self.redis._get_manager()
            return await manager.get_user_search_history(user_id, limit)
        except:
            return []

class CloudStorageBackend(DataCaptureBackend):
    """Cloud Storage backend for reliable data capture"""
    
    def __init__(self, bucket_name: str = "leafloaf-user-data"):
        self.bucket_name = bucket_name
        self.client = None
        self.buffer = []
        self.buffer_size = 100  # Batch writes
        self.last_flush = time.time()
        self.flush_interval = 60  # seconds
    
    def _get_client(self):
        if not self.client:
            self.client = storage.Client()
        return self.client
    
    async def capture_search(self, search_data: Dict) -> bool:
        """Capture search to Cloud Storage (batched)"""
        event = {
            "event_type": "search",
            "timestamp": datetime.utcnow().isoformat(),
            "data": search_data
        }
        
        self.buffer.append(event)
        
        # Flush if buffer is full or time elapsed
        if len(self.buffer) >= self.buffer_size or \
           (time.time() - self.last_flush) > self.flush_interval:
            await self._flush_buffer()
        
        return True
    
    async def _flush_buffer(self):
        """Flush buffer to Cloud Storage"""
        if not self.buffer:
            return
        
        try:
            client = self._get_client()
            bucket = client.bucket(self.bucket_name)
            
            # Create filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            blob_name = f"events/{timestamp}_{len(self.buffer)}_events.jsonl"
            
            blob = bucket.blob(blob_name)
            
            # Convert to JSONL format
            jsonl_data = "\n".join(json.dumps(event) for event in self.buffer)
            
            # Upload
            blob.upload_from_string(jsonl_data, content_type="application/x-ndjson")
            
            logger.info(f"Flushed {len(self.buffer)} events to {blob_name}")
            self.buffer = []
            self.last_flush = time.time()
            
        except Exception as e:
            logger.error(f"Failed to flush to Cloud Storage: {e}")
    
    async def capture_order(self, order_data: Dict) -> bool:
        event = {
            "event_type": "order",
            "timestamp": datetime.utcnow().isoformat(),
            "data": order_data
        }
        self.buffer.append(event)
        return True
    
    async def capture_interaction(self, interaction_data: Dict) -> bool:
        event = {
            "event_type": "interaction",
            "timestamp": datetime.utcnow().isoformat(),
            "data": interaction_data
        }
        self.buffer.append(event)
        return True
    
    async def get_user_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        # This would query from processed data in BigQuery
        return []

class BigQueryBackend(DataCaptureBackend):
    """BigQuery backend for analytics and ML"""
    
    def __init__(self, dataset_id: str = "leafloaf_events"):
        self.dataset_id = dataset_id
        self.client = None
        self.tables = {
            "searches": "user_searches",
            "orders": "user_orders",
            "interactions": "user_interactions"
        }
    
    def _get_client(self):
        if not self.client:
            self.client = bigquery.Client()
        return self.client
    
    async def capture_search(self, search_data: Dict) -> bool:
        """Stream search directly to BigQuery"""
        try:
            client = self._get_client()
            table_id = f"{client.project}.{self.dataset_id}.{self.tables['searches']}"
            
            row = {
                "user_id": search_data.get("user_id"),
                "session_id": search_data.get("session_id"),
                "query": search_data.get("query"),
                "intent": search_data.get("intent"),
                "results_count": search_data.get("results_count"),
                "timestamp": datetime.utcnow(),
                "metadata": json.dumps(search_data.get("metadata", {}))
            }
            
            errors = client.insert_rows_json(table_id, [row])
            if not errors:
                return True
            else:
                logger.error(f"BigQuery insert failed: {errors}")
                return False
                
        except Exception as e:
            logger.error(f"BigQuery capture failed: {e}")
            return False
    
    async def capture_order(self, order_data: Dict) -> bool:
        # Similar implementation for orders
        return True
    
    async def capture_interaction(self, interaction_data: Dict) -> bool:
        # Similar implementation for interactions
        return True
    
    async def get_user_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Query user history from BigQuery"""
        try:
            client = self._get_client()
            query = f"""
            SELECT *
            FROM `{self.dataset_id}.{self.tables['searches']}`
            WHERE user_id = @user_id
            ORDER BY timestamp DESC
            LIMIT @limit
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                    bigquery.ScalarQueryParameter("limit", "INT64", limit),
                ]
            )
            
            query_job = client.query(query, job_config=job_config)
            results = list(query_job)
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"BigQuery query failed: {e}")
            return []

class HybridDataCapture:
    """
    Hybrid data capture that uses multiple backends
    Ensures no data loss and provides flexibility
    """
    
    def __init__(self):
        self.backends = []
        
        # Add Redis if enabled
        if redis_feature.enabled:
            self.backends.append(("redis", RedisBackend()))
        
        # Always add Cloud Storage for reliability
        self.backends.append(("cloud_storage", CloudStorageBackend()))
        
        # Add BigQuery for analytics (optional)
        if self._should_use_bigquery():
            self.backends.append(("bigquery", BigQueryBackend()))
        
        logger.info(f"Data capture initialized with backends: {[name for name, _ in self.backends]}")
    
    def _should_use_bigquery(self) -> bool:
        """Check if BigQuery should be used"""
        import os
        return os.getenv("ENABLE_BIGQUERY", "false").lower() == "true"
    
    async def capture_search(self, 
                           user_id: str,
                           session_id: str,
                           query: str,
                           intent: str,
                           results: List[Dict],
                           response_time_ms: float,
                           metadata: Optional[Dict] = None) -> bool:
        """
        Capture search event to all backends
        Fire-and-forget pattern for non-blocking
        """
        
        search_data = {
            "user_id": user_id,
            "user_uuid": metadata.get("user_uuid", ""),
            "session_id": session_id,
            "query": query,
            "intent": intent,
            "confidence": metadata.get("confidence", 0.8),
            "results": results,
            "results_count": len(results),
            "response_time_ms": response_time_ms,
            "metadata": metadata
        }
        
        # Fire and forget - don't wait
        asyncio.create_task(self._capture_to_all_backends("search", search_data))
        
        return True
    
    async def _capture_to_all_backends(self, event_type: str, data: Dict):
        """Capture to all backends asynchronously"""
        tasks = []
        
        for name, backend in self.backends:
            if event_type == "search":
                task = backend.capture_search(data)
            elif event_type == "order":
                task = backend.capture_order(data)
            else:
                task = backend.capture_interaction(data)
            
            tasks.append((name, task))
        
        # Run all captures in parallel
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # Log results
        for (name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Backend {name} failed: {result}")
            elif not result:
                logger.warning(f"Backend {name} returned false")
    
    async def capture_order(self, order_data: Dict) -> bool:
        """Capture order event"""
        asyncio.create_task(self._capture_to_all_backends("order", order_data))
        return True
    
    async def get_user_data_for_ml(self, user_id: str) -> Dict:
        """
        Get user data for ML (cached if Redis available)
        This is async but with timeout for recommendation engine
        """
        
        # Try Redis first (fastest)
        for name, backend in self.backends:
            if name == "redis":
                try:
                    history = await asyncio.wait_for(
                        backend.get_user_history(user_id, limit=50),
                        timeout=0.5  # 500ms timeout
                    )
                    if history:
                        return self._process_for_ml(history)
                except asyncio.TimeoutError:
                    logger.warning("Redis timeout, falling back")
                    continue
        
        # Fallback to BigQuery (slower but complete)
        for name, backend in self.backends:
            if name == "bigquery":
                try:
                    history = await asyncio.wait_for(
                        backend.get_user_history(user_id, limit=100),
                        timeout=2.0  # 2 second timeout
                    )
                    return self._process_for_ml(history)
                except asyncio.TimeoutError:
                    logger.warning("BigQuery timeout for ML data")
        
        # Return empty if all fail
        return {"user_id": user_id, "features": {}}
    
    def _process_for_ml(self, history: List[Dict]) -> Dict:
        """Process raw history into ML features"""
        # Extract features for recommendation
        features = {
            "search_count": len(history),
            "common_queries": self._get_common_queries(history),
            "preferred_categories": self._get_preferred_categories(history),
            "avg_results_clicked": self._get_avg_clicks(history),
            "session_patterns": self._get_session_patterns(history)
        }
        
        return {
            "user_id": history[0]["user_id"] if history else "unknown",
            "features": features,
            "history_sample": history[:10]  # Recent history
        }
    
    def _get_common_queries(self, history: List[Dict]) -> List[str]:
        # Implementation
        return []
    
    def _get_preferred_categories(self, history: List[Dict]) -> Dict[str, float]:
        # Implementation
        return {}
    
    def _get_avg_clicks(self, history: List[Dict]) -> float:
        # Implementation
        return 0.0
    
    def _get_session_patterns(self, history: List[Dict]) -> Dict:
        # Implementation
        return {}

class FlexibleDataCapture:
    """
    Main data capture interface with BigQuery integration
    Used by order confirmation and other components
    """
    
    def __init__(self):
        # Use BigQuery client for primary storage
        from src.analytics.bigquery_client import bigquery_client
        self.bigquery = bigquery_client
        
        # Optional Redis for caching
        self.redis_backend = RedisBackend() if redis_feature.enabled else None
        
        # Cloud Storage for backup
        self.storage_backend = CloudStorageBackend()
    
    async def capture_order(self, order_data: Dict) -> bool:
        """Capture order to all backends"""
        try:
            # Primary: Stream to BigQuery
            asyncio.create_task(self.bigquery.stream_order_event(order_data))
            
            # Secondary: Redis cache (if available)
            if self.redis_backend:
                asyncio.create_task(self.redis_backend.capture_order(order_data))
            
            # Backup: Cloud Storage
            asyncio.create_task(self.storage_backend.capture_order(order_data))
            
            logger.info(f"Order {order_data.get('order_id')} captured to data pipeline")
            return True
            
        except Exception as e:
            logger.error(f"Failed to capture order: {e}")
            return False
    
    async def capture_search(self, search_data: Dict) -> bool:
        """Capture search event"""
        try:
            asyncio.create_task(self.bigquery.stream_search_event(search_data))
            
            if self.redis_backend:
                asyncio.create_task(self.redis_backend.capture_search(search_data))
            
            return True
        except Exception as e:
            logger.error(f"Failed to capture search: {e}")
            return False
    
    async def capture_interaction(self, interaction_data: Dict) -> bool:
        """Capture product interaction"""
        try:
            asyncio.create_task(self.bigquery.stream_interaction_event(interaction_data))
            return True
        except Exception as e:
            logger.error(f"Failed to capture interaction: {e}")
            return False
    
    async def capture_cart_modification(self, cart_data: Dict) -> bool:
        """Capture cart changes"""
        try:
            asyncio.create_task(self.bigquery.stream_cart_event(cart_data))
            return True
        except Exception as e:
            logger.error(f"Failed to capture cart event: {e}")
            return False


# Global instances
data_capture = HybridDataCapture()
flexible_data_capture = FlexibleDataCapture()