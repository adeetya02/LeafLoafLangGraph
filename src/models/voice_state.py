"""
Voice-native state models for multi-modal supervisor
"""
from typing import TypedDict, Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum

class VoiceMetadata(TypedDict):
    """Extracted voice characteristics for context-aware processing"""
    # Speaking characteristics
    pace: Literal["slow", "normal", "fast"]  # Speaking rate
    volume: Literal["quiet", "normal", "loud"]  # Voice volume
    clarity: Literal["low", "medium", "high"]  # Speech clarity/confidence
    
    # Emotional indicators
    emotion: Literal["neutral", "excited", "frustrated", "confused", "happy", "urgent"]
    stress_level: Literal["relaxed", "normal", "stressed"]
    
    # Conversation flow
    hesitation_count: int  # Number of pauses/hesitations
    interruption: bool  # Did user interrupt?
    
    # Environmental context
    noise_level: Literal["quiet", "moderate", "noisy"]
    
    # Linguistic features
    language_code: str  # Detected language (e.g., "en-US", "es-US", "hi-IN")
    accent_confidence: float  # Confidence in accent detection
    
    # Timing
    duration: float  # Total speech duration in seconds
    speaking_rate: Optional[float]  # Words per minute
    max_pause: Optional[float]  # Longest pause in seconds

class VoiceTranscript(TypedDict):
    """STT transcript with metadata"""
    text: str  # The transcribed text
    confidence: float  # Overall confidence score
    is_final: bool  # Is this a final transcript?
    
    # Alternative interpretations
    alternatives: List[Dict[str, Any]]  # Alternative transcripts with scores
    
    # Word-level details
    words: List[Dict[str, Any]]  # Word timings and confidence
    
    # Language detection
    language_code: str  # Detected language
    language_confidence: float  # Confidence in language detection

class AudioStream(TypedDict):
    """Audio streaming configuration"""
    sample_rate: int  # e.g., 16000
    encoding: str  # e.g., "LINEAR16"
    channels: int  # e.g., 1 (mono)
    chunk_size: int  # Bytes per chunk

class TTSConfig(TypedDict):
    """Text-to-speech configuration"""
    voice_name: str  # e.g., "en-US-Journey-F"
    speaking_rate: float  # 0.25 to 4.0
    pitch: float  # -20.0 to 20.0
    volume_gain_db: float  # -96.0 to 16.0
    
    # Voice style based on context
    style: Literal["normal", "friendly", "professional", "empathetic", "excited"]

class MultiModalInput(TypedDict):
    """Combined multi-modal input"""
    # Text input (typed or from STT)
    text: Optional[str]
    
    # Voice input
    audio_data: Optional[bytes]  # Raw audio if available
    voice_transcript: Optional[VoiceTranscript]  # STT result
    voice_metadata: Optional[VoiceMetadata]  # Voice characteristics
    
    # Visual input (future)
    image_data: Optional[bytes]  # Image if provided
    image_description: Optional[str]  # AI-generated description
    
    # Input modality
    primary_modality: Literal["text", "voice", "image", "mixed"]
    modalities_used: List[str]  # All modalities present

class VoiceSession(TypedDict):
    """Voice conversation session state"""
    session_id: str
    start_time: datetime
    
    # Conversation state
    turn_count: int  # Number of conversation turns
    is_active: bool  # Is conversation ongoing?
    
    # Language preference
    preferred_language: str  # User's preferred language
    detected_languages: List[str]  # All detected languages in session
    
    # Voice profile
    avg_speaking_rate: Optional[float]
    typical_volume: Optional[str]
    typical_emotion: Optional[str]
    
    # Conversation style learned
    prefers_brief_responses: bool
    prefers_confirmations: bool
    cultural_context: Optional[str]  # e.g., "south_asian", "hispanic"

class VoiceResponse(TypedDict):
    """Voice response configuration"""
    # Text response
    text: str
    
    # SSML markup for natural speech
    ssml: Optional[str]
    
    # TTS configuration
    tts_config: TTSConfig
    
    # Response metadata
    response_type: Literal["answer", "clarification", "confirmation", "greeting", "error"]
    requires_user_response: bool
    
    # Audio output
    audio_data: Optional[bytes]  # Generated TTS audio

class ConversationContext(TypedDict):
    """Full conversation context for multi-turn dialogue"""
    # Historical turns
    history: List[Dict[str, Any]]  # Previous turns
    
    # Current context
    current_topic: Optional[str]  # What we're discussing
    pending_clarification: Optional[str]  # What needs clarification
    
    # User state
    user_mood: Optional[str]  # Inferred from voice
    engagement_level: Literal["low", "medium", "high"]
    
    # Task state
    incomplete_tasks: List[str]  # Tasks mentioned but not completed
    confirmed_items: List[Dict[str, Any]]  # Items confirmed for cart

# Extend the existing SearchState with voice capabilities
class VoiceSearchState(TypedDict):
    """Extended state for voice-native processing"""
    # All existing SearchState fields...
    # (imported from existing state)
    
    # Voice-specific fields
    voice_session: Optional[VoiceSession]  # Voice session info
    multi_modal_input: Optional[MultiModalInput]  # Combined inputs
    voice_response: Optional[VoiceResponse]  # Voice output config
    conversation_context: Optional[ConversationContext]  # Multi-turn context
    
    # Audio streaming
    audio_stream_config: Optional[AudioStream]  # Stream configuration
    is_streaming: bool  # Currently streaming audio?
    
    # Voice-driven routing hints
    voice_routing_hints: Dict[str, Any]  # Voice-based routing suggestions
    voice_confidence: float  # Confidence in voice interpretation
    
    # Multi-language support
    target_language: str  # Response language
    translation_needed: bool  # Translate response?
    
    # Accessibility
    accessibility_mode: Optional[str]  # e.g., "voice_only", "slow_speech"