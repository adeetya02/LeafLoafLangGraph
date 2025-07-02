"""
Voice endpoints using OpenAI Whisper + LangGraph + ElevenLabs TTS
Perfect for multilingual grocery shopping with full conversation control
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import base64
import httpx
import os
import structlog
from datetime import datetime

from src.core.graph import search_graph
from src.models.state import SearchState
from src.api.main import create_initial_state
from src.utils.id_generator import generate_request_id

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice")

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") 
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Default: Sarah

class VoiceSearchRequest(BaseModel):
    """Voice search request with audio data"""
    audio_data: str  # Base64 encoded audio
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    language: Optional[str] = "en"  # Support multilingual

class VoiceResponse(BaseModel):
    """Voice response with audio and text"""
    text: str  # What the assistant said
    audio_data: str  # Base64 encoded audio response
    products: Optional[list] = None
    session_id: str

# In-memory conversation context (use Redis in production)
conversation_sessions = {}

async def transcribe_with_whisper(audio_data: bytes, language: str = "en") -> str:
    """
    Transcribe audio using OpenAI Whisper
    Handles multilingual queries like "I need sabzi" perfectly
    """
    try:
        async with httpx.AsyncClient() as client:
            # Prepare the audio file
            files = {
                "file": ("audio.webm", audio_data, "audio/webm"),
            }
            
            data = {
                "model": "whisper-1",
                "language": language if language != "auto" else None,
                "prompt": "This is a grocery shopping conversation. Common items include milk, bread, vegetables, fruits, and brand names like Organic Valley, Horizon, Chobani."  # Helps with accuracy
            }
            
            response = await client.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get("text", "")
                logger.info(f"Whisper transcription: '{transcript}'")
                return transcript
            else:
                logger.error(f"Whisper error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail="Transcription failed")
                
    except Exception as e:
        logger.error(f"Whisper transcription error: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")

async def generate_speech_with_elevenlabs(text: str, voice_settings: Optional[Dict] = None) -> bytes:
    """
    Generate speech using ElevenLabs TTS
    Most natural voice for building customer relationships
    """
    try:
        async with httpx.AsyncClient() as client:
            # Default voice settings for friendly grocery assistant
            if not voice_settings:
                voice_settings = {
                    "stability": 0.75,  # Consistent but not robotic
                    "similarity_boost": 0.75,  # Natural variation
                    "style": 0.5,  # Balanced style
                    "use_speaker_boost": True  # Clearer voice
                }
            
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",  # Supports multiple languages
                    "voice_settings": voice_settings
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"ElevenLabs error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail="Speech generation failed")
                
    except Exception as e:
        logger.error(f"ElevenLabs TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

def format_products_for_voice(products: list) -> str:
    """
    Format products for natural voice response
    Includes brand names for clarity
    """
    if not products:
        return "I couldn't find any products matching your search."
    
    if len(products) == 1:
        p = products[0]
        return f"I found {p['product_name']} from {p.get('supplier', 'our store')} for ${p['price']:.2f}."
    
    # Multiple products
    response = f"I found {len(products)} products. "
    
    # List top 3-5 for voice
    top_products = products[:min(5, len(products))]
    
    product_list = []
    for i, p in enumerate(top_products):
        name = p['product_name']
        supplier = p.get('supplier', '')
        price = p['price']
        
        # Include supplier for brand clarity
        if supplier and supplier not in name:
            product_desc = f"{name} from {supplier}"
        else:
            product_desc = name
            
        product_list.append(f"{product_desc} for ${price:.2f}")
    
    if len(product_list) <= 3:
        response += "Here are your options: " + ", ".join(product_list) + "."
    else:
        response += "The top options are: " + ", ".join(product_list[:3])
        response += f", and {len(product_list) - 3} more."
    
    return response

@router.post("/search", response_model=VoiceResponse)
async def voice_search(request: VoiceSearchRequest):
    """
    Complete voice search flow:
    1. Whisper transcribes user speech (handles multilingual)
    2. LangGraph agents process the query (your existing logic)
    3. ElevenLabs generates natural voice response
    """
    try:
        # Step 1: Transcribe audio with Whisper
        audio_bytes = base64.b64decode(request.audio_data)
        user_query = await transcribe_with_whisper(audio_bytes, request.language)
        
        if not user_query:
            raise HTTPException(status_code=400, detail="Could not transcribe audio")
        
        # Step 2: Get or create session context
        session_id = request.session_id or generate_request_id()
        
        if session_id not in conversation_sessions:
            conversation_sessions[session_id] = {
                "history": [],
                "user_id": request.user_id,
                "language": request.language
            }
        
        session = conversation_sessions[session_id]
        session["history"].append({"role": "user", "content": user_query})
        
        # Step 3: Process with LangGraph agents
        search_request = {
            "query": user_query,
            "user_id": request.user_id,
            "session_id": session_id,
            "limit": 10  # Get more for voice selection
        }
        
        initial_state = create_initial_state(search_request, 0.5)
        final_state = await search_graph.ainvoke(initial_state)
        
        # Get results
        response_data = final_state.get("final_response", {})
        products = response_data.get("products", [])
        
        # Step 4: Generate voice response
        if final_state.get("routing_decision") == "order_agent":
            # Handle order operations
            order = response_data.get("order", {})
            if order and order.get("items"):
                voice_text = f"Your cart has {len(order['items'])} items. "
                total = sum(item['quantity'] * item['price'] for item in order['items'])
                voice_text += f"The total is ${total:.2f}."
            else:
                voice_text = response_data.get("message", "I've updated your order.")
        else:
            # Handle search results
            voice_text = format_products_for_voice(products)
        
        # Add to conversation history
        session["history"].append({"role": "assistant", "content": voice_text})
        
        # Step 5: Generate speech with ElevenLabs
        audio_response = await generate_speech_with_elevenlabs(voice_text)
        
        return VoiceResponse(
            text=voice_text,
            audio_data=base64.b64encode(audio_response).decode(),
            products=products[:5] if products else None,  # Include top 5 for UI
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Voice search error: {e}")
        # Generate error voice response
        error_text = "I'm sorry, I had trouble processing that. Could you please try again?"
        error_audio = await generate_speech_with_elevenlabs(error_text)
        
        return VoiceResponse(
            text=error_text,
            audio_data=base64.b64encode(error_audio).decode(),
            products=None,
            session_id=request.session_id or "error"
        )

@router.post("/feedback")
async def voice_feedback(
    session_id: str,
    feedback: str,  # "helpful" or "not_helpful"
    issue: Optional[str] = None
):
    """
    Collect voice interaction feedback for improvement
    """
    # Log feedback for analysis
    logger.info(
        "Voice feedback received",
        session_id=session_id,
        feedback=feedback,
        issue=issue
    )
    
    return {"status": "Thank you for your feedback!"}

# Health check for voice services
@router.get("/health")
async def voice_health():
    """Check voice service health"""
    status = {
        "whisper": "ready" if OPENAI_API_KEY else "not_configured",
        "elevenlabs": "ready" if ELEVENLABS_API_KEY else "not_configured",
        "languages_supported": ["en", "es", "hi", "ta", "te", "bn", "ur", "ar", "zh"],
        "status": "operational"
    }
    
    return status