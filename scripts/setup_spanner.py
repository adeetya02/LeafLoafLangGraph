#!/usr/bin/env python3
"""
Set up Google Cloud Spanner instance and database for Graphiti
"""

import os
import time
from google.cloud import spanner
from google.cloud.spanner_admin_instance_v1 import CreateInstanceRequest, Instance
from google.cloud.spanner_admin_database_v1 import CreateDatabaseRequest

def setup_spanner():
    """Create Spanner instance and database with required tables"""
    
    project_id = os.getenv("GCP_PROJECT_ID", "leafloafai")
    instance_id = os.getenv("SPANNER_INSTANCE_ID", "leafloaf-graph")
    database_id = os.getenv("SPANNER_DATABASE_ID", "leafloaf-graphrag")
    
    print("🚀 Setting up Cloud Spanner for Graphiti")
    print("=" * 60)
    print(f"Project: {project_id}")
    print(f"Instance: {instance_id}")
    print(f"Database: {database_id}")
    
    # Create Spanner admin clients
    spanner_client = spanner.Client(project=project_id)
    
    # Check if instance exists
    try:
        instance = spanner_client.instance(instance_id)
        instance.reload()
        print(f"\n✅ Instance '{instance_id}' already exists")
    except Exception:
        print(f"\n📦 Creating instance '{instance_id}'...")
        
        # Create instance configuration
        config_name = f"projects/{project_id}/instanceConfigs/regional-us-central1"
        
        instance = spanner_client.instance(
            instance_id,
            configuration_name=config_name,
            display_name="LeafLoaf Graph Instance",
            node_count=1,  # Minimum for production
            labels={
                "app": "leafloaf",
                "component": "graphiti"
            }
        )
        
        operation = instance.create()
        print("⏳ Creating instance (this may take a few minutes)...")
        operation.result()  # Wait for operation to complete
        print("✅ Instance created successfully!")
    
    # Check if database exists
    database = instance.database(database_id)
    if database.exists():
        print(f"\n✅ Database '{database_id}' already exists")
    else:
        print(f"\n📊 Creating database '{database_id}' with tables...")
        
        # Define DDL statements for Graphiti tables
        ddl_statements = [
            # Users table
            """CREATE TABLE Users (
                user_id STRING(255) NOT NULL,
                email STRING(255),
                name STRING(255),
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                updated_at TIMESTAMP OPTIONS (allow_commit_timestamp=true),
                preferences JSON,
                shopping_pattern STRING(50),
            ) PRIMARY KEY (user_id)""",
            
            # Episodes table (for Graphiti memory)
            """CREATE TABLE Episodes (
                episode_id STRING(255) NOT NULL,
                user_id STRING(255) NOT NULL,
                session_id STRING(255),
                content STRING(MAX),
                episode_type STRING(50),
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                metadata JSON,
                embeddings ARRAY<FLOAT64>,
            ) PRIMARY KEY (episode_id),
            INTERLEAVE IN PARENT Users ON DELETE CASCADE""",
            
            # Entities table
            """CREATE TABLE Entities (
                entity_id STRING(255) NOT NULL,
                user_id STRING(255) NOT NULL,
                entity_type STRING(50),
                entity_value STRING(255),
                properties JSON,
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                updated_at TIMESTAMP OPTIONS (allow_commit_timestamp=true),
            ) PRIMARY KEY (entity_id),
            INTERLEAVE IN PARENT Users ON DELETE CASCADE""",
            
            # Facts table (relationships)
            """CREATE TABLE Facts (
                fact_id STRING(255) NOT NULL,
                user_id STRING(255) NOT NULL,
                subject_id STRING(255),
                predicate STRING(255),
                object_id STRING(255),
                confidence FLOAT64,
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
                metadata JSON,
            ) PRIMARY KEY (fact_id),
            INTERLEAVE IN PARENT Users ON DELETE CASCADE""",
            
            # Orders table
            """CREATE TABLE Orders (
                order_id STRING(255) NOT NULL,
                user_id STRING(255) NOT NULL,
                order_date TIMESTAMP NOT NULL,
                total_amount FLOAT64,
                item_count INT64,
                status STRING(50),
                created_at TIMESTAMP NOT NULL OPTIONS (allow_commit_timestamp=true),
            ) PRIMARY KEY (order_id),
            INTERLEAVE IN PARENT Users ON DELETE CASCADE""",
            
            # OrderItems table
            """CREATE TABLE OrderItems (
                order_id STRING(255) NOT NULL,
                item_id STRING(255) NOT NULL,
                sku STRING(100),
                product_name STRING(255),
                quantity INT64,
                price FLOAT64,
                category STRING(100),
                brand STRING(100),
            ) PRIMARY KEY (order_id, item_id),
            INTERLEAVE IN PARENT Orders ON DELETE CASCADE""",
            
            # ReorderPatterns table
            """CREATE TABLE ReorderPatterns (
                pattern_id STRING(255) NOT NULL,
                user_id STRING(255) NOT NULL,
                sku STRING(100),
                product_name STRING(255),
                avg_reorder_days FLOAT64,
                order_count INT64,
                last_order_date TIMESTAMP,
                next_predicted_date TIMESTAMP,
                confidence FLOAT64,
                updated_at TIMESTAMP OPTIONS (allow_commit_timestamp=true),
            ) PRIMARY KEY (pattern_id),
            INTERLEAVE IN PARENT Users ON DELETE CASCADE""",
            
            # ProductRelationships table
            """CREATE TABLE ProductRelationships (
                relationship_id STRING(255) NOT NULL,
                product1_sku STRING(100) NOT NULL,
                product2_sku STRING(100) NOT NULL,
                relationship_type STRING(50),
                strength FLOAT64,
                co_occurrence_count INT64,
                updated_at TIMESTAMP OPTIONS (allow_commit_timestamp=true),
            ) PRIMARY KEY (relationship_id)""",
            
            # Create indexes for better query performance
            "CREATE INDEX UserEmailIndex ON Users(email)",
            "CREATE INDEX EpisodeUserIndex ON Episodes(user_id, created_at DESC)",
            "CREATE INDEX EntityUserTypeIndex ON Entities(user_id, entity_type)",
            "CREATE INDEX OrderUserDateIndex ON Orders(user_id, order_date DESC)",
            "CREATE INDEX ReorderUserSkuIndex ON ReorderPatterns(user_id, sku)",
        ]
        
        operation = database.create(ddl_statements)
        print("⏳ Creating database and tables...")
        operation.result()  # Wait for operation to complete
        print("✅ Database and tables created successfully!")
    
    print("\n\n🎉 Spanner setup complete!")
    print("\nTables created:")
    print("- Users")
    print("- Episodes (Graphiti memory)")
    print("- Entities")
    print("- Facts (relationships)")
    print("- Orders")
    print("- OrderItems")
    print("- ReorderPatterns")
    print("- ProductRelationships")
    
    return instance, database

if __name__ == "__main__":
    setup_spanner()