#!/usr/bin/env python3
"""
LeafLoaf GCP Deployment Test Suite
Tests all endpoints and measures latency at each step
"""

import asyncio
import httpx
import time
import json
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional
# Remove pandas dependency for simpler installation
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class LatencyTracker:
    """Track latency for different operations"""
    
    def __init__(self):
        self.measurements: Dict[str, List[float]] = {}
    
    def record(self, operation: str, duration: float):
        """Record a latency measurement"""
        if operation not in self.measurements:
            self.measurements[operation] = []
        self.measurements[operation].append(duration)
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation"""
        if operation not in self.measurements or not self.measurements[operation]:
            return {"min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        
        values = sorted(self.measurements[operation])
        return {
            "min": min(values),
            "max": max(values),
            "avg": statistics.mean(values),
            "p50": values[int(len(values) * 0.5)],
            "p95": values[int(len(values) * 0.95)] if len(values) > 1 else values[0],
            "p99": values[int(len(values) * 0.99)] if len(values) > 1 else values[0],
            "count": len(values)
        }
    
    def generate_report(self) -> str:
        """Generate a formatted latency report"""
        report = []
        report.append("\n🔬 LATENCY REPORT")
        report.append("=" * 80)
        
        # Prepare data for table
        table_data = []
        for operation in sorted(self.measurements.keys()):
            stats = self.get_stats(operation)
            table_data.append([
                operation,
                f"{stats['min']:.2f}ms",
                f"{stats['avg']:.2f}ms",
                f"{stats['p50']:.2f}ms",
                f"{stats['p95']:.2f}ms",
                f"{stats['p99']:.2f}ms",
                f"{stats['max']:.2f}ms",
                stats['count']
            ])
        
        # Simple table formatting without tabulate
        headers = ["Operation", "Min", "Avg", "P50", "P95", "P99", "Max", "Count"]
        col_widths = [20, 10, 10, 10, 10, 10, 10, 8]
        
        # Header
        header_line = "|"
        for i, header in enumerate(headers):
            header_line += f" {header:<{col_widths[i]-2}} |"
        
        separator = "+" + "+".join(["-" * w for w in col_widths]) + "+"
        
        report.append(separator)
        report.append(header_line)
        report.append(separator)
        
        # Data rows
        for row in table_data:
            row_line = "|"
            for i, cell in enumerate(row):
                row_line += f" {str(cell):<{col_widths[i]-2}} |"
            report.append(row_line)
        
        report.append(separator)
        
        return "\n".join(report)

class GCPDeploymentTester:
    """Test suite for GCP deployment"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.latency = LatencyTracker()
        self.session_id = f"test-{int(time.time())}"
        self.results = []
    
    async def measure_request(self, 
                            client: httpx.AsyncClient,
                            method: str,
                            endpoint: str,
                            operation: str,
                            **kwargs) -> Dict[str, Any]:
        """Make a request and measure latency"""
        url = f"{self.base_url}{endpoint}"
        
        start_time = time.time()
        try:
            response = await client.request(method, url, **kwargs)
            duration = (time.time() - start_time) * 1000  # Convert to ms
            
            self.latency.record(operation, duration)
            
            result = {
                "operation": operation,
                "status": response.status_code,
                "duration_ms": duration,
                "success": 200 <= response.status_code < 300,
                "timestamp": datetime.now().isoformat()
            }
            
            if response.status_code == 200:
                result["data"] = response.json()
            else:
                result["error"] = response.text
            
            self.results.append(result)
            return result
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            result = {
                "operation": operation,
                "status": 0,
                "duration_ms": duration,
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            self.results.append(result)
            return result
    
    async def test_health_endpoint(self, client: httpx.AsyncClient):
        """Test health check endpoint"""
        print("\n🏥 Testing Health Endpoint...")
        result = await self.measure_request(
            client, "GET", "/health", "health_check"
        )
        
        if result["success"]:
            print(f"✅ Health check passed in {result['duration_ms']:.2f}ms")
            if "data" in result:
                print(f"   Status: {result['data'].get('status', 'unknown')}")
        else:
            print(f"❌ Health check failed: {result.get('error', 'Unknown error')}")
    
    async def test_search_endpoint(self, client: httpx.AsyncClient, queries: List[str]):
        """Test search endpoint with various queries"""
        print("\n🔍 Testing Search Endpoint...")
        
        for query in queries:
            # Measure full search latency
            search_start = time.time()
            result = await self.measure_request(
                client, "POST", "/api/v1/search", f"search_{query.replace(' ', '_')}",
                json={"query": query, "session_id": self.session_id}
            )
            
            if result["success"] and "data" in result:
                data = result["data"]
                print(f"\n✅ Search '{query}' completed in {result['duration_ms']:.2f}ms")
                
                # Extract component latencies if available
                if "metadata" in data:
                    metadata = data["metadata"]
                    
                    # Record component latencies
                    if "agent_latencies" in metadata:
                        for agent, latency in metadata["agent_latencies"].items():
                            self.latency.record(f"agent_{agent}", latency * 1000)
                    
                    if "llm_latency" in metadata:
                        self.latency.record("llm_intent_analysis", metadata["llm_latency"] * 1000)
                    
                    if "search_latency" in metadata:
                        self.latency.record("weaviate_search", metadata["search_latency"] * 1000)
                
                # Display results summary
                if "results" in data:
                    products = data["results"]
                    print(f"   Found {len(products)} products")
                    if products:
                        print(f"   Top result: {products[0].get('product_name', 'Unknown')}")
                
                # Show conversation state
                if "conversation" in data:
                    conv = data["conversation"]
                    print(f"   Intent: {conv.get('intent', 'unknown')}")
                    print(f"   Response: {conv.get('response', '')[:100]}...")
            else:
                print(f"❌ Search '{query}' failed: {result.get('error', 'Unknown error')}")
    
    async def test_conversation_flow(self, client: httpx.AsyncClient):
        """Test a full conversation flow"""
        print("\n💬 Testing Conversation Flow...")
        
        conversation_steps = [
            ("I need some organic milk", "initial_search"),
            ("Add 2 gallons of the first one", "add_to_order"),
            ("Also get me some oat milk", "additional_search"),
            ("What's in my cart?", "list_order"),
            ("Remove the milk", "remove_from_order"),
            ("Confirm my order", "confirm_order")
        ]
        
        for query, step_name in conversation_steps:
            result = await self.measure_request(
                client, "POST", "/api/v1/search", f"conversation_{step_name}",
                json={"query": query, "session_id": f"{self.session_id}-conv"}
            )
            
            if result["success"]:
                print(f"✅ Step '{step_name}': {result['duration_ms']:.2f}ms")
            else:
                print(f"❌ Step '{step_name}' failed")
            
            # Small delay between conversation steps
            await asyncio.sleep(0.5)
    
    async def test_concurrent_requests(self, client: httpx.AsyncClient, num_concurrent: int = 5):
        """Test concurrent request handling"""
        print(f"\n🚀 Testing {num_concurrent} Concurrent Requests...")
        
        queries = ["milk", "bread", "eggs", "cheese", "yogurt", "butter", "cream", "juice"]
        tasks = []
        
        start_time = time.time()
        for i in range(num_concurrent):
            query = queries[i % len(queries)]
            task = self.measure_request(
                client, "POST", "/api/v1/search", f"concurrent_{i}",
                json={"query": query, "session_id": f"{self.session_id}-concurrent-{i}"}
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        total_time = (time.time() - start_time) * 1000
        
        successful = sum(1 for r in results if r["success"])
        print(f"✅ Completed {successful}/{num_concurrent} requests in {total_time:.2f}ms")
        print(f"   Average: {total_time/num_concurrent:.2f}ms per request")
    
    async def test_edge_cases(self, client: httpx.AsyncClient):
        """Test edge cases and error handling"""
        print("\n🔧 Testing Edge Cases...")
        
        edge_cases = [
            ("", "empty_query"),
            ("a" * 500, "long_query"),
            ("!@#$%^&*()", "special_chars"),
            ("café naïve résumé", "unicode_chars"),
            ("milk AND bread OR eggs NOT cheese", "boolean_query")
        ]
        
        for query, case_name in edge_cases:
            result = await self.measure_request(
                client, "POST", "/api/v1/search", f"edge_case_{case_name}",
                json={"query": query, "session_id": self.session_id}
            )
            
            if result["success"]:
                print(f"✅ Edge case '{case_name}': Handled correctly")
            else:
                print(f"⚠️  Edge case '{case_name}': {result.get('error', 'Failed')[:50]}...")
    
    async def run_all_tests(self):
        """Run all tests and generate report"""
        print(f"\n🧪 LeafLoaf GCP Deployment Test Suite")
        print(f"📍 Testing: {self.base_url}")
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Configure client with longer timeout for GCP
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Run all test suites
            await self.test_health_endpoint(client)
            
            # Test various search queries
            search_queries = [
                "organic milk",
                "gluten free bread",
                "vegan cheese alternatives",
                "fresh bananas",
                "oat milk barista",
                "whole grain pasta",
                "breakfast cereals"
            ]
            await self.test_search_endpoint(client, search_queries)
            
            # Test conversation flow
            await self.test_conversation_flow(client)
            
            # Test concurrent requests
            await self.test_concurrent_requests(client, num_concurrent=10)
            
            # Test edge cases
            await self.test_edge_cases(client)
        
        # Generate and display report
        print("\n" + "=" * 80)
        print(self.latency.generate_report())
        
        # Save detailed results
        self.save_results()
        
        # Summary
        print("\n📊 SUMMARY")
        print("=" * 80)
        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful}")
        print(f"Failed: {total_tests - successful}")
        print(f"Success Rate: {(successful/total_tests)*100:.1f}%")
        
        # Overall latency stats
        all_latencies = []
        for r in self.results:
            if r["success"] and "duration_ms" in r:
                all_latencies.append(r["duration_ms"])
        
        if all_latencies:
            print(f"\nOverall Latency:")
            print(f"  Min: {min(all_latencies):.2f}ms")
            print(f"  Avg: {statistics.mean(all_latencies):.2f}ms")
            print(f"  Max: {max(all_latencies):.2f}ms")
    
    def save_results(self):
        """Save detailed test results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "test_run": {
                    "timestamp": datetime.now().isoformat(),
                    "base_url": self.base_url,
                    "session_id": self.session_id
                },
                "results": self.results,
                "latency_stats": {
                    op: self.latency.get_stats(op) 
                    for op in self.latency.measurements.keys()
                }
            }, f, indent=2)
        
        print(f"\n💾 Detailed results saved to: {filename}")

async def main():
    """Main test runner"""
    # Get service URL from environment or use default
    service_url = os.getenv("SERVICE_URL")
    
    if not service_url:
        # Try to get from gcloud
        import subprocess
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
    tester = GCPDeploymentTester(service_url)
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())