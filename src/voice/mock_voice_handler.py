"""
Mock Voice Handler for testing without Google Cloud credentials
"""
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime
import structlog

from src.models.voice_state import (
    VoiceMetadata, VoiceTranscript, TTSConfig,
    VoiceResponse, MultiModalInput
)

logger = structlog.get_logger()

class MockVoiceHandler:
    """
    Mock implementation of GoogleVoiceHandler for testing
    Returns realistic mock data without requiring Google Cloud
    """
    
    def __init__(self):
        self._active_sessions = {}
        logger.info("MockVoiceHandler initialized - no Google Cloud required")
        
    async def process_voice_input(
        self, 
        audio_generator: AsyncGenerator[bytes, None],
        session_id: str,
        language_hint: Optional[str] = None
    ) -> AsyncGenerator[MultiModalInput, None]:
        """Mock voice processing - returns sample queries"""
        
        # Simulate processing delay
        await asyncio.sleep(0.5)
        
        # Mock transcripts for testing
        mock_queries = [
            "Show me organic milk",
            "I need eggs and bread",
            "What's on sale today?",
            "Add 5 bananas to my cart"
        ]
        
        for i, query in enumerate(mock_queries):
            # Simulate voice metadata
            voice_metadata = VoiceMetadata(
                pace="normal" if i % 2 == 0 else "fast",
                volume="normal",
                clarity="high",
                emotion="neutral" if i < 2 else "excited",
                stress_level="normal",
                hesitation_count=0,
                interruption=False,
                noise_level="quiet",
                language_code=language_hint or "en-US",
                accent_confidence=0.95,
                duration=2.5,
                speaking_rate=150,
                max_pause=0.2
            )
            
            voice_transcript = VoiceTranscript(
                text=query,
                confidence=0.95,
                is_final=True,
                alternatives=[],
                words=[],
                language_code=language_hint or "en-US",
                language_confidence=0.95
            )
            
            multi_modal_input = MultiModalInput(
                text=query,
                audio_data=None,
                voice_transcript=voice_transcript,
                voice_metadata=voice_metadata,
                image_data=None,
                image_description=None,
                primary_modality="voice",
                modalities_used=["voice"]
            )
            
            yield multi_modal_input
            
            # Wait a bit between queries
            await asyncio.sleep(2)
    
    async def generate_voice_response(
        self,
        text: str,
        session_id: str,
        response_type: str = "answer",
        voice_metadata: Optional[VoiceMetadata] = None,
        style_hint: Optional[str] = None
    ) -> VoiceResponse:
        """Generate mock voice response"""
        
        # Mock TTS config
        tts_config = TTSConfig(
            voice_name="en-US-Mock-Voice",
            speaking_rate=1.0,
            pitch=0.0,
            volume_gain_db=0.0,
            style=style_hint or "normal"
        )
        
        # Mock audio data (just empty bytes for now)
        mock_audio = b"MOCK_AUDIO_DATA"
        
        return VoiceResponse(
            text=text,
            ssml=f"<speak>{text}</speak>",
            tts_config=tts_config,
            response_type=response_type,
            requires_user_response=response_type in ["clarification", "confirmation"],
            audio_data=mock_audio
        )
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get mock session summary"""
        return {
            "duration": 60.0,
            "turn_count": 4,
            "languages": ["en-US"],
            "voice_profile": {
                "avg_speaking_rate": 150,
                "typical_emotion": "neutral"
            }
        }
    
    async def cleanup_session(self, session_id: str):
        """Clean up mock session"""
        logger.info(f"Cleaned up mock session: {session_id}")