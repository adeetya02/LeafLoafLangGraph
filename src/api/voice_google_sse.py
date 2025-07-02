"""
Google Voice with Server-Sent Events (SSE)
Simple HTTP streaming approach
"""
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from google.cloud import speech
from google.cloud import texttospeech
import json
import base64
import asyncio
import structlog
from typing import AsyncGenerator

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/google-sse")

# Global clients
stt_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()

async def process_audio_stream(audio_data: bytes, language: str = "en-US") -> AsyncGenerator[str, None]:
    """Process audio and yield SSE events"""
    try:
        # Configure recognition
        audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code=language,
            enable_automatic_punctuation=True,
        )
        
        # Recognize speech
        response = stt_client.recognize(config=config, audio=audio)
        
        if response.results:
            result = response.results[0]
            alternative = result.alternatives[0]
            transcript = alternative.transcript
            confidence = alternative.confidence
            
            # Send transcript
            yield f"data: {json.dumps({'type': 'transcript', 'text': transcript, 'confidence': confidence})}\n\n"
            
            # Generate response
            response_text = generate_simple_response(transcript)
            yield f"data: {json.dumps({'type': 'response', 'text': response_text})}\n\n"
            
            # Generate TTS
            synthesis_input = texttospeech.SynthesisInput(text=response_text)
            voice = texttospeech.VoiceSelectionParams(
                language_code=language,
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            tts_response = tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            # Send audio
            audio_base64 = base64.b64encode(tts_response.audio_content).decode()
            yield f"data: {json.dumps({'type': 'audio', 'data': audio_base64})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'error', 'message': 'No speech detected'})}\n\n"
            
    except Exception as e:
        logger.error(f"Processing error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

def generate_simple_response(transcript: str) -> str:
    """Generate simple response"""
    text = transcript.lower()
    
    if any(greeting in text for greeting in ["hello", "hi", "hey"]):
        return "Hello! Welcome to LeafLoaf. What groceries can I help you find?"
    elif "organic" in text:
        return "We have a wide selection of organic products including fruits, vegetables, dairy, and pantry items."
    elif "milk" in text:
        return "We offer whole milk, 2%, skim, and plant-based options like oat, almond, and soy milk."
    elif "sale" in text or "deal" in text:
        return "Today's deals include 20% off all organic produce and buy-one-get-one on selected dairy items."
    else:
        return f"I can help you find {transcript}. Let me search our inventory for you."

@router.post("/stream")
async def stream_audio(request: Request):
    """Stream audio processing with SSE"""
    body = await request.json()
    audio_base64 = body.get("audio")
    language = body.get("language", "en-US")
    
    if not audio_base64:
        return {"error": "No audio data provided"}
    
    # Decode audio
    audio_data = base64.b64decode(audio_base64)
    
    # Return SSE stream
    return StreamingResponse(
        process_audio_stream(audio_data, language),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )

@router.get("/test")
async def test_endpoint():
    """Test if Google services are working"""
    try:
        # Test TTS
        synthesis_input = texttospeech.SynthesisInput(text="Test")
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return {"status": "ok", "tts": "working", "audio_size": len(response.audio_content)}
    except Exception as e:
        return {"status": "error", "message": str(e)}