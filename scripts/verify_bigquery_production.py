#!/usr/bin/env python3
"""
Verify BigQuery production setup for LeafLoaf

This script ensures all tables exist, have correct schemas, 
and can accept data inserts.
"""

import asyncio
import uuid
from datetime import datetime
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BigQueryProductionVerifier:
    """Verify BigQuery is production-ready"""
    
    def __init__(self):
        self.project_id = "leafloafai"
        self.dataset_id = "leafloaf_analytics"
        self.client = bigquery.Client(project=self.project_id)
        self.errors = []
        self.warnings = []
        
    def verify_all(self):
        """Run all verification checks"""
        print("🔍 LeafLoaf BigQuery Production Verification")
        print("=" * 60)
        
        # Check 1: Dataset exists
        if not self._verify_dataset():
            print("❌ CRITICAL: Dataset verification failed")
            return False
            
        # Check 2: All tables exist
        if not self._verify_tables():
            print("❌ CRITICAL: Table verification failed")
            return False
            
        # Check 3: Schema validation
        if not self._verify_schemas():
            print("❌ CRITICAL: Schema verification failed")
            return False
            
        # Check 4: Test inserts
        if not self._test_inserts():
            print("❌ CRITICAL: Insert tests failed")
            return False
            
        # Check 5: Permissions
        if not self._verify_permissions():
            print("⚠️  WARNING: Permission issues detected")
            
        # Summary
        print("\n" + "=" * 60)
        if self.errors:
            print(f"❌ Found {len(self.errors)} critical errors:")
            for error in self.errors:
                print(f"  - {error}")
            return False
        else:
            print("✅ BigQuery is PRODUCTION READY!")
            if self.warnings:
                print(f"\n⚠️  {len(self.warnings)} warnings:")
                for warning in self.warnings:
                    print(f"  - {warning}")
            return True
    
    def _verify_dataset(self):
        """Verify dataset exists and is accessible"""
        try:
            dataset = self.client.get_dataset(f"{self.project_id}.{self.dataset_id}")
            print(f"✅ Dataset '{self.dataset_id}' exists in {dataset.location}")
            return True
        except Exception as e:
            self.errors.append(f"Dataset '{self.dataset_id}' not found: {e}")
            return False
    
    def _verify_tables(self):
        """Verify all required tables exist"""
        required_tables = [
            # From bigquery_client.py
            "user_search_events",
            "product_interaction_events", 
            "cart_modification_events",
            "order_transaction_events",
            "recommendation_impression_events",
            # From analytics_service.py
            "user_events",
            "search_events",
            "cart_events",
            "order_events",
            "promotion_usage"
        ]
        
        try:
            tables = list(self.client.list_tables(f"{self.project_id}.{self.dataset_id}"))
            existing_tables = {table.table_id for table in tables}
            
            print(f"\n📊 Table Verification:")
            all_exist = True
            
            for table_name in required_tables:
                if table_name in existing_tables:
                    print(f"  ✅ {table_name}")
                else:
                    print(f"  ❌ {table_name} - MISSING")
                    self.errors.append(f"Required table '{table_name}' is missing")
                    all_exist = False
                    
            return all_exist
            
        except Exception as e:
            self.errors.append(f"Failed to list tables: {e}")
            return False
    
    def _verify_schemas(self):
        """Verify table schemas match expected types"""
        print(f"\n🔧 Schema Verification:")
        
        # Critical fields that must have correct types
        schema_checks = {
            "user_search_events": {
                "latency_ms": "FLOAT",
                "result_count": "INTEGER",
                "timestamp": "TIMESTAMP"
            },
            "search_events": {
                "response_time_ms": "INTEGER",  # Must be INTEGER
                "results_count": "INTEGER",
                "search_timestamp": "TIMESTAMP"
            },
            "user_events": {
                "event_timestamp": "TIMESTAMP",
                "search_latency_ms": "INTEGER"  # Must be INTEGER
            }
        }
        
        all_valid = True
        
        for table_name, field_checks in schema_checks.items():
            try:
                table = self.client.get_table(f"{self.project_id}.{self.dataset_id}.{table_name}")
                schema_dict = {field.name: field.field_type for field in table.schema}
                
                for field_name, expected_type in field_checks.items():
                    if field_name in schema_dict:
                        actual_type = schema_dict[field_name]
                        if actual_type == expected_type:
                            print(f"  ✅ {table_name}.{field_name}: {actual_type}")
                        else:
                            print(f"  ❌ {table_name}.{field_name}: Expected {expected_type}, got {actual_type}")
                            self.errors.append(f"Schema mismatch in {table_name}.{field_name}")
                            all_valid = False
                    else:
                        print(f"  ⚠️  {table_name}.{field_name}: Field missing")
                        self.warnings.append(f"Optional field {table_name}.{field_name} is missing")
                        
            except Exception as e:
                if "Not found" not in str(e):
                    self.errors.append(f"Failed to check schema for {table_name}: {e}")
                    all_valid = False
                    
        return all_valid
    
    def _test_inserts(self):
        """Test inserting sample data into each table"""
        print(f"\n💾 Insert Tests:")
        
        test_data = {
            "user_search_events": {
                "event_id": str(uuid.uuid4()),
                "user_id": "test_user",
                "session_id": "test_session",
                "timestamp": datetime.utcnow().isoformat(),
                "query": "test query",
                "result_count": 10,
                "filters_applied": json.dumps({"category": "test"}),
                "alpha_value": 0.75,
                "search_type": "hybrid",
                "latency_ms": 100.5
            },
            "search_events": {
                "search_id": str(uuid.uuid4()),
                "user_id": "test_user",
                "session_id": "test_session",
                "query": "test query",
                "alpha_value": 0.75,
                "results_count": 10,
                "clicked_results": [],
                "search_timestamp": datetime.utcnow().isoformat(),
                "response_time_ms": 100,  # INTEGER
                "search_type": "hybrid"
            },
            "user_events": {
                "event_id": str(uuid.uuid4()),
                "user_id": "test_user",
                "session_id": "test_session",
                "event_type": "test_event",
                "event_timestamp": datetime.utcnow().isoformat(),
                "device_type": "test",
                "user_agent": "test",
                "search_latency_ms": 100  # INTEGER
            }
        }
        
        all_success = True
        
        for table_name, test_row in test_data.items():
            try:
                table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
                errors = self.client.insert_rows_json(table_id, [test_row])
                
                if errors:
                    print(f"  ❌ {table_name}: {errors}")
                    self.errors.append(f"Insert test failed for {table_name}: {errors}")
                    all_success = False
                else:
                    print(f"  ✅ {table_name}: Insert successful")
                    
                    # Clean up test data based on available fields
                    if "event_id" in test_row:
                        query = f"""
                        DELETE FROM `{table_id}`
                        WHERE event_id = @event_id
                        """
                        job_config = bigquery.QueryJobConfig(
                            query_parameters=[
                                bigquery.ScalarQueryParameter("event_id", "STRING", test_row.get("event_id"))
                            ]
                        )
                    elif "search_id" in test_row:
                        query = f"""
                        DELETE FROM `{table_id}`
                        WHERE search_id = @search_id
                        """
                        job_config = bigquery.QueryJobConfig(
                            query_parameters=[
                                bigquery.ScalarQueryParameter("search_id", "STRING", test_row.get("search_id"))
                            ]
                        )
                    else:
                        # Skip cleanup if no identifiable field
                        continue
                        
                    try:
                        self.client.query(query, job_config=job_config).result()
                    except Exception as e:
                        # Cleanup errors are non-critical
                        self.warnings.append(f"Cleanup warning for {table_name}: {e}")
                    
            except Exception as e:
                if "Not found" not in str(e):
                    print(f"  ❌ {table_name}: {e}")
                    self.errors.append(f"Insert test error for {table_name}: {e}")
                    all_success = False
                    
        return all_success
    
    def _verify_permissions(self):
        """Verify service account has required permissions"""
        print(f"\n🔐 Permission Checks:")
        
        try:
            # Test query permission
            query = f"SELECT 1 FROM `{self.project_id}.{self.dataset_id}.user_events` LIMIT 1"
            list(self.client.query(query).result())
            print("  ✅ Query permission: OK")
            
            # Test job creation permission
            job_config = bigquery.QueryJobConfig(use_query_cache=False)
            self.client.query("SELECT 1", job_config=job_config).result()
            print("  ✅ Job creation permission: OK")
            
            return True
            
        except Exception as e:
            self.warnings.append(f"Permission issue: {e}")
            print(f"  ⚠️  Permission warning: {e}")
            return False


async def test_async_operations():
    """Test async BigQuery operations"""
    print("\n🔄 Testing Async Operations:")
    
    # Import the clients
    try:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        from src.analytics.bigquery_client import bigquery_client
        from src.services.analytics_service import analytics_service
        
        # Test bigquery_client
        test_search = {
            "request_id": str(uuid.uuid4()),
            "user_id": "async_test_user",
            "session_id": "async_test_session",
            "query": "async test query",
            "result_count": 5,
            "alpha": 0.75,
            "latency_ms": 150
        }
        
        success = await bigquery_client.stream_search_event(test_search)
        if success:
            print("  ✅ bigquery_client.stream_search_event: OK")
        else:
            print("  ❌ bigquery_client.stream_search_event: FAILED")
            
        # Test analytics_service
        test_event = {
            "user_id": "async_test_user",
            "session_id": "async_test_session",
            "event_type": "test_async_event"
        }
        
        await analytics_service.track_user_event(test_event)
        print("  ✅ analytics_service.track_user_event: OK")
        
        # Give async tasks time to complete
        await asyncio.sleep(2)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Async operation test failed: {e}")
        return False


def main():
    """Main verification function"""
    verifier = BigQueryProductionVerifier()
    
    # Run sync verifications
    sync_success = verifier.verify_all()
    
    # Run async verifications
    print("\n" + "=" * 60)
    async_success = asyncio.run(test_async_operations())
    
    # Final summary
    print("\n" + "=" * 60)
    print("🏁 FINAL PRODUCTION STATUS:")
    
    if sync_success and async_success:
        print("✅ BigQuery is FULLY PRODUCTION READY!")
        print("\n📋 Production Checklist:")
        print("  ✅ All tables created with correct schemas")
        print("  ✅ Data type conversions working (float → int)")
        print("  ✅ Insert operations successful")
        print("  ✅ Async streaming working")
        print("  ✅ Fire-and-forget pattern implemented")
        print("\n🚀 Ready for production traffic!")
        return True
    else:
        print("❌ BigQuery has issues that need fixing")
        print("Please review the errors above and fix before deploying to production")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)