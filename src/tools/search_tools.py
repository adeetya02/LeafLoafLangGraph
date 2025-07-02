import weaviate
from weaviate.auth import AuthApiKey
import weaviate.classes as wvc
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from src.config.settings import settings
from src.core.config_manager import config_manager
from src.config.constants import (
    TEST_MODE,
    WEAVIATE_MAX_SEARCHES_PER_MINUTE,
    WEAVIATE_MAX_RESULTS_PER_SEARCH,
    WEAVIATE_RETRIEVAL_LIMIT,
    WEAVIATE_EXPIRY_DATE,
    SEARCH_DEFAULT_LIMIT
)
from src.utils.wholesale_retail_converter import WholesaleRetailConverter
from src.integrations.weaviate_client_optimized import get_optimized_client
import structlog
from datetime import datetime
import os
import random

logger = structlog.get_logger()

class ProductSearchInput(BaseModel):
  """Input schema for product search tool"""
  query: str = Field(description="The search query for products")
  limit: int = Field(default=SEARCH_DEFAULT_LIMIT, description="Maximum number of results")
  filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters")

class ProductSearchTool:
  """Tool for searching products in Weaviate"""
  
  name: str = "product_search"
  description: str = """
  Search for products in the catalog. Use this when you need to find products
  based on user queries. Returns product names, descriptions, prices, and availability.
  """
  
  def __init__(self):
      self.test_mode = TEST_MODE
      self.search_count = 0
      self.last_reset_time = datetime.now()
      self._client = None  # Lazy load client
      self._optimized_client = None  # Optimized client with pooling
      
      if not self.test_mode:
          days_until_expiry = (WEAVIATE_EXPIRY_DATE - datetime.now()).days
          logger.info(f"Weaviate will be initialized on first use. Expires in {days_until_expiry} days")
          # Initialize optimized client with pooling
          self._optimized_client = get_optimized_client()
          logger.info("Optimized Weaviate client initialized with connection pooling")
      else:
          logger.info("Running in TEST_MODE - using mock data")
  
  @property
  def client(self):
      """Lazy load Weaviate client on first access"""
      if self._client is None and not self.test_mode:
          try:
              self._client = self._init_weaviate_client()
          except Exception as e:
              logger.error(f"Failed to initialize Weaviate client: {e}")
              # Don't raise - let the search method handle the None client
      return self._client
      
  def _init_weaviate_client(self):
      """Initialize Weaviate v4 client with HuggingFace headers"""
      try:
          # Get HuggingFace API key from settings
          hf_api_key = settings.huggingface_api_key
          
          # Set up additional headers for HuggingFace
          additional_headers = {
              "X-HuggingFace-Api-Key": hf_api_key  # Note: capital 'F' in HuggingFace
          } if hf_api_key else {}
          
          # Remove https:// prefix for connect_to_weaviate_cloud
          cluster_url = settings.weaviate_url.replace("https://", "").replace("http://", "")
          
          client = weaviate.connect_to_weaviate_cloud(
              cluster_url=cluster_url,
              auth_credentials=AuthApiKey(settings.weaviate_api_key),
              headers=additional_headers,
              skip_init_checks=True
          )
          logger.info("Weaviate v4 client initialized with HuggingFace auth")
          return client
      except Exception as e:
          logger.error(f"Failed to initialize Weaviate client: {e}")
          return None  # Return None to trigger fallback logic
  def close(self):
      """Close the Weaviate client connection"""
      if self._client is not None:
          self._client.close()
          logger.info("Weaviate client connection closed")
  
  def _get_mock_products(self, query: str, limit: int) -> List[Dict[str, Any]]:
      """Return mock products for testing - includes Baldor-style produce"""
      mock_products = [
          {
              "product_name": "Red Bell Peppers (3-pack)",
              "product_description": "Fresh red bell peppers, perfect for salads and cooking",
              "supplier": "Baldor Specialty Foods",
              "price": 4.99,
              "category": "Produce",
              "dietary_info": ["Fresh", "Gluten-Free"],
              "in_stock": True,
              "sku": "PEPPER_RED_3PK"
          },
          {
              "product_name": "Tri-Color Bell Peppers (3-pack)",
              "product_description": "Mix of red, yellow, and green bell peppers",
              "supplier": "Baldor Specialty Foods",
              "price": 5.99,
              "category": "Produce",
              "dietary_info": ["Fresh", "Gluten-Free"],
              "in_stock": True,
              "sku": "PEPPER_TRI_3PK"
          },
          {
              "product_name": "Green Bell Peppers (Each)",
              "product_description": "Fresh green bell pepper",
              "supplier": "Baldor Specialty Foods",
              "price": 1.49,
              "category": "Produce",
              "dietary_info": ["Fresh", "Gluten-Free"],
              "in_stock": True,
              "sku": "PEPPER_GREEN_EA"
          },
          {
              "product_name": "Organic Strawberries (1 lb)",
              "product_description": "Sweet organic strawberries",
              "supplier": "Baldor Specialty Foods",
              "price": 6.99,
              "category": "Produce",
              "dietary_info": ["Organic", "Fresh"],
              "in_stock": True,
              "sku": "STRAWBERRY_ORG_1LB"
          },
          {
              "product_name": "Baby Red Beets (Bunch)",
              "product_description": "Tender baby red beets with greens",
              "supplier": "Baldor Specialty Foods",
              "price": 3.99,
              "category": "Produce",
              "dietary_info": ["Fresh", "Gluten-Free"],
              "in_stock": True,
              "sku": "BEETS_BABY_RED"
          }
      ]
      
      # Filter based on query
      query_lower = query.lower()
      filtered = []
      
      for product in mock_products:
          score = 0
          product_text = f"{product['product_name']} {product['product_description']} {' '.join(product['dietary_info'])}".lower()
          
          # Simple scoring
          for word in query_lower.split():
              if word in product_text:
                  score += 1
          
          if score > 0:
              product['_score'] = score
              filtered.append(product)
      
      # Sort by score and return top results
      filtered.sort(key=lambda x: x['_score'], reverse=True)
      return filtered[:limit]

  def _check_rate_limit(self):
      """Check if we're within rate limits"""
      now = datetime.now()
      # Reset counter every minute
      if (now - self.last_reset_time).seconds >= 60:
          self.search_count = 0
          self.last_reset_time = now
      
      if self.search_count >= WEAVIATE_MAX_SEARCHES_PER_MINUTE:
          raise Exception(f"Rate limit exceeded: {WEAVIATE_MAX_SEARCHES_PER_MINUTE} searches/minute")
      
      self.search_count += 1

  async def run(self, query: str, limit: int = SEARCH_DEFAULT_LIMIT, alpha: Optional[float]= None,filters: Optional[Dict] = None) -> Dict[str, Any]:
      """Execute product search"""
      
      # Use mock data in test mode
      if self.test_mode:
          products = self._get_mock_products(query, limit)
          return {
              "success": True,
              "query": query,
              "count": len(products),
              "products": products,
              "search_config": {"alpha": alpha or 0.5, "test_mode": True}
          }
      
      # Check rate limits for production
      self._check_rate_limit()
      
      # Search for more internally but return only requested amount
      internal_limit = min(WEAVIATE_RETRIEVAL_LIMIT, max(30, limit * 3))  # Fetch more for filtering
      display_limit = min(limit, WEAVIATE_MAX_RESULTS_PER_SEARCH)  # Return max configured amount
      
      try:
          # Get search configuration
          search_config = config_manager.get_default_search_config()
          
          # Use provided alpha or fall back to config
          search_alpha = alpha if alpha is not None else search_config["alpha"]
          
          logger.info(f"Searching for: {query}, alpha: {search_alpha}, limit: {limit}")
          
          # Use optimized client with connection pooling
          if self._optimized_client:
              # Use the optimized search with connection pooling
              search_result = self._optimized_client.search(
                  query=query,
                  alpha=search_alpha,
                  limit=internal_limit  # Get more results internally
              )
              
              # Extract products from result
              raw_products = search_result.get("products", [])
              search_time = search_result.get("search_time_ms", 0)
              
              logger.info(f"Search completed in {search_time:.0f}ms, found {len(raw_products)} products")
              
              # Convert wholesale to retail format
              products = []
              converter = WholesaleRetailConverter()
              
              for product in raw_products:
                  # Convert datetime objects to strings
                  cleaned_product = {}
                  for key, value in product.items():
                      if isinstance(value, datetime):
                          cleaned_product[key] = value.isoformat()
                      else:
                          cleaned_product[key] = value
                  
                  # Convert wholesale to retail format
                  retail_product = converter.format_retail_display(cleaned_product)
                  products.append(retail_product)
              
              # Add search timing to config
              search_config["search_time_ms"] = search_time
              search_config["connection_pooling"] = False
              
          else:
              # Fallback to regular client
              logger.warning("Simple client not available, using regular client")
              
              # Check if client is available
              if self.client is None:
                  logger.error("Weaviate client unavailable - cannot perform search")
                  return {
                      "success": False,
                      "query": query,
                      "count": 0,
                      "products": [],
                      "error": "Search service temporarily unavailable",
                      "search_config": {"status": "weaviate_unavailable"}
                  }
              
              # Get collection
              collection = self.client.collections.get(settings.weaviate_class_name)
              
              # Try hybrid search first
              try:
                  # Hybrid search with alpha parameter
                  results = collection.query.hybrid(
                      query=query,
                      alpha=search_alpha,
                      limit=internal_limit
                  )
                  logger.info(f"Hybrid search succeeded with alpha={search_alpha}, fusion=relativeScoreFusion")
              except Exception as hybrid_error:
                  # If hybrid fails (e.g., no credits or auth issues), fall back to BM25
                  error_str = str(hybrid_error)
                  if "402" in error_str or "401" in error_str or "exceeded" in error_str.lower() or "vectorize" in error_str:
                      logger.warning(f"Hybrid search failed (credits exhausted), falling back to BM25: {hybrid_error}")
                      results = collection.query.bm25(
                          query=query,
                          limit=internal_limit
                      )
                      logger.info("BM25 search succeeded - using keyword search only")
                      search_config["search_type"] = "bm25_fallback"
                      search_config["fallback_reason"] = "vectorization_credits_exhausted"
                  else:
                      raise hybrid_error
              
              # Process results and convert wholesale to retail
              products = []
              converter = WholesaleRetailConverter()
              
              for item in results.objects:
                  product = item.properties
                  # Convert datetime objects to strings
                  cleaned_product = {}
                  for key, value in product.items():
                      if isinstance(value, datetime):
                          cleaned_product[key] = value.isoformat()
                      else:
                          cleaned_product[key] = value
                  
                  # Convert wholesale to retail format
                  retail_product = converter.format_retail_display(cleaned_product)
                  products.append(retail_product)
          
          logger.info(f"Found {len(products)} products total, returning {display_limit}")
          if len(products) > 0:
              logger.info(f"First product: {products[0].get('name', 'No name')}")
          
          # Return all products - let the agent handle filtering and limiting
          return {
              "success": True,
              "query": query,
              "count": len(products),
              "products": products,  # Return all products for filtering
              "search_config": search_config,
              "internal_limit": internal_limit,
              "requested_limit": limit
          }
          
      except Exception as e:
          logger.error(f"Product search failed: {e}")
          
          # Check if this is a connection error
          error_msg = str(e)
          if "Could not connect to Weaviate" in error_msg or "Connection to Weaviate failed" in error_msg:
              logger.error("Weaviate connection failed - service unavailable")
              return {
                  "success": False,
                  "query": query,
                  "count": 0,
                  "products": [],
                  "error": "Search service temporarily unavailable. Please try again later.",
                  "search_config": {"status": "weaviate_connection_failed"}
              }
          
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
      self.test_mode = TEST_MODE
      self._client = None  # Lazy load client
      
      if self.test_mode:
          logger.info("GetProductDetailsTool running in TEST_MODE")
      else:
          logger.info("GetProductDetailsTool will initialize Weaviate on first use")
  
  @property
  def client(self):
      """Lazy load Weaviate client on first access"""
      if self._client is None and not self.test_mode:
          hf_api_key = settings.huggingface_api_key
          additional_headers = {
              "X-HuggingFace-Api-Key": hf_api_key
          } if hf_api_key else {}
          
          self._client = weaviate.connect_to_weaviate_cloud(
              cluster_url=settings.weaviate_url,
              auth_credentials=AuthApiKey(settings.weaviate_api_key),
              headers=additional_headers,
              skip_init_checks=True
          )
          logger.info("GetProductDetailsTool Weaviate client initialized")
      return self._client
  
  def close(self):
      """Close the Weaviate client connection"""
      if self._client is not None:
          self._client.close()
          logger.info("GetProductDetailsTool Weaviate client connection closed")
  
  async def run(self, product_id: str) -> Dict[str, Any]:
      """Get detailed product information"""
      if self.test_mode:
          # Return mock product details
          return {
              "success": True,
              "product": {
                  "id": product_id,
                  "name": f"Product {product_id}",
                  "description": "Detailed product information",
                  "price": 4.99,
                  "nutrition": {
                      "calories": 120,
                      "protein": "8g",
                      "calcium": "30% DV"
                  },
                  "in_stock": True
              }
          }
          
      try:
          # Get collection
          collection = self.client.collections.get(settings.weaviate_class_name)
          
          # Query by product ID using the actual field name
          results = collection.query.fetch_objects(
              where=collection.filter.by_property("sku").equal(product_id),
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