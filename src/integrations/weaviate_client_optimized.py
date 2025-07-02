"""
Optimized Weaviate client with connection pooling for sub-300ms performance
"""
import weaviate
from weaviate.auth import AuthApiKey
import weaviate.classes.query
import weaviate.config
import httpx
import time
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
import threading
import queue
import structlog
from src.config.settings import settings
from src.config.constants import (
    WEAVIATE_TIMEOUT_SECONDS,
    WEAVIATE_MAX_RETRIES,
    SEARCH_DEFAULT_LIMIT
)

logger = structlog.get_logger()

class WeaviateConnectionPool:
    """Connection pool for Weaviate clients"""
    
    def __init__(self, 
                 pool_size: int = 5,
                 max_pool_size: int = 10,
                 connection_timeout: int = 30,
                 keep_alive: bool = True):
        self.pool_size = pool_size
        self.max_pool_size = max_pool_size
        self.connection_timeout = connection_timeout
        self.keep_alive = keep_alive
        
        # Pool management
        self._pool = queue.Queue(maxsize=max_pool_size)
        self._all_connections = []
        self._lock = threading.Lock()
        self._created_connections = 0
        
        # HTTP client configuration for connection reuse
        self._http_client_config = {
            "timeout": httpx.Timeout(
                connect=5.0,
                read=WEAVIATE_TIMEOUT_SECONDS,
                write=10.0,
                pool=5.0
            ),
            "limits": httpx.Limits(
                max_keepalive_connections=pool_size,
                max_connections=max_pool_size,
                keepalive_expiry=30.0
            ),
            "verify": True
        }
        
        # Initialize pool with minimum connections
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool with minimum connections"""
        logger.info(f"Initializing Weaviate connection pool with {self.pool_size} connections")
        
        for i in range(self.pool_size):
            try:
                client = self._create_client()
                self._pool.put(client)
                logger.debug(f"Created connection {i+1}/{self.pool_size}")
            except Exception as e:
                logger.error(f"Failed to create initial connection {i+1}: {e}")
    
    def _create_client(self) -> weaviate.WeaviateClient:
        """Create a new Weaviate client with optimized settings"""
        with self._lock:
            if self._created_connections >= self.max_pool_size:
                raise RuntimeError(f"Maximum pool size ({self.max_pool_size}) reached")
            
            # Create Weaviate v4 client with HuggingFace API key
            headers = {}
            
            # Add HuggingFace API key if available
            if hasattr(settings, 'huggingface_api_key') and settings.huggingface_api_key:
                headers["X-HuggingFace-Api-Key"] = settings.huggingface_api_key
            
            # Remove https:// prefix for connect_to_weaviate_cloud
            cluster_url = settings.weaviate_url.replace("https://", "").replace("http://", "")
            
            client = weaviate.connect_to_weaviate_cloud(
                cluster_url=cluster_url,
                auth_credentials=AuthApiKey(settings.weaviate_api_key),
                headers=headers,
                additional_config=weaviate.config.AdditionalConfig(
                    timeout=(5, WEAVIATE_TIMEOUT_SECONDS),
                    use_grpc_for_collections=False  # Disable GRPC to avoid RST_STREAM errors
                ),
                skip_init_checks=True  # Skip init for faster connection
            )
            
            self._created_connections += 1
            self._all_connections.append(client)
            
            logger.debug(f"Created new Weaviate client (total: {self._created_connections})")
            return client
    
    @contextmanager
    def get_client(self):
        """Get a client from the pool"""
        client = None
        start_time = time.time()
        
        try:
            # Try to get from pool with timeout
            try:
                client = self._pool.get(timeout=2.0)
                wait_time = (time.time() - start_time) * 1000
                if wait_time > 100:
                    logger.warning(f"Waited {wait_time:.0f}ms for connection from pool")
            except queue.Empty:
                # Pool exhausted, create new connection if under max
                logger.warning("Connection pool exhausted, creating new connection")
                client = self._create_client()
            
            # Test connection health
            try:
                client.is_ready()  # Quick health check
            except Exception:
                logger.warning("Connection unhealthy, creating new one")
                client = self._create_client()
            
            yield client
            
        finally:
            # Return to pool if healthy
            if client:
                try:
                    self._pool.put_nowait(client)
                except queue.Full:
                    # Pool is full, close the extra connection
                    logger.debug("Pool full, closing extra connection")
                    try:
                        client.close()
                    except:
                        pass
    
    def close_all(self):
        """Close all connections in the pool"""
        logger.info("Closing all Weaviate connections")
        
        # Empty the pool
        while not self._pool.empty():
            try:
                client = self._pool.get_nowait()
                client.close()
            except:
                pass
        
        # Close any outstanding connections
        for client in self._all_connections:
            try:
                client.close()
            except:
                pass
        
        self._all_connections.clear()
        self._created_connections = 0

# Global connection pool instance
_connection_pool = None

def get_connection_pool() -> WeaviateConnectionPool:
    """Get or create the global connection pool"""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = WeaviateConnectionPool(
            pool_size=5,  # Start with 5 connections
            max_pool_size=10,  # Allow up to 10 connections
            connection_timeout=30,
            keep_alive=True
        )
    return _connection_pool

class OptimizedWeaviateClient:
    """Optimized Weaviate client using connection pooling"""
    
    def __init__(self):
        self.pool = get_connection_pool()
        self.class_name = settings.weaviate_class_name
        
    def search(self, 
               query: str, 
               alpha: float = 0.5,
               limit: int = SEARCH_DEFAULT_LIMIT,
               properties: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute optimized search with connection pooling"""
        start_time = time.time()
        
        if properties is None:
            properties = [
                "sku", "name", "category", "supplier", 
                "retailPrice", "wholesalePrice", "packSize", 
                "retailPackSize", "usage", "searchTerms", 
                "isOrganic", "supplierCategory"
            ]
        
        try:
            with self.pool.get_client() as client:
                # Get the collection
                collection = client.collections.get(self.class_name)
                
                # Execute search based on alpha
                # Note: Currently using BM25 only due to HuggingFace credit limits
                # TODO: Re-enable hybrid/vector search when deployed to GCP with Vertex AI
                
                try:
                    logger.info(f"Weaviate search - query: '{query}', alpha: {alpha}, bm25_only: {settings.weaviate_bm25_only}")
                    
                    if alpha < 0.3 or settings.weaviate_bm25_only:
                        # BM25 keyword search
                        logger.info(f"Using BM25 search (alpha={alpha})")
                        result = collection.query.bm25(
                            query=query,
                            limit=limit,
                            return_properties=properties
                        )
                    elif alpha > 0.7:
                        # Pure vector search
                        logger.info(f"Using pure vector/semantic search (alpha={alpha})")
                        result = collection.query.near_text(
                            query=query,
                            limit=limit,
                            return_properties=properties
                        )
                    else:
                        # Hybrid search
                        logger.info(f"Using hybrid search (alpha={alpha})")
                        result = collection.query.hybrid(
                            query=query,
                            alpha=alpha,
                            limit=limit,
                            return_properties=properties
                        )
                except Exception as e:
                    # Fallback to BM25 if vector search fails
                    logger.error(f"Vector/hybrid search failed: {str(e)}")
                    logger.error(f"Error type: {type(e).__name__}")
                    logger.warning(f"Falling back to BM25 search")
                    result = collection.query.bm25(
                        query=query,
                        limit=limit,
                        return_properties=properties
                    )
                
                # Convert v4 objects to dict format with standardized field names
                products = []
                for obj in result.objects:
                    # Map Weaviate properties to expected format
                    product = {
                        'product_id': obj.properties.get('sku', ''),
                        'sku': obj.properties.get('sku', ''),
                        'product_name': obj.properties.get('name', ''),
                        'product_description': obj.properties.get('usage', ''),
                        'price': obj.properties.get('retailPrice', 0),
                        'wholesale_price': obj.properties.get('wholesalePrice', 0),
                        'pack_size': obj.properties.get('packSize', ''),
                        'retail_pack_size': obj.properties.get('retailPackSize', ''),
                        'supplier': obj.properties.get('supplier', ''),
                        'category': obj.properties.get('category', ''),
                        'sub_category': obj.properties.get('supplierCategory', ''),
                        'is_organic': obj.properties.get('isOrganic', False),
                        'search_terms': obj.properties.get('searchTerms', []),
                        '_additional': {
                            'id': str(obj.uuid),
                            'score': getattr(obj.metadata, 'score', None),
                            'distance': getattr(obj.metadata, 'distance', None)
                        }
                    }
                    products.append(product)
                
                # Log performance
                search_time = (time.time() - start_time) * 1000
                logger.info(f"Weaviate v4 search completed in {search_time:.0f}ms (alpha={alpha})")
                
                return {
                    "products": products,
                    "search_time_ms": search_time,
                    "alpha": alpha,
                    "query": query
                }
                
        except Exception as e:
            logger.error(f"Weaviate search failed: {e}")
            # Return empty results on error
            return {
                "products": [],
                "search_time_ms": (time.time() - start_time) * 1000,
                "alpha": alpha,
                "query": query,
                "error": str(e)
            }
    
    def get_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product by ID with connection pooling"""
        try:
            with self.pool.get_client() as client:
                collection = client.collections.get(self.class_name)
                result = collection.query.fetch_object_by_id(product_id)
                if result:
                    return result.properties
                return None
        except Exception as e:
            logger.error(f"Failed to get product by ID: {e}")
            return None
    
    def batch_get_by_ids(self, product_ids: List[str]) -> List[Dict[str, Any]]:
        """Get multiple products by IDs efficiently"""
        products = []
        
        try:
            with self.pool.get_client() as client:
                collection = client.collections.get(self.class_name)
                
                # Use where filter for batch retrieval
                result = collection.query.fetch_objects(
                    where=weaviate.classes.query.Filter.by_property("sku").contains_any(product_ids),
                    limit=len(product_ids),
                    return_properties=["sku", "name", "retailPrice", "wholesalePrice"]
                )
                
                for obj in result.objects:
                    products.append(obj.properties)
                
        except Exception as e:
            logger.error(f"Batch get failed: {e}")
        
        return products
    
    def health_check(self) -> bool:
        """Check Weaviate health using pooled connection"""
        try:
            with self.pool.get_client() as client:
                return client.is_ready()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

# Global optimized client instance
_optimized_client = None

def get_optimized_client() -> OptimizedWeaviateClient:
    """Get or create the global optimized client"""
    global _optimized_client
    if _optimized_client is None:
        _optimized_client = OptimizedWeaviateClient()
    return _optimized_client

# Cleanup function for graceful shutdown
def cleanup_connections():
    """Clean up all connections on shutdown"""
    global _connection_pool
    if _connection_pool:
        _connection_pool.close_all()
        _connection_pool = None