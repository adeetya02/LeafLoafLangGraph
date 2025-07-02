#!/usr/bin/env python3
"""
Check Spanner tables and data
"""

import asyncio
from google.cloud import spanner
import os

async def check_spanner():
    """Check Spanner database structure and data"""
    
    # Get Spanner config from environment
    instance_id = os.getenv("SPANNER_INSTANCE_ID", "leafloaf-graph")
    database_id = os.getenv("SPANNER_DATABASE_ID", "leafloaf-graphrag")
    project_id = os.getenv("GCP_PROJECT_ID", "leafloafai")
    
    print(f"🔍 Checking Spanner Database")
    print(f"Project: {project_id}")
    print(f"Instance: {instance_id}")
    print(f"Database: {database_id}")
    print("=" * 60)
    
    try:
        # Create Spanner client
        spanner_client = spanner.Client(project=project_id)
        instance = spanner_client.instance(instance_id)
        database = instance.database(database_id)
        
        # List all tables
        with database.snapshot() as snapshot:
            # Get table schema
            results = snapshot.execute_sql(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = ''"
            )
            
            print("\n📋 Tables in Spanner:")
            tables = []
            for row in results:
                table_name = row[0]
                tables.append(table_name)
                print(f"  - {table_name}")
        
        # Check each table with new snapshot
        for table in tables:
            with database.snapshot() as snapshot:
                print(f"\n\n📊 Table: {table}")
                print("-" * 40)
                
                # Get row count
                count_query = f"SELECT COUNT(*) FROM {table}"
                count_result = list(snapshot.execute_sql(count_query))[0][0]
                print(f"Rows: {count_result}")
                
                # Show sample data
                if count_result > 0:
                    sample_query = f"SELECT * FROM {table} LIMIT 3"
                    sample_results = snapshot.execute_sql(sample_query)
                    
                    # Get column names
                    columns = [field.name for field in sample_results.fields]
                    print(f"Columns: {', '.join(columns)}")
                    
                    print("\nSample data:")
                    for row in sample_results:
                        print(f"  {dict(zip(columns, row))}")
            
        # Check for order-related data
        print("\n\n🛒 Order Data Analysis:")
        print("-" * 40)
        
        # Check Users table
        if "Users" in tables:
            with database.snapshot() as snapshot:
                users_query = "SELECT user_id, name FROM Users LIMIT 10"
                users = snapshot.execute_sql(users_query)
                print("\nUsers:")
                for row in users:
                    print(f"  - {row[0]}: {row[1]}")
        
        # Check Orders table
        if "Orders" in tables:
            with database.snapshot() as snapshot:
                orders_query = """
                SELECT user_id, COUNT(*) as order_count
                FROM Orders
                GROUP BY user_id
                """
                orders = snapshot.execute_sql(orders_query)
                print("\nOrders by User:")
                for row in orders:
                    print(f"  - {row[0]}: {row[1]} orders")
        
        # Check Episodes table (Graphiti)
        if "Episodes" in tables:
            with database.snapshot() as snapshot:
                episodes_query = """
                SELECT user_id, episode_type, COUNT(*) as count
                FROM Episodes
                WHERE episode_type LIKE '%order%'
                GROUP BY user_id, episode_type
                LIMIT 10
                """
                episodes = snapshot.execute_sql(episodes_query)
                print("\nOrder Episodes:")
                for row in episodes:
                    print(f"  - {row[0]} ({row[1]}): {row[2]} episodes")
                    
    except Exception as e:
        print(f"\n❌ Error accessing Spanner: {e}")
        print("\nThis might mean:")
        print("1. Spanner instance/database doesn't exist")
        print("2. Authentication issues")
        print("3. Network connectivity problems")

if __name__ == "__main__":
    asyncio.run(check_spanner())