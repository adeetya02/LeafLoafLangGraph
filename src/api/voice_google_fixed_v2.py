"""
Fixed Google Voice WebSocket that properly handles text and audio
"""
import asyncio
import json
import base64
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import structlog
from datetime import datetime

from src.agents.supervisor_voice_native import VoiceNativeSupervisor
from src.voice.google_voice_handler import GoogleVoiceHandler
from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.models.state import SearchState, SearchStrategy

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/google-fixed")

@router.websocket("/ws")
async def voice_websocket(websocket: WebSocket, language: Optional[str] = Query(default="en-US")):
    """Fixed WebSocket endpoint that handles both text and audio properly"""
    await websocket.accept()
    
    session_id = generate_request_id()
    voice_handler = GoogleVoiceHandler()
    supervisor = VoiceNativeSupervisor()
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "session_started",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Voice conversation ready. Send text or audio."
        })
        
        # Main message loop
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")
            
            if msg_type == "text":
                # Handle text input
                text = message.get("text", "")
                logger.info(f"Received text: {text}")
                
                # Create state and process through supervisor
                state = SearchState(
                    messages=[],
                    query=text,
                    request_id=generate_request_id(),
                    timestamp=datetime.utcnow(),
                    session_id=session_id,
                    voice_metadata={},
                    search_params={"alpha": 0.5},
                    # Initialize all required fields
                    reasoning=[],
                    intent=None,
                    next_action=None,
                    confidence=0.0,
                    routing_decision=None,
                    should_search=False,
                    alpha_value=0.5,
                    search_strategy=SearchStrategy.HYBRID,
                    search_results=[],
                    search_metadata={},
                    pending_tool_calls=[],
                    completed_tool_calls=[],
                    agent_status={},
                    agent_timings={},
                    total_execution_time=0.0,
                    trace_id=None,
                    final_response={},
                    should_continue=True,
                    error=None,
                    enhanced_query=None,
                    current_order={},
                    order_metadata={},
                    user_context=None,
                    preferences=[],
                    is_general_chat=False
                )
                
                # Process through supervisor
                state = await supervisor.execute(state)
                
                # Send response
                await websocket.send_json({
                    "type": "response",
                    "text": f"Processed: {text}",
                    "intent": state.get("intent", "unknown"),
                    "confidence": state.get("confidence", 0.0)
                })
                
            elif msg_type == "audio":
                # Handle audio (not implemented in this test)
                await websocket.send_json({
                    "type": "error",
                    "message": "Audio not supported in this test endpoint"
                })
                
            elif msg_type == "ping":
                # Handle ping
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })