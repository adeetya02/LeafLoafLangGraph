"""
Ultra-thin API layer - just HTTP to Agent translation
All intelligence lives in agents
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time
from datetime import datetime
import uuid

from src.core.graph import search_graph
import structlog

logger = structlog.get_logger()

# Initialize FastAPI app
app = FastAPI(
    title="LeafLoaf API",
    version="3.0.0",
    description="Ultra-thin API for agent-based grocery shopping"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Minimal request/response models
class SearchRequest(BaseModel):
    """Universal request model - agents handle everything"""
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class SearchResponse(BaseModel):
    """Universal response model - agents determine structure"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/health")
async def health_check():
    """Minimal health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/v1/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Universal endpoint - all queries go here.
    Agents handle routing, validation, execution, formatting.
    """
    request_id = str(uuid.uuid4())
    start_time = time.perf_counter()
    
    try:
        # Log request (only boundary concern)
        logger.info("Request received", 
            request_id=request_id,
            query=request.query[:50]  # Truncate for logging
        )
        
        # Convert request to state and invoke agents
        state = request.dict()
        state["request_id"] = request_id
        state["timestamp"] = datetime.utcnow()
        
        # Agents handle EVERYTHING
        final_state = await search_graph.ainvoke(state)
        
        # Extract response (agents decide structure)
        if final_state.get("error"):
            return SearchResponse(
                success=False,
                error=final_state["error"]
            )
        
        return SearchResponse(
            success=True,
            data=final_state.get("final_response", final_state)
        )
        
    except Exception as e:
        # Only handle true system errors
        logger.error("System error", error=str(e), request_id=request_id)
        return SearchResponse(
            success=False,
            error="System error occurred"
        )
    finally:
        # Log response time (observability)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Request completed",
            request_id=request_id,
            duration_ms=elapsed_ms
        )

# Optional: SSE endpoint for streaming
@app.post("/api/v1/stream")
async def stream_search(request: SearchRequest):
    """
    Future: Streaming responses for real-time updates
    """
    # Would return SSE stream
    # Agent yields events as they process
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)