"""
Voice streaming using Server-Sent Events (SSE) - Cloud Run compatible
Alternative to WebSocket for better Cloud Run support
"""
import asyncio
import json
import base64
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
import structlog

from src.voice.deepgram_client import DeepgramClient
from src.core.graph import search_graph
from src.api.main import create_initial_state
from src.utils.id_generator import generate_request_id

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-sse")

# Store active sessions
sessions: Dict[str, Dict[str, Any]] = {}

@router.post("/start-session")
async def start_session(request: Request):
    """Start a new voice session"""
    data = await request.json()
    user_id = data.get("user_id", "anonymous")
    
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "conversation_history": [],
        "deepgram_client": DeepgramClient(settings.DEEPGRAM_API_KEY)
    }
    
    logger.info(f"Started voice session: {session_id}")
    
    return {
        "session_id": session_id,
        "status": "ready",
        "message": "Session started. Send audio to /process-audio"
    }

@router.post("/process-audio/{session_id}")
async def process_audio(session_id: str, request: Request):
    """Process audio and return text response"""
    if session_id not in sessions:
        return {"error": "Invalid session ID"}, 404
    
    session = sessions[session_id]
    deepgram_client = session["deepgram_client"]
    
    # Get audio data from request
    data = await request.json()
    audio_base64 = data.get("audio")
    
    if not audio_base64:
        return {"error": "No audio data provided"}, 400
    
    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_base64)
        
        # Process with Deepgram (simplified for now)
        # In production, you'd stream to Deepgram API
        transcript = "I need organic milk"  # Placeholder
        
        # Process through LangGraph
        search_request = {
            "query": transcript,
            "user_id": session["user_id"],
            "session_id": session_id,
            "limit": 10
        }
        
        initial_state = create_initial_state(search_request, 0.5)
        final_state = await search_graph.ainvoke(initial_state)
        
        # Get response
        response_data = final_state.get("final_response", {})
        products = response_data.get("products", [])
        
        # Format response
        if products:
            response_text = f"I found {len(products)} products for you. "
            for i, p in enumerate(products[:3]):
                name = p.get('product_name', 'Unknown')
                supplier = p.get('supplier', '')
                price = p.get('price', 0)
                
                if supplier and supplier not in name:
                    response_text += f"{name} from {supplier} for ${price:.2f}. "
                else:
                    response_text += f"{name} for ${price:.2f}. "
        else:
            response_text = "I couldn't find any products matching that."
        
        # Generate TTS
        audio_response = await deepgram_client.synthesize_speech(response_text)
        audio_response_base64 = base64.b64encode(audio_response).decode('utf-8')
        
        # Update conversation history
        session["conversation_history"].append({
            "user": transcript,
            "assistant": response_text,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "transcript": transcript,
            "response_text": response_text,
            "response_audio": audio_response_base64,
            "products": products[:5] if products else []
        }
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        return {"error": "Failed to process audio"}, 500

@router.get("/events/{session_id}")
async def event_stream(session_id: str):
    """Server-Sent Events endpoint for real-time updates"""
    if session_id not in sessions:
        return {"error": "Invalid session ID"}, 404
    
    async def generate():
        """Generate SSE events"""
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
            
            # Keep connection alive
            while True:
                # Send heartbeat every 30 seconds
                await asyncio.sleep(30)
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
                
        except asyncio.CancelledError:
            logger.info(f"SSE connection closed for session {session_id}")
            raise
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
            "Connection": "keep-alive"
        }
    )

@router.delete("/end-session/{session_id}")
async def end_session(session_id: str):
    """End a voice session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "ended", "session_id": session_id}
    return {"error": "Session not found"}, 404

@router.get("/health")
async def voice_sse_health():
    """Health check for voice SSE endpoints"""
    return {
        "status": "healthy",
        "active_sessions": len(sessions),
        "endpoints": {
            "start_session": "POST /api/v1/voice-sse/start-session",
            "process_audio": "POST /api/v1/voice-sse/process-audio/{session_id}",
            "event_stream": "GET /api/v1/voice-sse/events/{session_id}",
            "end_session": "DELETE /api/v1/voice-sse/end-session/{session_id}"
        }
    }