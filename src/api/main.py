import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import time
from datetime import datetime
import asyncio
import os

from src.config.settings import settings
from src.config.constants import SEARCH_DEFAULT_LIMIT
from src.core.graph import search_graph
# Optionally use enhanced graph with parallel execution
# from src.core.graph_v2 import enhanced_graph as search_graph
from src.models.state import SearchState, AgentStatus, SearchStrategy
from src.utils.id_generator import generate_request_id, generate_trace_id
import structlog
from src.core.config_manager import config_manager
from config.product_attributes import PRODUCT_ATTRIBUTES, DEFAULT_ALPHA, MIN_ALPHA, MAX_ALPHA
from langsmith import traceable
from src.cache.redis_feature import redis_feature, smart_redis_manager
from src.middleware.cache_middleware_v2 import create_cache_middleware_v2, SearchLoggingMiddlewareV2
from src.api.promotion_management import router as promotion_router
from src.api.personalization_endpoints import router as personalization_router
from src.memory.memory_registry import MemoryRegistry
from src.memory.memory_interfaces import MemoryBackend
from src.memory.feedback_collector import feedback_collector

logger = structlog.get_logger()

# Initialize FastAPI app
app = FastAPI(
  title=settings.api_title,
  version=settings.api_version,
  description="Intelligent product search with LangGraph autonomous agents"
)

# Add CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],  # Configure appropriately for production
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Add cache middleware with feature flag support
app.add_middleware(create_cache_middleware_v2)

# Initialize search logging
search_logger = SearchLoggingMiddlewareV2()

# Serve static files FIRST to avoid router conflicts
from pathlib import Path
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")
    logger.info(f"Static files mounted from: {static_dir}")
else:
    logger.warning(f"Static directory not found: {static_dir}")

# Include promotion management router
app.include_router(promotion_router)
app.include_router(personalization_router)

# Import learning loop for click tracking
from src.memory.learning_loop import learning_loop

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "LeafLoaf LangGraph API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "search": "POST /api/v1/search",
            "voice_webhooks": {
                "search": "POST /api/v1/voice/webhook/search",
                "add_to_cart": "POST /api/v1/voice/webhook/add_to_cart",
                "show_cart": "POST /api/v1/voice/webhook/show_cart",
                "confirm_order": "POST /api/v1/voice/webhook/confirm_order"
            }
        },
        "documentation": "https://github.com/adeetya02/LeafLoafLangGraph"
    }

# Click tracking endpoint for demos
@app.post("/api/v1/track/click")
async def track_click(request: Request):
    """Track product clicks for learning"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        product = data.get("product")
        query = data.get("query")
        
        if user_id and product:
            await learning_loop.record_search_click(
                user_id=user_id,
                query=query or "",
                clicked_product=product,
                position=data.get("position", 0)
            )
            
        return {"success": True}
    except Exception as e:
        logger.error(f"Error tracking click: {e}")
        return {"success": False, "error": str(e)}

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for GCP"""
    try:
        # Check Weaviate connection
        from src.integrations.weaviate_client_optimized import get_optimized_client
        weaviate_healthy = get_optimized_client().health_check()
        
        return {
            "status": "healthy",
            "service": "leafloaf",
            "version": "1.0.0",
            "weaviate": "connected" if weaviate_healthy else "disconnected",
            "environment": settings.environment,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info(
        "Starting LeafLoaf API",
        redis_enabled=redis_feature.enabled,
        redis_url_configured=bool(settings.redis_url),
        environment=settings.environment
    )
    
    if redis_feature.enabled:
        try:
            manager = await smart_redis_manager._get_manager()
            logger.info("Redis feature enabled and initialized")
        except Exception as e:
            logger.error(f"Redis initialization failed: {e}")
            redis_feature.mark_degraded()
    else:
        logger.info("Redis feature disabled - using in-memory fallback")
    
    # Graphiti will be initialized by agents as needed
    logger.info("Graphiti memory will be handled by individual agents")
    
    # Start feedback collector
    await feedback_collector.start()
    logger.info("Feedback collector started")
    
    # Start transcript processor for voice conversations
    try:
        from src.services.transcript_processor import get_transcript_processor
        processor = get_transcript_processor(os.getenv("DEEPGRAM_API_KEY", ""))
        asyncio.create_task(processor.start_processing())
        logger.info("Transcript processor started for voice analysis")
    except Exception as e:
        logger.warning(f"Could not start transcript processor: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    if redis_feature.enabled:
        try:
            manager = await smart_redis_manager._get_manager()
            if hasattr(manager, 'close'):
                await manager.close()
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")
    
    # Stop feedback collector
    try:
        await feedback_collector.stop()
        logger.info("Feedback collector stopped")
    except Exception as e:
        logger.error(f"Error stopping feedback collector: {e}")
    
    # Clean up Graphiti memory
    try:
        await MemoryRegistry.cleanup()
        logger.info("Graphiti memory cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up Graphiti: {e}")

# Request/Response models with OpenAPI documentation
class SearchRequest(BaseModel):
  """Search request with support for user context and preferences"""
  query: str = Field(
    ..., 
    description="Natural language search query",
    example="organic oat milk"
  )
  user_id: Optional[str] = Field(
    None,
    description="User identifier for personalization",
    example="user-123"
  )
  session_id: Optional[str] = Field(
    None,
    description="Session ID for conversation context",
    example="session-abc-123"
  )
  limit: Optional[int] = Field(
    SEARCH_DEFAULT_LIMIT,
    description="Maximum number of results",
    ge=1,
    le=50
  )
  filters: Optional[Dict[str, Any]] = Field(
    None,
    description="Additional filters (dietary, price range, brands)",
    example={"dietary": ["organic", "gluten-free"], "max_price": 10.0}
  )
  preferences: Optional[Dict[str, Any]] = Field(
    None,
    description="User preference overrides for this request"
  )
  graphiti_mode: Optional[str] = Field(
    None,
    description="Graphiti personalization mode: enhance, supplement, both, off",
    example="enhance"
  )
  show_all: Optional[bool] = Field(
    False,
    description="Override to show all results instead of personalized (for enhance mode)",
    example=False
  )
  source: Optional[str] = Field(
    "app",
    description="Request source: app, voice, web",
    example="app"
  )

class ProductInfo(BaseModel):
  """Product information schema"""
  product_id: str = Field(..., description="Unique product identifier")
  sku: Optional[str] = Field(None, description="Stock keeping unit for cart operations")
  product_name: str = Field(..., description="Product display name")
  product_description: Optional[str] = Field(None, description="Product description")
  price: float = Field(..., description="Current price")
  supplier: str = Field(..., description="Brand/supplier name")
  category: str = Field(..., description="Product category")
  dietary_info: List[str] = Field(default_factory=list, description="Dietary attributes")
  in_stock: bool = Field(True, description="Availability status")
  score: Optional[float] = Field(None, description="Search relevance score")
  
class SearchResponse(BaseModel):
  """Search response with detailed execution metadata"""
  success: bool = Field(..., description="Whether the search succeeded")
  query: str = Field(..., description="Original search query")
  results: Optional[List[ProductInfo]] = Field(
    None,
    description="List of matching products (deprecated, use products)"
  )
  products: List[ProductInfo] = Field(
    default_factory=list,
    description="List of matching products"
  )
  metadata: Dict[str, Any] = Field(
    default_factory=dict,
    description="Search metadata (counts, categories, facets)"
  )
  execution: Dict[str, Any] = Field(
    default_factory=dict,
    description="Execution details (timing, agents used)"
  )
  conversation: Optional[Dict[str, Any]] = Field(
    default_factory=dict,
    description="Conversation context (intent, response)"
  )
  message: Optional[str] = Field(None, description="User-facing message")
  error: Optional[str] = Field(None, description="Error message if failed")
  pagination: Optional[Dict[str, Any]] = Field(
    None,
    description="Pagination info for lazy loading"
  )
  langsmith_trace_url: Optional[str] = Field(
    None,
    description="LangSmith trace for debugging"
  )
  suggestions: Optional[List[str]] = Field(
    None,
    description="Alternative search suggestions"
  )
  order: Optional[Dict[str, Any]] = Field(
    None,
    description="Current order/cart information"
  )
# Alpha calculation is handled by Gemma (fine-tuned Garden version or API fallback)
# No rule-based calculation - Gemma is the single source of truth    

# Initialize state for a new search
def create_initial_state(request: SearchRequest, calculated_alpha: float) -> SearchState:
  """Create initial state for LangGraph execution"""
  request_id = generate_request_id()
  trace_id = generate_trace_id()
  
  # Get default search config
  search_config = config_manager.get_default_search_config()
  
  # Extract filters and preferences
  filters = request.filters or {}
  preferences = request.preferences or {}
  
  return {
      # Messages for React pattern
      "messages": [{
          "role": "human",
          "content": request.query,
          "tool_calls": None,
          "tool_call_id": None
      }],
      
      # Request context
      "query": request.query,
      "request_id": request_id,
      "timestamp": datetime.utcnow(),
      
      # Search config (static for now)
      "alpha_value": calculated_alpha,
      "search_strategy": SearchStrategy.HYBRID,
      
      # Agent state
      "next_action": None,
      "reasoning": [],
      "routing_decision": None,
      "should_search": False,    # This too!
      "search_params": {
          "graphiti_mode": request.graphiti_mode,
          "show_all": request.show_all,
          "limit": request.limit,
          "source": request.source
      },       # And this!
      "search_results": [],
      "search_metadata": {},
      "pending_tool_calls": [],
      "completed_tool_calls": [],
      
      # NEW FIELDS for Gemma and Order Agent
      "session_id": request.session_id or str(uuid.uuid4()),
      "enhanced_query": None,
      "current_order": {"items": []},
      "order_metadata": {},
      "user_context": {
          "user_id": request.user_id,
          "filters": filters,
          "preferences": preferences
      },
      "preferences": preferences.get("preferred_brands", []),
      "filters": filters,
      
      # Graphiti personalization parameters
      "user_id": request.user_id,  # Added at top level for agents
      "graphiti_mode": request.graphiti_mode,
      "show_all": request.show_all,
      "source": request.source,
      
      # Execution tracking
      "agent_status": {},
      "agent_timings": {},
      "total_execution_time": 0,
      
      # Tracing
      "trace_id": trace_id,
      "span_ids": {},
      
      # Control flow
      "should_continue": True,
      "final_response": {},
      "error": None,
      
      # Missing fields that agents expect
      "intent": None,
      "confidence": 0.0
  }

@app.post("/api/v1/search", response_model=SearchResponse)
async def search_products(request: SearchRequest, req: Request):
  """Main search endpoint with full execution transparency"""
  start_time = time.perf_counter()
  
  # Get user info from middleware
  user_id = getattr(req.state, 'user_id', request.user_id or 'anonymous')
  user_uuid = getattr(req.state, 'user_uuid', str(uuid.uuid4()))
  session_id = request.session_id or getattr(req.state, 'session_id', str(uuid.uuid4()))
  
  try:
      # Alpha will be calculated by Gemma in the supervisor
      # This is just a placeholder that will be overridden
      calculated_alpha = 0.5
      # Check cache first (only if Redis is enabled)
      cached_response = None
      if redis_feature.enabled:
          try:
              manager = await smart_redis_manager._get_manager()
              cached_response = await manager.get_cached_response(
                  user_id=user_id,
                  query=request.query,
                  intent="product_search"  # Will be refined later
              )
          except Exception as e:
              logger.error(f"Cache check failed: {e}")
              redis_feature.mark_degraded()
      
      if cached_response:
          # Add cache hit metadata
          cached_response["metadata"]["cache_hit"] = True
          cached_response["metadata"]["response_time_ms"] = (time.perf_counter() - start_time) * 1000
          return SearchResponse(
              success=True,
              query=request.query,
              products=cached_response.get("results", []),
              metadata=cached_response.get("metadata", {}),
              execution=cached_response.get("execution", {}),
              message=cached_response.get("conversation", {}).get("response"),
              suggestions=cached_response.get("suggestions")
          )
      
      # Graphiti will be handled by individual agents
      graphiti_entities = []
      graphiti_context = {}
      
      # Create initial state
      initial_state = create_initial_state(request,calculated_alpha)
      initial_state["user_id"] = user_id
      initial_state["user_uuid"] = user_uuid
      initial_state["session_id"] = session_id
      
      # Graphiti context will be populated by agents
      
      logger.info(
          "Starting search",
          request_id=initial_state["request_id"],
          query=request.query
      )
      
      # Execute the graph with timeout
      final_state = await asyncio.wait_for(
          search_graph.ainvoke(initial_state),
          timeout=settings.search_timeout_ms / 1000  # Convert to seconds
      )
      
      # Collect Graphiti results from final state (populated by agents)
      if final_state and "graphiti_context" in final_state:
          graphiti_context = final_state["graphiti_context"]
          graphiti_entities = graphiti_context.get("entities", [])
      
      # Calculate total execution time
      total_time = (time.perf_counter() - start_time) * 1000
      
      # Log performance breakdown
      if 'agent_timings' in final_state:
          timings = final_state['agent_timings']
          logger.info(f"Performance breakdown: Supervisor={timings.get('supervisor', 0):.0f}ms, "
                     f"Search={timings.get('product_search', 0):.0f}ms, "
                     f"Compiler={timings.get('response_compiler', 0):.0f}ms, "
                     f"Total={total_time:.0f}ms")
      
      # Get the compiled response
      response_data = final_state.get("final_response", {})
      
      logger.info(f"Final state routing: {final_state.get('routing_decision')}")
      logger.info(f"Final response success: {response_data.get('success')}")
      logger.info(f"Final response message: {response_data.get('message')}")
      logger.info(f"Response data keys: {list(response_data.keys())}")
      logger.info(f"Has order in response_data: {'order' in response_data}")
      if 'order' in response_data:
          logger.info(f"Order items: {len(response_data['order'].get('items', []))}")
      
      # Add LangSmith trace URL if available
      trace_url = None
      if settings.langchain_tracing_v2 and final_state.get("trace_id"):
          trace_url = f"https://smith.langchain.com/public/{final_state['trace_id']}/r"
      
      # Convert products to ProductInfo objects
      raw_products = response_data.get("products", [])
      products = []
      for p in raw_products:
          try:
              products.append(ProductInfo(
                  product_id=p.get("id", p.get("product_id", str(uuid.uuid4()))),
                  sku=p.get("sku"),  # Include SKU for cart operations
                  product_name=p.get("product_name", p.get("name", "Unknown")),
                  product_description=p.get("product_description", p.get("description")),
                  price=float(p.get("price", 0.0)),
                  supplier=p.get("supplier", p.get("brand", "Unknown")),
                  category=p.get("category", "General"),
                  dietary_info=p.get("dietary_info", []),
                  in_stock=p.get("in_stock", True),
                  score=p.get("_score")
              ))
          except Exception as e:
              logger.warning(f"Failed to parse product: {e}")
      
      # Prepare response data for logging
      response_for_logging = {
          "results": [p.dict() for p in products] if products else response_data.get("order", {}),
          "metadata": response_data.get("metadata", {}),
          "execution": {
              **response_data.get("execution", {}),
              "total_time_ms": total_time,
              "timeout_ms": settings.search_timeout_ms
          },
          "conversation": {
              "intent": final_state.get("intent", "unknown"),
              "confidence": final_state.get("confidence", 0.0),
              "response": response_data.get("message", "")
          },
          "suggestions": response_data.get("suggestions")
      }
      
      # Log search to Redis
      try:
          await search_logger.log_search_request(
              request_data={"query": request.query},
              response_data=response_for_logging,
              user_id=user_id,
              user_uuid=user_uuid,
              session_id=session_id,
              response_time_ms=total_time
          )
      except Exception as e:
          logger.error(f"Failed to log search to Redis: {e}")
      
      # Add Graphiti data to metadata
      if graphiti_entities or graphiti_context:
          response_data.setdefault("metadata", {})
          response_data["metadata"]["graphiti"] = {
              "entities_extracted": len(graphiti_entities),
              "entities": graphiti_entities[:10],  # Limit to first 10
              "context_available": bool(graphiti_context),
              "cached_entities": graphiti_context.get("cached_entities", [])[:10],
              "reorder_patterns": graphiti_context.get("reorder_patterns", [])[:5]
          }
      
      # Build response - check if this is an order operation
      logger.info(f"Response data keys: {list(response_data.keys())}")
      logger.info(f"Has order: {'order' in response_data}")
      logger.info(f"Order data: {response_data.get('order')}")
      logger.info(f"Routing decision: {final_state.get('routing_decision')}")
      if "order" in response_data:
          # For order operations, include order in response
          return SearchResponse(
              success=response_data.get("success", False),
              query=request.query,
              products=[],  # No products for order operations
              metadata=response_data.get("metadata", {}),
              execution={
                  **response_data.get("execution", {}),
                  "total_time_ms": total_time,
                  "timeout_ms": settings.search_timeout_ms
              },
              conversation={
                  "intent": final_state.get("intent", "unknown"),
                  "confidence": final_state.get("confidence", 0.0),
                  "response": response_data.get("message", "")
              },
              message=response_data.get("message"),
              error=response_data.get("error"),
              langsmith_trace_url=trace_url,
              suggestions=response_data.get("suggestions"),
              order=response_data.get("order")  # Include order data
          )
      else:
          # Regular search response
          return SearchResponse(
              success=response_data.get("success", False),
              query=request.query,
              products=products,
              metadata=response_data.get("metadata", {}),
              execution={
                  **response_data.get("execution", {}),
                  "total_time_ms": total_time,
                  "timeout_ms": settings.search_timeout_ms
              },
              conversation={
                  "intent": final_state.get("intent", "unknown"),
                  "confidence": final_state.get("confidence", 0.0),
                  "response": response_data.get("message", "")
              },
              message=response_data.get("message"),
              error=response_data.get("error"),
              langsmith_trace_url=trace_url,
              suggestions=response_data.get("suggestions")
          )
      
  except asyncio.TimeoutError:
      logger.error("Search timeout", query=request.query)
      return SearchResponse(
          success=False,
          query=request.query,
          products=[],
          metadata={},
          execution={
              "total_time_ms": settings.search_timeout_ms,
              "timeout": True
          },
          error=f"Search timeout after {settings.search_timeout_ms}ms"
      )
      
  except Exception as e:
      logger.error("Search failed", error=str(e), query=request.query)
      return SearchResponse(
          success=False,
          query=request.query,
          products=[],
          metadata={},
          execution={
              "total_time_ms": (time.perf_counter() - start_time) * 1000,
              "error": str(e)
          },
          error=f"Search failed: {str(e)}"
      )

@app.get("/health")
async def health_check():
  """Health check endpoint with Redis status"""
  
  # Check Redis health
  redis_status = "disabled"
  redis_details = {}
  
  if redis_feature.enabled:
      try:
          manager = await smart_redis_manager._get_manager()
          # Try a simple operation
          if hasattr(manager, 'async_client') and manager.async_client:
              await manager.async_client.ping()
              redis_status = "healthy"
          else:
              redis_status = "mock_mode"
      except Exception as e:
          redis_status = "degraded"
          redis_details["error"] = str(e)
  
  return {
      "status": "healthy",
      "redis": {
          "enabled": redis_feature.enabled,
          "status": redis_status,
          "url_configured": bool(settings.redis_url),
          "environment": settings.environment,
          **redis_details
      },
      "timestamp": datetime.utcnow().isoformat(),
      "version": settings.api_version
  }

@app.get("/api/v1/agents")
async def get_agent_info():
  """Get information about available agents"""
  return {
      "agents": [
          {
              "name": "supervisor",
              "type": "router",
              "description": "Analyzes queries and routes to appropriate agents"
          },
          {
              "name": "product_search", 
              "type": "executor",
              "description": "Searches products with ability to refine results"
          },
          {
              "name": "order_agent",
              "type": "executor", 
              "description": "Manages shopping cart and order operations with conversational memory"
          },
          {
              "name": "response_compiler",
              "type": "formatter", 
              "description": "Compiles final response with execution transparency"
          }
      ],
      "flow": "supervisor → (product_search | order_agent) → response_compiler"
  }

@app.post("/api/v1/order", response_model=SearchResponse)
async def handle_order(request: SearchRequest):
  """Handle order-related queries (add to cart, update, remove, etc.)"""
  start_time = time.perf_counter()
  
  try:
      # Alpha will be calculated by Gemma if needed
      calculated_alpha = 0.5  # Default placeholder
      
      # Create initial state with order intent hint
      initial_state = create_initial_state(request, calculated_alpha)
      initial_state["intent_hint"] = "order_operation"  # Help supervisor route to order agent
      
      logger.info(
          "Starting order operation",
          request_id=initial_state["request_id"],
          query=request.query
      )
      
      # Execute the graph with timeout
      final_state = await asyncio.wait_for(
          search_graph.ainvoke(initial_state),
          timeout=settings.search_timeout_ms / 1000
      )
      
      # Calculate total execution time
      total_time = (time.perf_counter() - start_time) * 1000
      
      # Get the compiled response
      response_data = final_state.get("final_response", {})
      
      # Add current order to response if available
      if "current_order" in final_state and final_state["current_order"].get("items"):
          response_data["current_order"] = final_state["current_order"]
      
      # Build response
      return SearchResponse(
          success=response_data.get("success", False),
          query=request.query,
          products=response_data.get("products", []),
          metadata=response_data.get("metadata", {}),
          execution={
              **response_data.get("execution", {}),
              "total_time_ms": total_time,
              "agent": "order_agent"
          },
          message=response_data.get("message"),
          error=response_data.get("error")
      )
      
  except asyncio.TimeoutError:
      logger.error("Order operation timeout", query=request.query)
      return SearchResponse(
          success=False,
          query=request.query,
          products=[],
          metadata={},
          execution={
              "total_time_ms": settings.search_timeout_ms,
              "timeout": True
          },
          error=f"Order operation timeout after {settings.search_timeout_ms}ms"
      )
      
  except Exception as e:
      logger.error("Order operation failed", error=str(e), query=request.query)
      return SearchResponse(
          success=False,
          query=request.query,
          products=[],
          metadata={},
          execution={
              "total_time_ms": (time.perf_counter() - start_time) * 1000,
              "error": str(e)
          },
          error=f"Order operation failed: {str(e)}"
      )

@app.post("/api/v1/voice/session")
async def create_voice_session(
  user_id: str = "anonymous",
  language: str = "en-US"
):
  """Create a new voice session"""
  from src.integrations.web_voice_handler import web_voice_handler
  
  session = await web_voice_handler.create_session(user_id, language)
  return session

@app.post("/api/v1/voice/process")
async def process_voice(request: Request):
  """Process voice input through supervisor for proper routing"""
  try:
      data = await request.json()
      query = data.get("query", "")
      session_id = data.get("session_id", str(uuid.uuid4()))
      voice_metadata = data.get("voice_metadata", {})
      
      # Create initial state with voice context
      initial_state = {
          "messages": [{
              "role": "human",
              "content": query,
              "tool_calls": None,
              "tool_call_id": None
          }],
          "query": query,
          "request_id": generate_request_id(),
          "timestamp": datetime.utcnow(),
          "alpha_value": 0.5,
          "search_strategy": "hybrid",
          "next_action": None,
          "reasoning": [],
          "routing_decision": None,
          "should_search": True,
          "search_params": {
              "limit": 10,
              "source": "voice"
          },
          "search_results": [],
          "search_metadata": {},
          "session_id": session_id,
          "user_id": data.get("user_id", "anonymous"),
          "source": "voice",
          "final_response": {},
          "error": None,
          "voice_metadata": voice_metadata
      }
      
      # Execute through LangGraph supervisor
      final_state = await search_graph.ainvoke(initial_state)
      
      # Check if this is general chat
      if final_state.get("is_general_chat") or final_state.get("routing_decision") == "general_chat":
          final_response = final_state.get("final_response", {})
          return {
              "type": "response",
              "text": final_response.get("response", "I'm here to help with your grocery shopping!"),
              "response": final_response.get("response", "I'm here to help with your grocery shopping!"),
              "is_general_chat": True,
              "intent": final_state.get("intent", "general_chat")
          }
      
      # Otherwise, it's a product search
      products = final_state.get("search_results", [])
      
      if products:
          # Build conversational response
          query_lower = query.lower()
          all_organic = all(p.get('is_organic', False) for p in products)
          
          if 'milk' in query_lower and all_organic:
              response_text = f"I found {len(products)} milk options. They're all organic varieties. "
          else:
              response_text = f"I found {len(products)} options for {query}. "
          
          # Describe top products
          top_products = products[:3]
          if len(top_products) == 1:
              p = top_products[0]
              response_text += f"We have {p['product_name']} from {p.get('supplier', 'our store')} for ${p['price']:.2f}."
          elif len(top_products) == 2:
              response_text += f"The top choices are {top_products[0]['product_name']} for ${top_products[0]['price']:.2f} "
              response_text += f"and {top_products[1]['product_name']} for ${top_products[1]['price']:.2f}."
          elif len(top_products) >= 3:
              response_text += f"The top picks are: "
              response_text += f"{top_products[0]['product_name']} at ${top_products[0]['price']:.2f}, "
              response_text += f"{top_products[1]['product_name']} at ${top_products[1]['price']:.2f}, "
              response_text += f"and {top_products[2]['product_name']} at ${top_products[2]['price']:.2f}."
          
          if len(products) > 3:
              response_text += f" I have {len(products) - 3} more options if you'd like to hear them."
          
          return {
              "type": "response",
              "text": response_text,
              "products": products[:5],
              "total_found": len(products)
          }
      else:
          return {
              "type": "response",
              "text": f"I couldn't find any {query}. What else can I help you find?",
              "products": []
          }
          
  except Exception as e:
      logger.error(f"Voice processing error: {e}")
      return {
          "type": "response",
          "text": "I'm having trouble understanding. Could you try again?",
          "error": str(e)
      }

@app.get("/api/v1/voice/health")
async def voice_health():
  """Check voice services health"""
  from src.integrations.web_voice_handler import web_voice_handler
  return await web_voice_handler.health_check()

# Include webhook routes
from src.api.voice_webhooks import router as voice_webhook_router
app.include_router(voice_webhook_router)

# Include new voice endpoints (Whisper + ElevenLabs)
from src.api.voice_endpoints import router as voice_router
app.include_router(voice_router)

# Include voice streaming endpoints (Deepgram STT + TTS)
from src.api.voice_streaming import router as voice_streaming_router
app.include_router(voice_streaming_router)

# Include HTTP-based voice endpoints (Cloud Run compatible)
try:
    from src.api.voice_http import router as voice_http_router
    app.include_router(voice_http_router)
    logger.info("Loaded voice_http router")
except Exception as e:
    logger.warning(f"Could not load voice_http router: {e}")

try:
    from src.api.voice_websocket import router as voice_websocket_router
    app.include_router(voice_websocket_router)
    logger.info("Loaded voice_websocket router with WebSocket support")
except Exception as e:
    logger.error(f"Could not load voice_websocket router: {e}")

try:
    from src.api.voice_realtime import router as voice_realtime_router
    app.include_router(voice_realtime_router)
    logger.info("Loaded voice_realtime router with natural conversation")
except Exception as e:
    logger.error(f"Could not load voice_realtime router: {e}")
    
# Static files already mounted above

# Include Deepgram conversational AI - After static files but with API prefix
try:
    from src.api.voice_deepgram_conversational import router as deepgram_router
    app.include_router(deepgram_router)
    logger.info("Loaded Deepgram conversational AI with full Audio Intelligence")
except Exception as e:
    logger.error(f"Could not load Deepgram conversational router: {e}")

# Include Deepgram proxy for production continuous voice
try:
    from src.api.voice_deepgram_proxy import router as deepgram_proxy_router
    app.include_router(deepgram_proxy_router)
    logger.info("Loaded Deepgram proxy for TRUE continuous voice")
except Exception as e:
    logger.error(f"Could not load Deepgram proxy router: {e}")

# Include simple streaming voice
try:
    from src.api.voice_stream_simple import router as voice_stream_router
    app.include_router(voice_stream_router)
    logger.info("Loaded simple voice streaming with SSE")
except Exception as e:
    logger.error(f"Could not load voice streaming router: {e}")

# Include test WebSocket endpoint for debugging
try:
    from src.api.test_ws import router as test_ws_router
    app.include_router(test_ws_router)
    logger.info("Loaded test WebSocket endpoint")
except Exception as e:
    logger.error(f"Could not load test WebSocket router: {e}")

# Include simple voice WebSocket endpoint
try:
    from src.api.voice_websocket_simple import router as voice_simple_ws_router
    app.include_router(voice_simple_ws_router)
    logger.info("Loaded simple voice WebSocket endpoint")
except Exception as e:
    logger.error(f"Could not load simple voice WebSocket router: {e}")

# Include fixed WebSocket streaming with Deepgram SDK
try:
    from src.api.voice_streaming_fixed import router as voice_streaming_fixed_router
    app.include_router(voice_streaming_fixed_router)
    logger.info("Loaded fixed voice streaming with Deepgram SDK")
except Exception as e:
    logger.error(f"Could not load fixed voice streaming router: {e}")

# Include simple WebSocket streaming
try:
    from src.api.voice_streaming_simple import router as voice_streaming_simple_router
    app.include_router(voice_streaming_simple_router)
    logger.info("Loaded simple voice streaming")
except Exception as e:
    logger.error(f"Could not load simple voice streaming router: {e}")

# Include full conversational AI
try:
    from src.api.voice_conversational_full import router as voice_conversational_router
    app.include_router(voice_conversational_router)
    logger.info("Loaded full conversational AI with STT and TTS")
except Exception as e:
    logger.error(f"Could not load conversational AI router: {e}")

# Include fixed Deepgram implementation
try:
    from src.api.voice_deepgram_fixed import router as deepgram_fixed_router
    app.include_router(deepgram_fixed_router)
    logger.info("Loaded fixed Deepgram implementation")
except Exception as e:
    logger.error(f"Could not load fixed Deepgram router: {e}")

# Include Deepgram SDK implementation
try:
    from src.api.voice_deepgram_sdk import router as deepgram_sdk_router
    app.include_router(deepgram_sdk_router)
    logger.info("Loaded Deepgram SDK implementation")
except Exception as e:
    logger.error(f"Could not load Deepgram SDK router: {e}")

# Include HTTP streaming voice (Production ready)
try:
    from src.api.voice_http_streaming import router as http_streaming_router
    app.include_router(http_streaming_router)
    logger.info("Loaded HTTP streaming voice (production ready)")
except Exception as e:
    logger.error(f"Could not load HTTP streaming router: {e}")

# Include Gemini native voice
try:
    from src.api.voice_gemini_native import router as gemini_voice_router
    app.include_router(gemini_voice_router)
    logger.info("Loaded Gemini native voice with STT and TTS")
except Exception as e:
    logger.error(f"Could not load Gemini voice router: {e}")

# Include Deepgram Voice Agent API
try:
    from src.api.voice_agent_api import router as voice_agent_router
    app.include_router(voice_agent_router)
    logger.info("Loaded Deepgram Voice Agent API")
except Exception as e:
    logger.error(f"Could not load Voice Agent router: {e}")

# Include new Deepgram Voice Agent with LangGraph integration
try:
    from src.api.voice_agent_new import router as voice_agent_new_router
    app.include_router(voice_agent_new_router)
    logger.info("Loaded NEW Deepgram Voice Agent with LangGraph integration")
except Exception as e:
    logger.error(f"Could not load NEW Deepgram Voice Agent router: {e}")

# Include Deepgram Voice Agent (original conversational)
try:
    from src.api.voice_agent_deepgram import router as voice_agent_deepgram_router
    app.include_router(voice_agent_deepgram_router)
    logger.info("Loaded Deepgram Voice Agent with LangGraph integration")
except Exception as e:
    logger.error(f"Could not load Deepgram Voice Agent router: {e}")

# Include Simple Working Voice (STT + LLM + TTS)
try:
    from src.api.voice_simple_working import router as voice_simple_router
    app.include_router(voice_simple_router)
    logger.info("Loaded SIMPLE Working Voice with reliable STT + LLM + TTS")
except Exception as e:
    logger.error(f"Could not load Simple Voice router: {e}")

# Include ElevenLabs Conversational AI (Natural Voice)
try:
    from src.api.voice_elevenlabs import router as elevenlabs_router
    app.include_router(elevenlabs_router)
    logger.info("Loaded ElevenLabs Conversational AI with natural voice and function calling")
except Exception as e:
    logger.error(f"Could not load ElevenLabs router: {e}")

# Include Google Voice Integration (Multi-ethnic STT/TTS)
try:
    from src.api.voice_google import router as google_voice_router
    app.include_router(google_voice_router)
    logger.info("Loaded Google Voice with multi-ethnic STT/TTS support")
    
    # Add Google Voice test endpoint
    from src.api.voice_google_test import router as google_test_router
    app.include_router(google_test_router)
    logger.info("Loaded Google Voice test endpoint")
    
    # Add fixed Google Voice endpoint
    from src.api.voice_google_fixed import router as google_fixed_router
    app.include_router(google_fixed_router)
    logger.info("Loaded Google Voice fixed endpoint")
    
    # Add streaming Google Voice endpoint
    from src.api.voice_google_streaming import router as google_streaming_router
    app.include_router(google_streaming_router)
    logger.info("Loaded Google Voice continuous streaming endpoint")
    
    # Add unified Google Voice with voice-native supervisor
    from src.api.voice_google_unified import router as google_unified_router
    app.include_router(google_unified_router)
    logger.info("Loaded unified Google Voice with voice-native supervisor")
    
    # Add fixed Google Voice v2 for testing
    from src.api.voice_google_fixed_v2 import router as google_fixed_v2_router
    app.include_router(google_fixed_v2_router)
    logger.info("Loaded fixed Google Voice v2 endpoint")
except Exception as e:
    logger.error(f"Could not load Google Voice router: {e}")

# Load Google Voice streaming endpoint with AI-native supervisor
try:
    from src.api.voice_google_streaming import router as voice_google_streaming_router
    app.include_router(voice_google_streaming_router)
    logger.info("Loaded Google Voice streaming with AI-native supervisor")
except Exception as e:
    logger.error(f"Could not load Google Voice streaming router: {e}")

# Load Google True Streaming with async-to-sync bridge
try:
    from src.api.voice_google_true_streaming import router as google_true_streaming_router
    app.include_router(google_true_streaming_router)
    logger.info("Loaded Google True Streaming with real streaming_recognize API")
except Exception as e:
    logger.error(f"Could not load Google True Streaming router: {e}")

# Add basic Google voice endpoint
try:
    from src.api.voice_google_basic import router as voice_google_basic_router
    app.include_router(voice_google_basic_router)
    logger.info("Loaded basic Google Voice (STT/TTS only)")
except Exception as e:
    logger.error(f"Could not load basic Google Voice router: {e}")

# Add Google WebSocket streaming
try:
    from src.api.voice_google_websocket import router as voice_google_ws_router
    app.include_router(voice_google_ws_router)
    logger.info("Loaded Google Voice WebSocket streaming")
except Exception as e:
    logger.error(f"Could not load Google Voice WebSocket router: {e}")

# Add Google SSE streaming
try:
    from src.api.voice_google_sse import router as voice_google_sse_router
    app.include_router(voice_google_sse_router)
    logger.info("Loaded Google Voice SSE streaming")
except Exception as e:
    logger.error(f"Could not load Google Voice SSE router: {e}")

# Add Gemini native voice streaming
try:
    from src.api.voice_gemini_streaming import router as voice_gemini_streaming_router
    app.include_router(voice_gemini_streaming_router)
    logger.info("Loaded Gemini native voice streaming with multimodal support")
except Exception as e:
    logger.error(f"Could not load Gemini voice streaming router: {e}")

# Add Hybrid voice streaming (Google STT + Gemini + Google TTS)
try:
    from src.api.voice_google_gemini_hybrid import router as voice_hybrid_router
    app.include_router(voice_hybrid_router)
    logger.info("Loaded hybrid voice streaming (Google STT + Gemini + Google TTS)")
except Exception as e:
    logger.error(f"Could not load hybrid voice router: {e}")

# Load simple working voice endpoint
try:
    from src.api.voice_simple_working import router as voice_simple_router
    app.include_router(voice_simple_router)
    logger.info("Loaded simple working voice endpoint")
except Exception as e:
    logger.error(f"Could not load simple voice router: {e}")

# Add Gemini 2.0 Flash native audio
try:
    from src.api.voice_gemini_2_flash import router as gemini_2_flash_router
    app.include_router(gemini_2_flash_router)
    logger.info("Loaded Gemini 2.0 Flash native audio streaming")
except Exception as e:
    logger.error(f"Could not load Gemini 2.0 Flash router: {e}")

# Add Gemini 2.5 native audio
try:
    from src.api.voice_gemini_25_native import router as voice_gemini25_router
    app.include_router(voice_gemini25_router)
    logger.info("Loaded Gemini 2.5 native audio streaming")
except Exception as e:
    logger.error(f"Could not load Gemini 2.5 voice router: {e}")

# Add simple Gemini voice
try:
    from src.api.voice_gemini_simple import router as voice_gemini_simple_router
    app.include_router(voice_gemini_simple_router)
    logger.info("Loaded simple Gemini voice with browser STT")
except Exception as e:
    logger.error(f"Could not load simple Gemini voice router: {e}")

# Add Dialogflow CX voice
try:
    from src.api.voice_dialogflow_cx import router as voice_dialogflow_router
    app.include_router(voice_dialogflow_router)
    logger.info("Loaded Dialogflow CX voice integration")
except Exception as e:
    logger.error(f"Could not load Dialogflow CX router: {e}")

# Add Vertex AI Conversation
try:
    from src.api.voice_vertex_conversation import router as voice_vertex_router
    app.include_router(voice_vertex_router)
    logger.info("Loaded Vertex AI Conversation integration")
except Exception as e:
    logger.error(f"Could not load Vertex AI Conversation router: {e}")

# Add Streaming Conversational Voice
try:
    from src.api.voice_streaming_conversational import router as voice_streaming_router
    app.include_router(voice_streaming_router)
    logger.info("Loaded streaming conversational voice")
except Exception as e:
    logger.error(f"Could not load streaming conversational router: {e}")

# Add Vertex AI Personalized Voice
try:
    from src.api.voice_vertex_personalized import router as voice_vertex_personalized_router
    app.include_router(voice_vertex_personalized_router)
    logger.info("Loaded Vertex AI personalized voice with full personalization features")
except Exception as e:
    logger.error(f"Could not load Vertex AI personalized router: {e}")

# Add Simple Vertex AI Voice (working implementation)
try:
    from src.api.voice_vertex_simple import router as voice_vertex_simple_router
    app.include_router(voice_vertex_simple_router)
    logger.info("Loaded simple Vertex AI voice (working implementation)")
except Exception as e:
    logger.error(f"Could not load simple Vertex AI router: {e}")


if __name__ == "__main__":
  import uvicorn
  uvicorn.run(app, host="0.0.0.0", port=settings.api_port)