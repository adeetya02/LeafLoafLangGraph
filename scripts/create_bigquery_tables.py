#!/usr/bin/env python3
"""
Create BigQuery tables for LeafLoaf analytics
"""

from google.cloud import bigquery
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Create all required BigQuery tables"""
    
    project_id = "leafloafai"
    dataset_id = "leafloaf_analytics"
    
    client = bigquery.Client(project=project_id)
    
    # Create dataset if it doesn't exist
    dataset_ref = f"{project_id}.{dataset_id}"
    try:
        dataset = client.get_dataset(dataset_ref)
        logger.info(f"Dataset {dataset_id} already exists")
    except:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "us-central1"
        dataset = client.create_dataset(dataset)
        logger.info(f"Created dataset {dataset_id}")
    
    # Define table schemas
    tables = {
        "user_search_events": [
            bigquery.SchemaField("event_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("session_id", "STRING"),
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("query", "STRING"),
            bigquery.SchemaField("result_count", "INTEGER"),
            bigquery.SchemaField("filters_applied", "STRING"),
            bigquery.SchemaField("alpha_value", "FLOAT"),
            bigquery.SchemaField("search_type", "STRING"),
            bigquery.SchemaField("latency_ms", "FLOAT"),
        ],
        "product_interaction_events": [
            bigquery.SchemaField("event_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("session_id", "STRING"),
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("interaction_type", "STRING"),
            bigquery.SchemaField("sku", "STRING"),
            bigquery.SchemaField("product_name", "STRING"),
            bigquery.SchemaField("quantity", "INTEGER"),
            bigquery.SchemaField("price", "FLOAT"),
            bigquery.SchemaField("subtotal", "FLOAT"),
            bigquery.SchemaField("order_id", "STRING"),
            bigquery.SchemaField("position", "INTEGER"),
            bigquery.SchemaField("source", "STRING"),
            bigquery.SchemaField("metadata", "STRING"),
        ],
        "cart_modification_events": [
            bigquery.SchemaField("event_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("session_id", "STRING"),
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("action", "STRING"),
            bigquery.SchemaField("sku", "STRING"),
            bigquery.SchemaField("product_name", "STRING"),
            bigquery.SchemaField("quantity_before", "INTEGER"),
            bigquery.SchemaField("quantity_after", "INTEGER"),
            bigquery.SchemaField("cart_total_before", "FLOAT"),
            bigquery.SchemaField("cart_total_after", "FLOAT"),
        ],
        "order_transaction_events": [
            bigquery.SchemaField("event_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("session_id", "STRING"),
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("order_id", "STRING"),
            bigquery.SchemaField("items", "STRING"),  # JSON
            bigquery.SchemaField("item_count", "INTEGER"),
            bigquery.SchemaField("total_amount", "FLOAT"),
            bigquery.SchemaField("order_status", "STRING"),
            bigquery.SchemaField("metadata", "STRING"),  # JSON
        ],
        "recommendation_impression_events": [
            bigquery.SchemaField("event_id", "STRING"),
            bigquery.SchemaField("user_id", "STRING"),
            bigquery.SchemaField("session_id", "STRING"),
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("recommendation_type", "STRING"),
            bigquery.SchemaField("products_shown", "STRING"),  # JSON array
            bigquery.SchemaField("position", "INTEGER"),
            bigquery.SchemaField("clicked", "BOOLEAN"),
            bigquery.SchemaField("added_to_cart", "BOOLEAN"),
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
    
    logger.info("All tables created successfully!")
    
    # List all tables
    tables = client.list_tables(dataset_ref)
    logger.info(f"\nTables in {dataset_id}:")
    for table in tables:
        logger.info(f"  - {table.table_id}")

if __name__ == "__main__":
    create_tables()