#!/usr/bin/env python3
"""
Debug Weaviate connection and data availability
"""

import asyncio
import os
import sys
from datetime import datetime
import weaviate
from colorama import init, Fore, Style

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings
from src.integrations.weaviate_client_simple import get_weaviate_client

init(autoreset=True)

class WeaviateDebugger:
    def __init__(self):
        self.settings = settings
        self.client = None
        
    def print_header(self, title: str):
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{title}")
        print('='*60)
        
    def check_connection(self):
        """Check basic Weaviate connection"""
        self.print_header("Weaviate Connection Check")
        
        try:
            self.client = get_weaviate_client()
            
            # Check if client is ready
            is_ready = self.client.is_ready()
            print(f"{'✅' if is_ready else '❌'} Weaviate Ready: {is_ready}")
            
            # Get cluster info
            if is_ready:
                meta = self.client.get_meta()
                print(f"✅ Version: {meta.get('version', 'unknown')}")
                print(f"✅ Modules: {', '.join(meta.get('modules', {}).keys())}")
                
            return is_ready
            
        except Exception as e:
            print(f"❌ Connection Error: {str(e)}")
            return False
            
    def check_schema(self):
        """Check Weaviate schema"""
        self.print_header("Schema Check")
        
        try:
            schema = self.client.schema.get()
            classes = schema.get('classes', [])
            
            print(f"Total Classes: {len(classes)}")
            
            for cls in classes:
                class_name = cls.get('class')
                properties = cls.get('properties', [])
                print(f"\n📊 Class: {class_name}")
                print(f"   Properties: {len(properties)}")
                print(f"   Property Names: {', '.join([p['name'] for p in properties[:5]])}...")
                
            # Check specifically for Product class
            product_class = next((c for c in classes if c['class'] == 'Product'), None)
            if product_class:
                print(f"\n{Fore.GREEN}✅ Product class exists")
                return True
            else:
                print(f"\n{Fore.RED}❌ Product class not found!")
                return False
                
        except Exception as e:
            print(f"❌ Schema Error: {str(e)}")
            return False
            
    def count_products(self):
        """Count products in Weaviate"""
        self.print_header("Product Count")
        
        try:
            # Get count using aggregate query
            result = (
                self.client.query
                .aggregate('Product')
                .with_meta_count()
                .do()
            )
            
            count = result.get('data', {}).get('Aggregate', {}).get('Product', [{}])[0].get('meta', {}).get('count', 0)
            print(f"Total Products: {count}")
            
            if count == 0:
                print(f"{Fore.RED}❌ No products in database!")
            else:
                print(f"{Fore.GREEN}✅ Products found")
                
            return count
            
        except Exception as e:
            print(f"❌ Count Error: {str(e)}")
            return 0
            
    def sample_products(self, limit: int = 5):
        """Get sample products"""
        self.print_header(f"Sample Products (limit: {limit})")
        
        try:
            result = (
                self.client.query
                .get('Product', ['name', 'supplier', 'category', 'price'])
                .with_limit(limit)
                .do()
            )
            
            products = result.get('data', {}).get('Get', {}).get('Product', [])
            
            if not products:
                print(f"{Fore.RED}No products returned!")
                return []
                
            print(f"\nFound {len(products)} products:")
            for i, product in enumerate(products, 1):
                print(f"\n{i}. {product.get('name', 'Unknown')}")
                print(f"   Supplier: {product.get('supplier', 'Unknown')}")
                print(f"   Category: {product.get('category', 'Unknown')}")
                print(f"   Price: ${product.get('price', 0):.2f}")
                
            return products
            
        except Exception as e:
            print(f"❌ Sample Error: {str(e)}")
            return []
            
    def test_search(self, query: str = "milk"):
        """Test a search query"""
        self.print_header(f"Test Search: '{query}'")
        
        try:
            # Test hybrid search
            result = (
                self.client.query
                .get('Product', ['name', 'supplier', 'category', 'price'])
                .with_hybrid(query=query, alpha=0.5)
                .with_limit(5)
                .do()
            )
            
            products = result.get('data', {}).get('Get', {}).get('Product', [])
            
            print(f"Search returned {len(products)} products")
            
            if products:
                print(f"{Fore.GREEN}✅ Search working!")
                for product in products[:3]:
                    print(f"- {product.get('name')}")
            else:
                print(f"{Fore.RED}❌ No results for '{query}'")
                
                # Try BM25 search
                print(f"\n{Fore.YELLOW}Trying BM25 search...")
                bm25_result = (
                    self.client.query
                    .get('Product', ['name', 'supplier'])
                    .with_bm25(query=query)
                    .with_limit(5)
                    .do()
                )
                
                bm25_products = bm25_result.get('data', {}).get('Get', {}).get('Product', [])
                if bm25_products:
                    print(f"BM25 returned {len(bm25_products)} products")
                    for product in bm25_products[:3]:
                        print(f"- {product.get('name')}")
                else:
                    print("BM25 also returned no results")
                    
            return products
            
        except Exception as e:
            print(f"❌ Search Error: {str(e)}")
            return []
            
    def check_environment_vars(self):
        """Check environment variables"""
        self.print_header("Environment Check")
        
        weaviate_url = os.getenv('WEAVIATE_URL', 'Not set')
        weaviate_key = os.getenv('WEAVIATE_API_KEY', 'Not set')
        
        print(f"WEAVIATE_URL: {weaviate_url}")
        print(f"WEAVIATE_API_KEY: {'*' * 10 if weaviate_key != 'Not set' else 'Not set'}")
        
        if weaviate_url == 'Not set' or weaviate_key == 'Not set':
            print(f"\n{Fore.RED}❌ Missing Weaviate credentials!")
            return False
            
        print(f"\n{Fore.GREEN}✅ Credentials present")
        return True
        
    async def run_all_checks(self):
        """Run all debug checks"""
        print(f"{Fore.CYAN}Weaviate Debug Report")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check environment
        env_ok = self.check_environment_vars()
        if not env_ok:
            print(f"\n{Fore.RED}Please set WEAVIATE_URL and WEAVIATE_API_KEY")
            return
            
        # Check connection
        connected = self.check_connection()
        if not connected:
            return
            
        # Check schema
        schema_ok = self.check_schema()
        
        # Count products
        count = self.count_products()
        
        # Get samples if products exist
        if count > 0:
            self.sample_products()
            
            # Test search
            self.test_search("milk")
            self.test_search("organic")
            self.test_search("Oatly")
            
        # Summary
        self.print_header("Summary")
        print(f"{'✅' if connected else '❌'} Connection: {'OK' if connected else 'Failed'}")
        print(f"{'✅' if schema_ok else '❌'} Schema: {'OK' if schema_ok else 'Missing Product class'}")
        print(f"{'✅' if count > 0 else '❌'} Data: {count} products")
        
        if count == 0:
            print(f"\n{Fore.YELLOW}Action Required: Load product data into Weaviate")
            print("Run: python scripts/load_weaviate_data.py")

async def main():
    debugger = WeaviateDebugger()
    await debugger.run_all_checks()

if __name__ == "__main__":
    asyncio.run(main())