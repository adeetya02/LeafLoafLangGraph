"""
Simple Weaviate v4 client without pooling
"""
import weaviate
from weaviate.auth import AuthApiKey
import weaviate.config
import time
from typing import Dict, List, Any, Optional
import logging
from src.config.settings import settings
from src.config.constants import (
    WEAVIATE_TIMEOUT_SECONDS,
    SEARCH_DEFAULT_LIMIT
)

logger = logging.getLogger(__name__)

class SimpleWeaviateClient:
    """Simple Weaviate client without connection pooling"""
    
    def __init__(self):
        self.class_name = settings.weaviate_class_name
        
    def _create_client(self):
        """Create a new Weaviate client"""
        headers = {}
        
        # Add HuggingFace API key if available
        if hasattr(settings, 'huggingface_api_key') and settings.huggingface_api_key:
            headers["X-HuggingFace-Api-Key"] = settings.huggingface_api_key
            logger.info(f"HuggingFace API key added to headers: {settings.huggingface_api_key[:10]}...")
            
        # Remove https:// prefix for connect_to_weaviate_cloud
        cluster_url = settings.weaviate_url.replace("https://", "").replace("http://", "")
        
        return weaviate.connect_to_weaviate_cloud(
            cluster_url=cluster_url,
            auth_credentials=AuthApiKey(settings.weaviate_api_key),
            headers=headers,
            additional_config=weaviate.config.AdditionalConfig(
                timeout=(5, WEAVIATE_TIMEOUT_SECONDS),
            )
        )
    
    def search(self, 
               query: str, 
               alpha: float = 0.5,
               limit: int = SEARCH_DEFAULT_LIMIT,
               properties: Optional[List[str]] = None) -> Dict[str, Any]:
        """Execute search"""
        start_time = time.time()
        
        if properties is None:
            properties = [
                "sku", "name", "category", "supplier", 
                "retailPrice", "wholesalePrice", "packSize", 
                "retailPackSize", "usage", "searchTerms", 
                "isOrganic", "supplierCategory"
            ]
        
        client = None
        try:
            # Create client
            client = self._create_client()
            collection = client.collections.get(self.class_name)
            
            # Try hybrid search first if alpha > 0
            if alpha > 0:
                try:
                    # Check if vectorizer is configured
                    config = collection.config.get()
                    if config.vectorizer and config.vectorizer != "none":
                        # Use hybrid search with alpha
                        result = collection.query.hybrid(
                            query=query,
                            alpha=alpha,
                            limit=limit,
                            return_properties=properties
                        )
                        logger.info(f"Hybrid search succeeded with alpha={alpha}")
                    else:
                        # No vectorizer, use BM25
                        logger.info("No vectorizer configured, using BM25 search")
                        result = collection.query.bm25(
                            query=query,
                            limit=limit,
                            return_properties=properties
                        )
                except Exception as hybrid_error:
                    # Fall back to BM25 on any hybrid search error
                    logger.warning(f"Hybrid search failed, falling back to BM25: {hybrid_error}")
                    result = collection.query.bm25(
                        query=query,
                        limit=limit,
                        return_properties=properties
                    )
            else:
                # Alpha = 0, pure keyword search
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
        finally:
            # Always close the client
            if client:
                try:
                    client.close()
                except:
                    pass
    
    def get_by_id(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product by ID"""
        client = None
        try:
            client = self._create_client()
            collection = client.collections.get(self.class_name)
            result = collection.query.fetch_object_by_id(product_id)
            if result:
                return result.properties
            return None
        except Exception as e:
            logger.error(f"Failed to get product by ID: {e}")
            return None
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass
    
    def health_check(self) -> bool:
        """Check Weaviate health"""
        client = None
        try:
            client = self._create_client()
            return client.is_ready()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
        finally:
            if client:
                try:
                    client.close()
                except:
                    pass

# Global simple client instance
_simple_client = None

def get_simple_client() -> SimpleWeaviateClient:
    """Get or create the global simple client"""
    global _simple_client
    if _simple_client is None:
        _simple_client = SimpleWeaviateClient()
    return _simple_client