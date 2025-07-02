"""
Basic Google Voice API - Just STT and TTS, no supervisor
Following Google Cloud documentation
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import base64
from google.cloud import speech
from google.cloud import texttospeech
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/google")

class VoiceRequest(BaseModel):
    audio: str  # base64 encoded audio
    format: str = "webm"  # audio format
    language: str = "en-US"

class VoiceResponse(BaseModel):
    transcript: str
    confidence: float
    response_text: str
    audio: str  # base64 encoded response audio

@router.post("/process", response_model=VoiceResponse)
async def process_voice(request: VoiceRequest):
    """
    Simple voice processing:
    1. Convert speech to text
    2. Generate a simple response
    3. Convert response to speech
    """
    try:
        # Decode audio
        audio_data = base64.b64decode(request.audio)
        
        # Step 1: Speech-to-Text
        stt_client = speech.SpeechClient()
        
        audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code=request.language,
            enable_automatic_punctuation=True,
        )
        
        # Recognize speech
        response = stt_client.recognize(config=config, audio=audio)
        
        if not response.results:
            return VoiceResponse(
                transcript="",
                confidence=0.0,
                response_text="I didn't catch that. Could you please repeat?",
                audio=""
            )
        
        # Get transcript
        result = response.results[0]
        alternative = result.alternatives[0]
        transcript = alternative.transcript
        confidence = alternative.confidence
        
        logger.info(f"Transcribed: {transcript} (confidence: {confidence})")
        
        # Step 2: Generate simple response (no AI for now)
        response_text = generate_simple_response(transcript)
        
        # Step 3: Text-to-Speech
        tts_client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=response_text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=request.language,
            name="en-US-Journey-D" if request.language.startswith("en") else None,
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
        
        # Encode audio response
        audio_base64 = base64.b64encode(tts_response.audio_content).decode()
        
        return VoiceResponse(
            transcript=transcript,
            confidence=confidence,
            response_text=response_text,
            audio=audio_base64
        )
        
    except Exception as e:
        logger.error(f"Voice processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_simple_response(transcript: str) -> str:
    """Generate a simple response without AI"""
    text = transcript.lower()
    
    # Simple keyword-based responses
    if any(greeting in text for greeting in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return "Hello! Welcome to LeafLoaf. How can I help you with your grocery shopping today?"
    
    elif "help" in text:
        return "I can help you find products, add items to your cart, or answer questions about our groceries. What would you like to do?"
    
    elif any(word in text for word in ["thank", "thanks"]):
        return "You're welcome! Is there anything else you need?"
    
    elif any(word in text for word in ["bye", "goodbye", "see you"]):
        return "Goodbye! Thanks for shopping with LeafLoaf!"
    
    # Product-related keywords
    elif any(word in text for word in ["milk", "bread", "eggs", "fruit", "vegetable"]):
        return f"I heard you mention {text}. In a full system, I would search for those products. This is a demo showing Google Cloud voice services."
    
    elif "cart" in text or "add" in text:
        return "In a full system, I would help you manage your shopping cart. This demo is showing the voice recognition capabilities."
    
    else:
        return f"I heard you say: {transcript}. This is a demo of Google Cloud Speech services working with LeafLoaf."

@router.get("/health")
async def health_check():
    """Check if Google Cloud services are accessible"""
    try:
        # Try to create clients
        speech.SpeechClient()
        texttospeech.TextToSpeechClient()
        return {"status": "healthy", "service": "Google Cloud Voice"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

@router.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "languages": [
            {"code": "en-US", "name": "English (US)"},
            {"code": "en-GB", "name": "English (UK)"},
            {"code": "es-US", "name": "Spanish (US)"},
            {"code": "es-ES", "name": "Spanish (Spain)"},
            {"code": "fr-FR", "name": "French"},
            {"code": "de-DE", "name": "German"},
            {"code": "it-IT", "name": "Italian"},
            {"code": "pt-BR", "name": "Portuguese (Brazil)"},
            {"code": "ru-RU", "name": "Russian"},
            {"code": "ja-JP", "name": "Japanese"},
            {"code": "ko-KR", "name": "Korean"},
            {"code": "zh-CN", "name": "Chinese (Mandarin)"},
            {"code": "hi-IN", "name": "Hindi"},
            {"code": "ar-SA", "name": "Arabic"},
        ]
    }

@router.get("/voices")
async def get_available_voices():
    """Get available TTS voices"""
    try:
        client = texttospeech.TextToSpeechClient()
        voices = client.list_voices()
        
        # Filter for some nice voices
        recommended_voices = []
        for voice in voices.voices:
            if voice.language_codes[0].startswith("en-US") and "Journey" in voice.name:
                recommended_voices.append({
                    "name": voice.name,
                    "language": voice.language_codes[0],
                    "gender": voice.ssml_gender.name
                })
        
        return {"voices": recommended_voices[:5]}  # Return top 5
        
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        return {"voices": []}