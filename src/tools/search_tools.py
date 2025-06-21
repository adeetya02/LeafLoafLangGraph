from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import weaviate
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
        """Initialize Weaviate client"""
        try:
            client = weaviate.Client(
                url=settings.weaviate_url,
                auth_client_secret=weaviate.AuthApiKey(api_key=settings.weaviate_api_key),
                timeout_config=(5, 15)  # (connect timeout, read timeout)
            )
            logger.info("Weaviate client initialized successfully")
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
            
            # Build the search query
            search_builder = (
                self.client.query
                .get(settings.weaviate_class_name, ["name", "description", "brand", "size", "category"])
                .with_hybrid(query=query, alpha=alpha)
                .with_limit(limit)
            )
            
            # Add filters if provided
            if filters:
                search_builder = search_builder.with_where(filters)
            
            # Execute search
            results = search_builder.do()
            
            # Process results
            products = results.get("data", {}).get("Get", {}).get(settings.weaviate_class_name, [])
            
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
        self.client = ProductSearchTool()._init_weaviate_client()
    
    async def run(self, product_id: str) -> Dict[str, Any]:
        """Get detailed product information"""
        try:
            # Get product by ID
            result = (
                self.client.query
                .get(settings.weaviate_class_name)
                .with_where({
                    "path": ["productId"],
                    "operator": "Equal", 
                    "valueText": product_id
                })
                .do()
            )
            
            products = result.get("data", {}).get("Get", {}).get(settings.weaviate_class_name, [])
            
            if products:
                return {
                    "success": True,
                    "product": products[0]
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