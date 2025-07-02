"""
Simplified voice HTTP endpoints for Deepgram - Cloud Run compatible
"""
import asyncio
import json
import base64
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-simple")

# Store active sessions
sessions: Dict[str, Dict[str, Any]] = {}

class SessionRequest(BaseModel):
    user_id: str = "anonymous"

class ProcessAudioRequest(BaseModel):
    audio: str  # base64 encoded audio
    format: str = "webm"
    test_transcript: Optional[str] = None

@router.post("/start-session")
async def start_session(request: SessionRequest):
    """Start a new voice session"""
    session_id = str(uuid.uuid4())
    
    sessions[session_id] = {
        "user_id": request.user_id,
        "created_at": datetime.utcnow(),
        "conversation_history": []
    }
    
    logger.info(f"Started simple voice session: {session_id}")
    
    return {
        "session_id": session_id,
        "status": "ready",
        "message": "Session started"
    }

@router.post("/process-audio/{session_id}")
async def process_audio(session_id: str, request: ProcessAudioRequest):
    """Process audio and return response"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    try:
        # For testing, use test transcript if provided
        if request.test_transcript:
            transcript = request.test_transcript
        else:
            # In production, this would call Deepgram
            transcript = "I need organic milk"
        
        # Simple search simulation
        from src.core.graph import search_graph
        from src.utils.id_generator import generate_request_id
        
        # Create minimal state for search
        initial_state = {
            "messages": [{
                "role": "human",
                "content": transcript,
                "tool_calls": None,
                "tool_call_id": None
            }],
            "query": transcript,
            "request_id": generate_request_id(),
            "timestamp": datetime.utcnow(),
            "alpha_value": 0.5,
            "search_strategy": "hybrid",
            "next_action": None,
            "reasoning": [],
            "routing_decision": None,
            "should_search": False,
            "search_params": {"limit": 10, "source": "voice"},
            "search_results": [],
            "search_metadata": {},
            "pending_tool_calls": [],
            "completed_tool_calls": [],
            "session_id": session_id,
            "enhanced_query": None,
            "current_order": {"items": []},
            "order_metadata": {},
            "user_context": {"user_id": session["user_id"], "filters": {}, "preferences": {}},
            "preferences": [],
            "filters": {},
            "user_id": session["user_id"],
            "source": "voice",
            "agent_status": {},
            "agent_timings": {},
            "total_execution_time": 0,
            "trace_id": str(uuid.uuid4()),
            "span_ids": {},
            "should_continue": True,
            "final_response": {},
            "error": None,
            "intent": None,
            "confidence": 0.0
        }
        
        # Execute search
        final_state = await search_graph.ainvoke(initial_state)
        response_data = final_state.get("final_response", {})
        products = response_data.get("products", [])
        
        # Format response
        if products:
            response_text = f"I found {len(products)} products for you. "
            for i, p in enumerate(products[:3]):
                name = p.get('product_name', 'Unknown')
                price = p.get('price', 0)
                response_text += f"{name} for ${price:.2f}. "
        else:
            response_text = "I couldn't find any products matching that."
        
        # Update conversation
        session["conversation_history"].append({
            "user": transcript,
            "assistant": response_text,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # For now, return simple base64 encoded text as "audio"
        audio_base64 = base64.b64encode(response_text.encode()).decode('utf-8')
        
        return {
            "status": "success",
            "transcript": transcript,
            "response_text": response_text,
            "response_audio": audio_base64,
            "audio_format": "text",  # Indicates it's just text, not real audio
            "products": products[:5] if products else []
        }
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return {
            "status": "error",
            "error": str(e),
            "response_text": "Sorry, I had trouble processing that."
        }

@router.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "active_sessions": len(sessions)
    }