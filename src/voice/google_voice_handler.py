"""
Unified Google Cloud Voice Handler for STT and TTS
Integrates with voice-native supervisor
"""
import asyncio
import json
from typing import AsyncGenerator, Optional, Dict, Any, List
from datetime import datetime
import structlog
from google.cloud import speech, texttospeech
from google.api_core import exceptions

from src.models.voice_state import (
    VoiceMetadata, VoiceTranscript, TTSConfig, 
    AudioStream, VoiceResponse, MultiModalInput
)
from src.api.voice_google_stt import GoogleSTTHandler
from src.api.voice_google_tts import GoogleTTSHandler

logger = structlog.get_logger()

class GoogleVoiceHandler:
    """
    Unified handler for Google Cloud voice services
    Manages both STT and TTS with voice metadata extraction
    """
    
    def __init__(self):
        self.stt_handler = GoogleSTTHandler()
        self.tts_handler = GoogleTTSHandler()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def process_voice_input(
        self, 
        audio_generator: AsyncGenerator[bytes, None],
        session_id: str,
        language_hint: Optional[str] = None
    ) -> AsyncGenerator[MultiModalInput, None]:
        """
        Process streaming audio input and yield multi-modal inputs
        
        Args:
            audio_generator: Async generator of audio chunks
            session_id: Voice session ID
            language_hint: Optional language hint
            
        Yields:
            MultiModalInput objects with voice data and metadata
        """
        # Update language if hint provided
        if language_hint:
            self.stt_handler.update_language(language_hint)
        
        # Track session
        if session_id not in self._active_sessions:
            self._active_sessions[session_id] = {
                "start_time": datetime.utcnow(),
                "turn_count": 0,
                "detected_languages": set(),
                "voice_profile": {}
            }
        
        session = self._active_sessions[session_id]
        session["turn_count"] += 1
        
        # Process audio stream
        async for stt_result in self.stt_handler.stream_recognize(audio_generator):
            if "error" in stt_result:
                logger.error(f"STT error: {stt_result}")
                continue
            
            # Extract voice metadata
            voice_metadata = self._extract_voice_metadata(stt_result)
            
            # Build voice transcript
            voice_transcript = VoiceTranscript(
                text=stt_result.get("transcript", ""),
                confidence=stt_result.get("confidence", 0.0),
                is_final=stt_result.get("is_final", False),
                alternatives=[],  # TODO: Extract from STT result
                words=stt_result.get("words", []),
                language_code=stt_result.get("language_code", "en-US"),
                language_confidence=0.95  # Google STT is confident
            )
            
            # Update session profile
            self._update_voice_profile(session, voice_metadata, voice_transcript)
            
            # Create multi-modal input
            multi_modal_input = MultiModalInput(
                text=voice_transcript["text"],
                audio_data=None,  # We don't store raw audio
                voice_transcript=voice_transcript,
                voice_metadata=voice_metadata,
                image_data=None,
                image_description=None,
                primary_modality="voice",
                modalities_used=["voice"]
            )
            
            yield multi_modal_input
    
    def _extract_voice_metadata(self, stt_result: Dict[str, Any]) -> VoiceMetadata:
        """Extract voice metadata from STT results"""
        voice_features = stt_result.get("voice_features", {})
        
        # Determine pace from speaking rate
        speaking_rate = voice_features.get("speaking_rate", None)
        if speaking_rate:
            if speaking_rate > 180:
                pace = "fast"
            elif speaking_rate < 120:
                pace = "slow"
            else:
                pace = "normal"
        else:
            pace = voice_features.get("pace_indicator", "normal")
        
        # Determine clarity from confidence
        clarity = voice_features.get("clarity", "medium")
        
        # Infer emotion from pace and clarity
        emotion = self._infer_emotion(pace, clarity, voice_features)
        
        # Build metadata
        return VoiceMetadata(
            pace=pace,
            volume="normal",  # TODO: Extract from audio amplitude
            clarity=clarity,
            emotion=emotion,
            stress_level=self._infer_stress_level(voice_features),
            hesitation_count=voice_features.get("hesitation_count", 0),
            interruption=False,  # TODO: Detect from conversation flow
            noise_level="quiet",  # TODO: Extract from audio
            language_code=stt_result.get("language_code", "en-US"),
            accent_confidence=stt_result.get("confidence", 0.0),
            duration=0.0,  # TODO: Calculate from word timings
            speaking_rate=speaking_rate,
            max_pause=voice_features.get("max_pause", 0.0)
        )
    
    def _infer_emotion(self, pace: str, clarity: str, features: Dict[str, Any]) -> str:
        """Infer emotion from voice characteristics"""
        # Simple heuristics - should be replaced with ML model
        hesitations = features.get("hesitation_count", 0)
        
        if pace == "fast" and clarity == "high":
            return "excited"
        elif pace == "fast" and clarity == "low":
            return "urgent"
        elif hesitations > 2:
            return "confused"
        elif pace == "slow" and clarity == "low":
            return "frustrated"
        else:
            return "neutral"
    
    def _infer_stress_level(self, features: Dict[str, Any]) -> str:
        """Infer stress level from voice features"""
        pace = features.get("pace_indicator", "normal")
        hesitations = features.get("hesitation_count", 0)
        
        if pace == "fast" or hesitations > 3:
            return "stressed"
        elif pace == "slow" and hesitations == 0:
            return "relaxed"
        else:
            return "normal"
    
    def _update_voice_profile(
        self, 
        session: Dict[str, Any], 
        metadata: VoiceMetadata,
        transcript: VoiceTranscript
    ):
        """Update session voice profile with new data"""
        profile = session["voice_profile"]
        
        # Track languages
        session["detected_languages"].add(transcript["language_code"])
        
        # Update average speaking rate
        if metadata["speaking_rate"]:
            if "avg_speaking_rate" not in profile:
                profile["avg_speaking_rate"] = metadata["speaking_rate"]
            else:
                # Running average
                count = session["turn_count"]
                profile["avg_speaking_rate"] = (
                    (profile["avg_speaking_rate"] * (count - 1) + metadata["speaking_rate"]) / count
                )
        
        # Track typical emotion
        if "emotion_counts" not in profile:
            profile["emotion_counts"] = {}
        profile["emotion_counts"][metadata["emotion"]] = (
            profile["emotion_counts"].get(metadata["emotion"], 0) + 1
        )
        
        # Determine typical emotion
        if profile["emotion_counts"]:
            profile["typical_emotion"] = max(
                profile["emotion_counts"].items(), 
                key=lambda x: x[1]
            )[0]
    
    async def generate_voice_response(
        self,
        text: str,
        session_id: str,
        response_type: str = "answer",
        voice_metadata: Optional[VoiceMetadata] = None,
        style_hint: Optional[str] = None
    ) -> VoiceResponse:
        """
        Generate voice response with appropriate TTS configuration
        
        Args:
            text: Text to speak
            session_id: Voice session ID
            response_type: Type of response
            voice_metadata: User's voice metadata for mirroring
            style_hint: Optional style hint from supervisor
            
        Returns:
            VoiceResponse with audio data
        """
        session = self._active_sessions.get(session_id, {})
        
        # Determine language
        if session and "detected_languages" in session:
            # Use most recent detected language
            language = list(session["detected_languages"])[-1]
        else:
            language = "en-US"
        
        # Determine voice style
        style = self._determine_voice_style(
            response_type, 
            voice_metadata, 
            style_hint,
            session.get("voice_profile", {})
        )
        
        # Create TTS config
        tts_config = TTSConfig(
            voice_name=self.tts_handler.get_voice_name(language, style),
            speaking_rate=self._calculate_speaking_rate(voice_metadata, style),
            pitch=0.0,  # Natural pitch
            volume_gain_db=0.0,  # Normal volume
            style=style
        )
        
        # Generate SSML for natural speech
        ssml = self.tts_handler.create_conversational_ssml(
            text, 
            style=style,
            language_code=language
        )
        
        # Synthesize speech
        try:
            # Try SSML first, fall back to plain text if voice doesn't support it
            try:
                audio_data = await self.tts_handler.synthesize_ssml(
                    ssml,
                    language_code=language
                )
            except Exception as ssml_error:
                if "SSML input" in str(ssml_error):
                    logger.info("Voice doesn't support SSML, using plain text")
                    audio_data = await self.tts_handler.synthesize(
                        text,
                        language_code=language,
                        voice_type=style,
                        speaking_rate=self._calculate_speaking_rate(voice_metadata, style)
                    )
                else:
                    raise ssml_error
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            audio_data = None
        
        # Build response
        return VoiceResponse(
            text=text,
            ssml=ssml,
            tts_config=tts_config,
            response_type=response_type,
            requires_user_response=response_type in ["clarification", "confirmation"],
            audio_data=audio_data
        )
    
    def _determine_voice_style(
        self,
        response_type: str,
        user_voice: Optional[VoiceMetadata],
        style_hint: Optional[str],
        voice_profile: Dict[str, Any]
    ) -> str:
        """Determine appropriate voice style for response"""
        # Use explicit hint if provided
        if style_hint:
            return style_hint
        
        # Match user's emotional state
        if user_voice:
            if user_voice["emotion"] == "frustrated":
                return "empathetic"
            elif user_voice["emotion"] == "excited":
                return "friendly"
            elif user_voice["emotion"] == "confused":
                return "professional"  # Clear and calm
        
        # Based on response type
        if response_type == "error":
            return "empathetic"
        elif response_type == "confirmation":
            return "professional"
        elif response_type == "greeting":
            return "friendly"
        
        # Default
        return "normal"
    
    def _calculate_speaking_rate(
        self, 
        user_voice: Optional[VoiceMetadata],
        style: str
    ) -> float:
        """Calculate appropriate speaking rate"""
        # Mirror user's pace slightly
        if user_voice and user_voice["speaking_rate"]:
            user_rate = user_voice["speaking_rate"]
            if user_rate > 160:  # Fast speaker
                return 1.1
            elif user_rate < 120:  # Slow speaker
                return 0.9
        
        # Adjust for style
        if style == "empathetic":
            return 0.95
        elif style == "excited":
            return 1.1
        
        return 1.0
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of voice session"""
        if session_id not in self._active_sessions:
            return {}
        
        session = self._active_sessions[session_id]
        return {
            "duration": (datetime.utcnow() - session["start_time"]).total_seconds(),
            "turn_count": session["turn_count"],
            "languages": list(session["detected_languages"]),
            "voice_profile": session["voice_profile"]
        }
    
    async def cleanup_session(self, session_id: str):
        """Clean up voice session"""
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
            logger.info(f"Cleaned up voice session: {session_id}")