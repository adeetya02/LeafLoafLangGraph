#!/usr/bin/env python3
"""
Verify data in BigQuery tables
"""

from google.cloud import bigquery
import json

def verify_data():
    """Check data in BigQuery tables"""
    
    project_id = "leafloafai"
    dataset_id = "leafloaf_analytics"
    
    client = bigquery.Client(project=project_id)
    
    # Check order_transaction_events
    query = f"""
    SELECT 
        order_id,
        user_id,
        timestamp,
        item_count,
        total_amount,
        items
    FROM `{project_id}.{dataset_id}.order_transaction_events`
    ORDER BY timestamp DESC
    LIMIT 5
    """
    
    print("📊 Recent Orders in BigQuery:")
    print("=" * 50)
    
    results = client.query(query).result()
    
    for row in results:
        print(f"\nOrder ID: {row.order_id}")
        print(f"User ID: {row.user_id}")
        print(f"Timestamp: {row.timestamp}")
        print(f"Items: {row.item_count}")
        print(f"Total: ${row.total_amount}")
        
        # Parse and display items
        if row["items"]:
            items = json.loads(row["items"])
            for item in items:
                print(f"  - {item.get('quantity')} {item.get('unit')} {item.get('name')} @ ${item.get('price')}")
    
    # Check product_interaction_events
    query2 = f"""
    SELECT COUNT(*) as count
    FROM `{project_id}.{dataset_id}.product_interaction_events`
    """
    
    result = list(client.query(query2).result())[0]
    print(f"\n✅ Total product interactions: {result.count}")

if __name__ == "__main__":
    verify_data()