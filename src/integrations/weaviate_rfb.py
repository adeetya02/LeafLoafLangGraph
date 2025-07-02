#!/usr/bin/env python3
"""
Weaviate RFB (Ready for Business) Implementation
Ensures Weaviate is always available with fallback strategies
"""

import weaviate
from weaviate.auth import AuthApiKey
import time
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import structlog
import asyncio
from functools import lru_cache
from src.config.constants import SEARCH_DEFAULT_LIMIT

logger = structlog.get_logger()

class WeaviateRFB:
    """
    Ready for Business Weaviate Client
    Implements:
    1. Health checks
    2. Auto-reconnection
    3. Fallback to cached data
    4. Circuit breaker pattern
    5. Performance monitoring
    """
    
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.last_health_check = None
        self.connection_attempts = 0
        self.circuit_breaker_open = False
        self.circuit_breaker_reset_time = None
        self.cached_products = self._load_cached_products()
        
        # Configuration
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.health_check_interval = 60  # seconds
        self.circuit_breaker_threshold = 5  # failures before opening
        self.circuit_breaker_timeout = 300  # 5 minutes
        
        # Performance tracking
        self.avg_response_time = 0
        self.total_searches = 0
        
    def _load_cached_products(self) -> Dict[str, List[Dict]]:
        """Load cached products for fallback"""
        cache_file = "weaviate_product_cache.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default fallback data
        return {
            "milk": [
                {"name": "Organic Whole Milk", "sku": "OV_MILK_WH", "price": 5.99, "brand": "Organic Valley"},
                {"name": "2% Milk", "sku": "MILK_2P_001", "price": 3.99, "brand": "Store Brand"},
                {"name": "Almond Milk", "sku": "ALM_MILK_001", "price": 4.99, "brand": "Blue Diamond"},
            ],
            "bread": [
                {"name": "Whole Wheat Bread", "sku": "BREAD_WW_001", "price": 3.49, "brand": "Artisan Bakery"},
                {"name": "White Bread", "sku": "BREAD_W_001", "price": 2.99, "brand": "Store Brand"},
            ]
        }
    
    def _save_cache(self, query: str, results: List[Dict]):
        """Save successful results to cache"""
        if query and results:
            self.cached_products[query.lower()] = results[:20]  # Cache top 20
            try:
                with open("weaviate_product_cache.json", 'w') as f:
                    json.dump(self.cached_products, f)
            except:
                pass
    
    async def ensure_connection(self) -> bool:
        """Ensure Weaviate connection is ready"""
        # Check circuit breaker
        if self.circuit_breaker_open:
            if time.time() < self.circuit_breaker_reset_time:
                logger.warning("Circuit breaker open, using cache")
                return False
            else:
                logger.info("Circuit breaker timeout expired, attempting reconnection")
                self.circuit_breaker_open = False
                self.connection_attempts = 0
        
        # Check existing connection
        if self.client and self.is_connected:
            # Periodic health check
            if (self.last_health_check is None or 
                time.time() - self.last_health_check > self.health_check_interval):
                if await self._health_check():
                    self.last_health_check = time.time()
                    return True
                else:
                    self.is_connected = False
            else:
                return True
        
        # Try to connect
        return await self._connect()
    
    async def _connect(self) -> bool:
        """Connect to Weaviate with retries"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Connecting to Weaviate (attempt {attempt + 1}/{self.max_retries})")
                
                # Get credentials
                weaviate_url = os.environ.get("WEAVIATE_URL", "https://leafloaf-p79lgj19.weaviate.network")
                weaviate_key = os.environ.get("WEAVIATE_API_KEY", "dqgYpLkm1gGaVJdN01Po6W0D8eX4SLeNImP7")
                
                # Clean URL for v4 client
                cluster_url = weaviate_url.replace("https://", "").replace("http://", "")
                
                # Connect with timeout
                self.client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=cluster_url,
                    auth_credentials=AuthApiKey(weaviate_key),
                    additional_config=weaviate.config.AdditionalConfig(
                        timeout=(5, 30),  # 5s connect, 30s read
                        use_grpc_for_collections=False
                    ),
                    skip_init_checks=True
                )
                
                # Verify connection
                if await self._health_check():
                    self.is_connected = True
                    self.connection_attempts = 0
                    logger.info("✅ Weaviate connected successfully")
                    return True
                
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
                self.connection_attempts += 1
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        # Max retries exceeded
        if self.connection_attempts >= self.circuit_breaker_threshold:
            self._open_circuit_breaker()
        
        return False
    
    async def _health_check(self) -> bool:
        """Check Weaviate health"""
        try:
            # Quick collection check
            collections = self.client.collections.list_all()
            return "GroceryProduct" in collections
        except:
            return False
    
    def _open_circuit_breaker(self):
        """Open circuit breaker after too many failures"""
        self.circuit_breaker_open = True
        self.circuit_breaker_reset_time = time.time() + self.circuit_breaker_timeout
        logger.warning(f"Circuit breaker opened, will retry in {self.circuit_breaker_timeout}s")
    
    async def search_products(self, query: str, alpha: float = 0.5, limit: int = SEARCH_DEFAULT_LIMIT) -> Tuple[List[Dict], bool]:
        """
        Search products with automatic fallback
        Returns: (results, is_from_cache)
        """
        start_time = time.time()
        
        # Try Weaviate first
        if await self.ensure_connection():
            try:
                # Perform search
                collection = self.client.collections.get("GroceryProduct")
                
                response = collection.query.hybrid(
                    query=query,
                    alpha=alpha,
                    limit=limit * 2  # Get extra for better results
                )
                
                # Process results
                results = []
                for item in response.objects[:limit]:
                    product = item.properties
                    results.append({
                        "name": product.get("name", "Unknown"),
                        "sku": product.get("sku", "N/A"),
                        "price": product.get("price", 0),
                        "brand": product.get("brand") or product.get("supplier", "Unknown"),
                        "category": product.get("category", "Unknown"),
                        "unit": product.get("unit", "each"),
                        "score": getattr(item.metadata, 'score', None) if hasattr(item, 'metadata') else None
                    })
                
                # Track performance
                response_time = (time.time() - start_time) * 1000
                self._update_performance(response_time)
                
                # Cache successful results
                self._save_cache(query, results)
                
                logger.info(f"✅ Weaviate search successful ({response_time:.0f}ms)")
                return results, False
                
            except Exception as e:
                logger.error(f"Search failed: {str(e)}")
                self.is_connected = False
        
        # Fallback to cache
        logger.warning("Using cached results")
        return self._search_cache(query, limit), True
    
    def _search_cache(self, query: str, limit: int) -> List[Dict]:
        """Search in cached products"""
        query_lower = query.lower()
        
        # Direct match
        if query_lower in self.cached_products:
            return self.cached_products[query_lower][:limit]
        
        # Fuzzy match
        all_products = []
        for key, products in self.cached_products.items():
            if query_lower in key or key in query_lower:
                all_products.extend(products)
        
        # If still no results, return all products
        if not all_products:
            for products in self.cached_products.values():
                all_products.extend(products)
        
        # Remove duplicates and limit
        seen_skus = set()
        unique_products = []
        for p in all_products:
            if p['sku'] not in seen_skus:
                seen_skus.add(p['sku'])
                unique_products.append(p)
        
        return unique_products[:limit]
    
    def _update_performance(self, response_time: float):
        """Update performance metrics"""
        self.total_searches += 1
        self.avg_response_time = (
            (self.avg_response_time * (self.total_searches - 1) + response_time) 
            / self.total_searches
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get RFB status"""
        return {
            "connected": self.is_connected,
            "circuit_breaker_open": self.circuit_breaker_open,
            "connection_attempts": self.connection_attempts,
            "avg_response_time_ms": round(self.avg_response_time, 2),
            "total_searches": self.total_searches,
            "cached_queries": len(self.cached_products),
            "last_health_check": self.last_health_check
        }
    
    def close(self):
        """Close connection"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.is_connected = False

# Global RFB instance
_weaviate_rfb = None

def get_weaviate_rfb() -> WeaviateRFB:
    """Get or create global RFB instance"""
    global _weaviate_rfb
    if _weaviate_rfb is None:
        _weaviate_rfb = WeaviateRFB()
    return _weaviate_rfb