#!/usr/bin/env python3
"""
GCP Production Testing Suite
Tests the deployed Cloud Run instance with real latency measurements
"""

import asyncio
import aiohttp
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from colorama import init, Fore, Style
import statistics

init(autoreset=True)

# GCP Production URL - Using the correct Cloud Run URL
GCP_URL = "https://leafloaf-32905605817.us-central1.run.app"
API_ENDPOINT = f"{GCP_URL}/api/v1/search"
HEALTH_ENDPOINT = f"{GCP_URL}/health"

@dataclass
class TestResult:
    test_name: str
    success: bool
    latency_ms: float
    response_data: Dict[str, Any]
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class WorkflowTest:
    name: str
    description: str
    messages: List[Dict[str, str]]
    expected_behavior: str
    
class GCPProductionTester:
    def __init__(self):
        self.session_id = f"gcp_test_{int(time.time())}"
        self.results: List[TestResult] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        # Create session with SSL verification
        import ssl
        import certifi
        
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        self.session = aiohttp.ClientSession(connector=connector)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    def print_header(self):
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"GCP PRODUCTION TESTING")
        print(f"Target: {GCP_URL}")
        print(f"Session: {self.session_id}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('='*80)
        
    async def check_health(self) -> TestResult:
        """Check if the service is healthy"""
        print(f"\n{Fore.YELLOW}Checking service health...")
        
        start = time.time()
        try:
            async with self.session.get(HEALTH_ENDPOINT) as response:
                latency = (time.time() - start) * 1000
                data = await response.json()
                
                result = TestResult(
                    test_name="Health Check",
                    success=response.status == 200,
                    latency_ms=latency,
                    response_data=data
                )
                
                if result.success:
                    print(f"{Fore.GREEN}✅ Service is healthy ({latency:.2f}ms)")
                else:
                    print(f"{Fore.RED}❌ Service unhealthy: {response.status}")
                    
                return result
                
        except Exception as e:
            latency = (time.time() - start) * 1000
            print(f"{Fore.RED}❌ Health check failed: {str(e)}")
            
            return TestResult(
                test_name="Health Check",
                success=False,
                latency_ms=latency,
                response_data={},
                error=str(e)
            )
            
    async def send_message(self, message: str, test_name: str) -> TestResult:
        """Send a message to the chat API and measure latency"""
        print(f"\n{Fore.CYAN}Test: {test_name}")
        print(f"{Fore.GREEN}User: {message}")
        
        payload = {
            "query": message,
            "session_id": self.session_id,
            "limit": 10
        }
        
        start = time.time()
        try:
            async with self.session.post(
                API_ENDPOINT, 
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                latency = (time.time() - start) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Print response
                    if "message" in data:
                        print(f"{Fore.BLUE}Assistant: {data['message'][:150]}...")
                    elif "products" in data and data["products"]:
                        print(f"{Fore.BLUE}Found {len(data['products'])} products")
                    
                    result = TestResult(
                        test_name=test_name,
                        success=True,
                        latency_ms=latency,
                        response_data=data
                    )
                    
                    print(f"{Fore.YELLOW}Latency: {latency:.2f}ms")
                    
                else:
                    error_text = await response.text()
                    print(f"{Fore.RED}❌ Request failed ({response.status}): {error_text}")
                    
                    result = TestResult(
                        test_name=test_name,
                        success=False,
                        latency_ms=latency,
                        response_data={"status": response.status, "error": error_text},
                        error=f"HTTP {response.status}"
                    )
                    
                self.results.append(result)
                return result
                
        except Exception as e:
            latency = (time.time() - start) * 1000
            print(f"{Fore.RED}❌ Request failed: {str(e)}")
            
            result = TestResult(
                test_name=test_name,
                success=False,
                latency_ms=latency,
                response_data={},
                error=str(e)
            )
            
            self.results.append(result)
            return result
            
    async def run_workflow_test(self, workflow: WorkflowTest):
        """Run a complete workflow test"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"Workflow: {workflow.name}")
        print(f"Description: {workflow.description}")
        print(f"Expected: {workflow.expected_behavior}")
        print('='*60)
        
        workflow_start = time.time()
        workflow_results = []
        
        for i, msg in enumerate(workflow.messages):
            step_name = f"{workflow.name} - Step {i+1}"
            result = await self.send_message(msg["content"], step_name)
            workflow_results.append(result)
            
            # Brief pause between messages to simulate real conversation
            await asyncio.sleep(0.5)
            
        total_latency = (time.time() - workflow_start) * 1000
        success_rate = sum(1 for r in workflow_results if r.success) / len(workflow_results) * 100
        
        print(f"\n{Fore.YELLOW}Workflow Summary:")
        print(f"  Total Time: {total_latency:.2f}ms")
        print(f"  Success Rate: {success_rate:.0f}%")
        print(f"  Avg Step Latency: {statistics.mean([r.latency_ms for r in workflow_results]):.2f}ms")
        
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        self.print_header()
        
        # First check health
        health_result = await self.check_health()
        if not health_result.success:
            print(f"\n{Fore.RED}Service is not healthy. Aborting tests.")
            return
            
        # Define test workflows
        workflows = [
            WorkflowTest(
                name="Simple Search",
                description="Basic product search",
                messages=[
                    {"role": "user", "content": "I need milk"}
                ],
                expected_behavior="Should return milk products"
            ),
            
            WorkflowTest(
                name="Brand Search",
                description="Search for specific brand",
                messages=[
                    {"role": "user", "content": "Show me Oatly products"}
                ],
                expected_behavior="Should return Oatly brand products"
            ),
            
            WorkflowTest(
                name="Add to Cart",
                description="Add items to cart",
                messages=[
                    {"role": "user", "content": "I want bananas"},
                    {"role": "user", "content": "Add 2 bunches to cart"}
                ],
                expected_behavior="Should search and add to cart"
            ),
            
            WorkflowTest(
                name="Cart Management",
                description="Update and view cart",
                messages=[
                    {"role": "user", "content": "Add apples to cart"},
                    {"role": "user", "content": "Change it to 5 apples"},
                    {"role": "user", "content": "What's in my cart?"}
                ],
                expected_behavior="Should add, update, and show cart"
            ),
            
            WorkflowTest(
                name="Reorder Flow",
                description="Reorder previous items",
                messages=[
                    {"role": "user", "content": "What did I order last time?"},
                    {"role": "user", "content": "Add my usual milk"}
                ],
                expected_behavior="Should use Graphiti memory for reorder"
            ),
            
            WorkflowTest(
                name="Complex Shopping",
                description="Multi-step shopping flow",
                messages=[
                    {"role": "user", "content": "I'm making dinner tonight"},
                    {"role": "user", "content": "I need pasta and sauce"},
                    {"role": "user", "content": "Add garlic bread too"},
                    {"role": "user", "content": "Show my cart"}
                ],
                expected_behavior="Should handle context and multiple adds"
            )
        ]
        
        # Run all workflows
        for workflow in workflows:
            await self.run_workflow_test(workflow)
            await asyncio.sleep(1)  # Pause between workflows
            
        # Generate report
        self.generate_report()
        
    def generate_report(self):
        """Generate comprehensive test report"""
        print(f"\n\n{Fore.CYAN}{'='*80}")
        print("GCP PRODUCTION TEST REPORT")
        print('='*80)
        
        # Overall metrics
        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        success_rate = (successful / total_tests * 100) if total_tests > 0 else 0
        
        latencies = [r.latency_ms for r in self.results]
        
        print(f"\n{Fore.YELLOW}Overall Metrics:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Successful: {successful}/{total_tests} ({success_rate:.1f}%)")
        print(f"  Average Latency: {statistics.mean(latencies):.2f}ms")
        print(f"  Median Latency: {statistics.median(latencies):.2f}ms")
        print(f"  Min Latency: {min(latencies):.2f}ms")
        print(f"  Max Latency: {max(latencies):.2f}ms")
        
        if latencies:
            print(f"  P95 Latency: {sorted(latencies)[int(len(latencies) * 0.95)]:.2f}ms")
            
        # Failed tests
        failed_tests = [r for r in self.results if not r.success]
        if failed_tests:
            print(f"\n{Fore.RED}Failed Tests:")
            for test in failed_tests:
                print(f"  - {test.test_name}: {test.error}")
                
        # Performance breakdown
        print(f"\n{Fore.YELLOW}Performance Breakdown:")
        print(f"{'Test Name':<40} {'Status':<10} {'Latency (ms)':<15}")
        print("-" * 65)
        
        for result in self.results:
            status = "✅ Pass" if result.success else "❌ Fail"
            print(f"{result.test_name:<40} {status:<10} {result.latency_ms:<15.2f}")
            
        # Save detailed report
        self.save_report()
        
    def save_report(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gcp_test_report_{timestamp}.json"
        
        report = {
            "test_session": self.session_id,
            "timestamp": timestamp,
            "gcp_url": GCP_URL,
            "summary": {
                "total_tests": len(self.results),
                "successful": sum(1 for r in self.results if r.success),
                "average_latency_ms": statistics.mean([r.latency_ms for r in self.results]),
                "median_latency_ms": statistics.median([r.latency_ms for r in self.results])
            },
            "results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "latency_ms": r.latency_ms,
                    "error": r.error,
                    "timestamp": r.timestamp.isoformat()
                }
                for r in self.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n{Fore.GREEN}Detailed report saved to: {filename}")
        
        # Also create a simple latency CSV for analysis
        csv_filename = f"gcp_latencies_{timestamp}.csv"
        with open(csv_filename, 'w') as f:
            f.write("test_name,latency_ms,success\n")
            for r in self.results:
                f.write(f"{r.test_name},{r.latency_ms},{r.success}\n")
                
        print(f"{Fore.GREEN}Latency data saved to: {csv_filename}")

async def main():
    import sys
    
    print(f"{Fore.CYAN}LeafLoaf GCP Production Testing")
    print(f"{Fore.YELLOW}This will test the deployed Cloud Run instance")
    
    # Check if running interactively
    if sys.stdin.isatty():
        print(f"\nPress Enter to start testing...")
        input()
    else:
        print(f"\nStarting tests...")
    
    async with GCPProductionTester() as tester:
        await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())