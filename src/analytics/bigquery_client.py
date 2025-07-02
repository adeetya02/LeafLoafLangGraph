"""
BigQuery Analytics Client for LeafLoaf

Handles streaming inserts for real-time analytics and ML features.
Fire-and-forget pattern for zero latency impact.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import structlog

logger = structlog.get_logger()


class BigQueryClient:
    """Async BigQuery client for analytics data capture"""
    
    def __init__(self, project_id: str = "leafloafai", dataset_id: str = "leafloaf_analytics"):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.client = None
        self._initialized = False
        
        # Table references
        self.tables = {
            "user_search_events": f"{project_id}.{dataset_id}.user_search_events",
            "product_interaction_events": f"{project_id}.{dataset_id}.product_interaction_events",
            "cart_modification_events": f"{project_id}.{dataset_id}.cart_modification_events",
            "order_transaction_events": f"{project_id}.{dataset_id}.order_transaction_events",
            "recommendation_impression_events": f"{project_id}.{dataset_id}.recommendation_impression_events"
        }
        
    def _get_client(self):
        """Lazy initialize BigQuery client"""
        if not self.client:
            self.client = bigquery.Client(project=self.project_id)
        return self.client
    
    async def stream_order_event(self, order_data: Dict[str, Any]) -> bool:
        """Stream order event to BigQuery"""
        try:
            event = {
                "event_id": order_data.get("order_id"),
                "user_id": order_data.get("user_id", "anonymous"),
                "session_id": order_data.get("session_id"),
                "timestamp": datetime.utcnow().isoformat(),
                "order_id": order_data.get("order_id"),
                "items": json.dumps(order_data.get("items", [])),
                "item_count": len(order_data.get("items", [])),
                "total_amount": order_data.get("totals", {}).get("estimated_total", 0),
                "order_status": order_data.get("status", "confirmed"),
                "metadata": json.dumps(order_data.get("metadata", {}))
            }
            
            # Fire and forget - don't await
            asyncio.create_task(self._insert_rows("order_transaction_events", [event]))
            
            # Also stream individual item events for ML
            for item in order_data.get("items", []):
                item_event = {
                    "event_id": f"{order_data.get('order_id')}_{item.get('sku', 'unknown')}",
                    "user_id": order_data.get("user_id", "anonymous"),
                    "session_id": order_data.get("session_id"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "order_id": order_data.get("order_id"),
                    "sku": item.get("sku"),
                    "product_name": item.get("name"),
                    "quantity": item.get("quantity", 1),
                    "price": item.get("price", 0),
                    "subtotal": item.get("quantity", 1) * item.get("price", 0)
                }
                asyncio.create_task(self._insert_rows("product_interaction_events", [item_event]))
            
            logger.info(f"Streamed order {order_data.get('order_id')} to BigQuery")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stream order event: {e}")
            return False
    
    async def stream_search_event(self, search_data: Dict[str, Any]) -> bool:
        """Stream search event to BigQuery"""
        try:
            event = {
                "event_id": search_data.get("request_id"),
                "user_id": search_data.get("user_id", "anonymous"),
                "session_id": search_data.get("session_id"),
                "timestamp": datetime.utcnow().isoformat(),
                "query": search_data.get("query"),
                "result_count": search_data.get("result_count", 0),
                "filters_applied": json.dumps(search_data.get("filters", {})),
                "alpha_value": search_data.get("alpha", 0.75),
                "search_type": search_data.get("search_type", "hybrid"),
                "latency_ms": search_data.get("latency_ms", 0)
            }
            
            asyncio.create_task(self._insert_rows("user_search_events", [event]))
            return True
            
        except Exception as e:
            logger.error(f"Failed to stream search event: {e}")
            return False
    
    async def stream_interaction_event(self, interaction_data: Dict[str, Any]) -> bool:
        """Stream product interaction event (view, click, etc)"""
        try:
            event = {
                "event_id": interaction_data.get("event_id"),
                "user_id": interaction_data.get("user_id", "anonymous"),
                "session_id": interaction_data.get("session_id"),
                "timestamp": datetime.utcnow().isoformat(),
                "interaction_type": interaction_data.get("type"),  # view, click, add_to_cart
                "sku": interaction_data.get("sku"),
                "product_name": interaction_data.get("product_name"),
                "position": interaction_data.get("position"),  # Position in search results
                "source": interaction_data.get("source"),  # search, recommendation, etc
                "metadata": json.dumps(interaction_data.get("metadata", {}))
            }
            
            asyncio.create_task(self._insert_rows("product_interaction_events", [event]))
            return True
            
        except Exception as e:
            logger.error(f"Failed to stream interaction event: {e}")
            return False
    
    async def stream_cart_event(self, cart_data: Dict[str, Any]) -> bool:
        """Stream cart modification event"""
        try:
            event = {
                "event_id": cart_data.get("event_id"),
                "user_id": cart_data.get("user_id", "anonymous"),
                "session_id": cart_data.get("session_id"),
                "timestamp": datetime.utcnow().isoformat(),
                "action": cart_data.get("action"),  # add, remove, update_quantity
                "sku": cart_data.get("sku"),
                "product_name": cart_data.get("product_name"),
                "quantity_before": cart_data.get("quantity_before", 0),
                "quantity_after": cart_data.get("quantity_after", 0),
                "cart_total_before": cart_data.get("cart_total_before", 0),
                "cart_total_after": cart_data.get("cart_total_after", 0)
            }
            
            asyncio.create_task(self._insert_rows("cart_modification_events", [event]))
            return True
            
        except Exception as e:
            logger.error(f"Failed to stream cart event: {e}")
            return False
    
    async def _insert_rows(self, table_name: str, rows: List[Dict[str, Any]]) -> None:
        """Insert rows into BigQuery table"""
        try:
            client = self._get_client()
            table_ref = self.tables.get(table_name)
            
            if not table_ref:
                logger.error(f"Unknown table: {table_name}")
                return
                
            table = client.get_table(table_ref)
            errors = client.insert_rows_json(table, rows)
            
            if errors:
                logger.error(f"BigQuery insert errors for {table_name}: {errors}")
            else:
                logger.debug(f"Inserted {len(rows)} rows into {table_name}")
                
        except GoogleCloudError as e:
            logger.error(f"BigQuery error for {table_name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error inserting to {table_name}: {e}")
    
    async def get_user_purchase_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get user purchase history for ML features"""
        try:
            client = self._get_client()
            
            query = f"""
            SELECT 
                order_id,
                timestamp,
                items,
                total_amount,
                item_count
            FROM `{self.tables['order_transaction_events']}`
            WHERE user_id = @user_id
            ORDER BY timestamp DESC
            LIMIT @limit
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                    bigquery.ScalarQueryParameter("limit", "INT64", limit)
                ]
            )
            
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()
            
            history = []
            for row in results:
                history.append({
                    "order_id": row["order_id"],
                    "timestamp": row["timestamp"],
                    "items": json.loads(row["items"]) if row["items"] else [],
                    "total_amount": row["total_amount"],
                    "item_count": row["item_count"]
                })
                
            return history
            
        except Exception as e:
            logger.error(f"Failed to get purchase history: {e}")
            return []
    
    async def get_popular_products(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get popular products for recommendations"""
        try:
            client = self._get_client()
            
            query = f"""
            SELECT 
                sku,
                product_name,
                COUNT(*) as order_count,
                SUM(quantity) as total_quantity,
                AVG(price) as avg_price
            FROM `{self.tables['product_interaction_events']}`
            WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
                AND sku IS NOT NULL
            GROUP BY sku, product_name
            ORDER BY order_count DESC
            LIMIT @limit
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("limit", "INT64", limit)
                ]
            )
            
            query_job = client.query(query, job_config=job_config)
            results = query_job.result()
            
            products = []
            for row in results:
                products.append({
                    "sku": row["sku"],
                    "name": row["product_name"],
                    "popularity_score": row["order_count"],
                    "total_quantity_sold": row["total_quantity"],
                    "avg_price": row["avg_price"]
                })
                
            return products
            
        except Exception as e:
            logger.error(f"Failed to get popular products: {e}")
            return []


# Global instance for easy access
bigquery_client = BigQueryClient()