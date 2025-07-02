#!/usr/bin/env python3
"""
LeafLoaf GCP Deployment Test Suite V2
Enhanced with detailed query categorization and Weaviate production testing
"""

import asyncio
import httpx
import time
import json
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import os
import sys
import subprocess

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class QueryCategory:
    """Categories of queries for testing"""
    
    SPECIFIC_PRODUCT = "specific_product"
    VAGUE_PRODUCT = "vague_product"
    CATEGORY_SEARCH = "category_search"
    ATTRIBUTE_SEARCH = "attribute_search"
    CONVERSATIONAL_SPECIFIC = "conversational_specific"
    CONVERSATIONAL_VAGUE = "conversational_vague"
    EXPLORATORY = "exploratory"

class TestQuery:
    """Test query with metadata"""
    
    def __init__(self, query: str, category: str, expected_alpha: float = 0.5, description: str = ""):
        self.query = query
        self.category = category
        self.expected_alpha = expected_alpha
        self.description = description or query

class LatencyTracker:
    """Enhanced latency tracker with query details"""
    
    def __init__(self):
        self.measurements: Dict[str, List[Tuple[float, str, str]]] = {}
    
    def record(self, operation: str, duration: float, query: str = "", details: str = ""):
        """Record a latency measurement with query details"""
        if operation not in self.measurements:
            self.measurements[operation] = []
        self.measurements[operation].append((duration, query, details))
    
    def get_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for an operation"""
        if operation not in self.measurements or not self.measurements[operation]:
            return {"min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0, "queries": []}
        
        values = sorted([m[0] for m in self.measurements[operation]])
        all_measurements = self.measurements[operation]
        
        return {
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "p50": values[int(len(values) * 0.5)],
            "p95": values[int(len(values) * 0.95)] if len(values) > 1 else values[0],
            "p99": values[int(len(values) * 0.99)] if len(values) > 1 else values[0],
            "count": len(values),
            "queries": [(m[1], m[0], m[2]) for m in all_measurements]  # (query, latency, details)
        }
    
    def generate_detailed_report(self) -> str:
        """Generate a detailed latency report with query information"""
        report = []
        report.append("\n🔬 DETAILED LATENCY REPORT")
        report.append("=" * 100)
        
        # Group by category
        categories = {}
        for operation, measurements in self.measurements.items():
            if operation.startswith("search_"):
                category = operation.replace("search_", "").split("_")[0]
                if category not in categories:
                    categories[category] = []
                categories[category].extend(measurements)
        
        # Report by category
        for category in sorted(categories.keys()):
            report.append(f"\n📋 Category: {category.upper()}")
            report.append("-" * 80)
            
            measurements = categories[category]
            if measurements:
                # Sort by latency
                sorted_measurements = sorted(measurements, key=lambda x: x[0])
                
                report.append(f"{'Query':<50} {'Latency':<12} {'Details':<30}")
                report.append("-" * 92)
                
                for latency, query, details in sorted_measurements:
                    query_display = query[:47] + "..." if len(query) > 50 else query
                    details_display = details[:27] + "..." if len(details) > 30 else details
                    report.append(f"{query_display:<50} {latency:>8.2f}ms  {details_display:<30}")
                
                # Stats for this category
                latencies = [m[0] for m in measurements]
                report.append("-" * 92)
                report.append(f"Min: {min(latencies):.2f}ms | "
                            f"Avg: {statistics.mean(latencies):.2f}ms | "
                            f"Max: {max(latencies):.2f}ms | "
                            f"Count: {len(latencies)}")
        
        return "\n".join(report)

class GCPDeploymentTesterV2:
    """Enhanced test suite with categorized queries"""
    
    def __init__(self, base_url: str, test_weaviate: bool = False):
        self.base_url = base_url.rstrip('/')
        self.latency = LatencyTracker()
        self.session_id = f"test-v2-{int(time.time())}"
        self.results = []
        self.test_weaviate = test_weaviate
        
        # Define test queries by category
        self.test_queries = [
            # Specific Product Searches
            TestQuery("Oatly Barista Edition oat milk", QueryCategory.SPECIFIC_PRODUCT, 0.1, "Brand + specific variant"),
            TestQuery("Organic Valley 2% milk gallon", QueryCategory.SPECIFIC_PRODUCT, 0.15, "Brand + type + size"),
            TestQuery("Horizon organic whole milk", QueryCategory.SPECIFIC_PRODUCT, 0.2, "Brand + attributes"),
            TestQuery("Nature's Path Heritage Flakes", QueryCategory.SPECIFIC_PRODUCT, 0.1, "Exact product name"),
            
            # Vague Product Searches
            TestQuery("milk", QueryCategory.VAGUE_PRODUCT, 0.5, "Single word, common"),
            TestQuery("bread", QueryCategory.VAGUE_PRODUCT, 0.5, "Single word, common"),
            TestQuery("something for breakfast", QueryCategory.VAGUE_PRODUCT, 0.7, "Very vague"),
            TestQuery("healthy snacks", QueryCategory.VAGUE_PRODUCT, 0.6, "Vague category"),
            
            # Category Searches
            TestQuery("dairy products", QueryCategory.CATEGORY_SEARCH, 0.6, "Product category"),
            TestQuery("breakfast cereals", QueryCategory.CATEGORY_SEARCH, 0.5, "Specific category"),
            TestQuery("plant-based alternatives", QueryCategory.CATEGORY_SEARCH, 0.6, "Modern category"),
            TestQuery("frozen foods", QueryCategory.CATEGORY_SEARCH, 0.5, "Department category"),
            
            # Attribute-based Searches
            TestQuery("organic gluten-free products", QueryCategory.ATTRIBUTE_SEARCH, 0.4, "Multiple attributes"),
            TestQuery("vegan protein sources", QueryCategory.ATTRIBUTE_SEARCH, 0.5, "Diet + nutrition"),
            TestQuery("low sodium items", QueryCategory.ATTRIBUTE_SEARCH, 0.4, "Health attribute"),
            TestQuery("non-GMO snacks", QueryCategory.ATTRIBUTE_SEARCH, 0.4, "Certification attribute"),
            
            # Exploratory Searches
            TestQuery("what's good for a picnic", QueryCategory.EXPLORATORY, 0.8, "Use case query"),
            TestQuery("dinner ideas for tonight", QueryCategory.EXPLORATORY, 0.9, "Meal planning"),
            TestQuery("healthy options for kids", QueryCategory.EXPLORATORY, 0.7, "Demographic + health"),
            TestQuery("quick lunch solutions", QueryCategory.EXPLORATORY, 0.8, "Time-based need"),
        ]
        
        # Conversational flows
        self.conversation_flows = {
            "specific": [
                ("I need Oatly Barista Edition", "specific_initial", "Exact product request"),
                ("Add 2 cartons to my cart", "specific_add", "Specific quantity"),
                ("Also get me Horizon organic milk", "specific_additional", "Another specific product"),
                ("Change Oatly quantity to 3", "specific_modify", "Modify specific item"),
                ("Show me my order", "specific_list", "Review order"),
                ("That's all, confirm order", "specific_confirm", "Confirm with context")
            ],
            "vague": [
                ("I need some milk", "vague_initial", "Vague product request"),
                ("What options do you have?", "vague_explore", "Exploration"),
                ("I'll take the organic one", "vague_select", "Relative selection"),
                ("Add some bread too", "vague_additional", "Another vague request"),
                ("Something for breakfast", "vague_category", "Very vague addition"),
                ("That's good, checkout", "vague_confirm", "Casual confirmation")
            ]
        }
    
    async def measure_request(self, 
                            client: httpx.AsyncClient,
                            method: str,
                            endpoint: str,
                            operation: str,
                            query: str = "",
                            details: str = "",
                            **kwargs) -> Dict[str, Any]:
        """Make a request and measure latency"""
        url = f"{self.base_url}{endpoint}"
        
        start_time = time.time()
        try:
            response = await client.request(method, url, **kwargs)
            duration = (time.time() - start_time) * 1000  # Convert to ms
            
            self.latency.record(operation, duration, query, details)
            
            result = {
                "operation": operation,
                "status": response.status_code,
                "duration_ms": duration,
                "success": 200 <= response.status_code < 300,
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "details": details
            }
            
            if response.status_code == 200:
                result["data"] = response.json()
            else:
                result["error"] = response.text
            
            self.results.append(result)
            return result
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.latency.record(operation, duration, query, f"Error: {str(e)[:30]}")
            result = {
                "operation": operation,
                "status": 0,
                "duration_ms": duration,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "details": details
            }
            self.results.append(result)
            return result
    
    async def test_categorized_searches(self, client: httpx.AsyncClient):
        """Test searches by category"""
        print("\n🔍 Testing Categorized Searches...")
        
        for test_query in self.test_queries:
            result = await self.measure_request(
                client, "POST", "/api/v1/search", 
                f"search_{test_query.category}",
                query=test_query.query,
                details=test_query.description,
                json={"query": test_query.query, "session_id": self.session_id}
            )
            
            if result["success"] and "data" in result:
                data = result["data"]
                print(f"\n✅ [{test_query.category.upper()}] '{test_query.query}'")
                print(f"   Latency: {result['duration_ms']:.2f}ms")
                print(f"   Description: {test_query.description}")
                
                # Extract alpha if available
                if "metadata" in data and "search_config" in data["metadata"]:
                    actual_alpha = data["metadata"]["search_config"].get("alpha", 0.5)
                    print(f"   Expected α: {test_query.expected_alpha}, Actual α: {actual_alpha}")
                
                # Show results count
                if "results" in data:
                    print(f"   Results: {len(data['results'])} products found")
            else:
                print(f"\n❌ [{test_query.category.upper()}] '{test_query.query}' failed")
    
    async def test_conversation_flows(self, client: httpx.AsyncClient):
        """Test conversation flows"""
        print("\n💬 Testing Conversation Flows...")
        
        for flow_type, steps in self.conversation_flows.items():
            print(f"\n📝 {flow_type.upper()} Conversation Flow:")
            session_id = f"{self.session_id}-conv-{flow_type}"
            
            for query, step_name, description in steps:
                result = await self.measure_request(
                    client, "POST", "/api/v1/search",
                    f"conversation_{flow_type}_{step_name}",
                    query=query,
                    details=description,
                    json={"query": query, "session_id": session_id}
                )
                
                if result["success"]:
                    print(f"   ✅ {description}: {result['duration_ms']:.2f}ms - \"{query}\"")
                else:
                    print(f"   ❌ {description} failed - \"{query}\"")
                
                await asyncio.sleep(0.3)  # Small delay between steps
    
    async def test_weaviate_production(self, client: httpx.AsyncClient):
        """Test with real Weaviate if enabled"""
        if not self.test_weaviate:
            print("\n⏭️  Skipping Weaviate production test (use --weaviate flag to enable)")
            return
        
        print("\n🌐 Testing with Real Weaviate...")
        print("   Switching to production mode...")
        
        # Switch to production mode
        switch_result = subprocess.run(
            ["./scripts/switch_modes.sh", "prod"],
            capture_output=True,
            text=True
        )
        
        if switch_result.returncode != 0:
            print("❌ Failed to switch to production mode")
            return
        
        print("   ✅ Switched to production mode")
        print("   ⏳ Waiting for service to update...")
        await asyncio.sleep(30)  # Wait for Cloud Run to update
        
        # Run subset of tests with Weaviate
        weaviate_queries = [
            TestQuery("Oatly Barista Edition", QueryCategory.SPECIFIC_PRODUCT, 0.1, "Real product test"),
            TestQuery("organic milk", QueryCategory.ATTRIBUTE_SEARCH, 0.3, "Attribute search"),
            TestQuery("breakfast", QueryCategory.CATEGORY_SEARCH, 0.6, "Category search"),
        ]
        
        for test_query in weaviate_queries:
            result = await self.measure_request(
                client, "POST", "/api/v1/search",
                f"weaviate_{test_query.category}",
                query=test_query.query,
                details=f"WEAVIATE: {test_query.description}",
                json={"query": test_query.query, "session_id": f"{self.session_id}-weaviate"}
            )
            
            if result["success"]:
                print(f"\n✅ [WEAVIATE] '{test_query.query}': {result['duration_ms']:.2f}ms")
                if "data" in result and "results" in result["data"]:
                    products = result["data"]["results"]
                    print(f"   Real products found: {len(products)}")
                    if products:
                        print(f"   First result: {products[0].get('product_name', 'Unknown')}")
            else:
                print(f"\n❌ [WEAVIATE] '{test_query.query}' failed")
        
        # Switch back to test mode
        print("\n   Switching back to test mode...")
        subprocess.run(["./scripts/switch_modes.sh", "test-prod"], capture_output=True)
        await asyncio.sleep(10)
    
    async def run_all_tests(self):
        """Run all tests and generate detailed report"""
        print(f"\n🧪 LeafLoaf GCP Deployment Test Suite V2")
        print(f"📍 Testing: {self.base_url}")
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔧 Weaviate Testing: {'Enabled' if self.test_weaviate else 'Disabled'}")
        print("=" * 100)
        
        # Configure client with longer timeout
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test health
            print("\n🏥 Testing Health Endpoint...")
            health_result = await self.measure_request(
                client, "GET", "/health", "health_check"
            )
            if health_result["success"]:
                print(f"✅ Health check passed in {health_result['duration_ms']:.2f}ms")
            
            # Run categorized searches
            await self.test_categorized_searches(client)
            
            # Run conversation flows
            await self.test_conversation_flows(client)
            
            # Test Weaviate if enabled
            if self.test_weaviate:
                await self.test_weaviate_production(client)
        
        # Generate detailed report
        print("\n" + "=" * 100)
        print(self.latency.generate_detailed_report())
        
        # Save results
        self.save_detailed_results()
        
        # Summary
        print("\n📊 SUMMARY")
        print("=" * 100)
        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful}")
        print(f"Failed: {total_tests - successful}")
        print(f"Success Rate: {(successful/total_tests)*100:.1f}%")
        
        # Category summaries
        print("\n📈 Performance by Category:")
        categories_perf = {}
        for result in self.results:
            if result["success"] and "query" in result and result["query"]:
                op = result["operation"]
                if op.startswith("search_"):
                    category = op.replace("search_", "")
                    if category not in categories_perf:
                        categories_perf[category] = []
                    categories_perf[category].append(result["duration_ms"])
        
        for category, latencies in sorted(categories_perf.items()):
            if latencies:
                avg_latency = statistics.mean(latencies)
                print(f"  {category:<25} Avg: {avg_latency:>6.2f}ms  "
                      f"Min: {min(latencies):>6.2f}ms  Max: {max(latencies):>6.2f}ms")
    
    def save_detailed_results(self):
        """Save detailed test results with query information"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_detailed_{timestamp}.json"
        
        # Prepare detailed stats
        detailed_stats = {}
        for operation, measurements in self.latency.measurements.items():
            stats = self.latency.get_stats(operation)
            stats["queries"] = [
                {
                    "query": m[1],
                    "latency_ms": m[0],
                    "details": m[2]
                } for m in measurements
            ]
            detailed_stats[operation] = stats
        
        with open(filename, 'w') as f:
            json.dump({
                "test_run": {
                    "timestamp": datetime.now().isoformat(),
                    "base_url": self.base_url,
                    "session_id": self.session_id,
                    "weaviate_tested": self.test_weaviate
                },
                "results": self.results,
                "detailed_latency_stats": detailed_stats,
                "test_queries": [
                    {
                        "query": tq.query,
                        "category": tq.category,
                        "expected_alpha": tq.expected_alpha,
                        "description": tq.description
                    } for tq in self.test_queries
                ]
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")

async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test LeafLoaf GCP deployment")
    parser.add_argument("--weaviate", action="store_true", help="Test with real Weaviate data")
    parser.add_argument("--url", help="Service URL (optional)")
    args = parser.parse_args()
    
    # Get service URL
    service_url = args.url or os.getenv("SERVICE_URL")
    
    if not service_url:
        # Try to get from gcloud
        try:
            result = subprocess.run(
                ["gcloud", "run", "services", "describe", "leafloaf", 
                 "--region", "northamerica-northeast1", 
                 "--format", "value(status.url)"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                service_url = result.stdout.strip()
        except:
            pass
    
    if not service_url:
        print("❌ No service URL found. Please set SERVICE_URL environment variable")
        print("   Example: export SERVICE_URL=https://leafloaf-xxx.run.app")
        return
    
    # Run tests
    tester = GCPDeploymentTesterV2(service_url, test_weaviate=args.weaviate)
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())