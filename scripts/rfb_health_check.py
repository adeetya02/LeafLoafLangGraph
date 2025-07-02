#!/usr/bin/env python3
"""
Ready For Business (RFB) Health Check Script
Verifies all services are operational before testing
"""

import asyncio
import time
import os
import sys
from datetime import datetime
from typing import Dict, Tuple, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import get_settings
from src.integrations.weaviate_client import get_weaviate_client
from src.integrations.gemma_client import GemmaClient
from src.memory.graphiti_memory_spanner import SpannerGraphStore
from google.cloud import spanner
import weaviate
from colorama import init, Fore, Style

init(autoreset=True)

class RFBHealthChecker:
    def __init__(self):
        self.settings = get_settings()
        self.results = {}
        self.start_time = None
        
    def print_header(self):
        print("\n" + "="*60)
        print(f"{Fore.CYAN}LeafLoaf RFB Health Check")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        
    def print_result(self, service: str, status: bool, latency: float, details: str = ""):
        icon = "✅" if status else "❌"
        color = Fore.GREEN if status else Fore.RED
        print(f"{icon} {color}{service:<20} {latency:>8.2f}ms   {details}")
        
    async def check_weaviate(self) -> Tuple[bool, float, str]:
        """Check Weaviate connectivity and schema"""
        start = time.time()
        try:
            client = get_weaviate_client()
            
            # Check if client is ready
            if not client.is_ready():
                return False, (time.time() - start) * 1000, "Client not ready"
                
            # Check schema exists
            schema = client.schema.get()
            product_class = next((c for c in schema['classes'] if c['class'] == 'Product'), None)
            
            if not product_class:
                return False, (time.time() - start) * 1000, "Product class not found"
                
            # Test query
            result = client.query.get('Product', ['name']).with_limit(1).do()
            
            latency = (time.time() - start) * 1000
            return True, latency, f"Schema OK, {len(schema['classes'])} classes"
            
        except Exception as e:
            latency = (time.time() - start) * 1000
            return False, latency, str(e)[:50]
            
    async def check_gemma(self) -> Tuple[bool, float, str]:
        """Check Gemma/LLM connectivity"""
        start = time.time()
        try:
            client = GemmaClient()
            
            # Simple test query
            test_prompt = "Say 'OK' if you're working"
            messages = [{"role": "user", "content": test_prompt}]
            
            response = await client.chat_completion_async(
                messages=messages,
                temperature=0.1,
                max_tokens=10
            )
            
            latency = (time.time() - start) * 1000
            
            if response and len(response) > 0:
                model_info = f"Model: {client.hf_model_id.split('/')[-1]}"
                return True, latency, model_info
            else:
                return False, latency, "Empty response"
                
        except Exception as e:
            latency = (time.time() - start) * 1000
            return False, latency, str(e)[:50]
            
    async def check_spanner_graph(self) -> Tuple[bool, float, str]:
        """Check SpannerGraph connectivity"""
        start = time.time()
        try:
            # Test Spanner connection
            project_id = self.settings.GOOGLE_CLOUD_PROJECT
            instance_id = "leafloaf-instance"
            database_id = "leafloaf-graphiti"
            
            spanner_client = spanner.Client(project=project_id)
            instance = spanner_client.instance(instance_id)
            database = instance.database(database_id)
            
            # Simple connectivity test
            with database.snapshot() as snapshot:
                results = snapshot.execute_sql(
                    "SELECT 1 as test"
                )
                list(results)  # Force execution
                
            latency = (time.time() - start) * 1000
            return True, latency, f"DB: {database_id}"
            
        except Exception as e:
            latency = (time.time() - start) * 1000
            return False, latency, str(e)[:50]
            
    async def check_redis(self) -> Tuple[bool, float, str]:
        """Check Redis connectivity (optional)"""
        start = time.time()
        try:
            import redis.asyncio as redis
            
            # Assuming Redis URL from settings
            redis_url = getattr(self.settings, 'REDIS_URL', None)
            if not redis_url:
                return False, 0, "Redis URL not configured"
                
            client = await redis.from_url(redis_url)
            await client.ping()
            await client.close()
            
            latency = (time.time() - start) * 1000
            return True, latency, "Connected"
            
        except Exception as e:
            latency = (time.time() - start) * 1000
            return False, latency, "Not available (using in-memory)"
            
    async def check_all_services(self):
        """Run all health checks"""
        self.print_header()
        
        # Run checks
        checks = [
            ("Weaviate", self.check_weaviate()),
            ("Gemma/LLM", self.check_gemma()),
            ("SpannerGraph", self.check_spanner_graph()),
            ("Redis Cache", self.check_redis()),
        ]
        
        print(f"{Fore.YELLOW}Running health checks...\n")
        
        total_latency = 0
        all_healthy = True
        
        for service_name, check_coro in checks:
            status, latency, details = await check_coro
            self.print_result(service_name, status, latency, details)
            
            self.results[service_name] = {
                "status": status,
                "latency": latency,
                "details": details
            }
            
            total_latency += latency
            if not status:
                all_healthy = False
                
        # Summary
        print("\n" + "-"*60)
        print(f"{Fore.CYAN}Summary:")
        print(f"Total Check Time: {total_latency:.2f}ms")
        
        if all_healthy:
            print(f"{Fore.GREEN}✅ All services healthy - READY FOR BUSINESS!")
        else:
            failed = [s for s, r in self.results.items() if not r["status"]]
            print(f"{Fore.RED}❌ Failed services: {', '.join(failed)}")
            
        return all_healthy
        
    async def run_continuous_check(self, interval: int = 30):
        """Run health checks continuously"""
        print(f"\n{Fore.YELLOW}Starting continuous health monitoring (interval: {interval}s)")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                await self.check_all_services()
                print(f"\n{Fore.CYAN}Next check in {interval} seconds...")
                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Health monitoring stopped.")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description='LeafLoaf RFB Health Check')
    parser.add_argument('--continuous', '-c', action='store_true', 
                       help='Run continuous monitoring')
    parser.add_argument('--interval', '-i', type=int, default=30,
                       help='Check interval in seconds (default: 30)')
    
    args = parser.parse_args()
    
    checker = RFBHealthChecker()
    
    if args.continuous:
        await checker.run_continuous_check(args.interval)
    else:
        all_healthy = await checker.check_all_services()
        sys.exit(0 if all_healthy else 1)

if __name__ == "__main__":
    asyncio.run(main())