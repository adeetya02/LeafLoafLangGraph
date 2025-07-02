"""
Simple in-memory cache for common searches
"""
import time
from typing import Dict, List, Any, Optional
import hashlib

class SearchCache:
    """LRU cache for search results"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.access_times: Dict[str, float] = {}
        
    def _make_key(self, query: str, alpha: float) -> str:
        """Create cache key from query and alpha"""
        key_str = f"{query.lower().strip()}:{alpha:.2f}"
        return hashlib.md5(key_str.encode()).hexdigest()[:16]
    
    def get(self, query: str, alpha: float) -> Optional[List[Dict]]:
        """Get cached results if available and not expired"""
        key = self._make_key(query, alpha)
        
        if key in self.cache:
            entry = self.cache[key]
            age = time.time() - entry["timestamp"]
            
            if age < self.ttl_seconds:
                self.access_times[key] = time.time()
                return entry["results"]
            else:
                # Expired
                del self.cache[key]
                del self.access_times[key]
        
        return None
    
    def set(self, query: str, alpha: float, results: List[Dict]):
        """Cache search results"""
        key = self._make_key(query, alpha)
        
        # Evict LRU if at capacity
        if len(self.cache) >= self.max_size:
            lru_key = min(self.access_times, key=self.access_times.get)
            del self.cache[lru_key]
            del self.access_times[lru_key]
        
        self.cache[key] = {
            "results": results,
            "timestamp": time.time(),
            "query": query,
            "alpha": alpha
        }
        self.access_times[key] = time.time()

# Global cache instance
search_cache = SearchCache()