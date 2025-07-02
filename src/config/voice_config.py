"""
Voice conversation configuration settings
"""
from typing import Dict, Any
import os

# Conversational AI Parameters
VOICE_CONFIG = {
    # Speech Recognition (STT) Settings
    "stt": {
        "model": os.getenv("DEEPGRAM_STT_MODEL", "nova-2"),
        "language": "en-US",
        "encoding": "linear16",
        "sample_rate": 16000,
        "channels": 1,
        "smart_format": True,
        "punctuate": True,
        "interim_results": True,
        "utterance_end_ms": int(os.getenv("VOICE_UTTERANCE_END_MS", "500")),  # Faster end detection
        "vad_events": True,
        "endpointing": int(os.getenv("VOICE_ENDPOINTING_MS", "250")),  # Faster endpointing
        "diarize": False,  # Speaker detection off for single user
        "filler_words": False,  # Remove ums and ahs
        "profanity_filter": False,
        # New conversational parameters
        "speech_final_sensitivity": float(os.getenv("VOICE_SPEECH_FINAL_SENSITIVITY", "0.8")),
        "silence_threshold_ms": int(os.getenv("VOICE_SILENCE_THRESHOLD_MS", "300")),  # Faster response
    },
    
    # Text-to-Speech (TTS) Settings
    "tts": {
        "model": os.getenv("DEEPGRAM_TTS_MODEL", "aura-luna-en"),  # Natural female voice
        # "model": "aura-arcas-en",  # Natural male voice
        "encoding": "linear16",
        "container": "wav",
        "sample_rate": 24000,
        # Voice characteristics
        "speed": float(os.getenv("VOICE_TTS_SPEED", "1.1")),  # Slightly faster
        "pitch": float(os.getenv("VOICE_TTS_PITCH", "1.0")),
        # Streaming settings
        "chunk_size": int(os.getenv("VOICE_TTS_CHUNK_SIZE", "1024")),  # Smaller chunks for streaming
        "enable_ssml": True,  # Support speech markup
    },
    
    # Conversation Flow Settings
    "conversation": {
        # Response timing
        "min_speech_duration_ms": int(os.getenv("VOICE_MIN_SPEECH_MS", "200")),  # Min speech to process
        "max_initial_silence_ms": int(os.getenv("VOICE_MAX_INITIAL_SILENCE_MS", "3000")),
        "inter_word_pause_ms": int(os.getenv("VOICE_INTER_WORD_PAUSE_MS", "150")),
        
        # Interruption handling
        "allow_interruption": os.getenv("VOICE_ALLOW_INTERRUPTION", "true").lower() == "true",
        "interruption_threshold_ms": int(os.getenv("VOICE_INTERRUPTION_THRESHOLD_MS", "100")),
        
        # Response generation
        "streaming_response": os.getenv("VOICE_STREAMING_RESPONSE", "true").lower() == "true",
        "response_chunk_size": int(os.getenv("VOICE_RESPONSE_CHUNK_SIZE", "10")),  # Words per chunk
        "response_delay_ms": int(os.getenv("VOICE_RESPONSE_DELAY_MS", "100")),  # Delay before speaking
        
        # Conversational style
        "use_acknowledgments": os.getenv("VOICE_USE_ACKNOWLEDGMENTS", "true").lower() == "true",
        "acknowledgment_phrases": [
            "I see", "Got it", "Sure", "Alright", "Okay", "Understood",
            "Let me find that", "Looking for", "Searching for"
        ],
        "use_thinking_sounds": os.getenv("VOICE_USE_THINKING_SOUNDS", "false").lower() == "true",
        "thinking_sounds": ["hmm", "let's see", "uh"],
        
        # Personality
        "personality": os.getenv("VOICE_PERSONALITY", "friendly"),  # friendly, professional, casual
        "use_names": os.getenv("VOICE_USE_NAMES", "false").lower() == "true",
        "enthusiasm_level": float(os.getenv("VOICE_ENTHUSIASM_LEVEL", "0.7")),  # 0-1
    },
    
    # Performance Settings
    "performance": {
        "prefetch_common_responses": True,
        "cache_tts_audio": True,
        "max_concurrent_tts": 3,
        "audio_buffer_size": 16384,
        "enable_voice_activity_detection": True,
    }
}

def get_voice_config() -> Dict[str, Any]:
    """Get voice configuration"""
    return VOICE_CONFIG

def get_stt_config() -> Dict[str, Any]:
    """Get STT-specific configuration"""
    return VOICE_CONFIG["stt"]

def get_tts_config() -> Dict[str, Any]:
    """Get TTS-specific configuration"""
    return VOICE_CONFIG["tts"]

def get_conversation_config() -> Dict[str, Any]:
    """Get conversation flow configuration"""
    return VOICE_CONFIG["conversation"]

def update_config(section: str, key: str, value: Any) -> None:
    """Update configuration value at runtime"""
    if section in VOICE_CONFIG and key in VOICE_CONFIG[section]:
        VOICE_CONFIG[section][key] = value
        
def get_acknowledgment_phrase() -> str:
    """Get a random acknowledgment phrase"""
    import random
    conv_config = get_conversation_config()
    if conv_config["use_acknowledgments"] and conv_config["acknowledgment_phrases"]:
        return random.choice(conv_config["acknowledgment_phrases"])
    return ""