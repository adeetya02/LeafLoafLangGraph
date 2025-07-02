"""
Production API with Gemma 2 9B and WebSocket support for agent flow visualization.
"""
import os
import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from src.integrations.gemma_production_client import GemmaProductionClient
from src.core.graph import create_graph
from src.models.state import ConversationState
from src.utils.id_generator import generate_request_id
from src.data_capture.capture_strategy import CaptureStrategy

# Initialize FastAPI app
app = FastAPI(
    title="LeafLoaf Production API",
    description="Production-ready grocery shopping with Gemma 2 9B and real-time agent flow",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast_event(self, event: dict):
        """Broadcast agent flow event to all connected clients."""
        if self.active_connections:
            # Create tasks for all broadcasts
            tasks = []
            for connection in self.active_connections.copy():
                tasks.append(self._send_to_connection(connection, event))
            
            # Wait for all broadcasts to complete
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_to_connection(self, connection: WebSocket, event: dict):
        try:
            await connection.send_json(event)
        except Exception:
            # Remove disconnected clients
            self.active_connections.discard(connection)

# Global instances
manager = ConnectionManager()
capture_strategy = CaptureStrategy()

# Flow callback for WebSocket broadcasting
async def flow_callback(event: dict):
    """Callback to broadcast agent flow events."""
    await manager.broadcast_event(event)

# Initialize Gemma client with flow callback
gemma_client = GemmaProductionClient(flow_callback=flow_callback)

# Initialize graph
graph = create_graph()

# Request models
class SearchRequest(BaseModel):
    query: str
    user_id: str = "demo_user"
    session_id: Optional[str] = None
    features: Optional[Dict[str, bool]] = None

class CartRequest(BaseModel):
    action: str
    product_id: Optional[str] = None
    quantity: Optional[int] = None
    user_id: str = "demo_user"

# API endpoints
@app.get("/")
async def root():
    return {
        "name": "LeafLoaf Production API",
        "version": "2.0.0",
        "features": {
            "llm": "Gemma 2 9B (Vertex AI)",
            "entity_extraction": "Gemini Pro 2.5",
            "memory": "Graphiti + Spanner GraphRAG",
            "search": "Production vector search (768D)",
            "real_time": "WebSocket agent flow visualization"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "gemma": "active",
            "graphiti": "active",
            "weaviate": "active",
            "websocket": len(manager.active_connections)
        }
    }

@app.post("/api/search")
async def search(request: SearchRequest):
    """Main search endpoint with Gemma 2 9B analysis."""
    try:
        # Generate request ID
        request_id = generate_request_id()
        
        # Broadcast search start
        await flow_callback({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "API",
            "action": "search_request",
            "details": {
                "query": request.query,
                "user_id": request.user_id,
                "features": request.features
            },
            "latency_ms": 0
        })
        
        # Analyze query with Gemma 2 9B
        start_time = datetime.utcnow()
        analysis = await gemma_client.analyze_query(
            request.query,
            user_context={
                "user_id": request.user_id,
                "features": request.features or {}
            }
        )
        
        # Create initial state
        state = ConversationState(
            query=request.query,
            user_id=request.user_id,
            session_id=request.session_id or f"session_{request_id}",
            intent=analysis.get("intent", "search"),
            context=analysis.get("context", {}),
            search_alpha=analysis.get("alpha", 0.75),
            messages=[],
            products=[],
            cart=[],
            needs_clarification=False,
            clarification_options=[],
            metadata={
                "request_id": request_id,
                "features": request.features or {},
                "analysis": analysis
            }
        )
        
        # Execute graph
        result = await graph.ainvoke(state)
        
        # Capture data
        capture_strategy.capture_search_event(
            user_id=request.user_id,
            query=request.query,
            products=result["products"],
            metadata={
                "intent": result["intent"],
                "alpha": result["search_alpha"],
                "personalization": request.features
            }
        )
        
        # Return response
        return {
            "request_id": request_id,
            "query": request.query,
            "products": result["products"],
            "metadata": {
                "intent": result["intent"],
                "search_alpha": result["search_alpha"],
                "total_latency_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "agent_latencies": result.get("metadata", {}).get("latencies", {}),
                "personalization_applied": any(request.features.values()) if request.features else False,
                "session_id": state.session_id
            }
        }
        
    except Exception as e:
        await flow_callback({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "API",
            "action": "error",
            "details": {"error": str(e)},
            "latency_ms": 0
        })
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cart/{action}")
async def cart_action(action: str, request: CartRequest):
    """Handle cart operations."""
    try:
        # Broadcast cart action
        await flow_callback({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "Cart",
            "action": f"cart_{action}",
            "details": {
                "product_id": request.product_id,
                "quantity": request.quantity,
                "user_id": request.user_id
            },
            "latency_ms": 0
        })
        
        # Create state for cart operation
        state = ConversationState(
            query=f"cart {action}",
            user_id=request.user_id,
            session_id=f"cart_{generate_request_id()}",
            intent="order",
            context={"action": action},
            cart=[],
            metadata={
                "cart_action": action,
                "product_id": request.product_id,
                "quantity": request.quantity
            }
        )
        
        # Execute graph
        result = await graph.ainvoke(state)
        
        return {
            "status": "success",
            "action": action,
            "cart": result.get("cart", []),
            "message": result.get("messages", ["Cart updated"])[-1] if result.get("messages") else "Cart updated"
        }
        
    except Exception as e:
        await flow_callback({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "Cart",
            "action": "error",
            "details": {"error": str(e)},
            "latency_ms": 0
        })
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/agent-flow")
async def websocket_agent_flow(websocket: WebSocket):
    """WebSocket endpoint for real-time agent flow."""
    await manager.connect(websocket)
    
    try:
        # Send initial connection event
        await websocket.send_json({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "WebSocket",
            "action": "connected",
            "details": {"message": "Connected to agent flow"},
            "latency_ms": 0
        })
        
        # Keep connection alive
        while True:
            # Wait for any message from client (heartbeat)
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics."""
    return {
        "active_websocket_connections": len(manager.active_connections),
        "uptime_seconds": int((datetime.utcnow() - app.state.get("start_time", datetime.utcnow())).total_seconds()),
        "system_status": {
            "gemma": "active",
            "graphiti": "active",
            "weaviate": "active"
        }
    }

# Startup event
@app.on_event("startup")
async def startup():
    app.state["start_time"] = datetime.utcnow()
    print("🚀 LeafLoaf Production API started")
    print(f"🤖 Using Gemma 2 9B endpoint: {gemma_client.endpoint_id}")
    print(f"📊 WebSocket support enabled")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "src.api.main_production:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )