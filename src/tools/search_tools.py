import weaviate
from weaviate.auth import AuthApiKey
import weaviate.classes as wvc
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from src.config.settings import settings
from src.core.config_manager import config_manager
import structlog

logger = structlog.get_logger()

class ProductSearchInput(BaseModel):
    """Input schema for product search tool"""
    query: str = Field(description="The search query for products")
    limit: int = Field(default=10, description="Maximum number of results")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters")

class ProductSearchTool:
    """Tool for searching products in Weaviate"""
    
    name: str = "product_search"
    description: str = """
    Search for products in the catalog. Use this when you need to find products
    based on user queries. Returns product names, descriptions, prices, and availability.
    """
    
    def __init__(self):
        self.client = self._init_weaviate_client()
        
    def _init_weaviate_client(self):
        """Initialize Weaviate v4 client"""
        try:
            client = weaviate.connect_to_wcs(
                cluster_url=settings.weaviate_url,
                auth_credentials=AuthApiKey(settings.weaviate_api_key),
                skip_init_checks=True
            )
            logger.info("Weaviate v4 client initialized successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}")
            raise
    
    async def run(self, query: str, limit: int = 10, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute product search"""
        try:
            # Get search configuration
            search_config = config_manager.get_default_search_config()
            alpha = search_config["alpha"]
            
            # Get collection
            collection = self.client.collections.get(settings.weaviate_class_name)
            
            # Execute hybrid search
            results = collection.query.hybrid(
                query=query,
                alpha=alpha,
                limit=limit
            )
            
            # Process results
            products = []
            for item in results.objects:
                products.append(item.properties)
            
            return {
                "success": True,
                "query": query,
                "count": len(products),
                "products": products,
                "search_config": search_config
            }
            
        except Exception as e:
            logger.error(f"Product search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "products": []
            }

class GetProductDetailsInput(BaseModel):
    """Input schema for getting product details"""
    product_id: str = Field(description="The product ID to get details for")

class GetProductDetailsTool:
    """Tool for getting detailed information about a specific product"""
    
    name: str = "get_product_details"
    description: str = """
    Get detailed information about a specific product including full description,
    nutritional info, and availability. Use this when you need more details about
    a product found in search results.
    """
    
    def __init__(self):
        self.client = weaviate.connect_to_wcs(
            cluster_url=settings.weaviate_url,
            auth_credentials=AuthApiKey(settings.weaviate_api_key),
            skip_init_checks=True
        )
    
    async def run(self, product_id: str) -> Dict[str, Any]:
        """Get detailed product information"""
        try:
            # Get collection
            collection = self.client.collections.get(settings.weaviate_class_name)
            
            # Query by product ID
            results = collection.query.fetch_objects(
                where=collection.filter.by_property("productId").equal(product_id),
                limit=1
            )
            
            if results.objects:
                product = results.objects[0].properties
                return {
                    "success": True,
                    "product": product
                }
            else:
                return {
                    "success": False,
                    "error": "Product not found",
                    "product_id": product_id
                }
                
        except Exception as e:
            logger.error(f"Get product details failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "product_id": product_id
            }

# Tool instances
product_search_tool = ProductSearchTool()
get_product_details_tool = GetProductDetailsTool()

# Tool definitions for agents
AVAILABLE_TOOLS = {
    "product_search": product_search_tool,
    "get_product_details": get_product_details_tool
}