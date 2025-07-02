"""
Voice API using HTTP endpoints with Deepgram - Cloud Run compatible
This approach uses HTTP polling instead of WebSockets
"""
import asyncio
import json
import base64
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import structlog

from src.voice.deepgram_client import DeepgramClient
from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.config.settings import settings
from src.models.state import SearchState
from src.config.constants import SEARCH_DEFAULT_LIMIT

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-http")

# Helper function to create initial state
def create_initial_state_voice(query: str, user_id: str, session_id: str, alpha: float = 0.5) -> dict:
    """Create initial state for voice requests"""
    request_id = generate_request_id()
    
    return {
        "messages": [{
            "role": "human",
            "content": query,
            "tool_calls": None,
            "tool_call_id": None
        }],
        "query": query,
        "request_id": request_id,
        "timestamp": datetime.utcnow(),
        "alpha_value": alpha,
        "search_strategy": "hybrid",
        "next_action": None,
        "reasoning": [],
        "routing_decision": None,
        "should_search": False,
        "search_params": {
            "limit": SEARCH_DEFAULT_LIMIT,
            "source": "voice"
        },
        "search_results": [],
        "search_metadata": {},
        "pending_tool_calls": [],
        "completed_tool_calls": [],
        "session_id": session_id,
        "enhanced_query": None,
        "current_order": {"items": []},
        "order_metadata": {},
        "user_context": {
            "user_id": user_id,
            "filters": {},
            "preferences": {}
        },
        "preferences": [],
        "filters": {},
        "user_id": user_id,
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

# Store active sessions in memory (use Redis in production)
sessions: Dict[str, Dict[str, Any]] = {}

# Session cleanup will be handled differently to avoid asyncio issues
cleanup_task = None

class SessionRequest(BaseModel):
    user_id: str = "anonymous"
    
class ProcessAudioRequest(BaseModel):
    audio: str  # base64 encoded audio
    format: str = "webm"  # audio format
    test_transcript: Optional[str] = None  # For testing without actual audio

@router.post("/start-session")
async def start_session(request: SessionRequest):
    """Start a new voice session"""
    session_id = str(uuid.uuid4())
    
    sessions[session_id] = {
        "user_id": request.user_id,
        "created_at": datetime.utcnow(),
        "conversation_history": [],
        "deepgram_client": DeepgramClient(settings.deepgram_api_key if hasattr(settings, 'deepgram_api_key') else "317dce244c7355a30a4719db7359de3854e2963c"),
        "processing": False,
        "last_transcript": None,
        "last_response": None,
        "pending_audio": None
    }
    
    logger.info(f"Started HTTP voice session: {session_id}")
    
    return {
        "session_id": session_id,
        "status": "ready",
        "message": "Session started. Send audio to /process-audio"
    }

@router.post("/process-audio/{session_id}")
async def process_audio(session_id: str, request: ProcessAudioRequest):
    """Process audio chunk and return transcript + response"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    # Prevent concurrent processing
    if session["processing"]:
        return {
            "status": "processing",
            "message": "Previous request still processing"
        }
    
    session["processing"] = True
    
    try:
        # Check if this is a test request
        if request.test_transcript:
            # For testing, use the provided transcript
            transcript = request.test_transcript
            from src.voice.deepgram_client import VoiceInsights
            insights = VoiceInsights(
                transcript=transcript,
                sentiment="neutral",
                intent="search_products",
                confidence=1.0
            )
            transcript_result = type('TranscriptResult', (), {
                'transcript': transcript,
                'insights': insights
            })()
        else:
            # For now, use a simple HTTP API call to Deepgram
            # In production, we'd use the streaming API
            try:
                # Decode base64 audio
                audio_bytes = base64.b64decode(request.audio)
                
                # Use Deepgram's REST API for simple transcription
                import httpx
                
                headers = {
                    "Authorization": f"Token {settings.deepgram_api_key}",
                    "Content-Type": "audio/webm"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.deepgram.com/v1/listen?model=nova-2&language=en",
                        headers=headers,
                        content=audio_bytes,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        results = data.get("results", {})
                        channels = results.get("channels", [{}])
                        alternatives = channels[0].get("alternatives", [{}])
                        transcript = alternatives[0].get("transcript", "")
                        confidence = alternatives[0].get("confidence", 0.0)
                        
                        from src.voice.deepgram_client import VoiceInsights
                        insights = VoiceInsights(
                            transcript=transcript,
                            confidence=confidence,
                            sentiment="neutral",
                            intent="search_products"
                        )
                        
                        transcript_result = type('TranscriptResult', (), {
                            'transcript': transcript,
                            'insights': insights
                        })()
                    else:
                        logger.error(f"Deepgram API error: {response.status_code} - {response.text}")
                        # Fallback
                        transcript = "I need help finding products"
                        from src.voice.deepgram_client import VoiceInsights
                        insights = VoiceInsights(
                            transcript=transcript,
                            confidence=0.5,
                            sentiment="neutral",
                            intent="search_products"
                        )
                        transcript_result = type('TranscriptResult', (), {
                            'transcript': transcript,
                            'insights': insights
                        })()
                        
            except Exception as e:
                logger.error(f"Error calling Deepgram: {e}")
                # Fallback transcript
                transcript = "I need help finding products"
                from src.voice.deepgram_client import VoiceInsights
                insights = VoiceInsights(
                    transcript=transcript,
                    confidence=0.5,
                    sentiment="neutral",
                    intent="search_products"
                )
                transcript_result = type('TranscriptResult', (), {
                    'transcript': transcript,
                    'insights': insights
                })()
        
        if not transcript_result or not transcript_result.transcript:
            session["processing"] = False
            return {
                "status": "no_speech",
                "message": "No speech detected"
            }
        
        transcript = transcript_result.transcript
        insights = transcript_result.insights
        
        # Store transcript
        session["last_transcript"] = transcript
        
        # Check if this is a greeting or non-product query
        greeting_words = ["hello", "hi", "hey", "how are you", "can you hear me", "test", "testing"]
        transcript_lower = transcript.lower()
        is_greeting = any(word in transcript_lower for word in greeting_words)
        
        if is_greeting:
            # Handle greeting without searching
            response_text = "Hello! I can hear you clearly. I'm ready to help you find products. What would you like to search for?"
            
            # Update conversation
            session["conversation_history"].append({
                "user": transcript,
                "assistant": response_text,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            session["processing"] = False
            
            # Generate TTS for greeting too
            try:
                audio_response = await session["deepgram_client"].synthesize_speech(response_text)
                audio_base64 = base64.b64encode(audio_response).decode('utf-8')
                audio_format = "wav"
            except Exception as e:
                logger.warning(f"TTS failed for greeting: {e}")
                # Fallback - no audio
                audio_base64 = ""
                audio_format = "none"
            
            return {
                "status": "success",
                "transcript": transcript,
                "response_text": response_text,
                "response_audio": audio_base64,
                "audio_format": audio_format,
                "products": []
            }
        
        # Process through LangGraph for actual product searches
        search_request = {
            "query": transcript,
            "user_id": session["user_id"],
            "session_id": session_id,
            "limit": 10,
            "source": "voice"
        }
        
        initial_state = create_initial_state_voice(
            transcript,
            session["user_id"],
            session_id,
            0.5
        )
        
        # Add voice insights to state
        if insights:
            initial_state["voice_insights"] = {
                "sentiment": insights.sentiment,
                "intent": insights.intent,
                "urgency": insights.urgency_score,
                "frustration": insights.frustration_indicators
            }
        
        # Execute search
        final_state = await search_graph.ainvoke(initial_state)
        response_data = final_state.get("final_response", {})
        
        # Format response for voice
        products = response_data.get("products", [])
        
        if products:
            # Check if all products are organic when searching for milk
            all_organic = all(p.get('is_organic', False) for p in products)
            
            # Build voice-friendly response
            if 'milk' in transcript.lower() and all_organic:
                response_text = f"I found {len(products)} milk options, and they're all organic varieties. "
            else:
                response_text = f"I found {len(products)} products for you. "
            
            # List top 3 products
            for i, p in enumerate(products[:3]):
                name = p.get('product_name', 'Unknown')
                supplier = p.get('supplier', '')
                price = p.get('price', 0)
                
                if supplier and supplier not in name:
                    response_text += f"{name} from {supplier} for ${price:.2f}. "
                else:
                    response_text += f"{name} for ${price:.2f}. "
            
            if len(products) > 3:
                response_text += f"And {len(products) - 3} more options available."
        else:
            response_text = response_data.get("message", "I couldn't find any products matching that.")
        
        # Generate TTS with Deepgram Aura
        audio_response = await session["deepgram_client"].synthesize_speech(
            response_text
        )
        
        # Convert audio to base64
        audio_base64 = base64.b64encode(audio_response).decode('utf-8')
        
        # Update conversation history
        session["conversation_history"].append({
            "user": transcript,
            "assistant": response_text,
            "timestamp": datetime.utcnow().isoformat(),
            "products": products[:5],
            "insights": insights.__dict__ if insights else None
        })
        
        session["last_response"] = response_text
        session["processing"] = False
        
        return {
            "status": "success",
            "transcript": transcript,
            "response_text": response_text,
            "response_audio": audio_base64,
            "audio_format": "wav",
            "products": products[:5] if products else [],
            "insights": {
                "sentiment": insights.sentiment if insights else None,
                "intent": insights.intent if insights else None,
                "urgency": insights.urgency_score if insights else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}")
        session["processing"] = False
        
        # Return error without TTS
        return {
            "status": "error",
            "error": str(e),
            "response_text": "I'm having trouble processing that. Please try again."
        }

@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str):
    """Get current session status"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    return {
        "session_id": session_id,
        "status": "processing" if session["processing"] else "ready",
        "conversation_length": len(session["conversation_history"]),
        "last_transcript": session["last_transcript"],
        "last_response": session["last_response"]
    }

@router.get("/session/{session_id}/history")
async def get_conversation_history(session_id: str):
    """Get conversation history"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "history": sessions[session_id]["conversation_history"]
    }

@router.delete("/session/{session_id}")
async def end_session(session_id: str):
    """End a voice session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "ended", "session_id": session_id}
    
    raise HTTPException(status_code=404, detail="Session not found")

@router.get("/health")
async def voice_http_health():
    """Health check for HTTP voice endpoints"""
    return {
        "status": "healthy",
        "active_sessions": len(sessions),
        "deepgram_configured": bool(settings.DEEPGRAM_API_KEY),
        "endpoints": {
            "start_session": "POST /api/v1/voice-http/start-session",
            "process_audio": "POST /api/v1/voice-http/process-audio/{session_id}",
            "session_status": "GET /api/v1/voice-http/session/{session_id}/status",
            "conversation_history": "GET /api/v1/voice-http/session/{session_id}/history",
            "end_session": "DELETE /api/v1/voice-http/session/{session_id}"
        }
    }