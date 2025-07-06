"""
Production-ready Deepgram Nova-3 client with dynamic intent support
Built incrementally with proper error handling and audio intelligence
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveOptions,
    LiveTranscriptionEvents,
    LiveResultResponse
)
from src.voice.deepgram.base_client_with_intents import BaseDeepgramClientWithIntents
import structlog

logger = structlog.get_logger()

# Ethnic product vocabulary for grocery shopping
ETHNIC_KEYWORDS = [
    # South Asian
    "paneer:15", "ghee:15", "dal:12", "daal:12", "masala:10",
    "basmati:10", "atta:12", "jaggery:15", "garam masala:12",
    "chapati:12", "roti:12", "naan:10", "lassi:10",
    
    # East Asian  
    "gochujang:15", "kimchi:12", "miso:12", "dashi:15",
    "tofu:10", "wakame:15", "nori:12", "soba:12",
    "udon:12", "edamame:12", "tempeh:12",
    
    # Middle Eastern
    "harissa:15", "zaatar:15", "tahini:12", "sumac:12",
    "labneh:15", "halloumi:12", "falafel:10", "shawarma:12",
    
    # Latin American
    "plantains:10", "yuca:15", "yucca:15", "mole:15",
    "achiote:15", "epazote:18", "queso fresco:12",
    
    # African
    "injera:15", "berbere:15", "fufu:15", "jollof:12"
]


class DeepgramNova3ClientWithIntents(BaseDeepgramClientWithIntents):
    """Production-ready Deepgram Nova-3 client with dynamic intent learning"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        
        # Configure client
        self.deepgram = DeepgramClient(api_key)
        
        # Connection state
        self.connection = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
        
        # Callbacks
        self.transcript_callback = None
        self.error_callback = None
        self.audio_intelligence_callback = None
        
        # Keep-alive task
        self.keepalive_task = None
        
        # Audio validation
        self.last_audio_time = None
        self.audio_timeout = 10  # seconds
        
        # Metrics
        self.recognized_products = set()
        self.sentiment_history = []
        
    async def connect(
        self,
        on_transcript: Callable,
        on_error: Optional[Callable] = None,
        on_audio_intelligence: Optional[Callable] = None,
        options: Optional[Dict[str, Any]] = None,
        enable_intents: bool = True
    ) -> bool:
        """
        Establish connection to Deepgram with dynamic intent support
        """
        try:
            # Store callbacks
            self.transcript_callback = on_transcript
            self.error_callback = on_error
            self.audio_intelligence_callback = on_audio_intelligence
            
            # Create connection
            self.connection = self.deepgram.listen.asyncwebsocket.v("1")
            
            # Set up event handlers
            self.connection.on("open", self._on_open)
            self.connection.on("transcript", self._on_transcript)
            self.connection.on("error", self._on_error)
            self.connection.on("close", self._on_close)
            
            # Configure options with Nova-3
            live_options = LiveOptions(
                # Basic options
                model="nova-3",
                language="en-US",
                encoding="linear16",
                sample_rate=16000,
                channels=1,
                
                # Formatting
                smart_format=True,
                punctuate=True,
                
                # Real-time features
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True,
                
                # Ethnic keywords
                keyterm=ETHNIC_KEYWORDS
            )
            
            # Add dynamic intents if enabled
            if enable_intents:
                # Enable extended intent mode
                live_options.intents = "extended"
                
                # Add custom intents from learner
                if self._current_custom_intents:
                    live_options.custom_intents = self._current_custom_intents
                    logger.info(f"Nova-3: Added {len(self._current_custom_intents)} custom intents")
                
                # Start intent learning
                await self.start_intent_learning()
            
            # Apply custom options
            if options:
                for key, value in options.items():
                    setattr(live_options, key, value)
            
            # Start the connection
            logger.info(f"Attempting to connect to Deepgram Nova-3 (intents: {enable_intents})...")
            success = await self.connection.start(live_options)
            
            if success:
                self.is_connected = True
                self.reconnect_attempts = 0
                self.last_audio_time = time.time()
                
                # Start keep-alive task
                self.keepalive_task = asyncio.create_task(self._keepalive_loop())
                
                logger.info("Successfully connected to Deepgram Nova-3")
                return True
            else:
                raise Exception("Failed to start Deepgram connection")
                
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            await self._handle_connection_error(e)
            return False
    
    async def send_audio(self, audio_data: bytes) -> bool:
        """Send audio data with validation"""
        if not audio_data or len(audio_data) == 0:
            logger.warning("Skipping empty audio data")
            return False
            
        if not self.is_connected or not self.connection:
            logger.warning("Not connected, cannot send audio")
            return False
            
        try:
            await self.connection.send(audio_data)
            self.last_audio_time = time.time()
            return True
            
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            await self._handle_connection_error(e)
            return False
    
    async def update_custom_intents(self) -> bool:
        """Update custom intents dynamically"""
        if not self.connection or not self.is_connected:
            return False
            
        try:
            # Send configuration update
            update_msg = {
                "type": "Configure",
                "config": {
                    "custom_intents": self._current_custom_intents
                }
            }
            
            await self.connection.send(json.dumps(update_msg))
            logger.info(f"Nova-3: Updated custom intents dynamically: {len(self._current_custom_intents)} patterns")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update custom intents: {e}")
            return False
    
    async def disconnect(self):
        """Gracefully disconnect from Deepgram"""
        logger.info("Disconnecting from Deepgram...")
        
        # Stop intent learning
        await self.stop_intent_learning()
        
        # Cancel keep-alive
        if self.keepalive_task:
            self.keepalive_task.cancel()
            try:
                await self.keepalive_task
            except asyncio.CancelledError:
                pass
        
        # Close connection
        if self.connection:
            try:
                await self.connection.finish()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.connection = None
                self.is_connected = False
        
        logger.info("Disconnected from Deepgram")
    
    async def _keepalive_loop(self):
        """Send keep-alive messages to prevent timeout"""
        while self.is_connected:
            try:
                await asyncio.sleep(8)
                
                if time.time() - self.last_audio_time > self.audio_timeout:
                    logger.warning("No audio received for 10s, sending keep-alive")
                
                if self.connection:
                    keepalive_msg = json.dumps({"type": "KeepAlive"})
                    await self.connection.send(keepalive_msg)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Keep-alive error: {e}")
    
    def _on_open(self, *args, **kwargs):
        """Handle connection open event"""
        logger.info("Deepgram connection opened")
        self.is_connected = True
        
        if self.transcript_callback:
            asyncio.create_task(self.transcript_callback({
                "event": "connection_opened",
                "timestamp": datetime.utcnow().isoformat()
            }))
    
    def _on_transcript(self, *args, **kwargs):
        """Handle transcript with intent detection"""
        result = kwargs.get("result")
        
        if not result or not result.channel:
            return
            
        try:
            alternative = result.channel.alternatives[0]
            transcript = alternative.transcript
            
            # Basic transcript data
            transcript_data = {
                "transcript": transcript,
                "is_final": result.is_final,
                "speech_final": result.speech_final,
                "confidence": alternative.confidence if hasattr(alternative, 'confidence') else 1.0,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Extract intent if available (from Deepgram's extended intent mode)
            if hasattr(alternative, 'intent'):
                transcript_data["intent_info"] = {
                    "intent": alternative.intent,
                    "confidence": alternative.intent_confidence if hasattr(alternative, 'intent_confidence') else None
                }
                logger.debug(f"Deepgram detected intent: {alternative.intent}")
            
            # Process final transcripts
            if result.is_final and transcript:
                # Check for ethnic products
                ethnic_products = self._check_ethnic_products(transcript)
                if ethnic_products:
                    transcript_data["ethnic_products"] = ethnic_products
            
            # Send transcript
            if self.transcript_callback:
                asyncio.create_task(self.transcript_callback(transcript_data))
                
        except Exception as e:
            logger.error(f"Error processing transcript: {e}", exc_info=True)
    
    def _on_error(self, *args, **kwargs):
        """Handle Deepgram errors"""
        error = kwargs.get("error")
        logger.error(f"Deepgram error: {error}")
        
        error_str = str(error)
        if "NET-0001" in error_str:
            logger.error("No audio received timeout - check keep-alive")
        elif "DATA-0000" in error_str:
            logger.error("Audio decoding error - check format")
        
        asyncio.create_task(self._handle_connection_error(error))
    
    def _on_close(self, *args, **kwargs):
        """Handle connection close"""
        logger.info("Deepgram connection closed")
        self.is_connected = False
        
        if self.reconnect_attempts < self.max_reconnect_attempts:
            asyncio.create_task(self._attempt_reconnect())
    
    async def _handle_connection_error(self, error: Exception):
        """Handle connection errors with retry logic"""
        self.is_connected = False
        
        if self.error_callback:
            await self.error_callback(str(error))
        
        if self.reconnect_attempts < self.max_reconnect_attempts:
            await self._attempt_reconnect()
    
    async def _attempt_reconnect(self):
        """Attempt to reconnect with exponential backoff"""
        self.reconnect_attempts += 1
        backoff = min(30, 2 ** self.reconnect_attempts)
        
        logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {backoff}s")
        await asyncio.sleep(backoff)
        
        if self.transcript_callback:
            success = await self.connect(
                self.transcript_callback,
                self.error_callback,
                self.audio_intelligence_callback
            )
            
            if not success:
                logger.error("Reconnection failed")
    
    def _check_ethnic_products(self, transcript: str) -> List[Dict[str, Any]]:
        """Check for ethnic products in transcript"""
        transcript_lower = transcript.lower()
        found = []
        
        for keyword_boost in ETHNIC_KEYWORDS:
            keyword = keyword_boost.split(':')[0]
            boost = int(keyword_boost.split(':')[1])
            
            if keyword.lower() in transcript_lower:
                found.append({
                    "product": keyword,
                    "boost": boost
                })
                self.recognized_products.add(keyword)
        
        return found
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics including intent statistics"""
        base_metrics = {
            "is_connected": self.is_connected,
            "reconnect_attempts": self.reconnect_attempts,
            "recognized_products": list(self.recognized_products),
            "sentiment_average": sum(s["score"] for s in self.sentiment_history) / len(self.sentiment_history) if self.sentiment_history else 0
        }
        
        # Add intent statistics
        intent_stats = self.get_intent_statistics()
        base_metrics.update(intent_stats)
        
        return base_metrics