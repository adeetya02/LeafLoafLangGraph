from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import time
from datetime import datetime
import asyncio

from src.config.settings import settings
from src.core.graph import search_graph
from src.models.state import SearchState, AgentStatus, SearchStrategy
from src.utils.id_generator import generate_request_id, generate_trace_id
import structlog
from src.core.config_manager import config_manager
from config.product_attributes import PRODUCT_ATTRIBUTES, DEFAULT_ALPHA, MIN_ALPHA, MAX_ALPHA

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

# Request/Response models
class SearchRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    limit: Optional[int] = 10

class SearchResponse(BaseModel):
    success: bool
    query: str
    products: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    execution: Dict[str, Any]
    message: Optional[str] = None
    error: Optional[str] = None
    langsmith_trace_url: Optional[str] = None

def calculate_dynamic_alpha(query: str) -> float:
    """Calculate alpha using product attributes config"""
    query_lower = query.lower()
    alpha = DEFAULT_ALPHA
    
    # Track what we find
    attribute_matches = []
    
    # Check each attribute category
    for category, config in PRODUCT_ATTRIBUTES.items():
        terms = config["terms"]
        impact = config["alpha_impact"]
        
        # Count matches in this category
        matches = sum(1 for term in terms if term in query_lower)
        
        if matches > 0:
            alpha += impact * matches
            attribute_matches.append(f"{category}:{matches}")
    
    # Keep alpha in bounds
    alpha = max(MIN_ALPHA, min(MAX_ALPHA, alpha))
    
    # Log for debugging
    logger.info(f"Query: '{query}' | Matches: {attribute_matches} | Alpha: {alpha}")
    
    return alpha    

# Initialize state for a new search
def create_initial_state(request: SearchRequest,calculated_alpha: float) -> SearchState:
    """Create initial state for LangGraph execution"""
    request_id = generate_request_id()
    trace_id = generate_trace_id()
    
    # Get default search config
    search_config = config_manager.get_default_search_config()
    
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
        "search_params": {},       # And this!
        "search_results": [],
        "search_metadata": {},
        "pending_tool_calls": [],
        "completed_tool_calls": [],
        
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
        "error": None
    }

@app.post("/api/v1/search", response_model=SearchResponse)
async def search_products(request: SearchRequest):
    """Main search endpoint with full execution transparency"""
    start_time = time.perf_counter()
    
    try:
        # Calculate dynamic alpha based on query
        calculated_alpha = calculate_dynamic_alpha(request.query)
        # Create initial state
        initial_state = create_initial_state(request,calculated_alpha)
        
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
        
        # Calculate total execution time
        total_time = (time.perf_counter() - start_time) * 1000
        
        # Get the compiled response
        response_data = final_state.get("final_response", {})
        
        # Add LangSmith trace URL if available
        trace_url = None
        if settings.langchain_tracing_v2 and final_state.get("trace_id"):
            trace_url = f"https://smith.langchain.com/public/{final_state['trace_id']}/r"
        
        # Build response
        return SearchResponse(
            success=response_data.get("success", False),
            query=request.query,
            products=response_data.get("products", []),
            metadata=response_data.get("metadata", {}),
            execution={
                **response_data.get("execution", {}),
                "total_time_ms": total_time,
                "timeout_ms": settings.search_timeout_ms
            },
            message=response_data.get("message"),
            error=response_data.get("error"),
            langsmith_trace_url=trace_url
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
    """Health check endpoint"""
    return {
        "status": "healthy",
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
                "name": "response_compiler",
                "type": "formatter", 
                "description": "Compiles final response with execution transparency"
            }
        ],
        "flow": "supervisor → product_search → response_compiler"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.api_port)