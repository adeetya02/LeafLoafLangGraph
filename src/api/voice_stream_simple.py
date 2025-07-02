"""
Simple HTTP streaming for voice - production ready
Direct Deepgram integration with SSE for real-time updates
"""
import asyncio
import json
import base64
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import structlog

from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-stream")

DEEPGRAM_API_KEY = "36a821d351939023aabad9beeaa68b391caa124a"

class VoiceRequest(BaseModel):
    audio_base64: str
    user_id: str = "voice_user"
    session_id: str = ""

class TranscriptionResult(BaseModel):
    transcript: str
    confidence: float
    
async def transcribe_audio(audio_base64: str) -> TranscriptionResult:
    """Transcribe audio using Deepgram"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.deepgram.com/v1/listen?model=nova-2&language=en-US&punctuate=true&smart_format=true",
                headers={
                    "Authorization": f"Token {DEEPGRAM_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={"audio": audio_base64},
                timeout=30.0
            )
            
            if response.status_code != 200:
                logger.error(f"Deepgram error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail="Transcription failed")
            
            data = response.json()
            
            # Extract transcript
            results = data.get("results", {})
            channels = results.get("channels", [])
            if channels and channels[0].get("alternatives"):
                alt = channels[0]["alternatives"][0]
                return TranscriptionResult(
                    transcript=alt.get("transcript", ""),
                    confidence=alt.get("confidence", 0.0)
                )
            
            return TranscriptionResult(transcript="", confidence=0.0)
            
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def search_products(query: str, user_id: str) -> dict:
    """Search for products using LeafLoaf"""
    try:
        from src.models.state import SearchState
        
        initial_state = SearchState(
            query=query,
            user_id=user_id,
            request_id=generate_request_id(),
            limit=8
        )
        
        # Run search
        result = await asyncio.to_thread(
            search_graph.invoke,
            initial_state.model_dump()
        )
        
        # Extract products
        products = []
        if result.get("products"):
            products = [
                {
                    "name": p.get("name") or p.get("product_name", "Unknown"),
                    "price": float(p.get("price") or p.get("unit_price", 0)),
                    "unit": p.get("unit", ""),
                    "category": p.get("category", "")
                }
                for p in result["products"][:8]
            ]
        
        return {
            "query": query,
            "products": products,
            "count": len(products)
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {
            "query": query,
            "products": [],
            "count": 0,
            "error": str(e)
        }

async def stream_voice_response(request: VoiceRequest) -> AsyncGenerator[str, None]:
    """Stream voice processing events"""
    
    # Step 1: Acknowledge
    yield f"data: {json.dumps({'type': 'status', 'message': 'Processing audio...'})}\n\n"
    
    # Step 2: Transcribe
    try:
        result = await transcribe_audio(request.audio_base64)
        
        if not result.transcript:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No speech detected'})}\n\n"
            return
            
        yield f"data: {json.dumps({'type': 'transcript', 'text': result.transcript, 'confidence': result.confidence})}\n\n"
        
        # Step 3: Search
        yield f"data: {json.dumps({'type': 'searching', 'query': result.transcript})}\n\n"
        
        search_result = await search_products(result.transcript, request.user_id)
        
        # Step 4: Results
        yield f"data: {json.dumps({'type': 'results', **search_result})}\n\n"
        
        # Step 5: Complete
        yield f"data: {json.dumps({'type': 'complete', 'message': 'Ready for next query'})}\n\n"
        
    except Exception as e:
        logger.error(f"Stream error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

@router.post("/process")
async def process_voice(request: VoiceRequest):
    """Process voice input and stream results"""
    return StreamingResponse(
        stream_voice_response(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

@router.get("/health")
async def health_check():
    """Health check for voice streaming"""
    return {
        "status": "healthy",
        "deepgram_configured": bool(DEEPGRAM_API_KEY),
        "endpoint": "/api/v1/voice-stream/process"
    }