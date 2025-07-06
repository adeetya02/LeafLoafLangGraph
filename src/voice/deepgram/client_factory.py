"""
Factory for creating Deepgram clients with dynamic intent support
"""
import os
from typing import Optional, Literal
from src.voice.deepgram.streaming_client_with_intents import DeepgramStreamingClientWithIntents
from src.voice.deepgram.conversational_client_with_intents import DeepgramConversationalClientWithIntents
from src.voice.deepgram.nova3_client_with_intents import DeepgramNova3ClientWithIntents
import structlog

logger = structlog.get_logger()

ClientType = Literal["streaming", "conversational", "nova3"]


def create_deepgram_client(
    client_type: ClientType = "streaming",
    api_key: Optional[str] = None,
    enable_dynamic_intents: bool = True
):
    """
    Factory function to create Deepgram clients with dynamic intent support
    
    Args:
        client_type: Type of client - "streaming", "conversational", or "nova3"
        api_key: Deepgram API key (defaults to env var)
        enable_dynamic_intents: Whether to enable dynamic intent learning
        
    Returns:
        Configured Deepgram client with intent support
    """
    api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
    
    if not api_key:
        raise ValueError("Deepgram API key not provided and DEEPGRAM_API_KEY env var not set")
    
    logger.info(f"Creating Deepgram {client_type} client (dynamic_intents: {enable_dynamic_intents})")
    
    if client_type == "streaming":
        return DeepgramStreamingClientWithIntents(api_key)
    elif client_type == "conversational":
        return DeepgramConversationalClientWithIntents(api_key)
    elif client_type == "nova3":
        return DeepgramNova3ClientWithIntents(api_key)
    else:
        raise ValueError(f"Unknown client type: {client_type}")


# Convenience functions for specific client types
def create_streaming_client(api_key: Optional[str] = None) -> DeepgramStreamingClientWithIntents:
    """Create a streaming STT client with dynamic intents"""
    return create_deepgram_client("streaming", api_key)


def create_conversational_client(api_key: Optional[str] = None) -> DeepgramConversationalClientWithIntents:
    """Create a conversational (STT+TTS) client with dynamic intents"""
    return create_deepgram_client("conversational", api_key)


def create_nova3_client(api_key: Optional[str] = None) -> DeepgramNova3ClientWithIntents:
    """Create a Nova-3 client with dynamic intents and ethnic product support"""
    return create_deepgram_client("nova3", api_key)