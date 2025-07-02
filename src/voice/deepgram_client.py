"""
Deepgram client for unified STT + Intelligence + TTS
Captures all insights for ML and personalization
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import websockets
import ssl
import httpx
import structlog
from dataclasses import dataclass, asdict
import os

logger = structlog.get_logger()

@dataclass
class VoiceInsights:
    """Rich insights from voice analysis"""
    transcript: str
    confidence: float
    
    # Audio Intelligence
    sentiment: Optional[str] = None  # positive, negative, neutral
    sentiment_score: Optional[float] = None
    intent: Optional[str] = None
    intent_confidence: Optional[float] = None
    topics: List[str] = None
    entities: List[Dict[str, Any]] = None
    summary: Optional[str] = None
    
    # Speech characteristics
    speaking_rate: Optional[float] = None  # words per minute
    silence_ratio: Optional[float] = None  # proportion of silence
    
    # Custom grocery insights
    urgency_score: Optional[float] = None  # 0-1, derived from sentiment + words
    clarity_score: Optional[float] = None  # How clear the request is
    frustration_indicators: List[str] = None  # ["repeated_words", "rising_tone"]
    
    # Timing
    start_time: float = None
    end_time: float = None
    processing_time: float = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage"""
        return asdict(self)

@dataclass 
class ConversationTurn:
    """Single turn in a conversation"""
    turn_id: str
    speaker: str  # "user" or "assistant"
    insights: Optional[VoiceInsights] = None
    text: Optional[str] = None  # For assistant responses
    timestamp: datetime = None
    
    # ML features
    time_to_speak: Optional[float] = None  # Time before user started speaking
    interruption: bool = False  # Did they interrupt the assistant?
    
class DeepgramClient:
    """Unified Deepgram client for voice commerce"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepgram.com/v1"
        
        # Feature configuration for grocery/commerce
        self.stt_config = {
            "model": "nova-2",  # Best for conversational AI
            "language": "en-US",  # Can be dynamic based on user
            
            # Formatting
            "smart_format": True,  # Formats numbers, currencies
            "punctuate": True,
            "numerals": True,
            "measurements": True,  # Important for "2 gallons", "1 pound"
            
            # Intelligence features
            "sentiment": True,
            "intents": True,
            "topics": True,
            "summarize": "v2",
            "detect_entities": True,
            
            # Speech insights  
            "utterances": True,
            "detect_language": True,
            "filler_words": True,
            "speech_rate": True,
            
            # Streaming
            "interim_results": True,
            "utterance_end_ms": 1000,
            "vad_events": True,
            
            # Custom vocabulary boost
            "keywords": [
                "Organic Valley:3",
                "Horizon:2",
                "Chobani:2", 
                "Kerrygold:2",
                "milk:2",
                "bread:2",
                "sabzi:2",
                "dal:2",
                "ghee:2",
                "paneer:2"
            ]
        }
        
        # TTS configuration
        self.tts_config = {
            "model": "aura-arcas-en",  # Natural male voice
            # "model": "aura-luna-en",  # Natural female voice
        }
        
    async def create_stream_connection(self) -> websockets.WebSocketClientProtocol:
        """Create WebSocket connection for streaming STT"""
        # Build query parameters
        params = "&".join([f"{k}={v}" for k, v in self.stt_config.items() if isinstance(v, (str, bool, int))])
        
        # Handle special parameters
        if self.stt_config.get("keywords"):
            keywords_param = "&".join([f"keywords={kw}" for kw in self.stt_config["keywords"]])
            params += f"&{keywords_param}"
            
        url = f"wss://api.deepgram.com/v1/listen?{params}"
        
        headers = {
            "Authorization": f"Token {self.api_key}"
        }
        
        # Create SSL context that doesn't verify certificates (for development)
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        websocket = await websockets.connect(url, additional_headers=headers, ssl=ssl_context)
        logger.info("Deepgram streaming connection established")
        
        return websocket
    
    async def process_audio_stream(
        self, 
        audio_stream: AsyncGenerator[bytes, None],
        session_id: str
    ) -> AsyncGenerator[VoiceInsights, None]:
        """
        Process streaming audio and yield insights
        """
        websocket = await self.create_stream_connection()
        
        try:
            # Start time for latency tracking
            stream_start = time.time()
            
            # Send audio and receive transcripts concurrently
            async def send_audio():
                async for audio_chunk in audio_stream:
                    await websocket.send(audio_chunk)
                    
                # Send empty message to signal end
                await websocket.send(json.dumps({"type": "FinishStream"}))
            
            # Start sending audio
            send_task = asyncio.create_task(send_audio())
            
            # Process responses
            async for message in websocket:
                try:
                    response = json.loads(message)
                    
                    if response.get("type") == "Results":
                        insights = await self._parse_stt_response(response, stream_start)
                        if insights:
                            yield insights
                            
                    elif response.get("type") == "Metadata":
                        # Process metadata (like detected language)
                        await self._process_metadata(response, session_id)
                        
                    elif response.get("type") == "SpeechStarted":
                        # User started speaking
                        logger.info("Speech started", session_id=session_id)
                        
                    elif response.get("type") == "UtteranceEnd":
                        # Natural pause detected
                        logger.info("Utterance ended", session_id=session_id)
                        
                except Exception as e:
                    logger.error(f"Error processing Deepgram message: {e}")
                    
            await send_task
            
        finally:
            await websocket.close()
    
    async def _parse_stt_response(
        self, 
        response: Dict[str, Any],
        stream_start: float
    ) -> Optional[VoiceInsights]:
        """Parse Deepgram response into VoiceInsights"""
        
        channel = response.get("channel", {})
        alternatives = channel.get("alternatives", [])
        
        if not alternatives:
            return None
            
        best_alt = alternatives[0]
        transcript = best_alt.get("transcript", "").strip()
        
        if not transcript:
            return None
            
        # Extract all the insights
        insights = VoiceInsights(
            transcript=transcript,
            confidence=best_alt.get("confidence", 0.0),
            start_time=stream_start,
            end_time=time.time(),
            processing_time=time.time() - stream_start
        )
        
        # Audio Intelligence data
        if "sentiment" in best_alt:
            sentiment_info = best_alt["sentiment"]
            insights.sentiment = sentiment_info.get("sentiment")
            insights.sentiment_score = sentiment_info.get("confidence")
            
        if "intents" in best_alt:
            intents = best_alt["intents"]
            if intents:
                # Take the highest confidence intent
                best_intent = max(intents, key=lambda x: x.get("confidence", 0))
                insights.intent = best_intent.get("intent")
                insights.intent_confidence = best_intent.get("confidence")
                
        if "topics" in best_alt:
            insights.topics = [t.get("topic") for t in best_alt["topics"]]
            
        if "entities" in best_alt:
            insights.entities = best_alt["entities"]
            
        if "summaries" in best_alt:
            summaries = best_alt["summaries"]
            if summaries:
                insights.summary = summaries[0].get("summary")
        
        # Speech characteristics
        words = best_alt.get("words", [])
        if words:
            # Calculate speaking rate
            duration = words[-1]["end"] - words[0]["start"]
            word_count = len(words)
            insights.speaking_rate = (word_count / duration) * 60 if duration > 0 else 0
            
            # Calculate silence ratio
            total_speech_time = sum(w["end"] - w["start"] for w in words)
            insights.silence_ratio = 1 - (total_speech_time / duration) if duration > 0 else 0
        
        # Custom grocery insights
        insights.urgency_score = self._calculate_urgency(transcript, insights.sentiment)
        insights.clarity_score = self._calculate_clarity(best_alt)
        insights.frustration_indicators = self._detect_frustration(best_alt)
        
        return insights
    
    def _calculate_urgency(self, transcript: str, sentiment: Optional[str]) -> float:
        """Calculate urgency score from transcript and sentiment"""
        urgency_score = 0.0
        
        # Urgency words
        urgency_words = ["need", "urgent", "immediately", "asap", "now", "today", 
                        "running out", "almost out", "last", "emergency"]
        
        transcript_lower = transcript.lower()
        for word in urgency_words:
            if word in transcript_lower:
                urgency_score += 0.2
                
        # Sentiment factor
        if sentiment == "negative":
            urgency_score += 0.3
            
        return min(urgency_score, 1.0)
    
    def _calculate_clarity(self, alternative: Dict[str, Any]) -> float:
        """Calculate how clear/specific the request is"""
        clarity_score = alternative.get("confidence", 0.0)
        
        # Boost for specific entities
        entities = alternative.get("entities", [])
        if entities:
            clarity_score += 0.1 * len(entities)
            
        # Boost for clear intent
        intents = alternative.get("intents", [])
        if intents and intents[0].get("confidence", 0) > 0.8:
            clarity_score += 0.2
            
        return min(clarity_score, 1.0)
    
    def _detect_frustration(self, alternative: Dict[str, Any]) -> List[str]:
        """Detect frustration indicators"""
        indicators = []
        
        words = alternative.get("words", [])
        transcript = alternative.get("transcript", "").lower()
        
        # Repetition detection
        word_list = [w["word"].lower() for w in words]
        if len(word_list) > len(set(word_list)) * 1.5:  # High repetition
            indicators.append("word_repetition")
            
        # Filler words
        filler_count = sum(1 for w in words if w.get("word", "").lower() in ["um", "uh", "like", "you know"])
        if filler_count > len(words) * 0.1:  # More than 10% filler
            indicators.append("high_filler_words")
            
        # Correction patterns
        if any(phrase in transcript for phrase in ["no wait", "i mean", "actually", "sorry"]):
            indicators.append("self_correction")
            
        return indicators
    
    async def _process_metadata(self, metadata: Dict[str, Any], session_id: str):
        """Process metadata like language detection"""
        if "language" in metadata:
            detected_lang = metadata["language"]
            logger.info(f"Language detected: {detected_lang}", session_id=session_id)
            # Could switch language model here if needed
    
    async def synthesize_speech(
        self,
        text: str,
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        Synthesize speech using Deepgram Aura TTS
        """
        url = f"{self.base_url}/speak"
        
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Default voice settings for natural conversation
        if not voice_settings:
            voice_settings = {
                "speed": 1.0,  # Natural speed
                "pitch": 1.0,  # Natural pitch
            }
        
        # Deepgram expects query parameters for TTS, not JSON body
        params = {
            "model": self.tts_config["model"],
            "encoding": "linear16",  # Raw audio
            "container": "wav",      # WAV container
            "sample_rate": 24000
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=headers,
                params=params,
                json={"text": text},  # Text goes in the body
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"TTS error: {response.status_code} - {response.text}")
                raise Exception(f"TTS failed: {response.status_code}")
    
    async def stream_tts(
        self,
        text_stream: AsyncGenerator[str, None],
        voice_settings: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream TTS for real-time response generation
        """
        # For now, using batch TTS
        # TODO: Implement true streaming when Deepgram releases streaming TTS API
        
        full_text = ""
        async for text_chunk in text_stream:
            full_text += text_chunk
            
        audio = await self.synthesize_speech(full_text, voice_settings)
        yield audio