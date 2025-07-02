#!/usr/bin/env python3
"""
Create additional BigQuery tables needed by analytics_service
"""

from google.cloud import bigquery
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_additional_tables():
    """Create additional tables used by analytics_service"""
    
    project_id = "leafloafai"
    dataset_id = "leafloaf_analytics"
    
    client = bigquery.Client(project=project_id)
    
    # Additional tables needed by analytics_service
    tables = {
        "user_events": [
            bigquery.SchemaField("event_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("session_id", "STRING"),
            bigquery.SchemaField("event_type", "STRING"),
            bigquery.SchemaField("event_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("device_type", "STRING"),
            bigquery.SchemaField("user_agent", "STRING"),
            # Event-specific fields
            bigquery.SchemaField("query", "STRING"),
            bigquery.SchemaField("intent", "STRING"),
            bigquery.SchemaField("confidence", "FLOAT"),
            bigquery.SchemaField("alpha", "FLOAT"),
            bigquery.SchemaField("results_count", "INTEGER"),
            bigquery.SchemaField("search_latency_ms", "INTEGER"),
        ],
        "search_events": [
            bigquery.SchemaField("search_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("session_id", "STRING"),
            bigquery.SchemaField("query", "STRING"),
            bigquery.SchemaField("alpha_value", "FLOAT"),
            bigquery.SchemaField("results_count", "INTEGER"),
            bigquery.SchemaField("clicked_results", "STRING", mode="REPEATED"),
            bigquery.SchemaField("search_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("response_time_ms", "INTEGER"),
            bigquery.SchemaField("search_type", "STRING"),
        ],
        "cart_events": [
            bigquery.SchemaField("event_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("session_id", "STRING"),
            bigquery.SchemaField("event_type", "STRING"),
            bigquery.SchemaField("product_sku", "STRING"),
            bigquery.SchemaField("product_name", "STRING"),
            bigquery.SchemaField("quantity", "INTEGER"),
            bigquery.SchemaField("price", "FLOAT"),
            bigquery.SchemaField("event_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("cart_total_after", "FLOAT"),
        ],
        "order_events": [
            bigquery.SchemaField("order_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("order_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("order_total", "FLOAT"),
            bigquery.SchemaField("discount_total", "FLOAT"),
            bigquery.SchemaField("promotions_applied", "STRING", mode="REPEATED"),
            bigquery.SchemaField("products", "RECORD", mode="REPEATED", fields=[
                bigquery.SchemaField("sku", "STRING"),
                bigquery.SchemaField("name", "STRING"),
                bigquery.SchemaField("quantity", "INTEGER"),
                bigquery.SchemaField("unit_price", "FLOAT"),
                bigquery.SchemaField("total_price", "FLOAT"),
            ]),
            bigquery.SchemaField("delivery_method", "STRING"),
            bigquery.SchemaField("payment_method", "STRING"),
        ],
        "promotion_usage": [
            bigquery.SchemaField("usage_id", "STRING"),
            bigquery.SchemaField("promotion_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("order_id", "STRING"),
            bigquery.SchemaField("discount_amount", "FLOAT"),
            bigquery.SchemaField("usage_timestamp", "TIMESTAMP"),
            bigquery.SchemaField("products_discounted", "STRING", mode="REPEATED"),
        ],
    }
    
    # Create tables
    for table_name, schema in tables.items():
        table_id = f"{project_id}.{dataset_id}.{table_name}"
        
        try:
            table = client.get_table(table_id)
            logger.info(f"Table {table_name} already exists")
        except:
            table = bigquery.Table(table_id, schema=schema)
            table = client.create_table(table)
            logger.info(f"Created table {table_name}")
    
    logger.info("All additional tables created successfully!")

if __name__ == "__main__":
    create_additional_tables()
