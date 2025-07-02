"""11Labs Voice Integration for natural conversation"""
import os
import httpx
import asyncio
from typing import Optional, Dict, Any, AsyncIterator
import structlog
from src.config.settings import settings

logger = structlog.get_logger()

class ElevenLabsClient:
    """11Labs text-to-speech and speech-to-text integration"""
    
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel voice default
        self.model_id = "eleven_monolingual_v1"
        self.api_base = "https://api.elevenlabs.io/v1"
        
    async def text_to_speech(self, text: str, voice_settings: Optional[Dict] = None) -> bytes:
        """
        Convert text to speech audio
        
        Args:
            text: Text to convert to speech
            voice_settings: Optional voice customization settings
            
        Returns:
            Audio bytes (MP3 format)
        """
        if not self.api_key:
            logger.error("11Labs API key not configured")
            return b""
            
        url = f"{self.api_base}/text-to-speech/{self.voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        # Default voice settings for natural conversation
        default_settings = {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
        
        if voice_settings:
            default_settings.update(voice_settings)
            
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": default_settings
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"11Labs TTS error: {response.status_code} - {response.text}")
                    return b""
                    
        except Exception as e:
            logger.error(f"11Labs TTS failed: {str(e)}")
            return b""
            
    async def text_to_speech_stream(self, text: str, chunk_size: int = 1024) -> AsyncIterator[bytes]:
        """
        Stream text to speech for real-time playback
        
        Args:
            text: Text to convert
            chunk_size: Size of audio chunks to yield
            
        Yields:
            Audio chunks for streaming
        """
        if not self.api_key:
            logger.error("11Labs API key not configured")
            return
            
        url = f"{self.api_base}/text-to-speech/{self.voice_id}/stream"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        payload = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream('POST', url, headers=headers, json=payload) as response:
                    if response.status_code == 200:
                        async for chunk in response.aiter_bytes(chunk_size):
                            yield chunk
                    else:
                        logger.error(f"11Labs stream error: {response.status_code}")
                        
        except Exception as e:
            logger.error(f"11Labs streaming failed: {str(e)}")
            
    async def speech_to_text(self, audio_data: bytes, language: str = "en") -> Optional[str]:
        """
        Convert speech to text (if 11Labs adds STT support)
        Currently, you might use Whisper API or Google STT
        
        Args:
            audio_data: Audio bytes to transcribe
            language: Language code
            
        Returns:
            Transcribed text or None
        """
        # Placeholder for when 11Labs adds STT
        # For now, you'd integrate Whisper or Google STT here
        logger.info("STT not implemented - use Whisper or Google STT")
        return None
        
    def estimate_duration(self, text: str) -> float:
        """
        Estimate speech duration for UI timing
        
        Args:
            text: Text to speak
            
        Returns:
            Estimated duration in seconds
        """
        # Rough estimate: 150 words per minute
        word_count = len(text.split())
        return (word_count / 150) * 60
        
    async def get_voice_list(self) -> list:
        """Get available voices from 11Labs"""
        if not self.api_key:
            return []
            
        url = f"{self.api_base}/voices"
        headers = {"xi-api-key": self.api_key}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    return response.json().get("voices", [])
                    
        except Exception as e:
            logger.error(f"Failed to get voices: {str(e)}")
            
        return []
        
    def format_for_speech(self, text: str) -> str:
        """
        Format text for natural speech output
        
        Args:
            text: Raw text from agents
            
        Returns:
            Speech-optimized text
        """
        # Convert lists to natural speech
        if "• " in text:
            text = text.replace("• ", "")
            
        # Add pauses for better flow
        text = text.replace(". ", ". <break time='0.5s'/> ")
        text = text.replace(", ", ", <break time='0.2s'/> ")
        
        # Convert prices to speech format
        import re
        price_pattern = r'\$(\d+)\.(\d{2})'
        text = re.sub(price_pattern, r'\1 dollars and \2 cents', text)
        
        return text