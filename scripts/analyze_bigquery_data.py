#!/usr/bin/env python3
"""
Analyze and visualize BigQuery data from multi-user test
"""

from google.cloud import bigquery
import json
from datetime import datetime
from collections import defaultdict

def analyze_data():
    """Analyze shopping patterns in BigQuery"""
    
    project_id = "leafloafai"
    dataset_id = "leafloaf_analytics"
    
    client = bigquery.Client(project=project_id)
    
    print("📊 LeafLoaf Shopping Analytics Report")
    print("=" * 60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Total orders and revenue
    query = f"""
    SELECT 
        COUNT(DISTINCT order_id) as total_orders,
        COUNT(DISTINCT user_id) as total_users,
        SUM(total_amount) as total_revenue,
        AVG(total_amount) as avg_order_value,
        MAX(total_amount) as max_order_value,
        MIN(total_amount) as min_order_value
    FROM `{project_id}.{dataset_id}.order_transaction_events`
    """
    
    results = list(client.query(query).result())[0]
    print("📈 Overall Statistics:")
    print(f"  Total Orders: {results['total_orders']}")
    print(f"  Total Users: {results['total_users']}")
    print(f"  Total Revenue: ₹{results['total_revenue']:.2f}")
    print(f"  Average Order Value: ₹{results['avg_order_value']:.2f}")
    print(f"  Order Value Range: ₹{results['min_order_value']:.2f} - ₹{results['max_order_value']:.2f}")
    
    # 2. User segmentation
    query2 = f"""
    SELECT 
        user_id,
        COUNT(*) as order_count,
        SUM(total_amount) as total_spent,
        AVG(total_amount) as avg_order_value,
        MIN(timestamp) as first_order,
        MAX(timestamp) as last_order
    FROM `{project_id}.{dataset_id}.order_transaction_events`
    GROUP BY user_id
    ORDER BY total_spent DESC
    """
    
    print("\n\n👥 User Segmentation:")
    print("-" * 60)
    
    user_segments = {
        "Premium": [],
        "Regular": [],
        "Budget": []
    }
    
    for row in client.query(query2).result():
        avg_value = row['avg_order_value']
        user_info = {
            "user_id": row['user_id'],
            "orders": row['order_count'],
            "total": row['total_spent'],
            "avg": avg_value
        }
        
        if avg_value > 150:
            user_segments["Premium"].append(user_info)
        elif avg_value > 50:
            user_segments["Regular"].append(user_info)
        else:
            user_segments["Budget"].append(user_info)
    
    for segment, users in user_segments.items():
        if users:
            print(f"\n{segment} Shoppers ({len(users)} users):")
            for user in users:
                print(f"  - {user['user_id']}: {user['orders']} orders, ₹{user['avg']:.2f} avg")
    
    # 3. Product popularity analysis
    query3 = f"""
    SELECT 
        product_name,
        sku,
        COUNT(*) as times_ordered,
        SUM(quantity) as total_quantity,
        AVG(price) as avg_price,
        COUNT(DISTINCT user_id) as unique_customers
    FROM `{project_id}.{dataset_id}.product_interaction_events`
    WHERE product_name IS NOT NULL
    GROUP BY product_name, sku
    ORDER BY times_ordered DESC
    LIMIT 15
    """
    
    print("\n\n🏆 Top 15 Products by Order Frequency:")
    print("-" * 60)
    
    for i, row in enumerate(client.query(query3).result(), 1):
        print(f"{i:2d}. {row['product_name']}")
        print(f"    SKU: {row['sku']}, Orders: {row['times_ordered']}, "
              f"Qty Sold: {row['total_quantity']}, Customers: {row['unique_customers']}")
    
    # 4. Shopping patterns by category
    query4 = f"""
    WITH category_orders AS (
        SELECT 
            user_id,
            JSON_EXTRACT_SCALAR(item, '$.category') as category,
            JSON_EXTRACT_SCALAR(item, '$.price') as price,
            JSON_EXTRACT_SCALAR(item, '$.quantity') as quantity
        FROM `{project_id}.{dataset_id}.order_transaction_events`,
        UNNEST(JSON_EXTRACT_ARRAY(items)) as item
    )
    SELECT 
        category,
        COUNT(DISTINCT user_id) as unique_users,
        COUNT(*) as item_count,
        SUM(CAST(price as FLOAT64) * CAST(quantity as INT64)) as category_revenue
    FROM category_orders
    WHERE category IS NOT NULL
    GROUP BY category
    ORDER BY category_revenue DESC
    """
    
    print("\n\n🛍️ Category Performance:")
    print("-" * 60)
    
    for row in client.query(query4).result():
        print(f"{row['category']:20s} - ₹{row['category_revenue']:8.2f} "
              f"({row['unique_users']} users, {row['item_count']} items)")
    
    # 5. User persona insights
    print("\n\n🎯 User Persona Insights:")
    print("-" * 60)
    
    personas = {
        "user_001_vegan": "Vegan Shopper",
        "user_002_family": "Family Shopper",
        "user_003_diabetic": "Health-Conscious",
        "user_004_budget": "Budget-Conscious",
        "user_005_premium": "Premium Shopper"
    }
    
    for user_id, persona_name in personas.items():
        query5 = f"""
        SELECT 
            COUNT(DISTINCT sku) as unique_products,
            COUNT(*) as total_items,
            STRING_AGG(DISTINCT JSON_EXTRACT_SCALAR(item, '$.category'), ', ') as categories
        FROM `{project_id}.{dataset_id}.order_transaction_events`,
        UNNEST(JSON_EXTRACT_ARRAY(items)) as item
        WHERE user_id = '{user_id}'
        """
        
        result = list(client.query(query5).result())[0]
        print(f"\n{persona_name} ({user_id}):")
        print(f"  Unique Products: {result['unique_products']}")
        print(f"  Categories: {result['categories']}")
    
    # 6. Reorder potential
    query6 = f"""
    WITH product_frequency AS (
        SELECT 
            user_id,
            product_name,
            COUNT(*) as order_count
        FROM `{project_id}.{dataset_id}.product_interaction_events`
        WHERE product_name IS NOT NULL
        GROUP BY user_id, product_name
        HAVING COUNT(*) >= 2
    )
    SELECT 
        user_id,
        COUNT(*) as reorderable_products,
        STRING_AGG(product_name, ', ' LIMIT 3) as frequent_products
    FROM product_frequency
    GROUP BY user_id
    ORDER BY reorderable_products DESC
    """
    
    print("\n\n🔄 Reorder Opportunities:")
    print("-" * 60)
    
    for row in client.query(query6).result():
        print(f"{row['user_id']}: {row['reorderable_products']} products")
        print(f"  Frequently ordered: {row['frequent_products']}")
    
    print("\n\n✅ Analysis Complete!")

if __name__ == "__main__":
    analyze_data()