"""
True real-time conversational voice with Deepgram
Captures intent, emotion, urgency, and all voice insights
"""
import asyncio
import json
import base64
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import structlog
import httpx

from src.voice.deepgram_client import DeepgramClient, VoiceInsights
from src.core.graph import search_graph
from src.utils.id_generator import generate_request_id
from src.config.settings import settings
# from src.integrations.voice_event_publisher import VoiceEventPublisher  # TODO: Implement

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice-realtime")

class RealTimeConversation:
    """Manages real-time conversational flow with full insights"""
    
    def __init__(self, session_id: str, websocket: WebSocket):
        self.session_id = session_id
        self.websocket = websocket
        self.deepgram_api_key = settings.deepgram_api_key if hasattr(settings, 'deepgram_api_key') else "317dce244c7355a30a4719db7359de3854e2963c"
        # self.voice_publisher = VoiceEventPublisher()  # TODO: Implement
        
        # Conversation state
        self.conversation_history = []
        self.current_emotion = "neutral"
        self.user_context = {
            "frustration_level": 0,
            "engagement_score": 1.0,
            "preferred_pace": "normal",
            "detected_intents": [],
            "emotional_journey": []
        }
        
        # Deepgram connections
        self.stt_websocket = None
        self.is_speaking = False
        self.pending_response = ""
        
    async def connect_deepgram_stt(self):
        """Connect to Deepgram for Speech-to-Text with Audio Intelligence"""
        url = "wss://api.deepgram.com/v1/listen"
        
        # Enhanced parameters for conversational AI
        params = {
            "model": "nova-2",
            "language": "en-US",
            "smart_format": True,
            "punctuate": True,
            "numerals": True,
            "measurements": True,
            "interim_results": True,
            "utterance_end_ms": 1000,
            "vad_events": True,
            "endpointing": 300,  # Quick response
            
            # Audio Intelligence features
            "sentiment": True,
            "intents": True,
            "topics": True,
            "summarize": "v2",
            "detect_entities": True,
            "detect_language": True,
            
            # Enhanced features
            "diarize": True,  # Speaker detection
            "filler_words": True,
            "profanity_filter": False
        }
        
        # Build URL with params
        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{param_str}"
        
        headers = {
            "Authorization": f"Token {self.deepgram_api_key}"
        }
        
        import websockets
        self.stt_websocket = await websockets.connect(full_url, extra_headers=headers)
        logger.info("Deepgram STT connected with Audio Intelligence")
        
    async def process_audio_stream(self):
        """Main processing loop for audio streaming"""
        try:
            # Connect to Deepgram
            await self.connect_deepgram_stt()
            
            # Send initial greeting
            await self.send_assistant_message(
                "Hi! I'm here to help with your shopping. What are you looking for?",
                emotion="friendly",
                pace="relaxed"
            )
            
            # Process audio concurrently
            await asyncio.gather(
                self.receive_client_audio(),
                self.process_deepgram_responses(),
                return_exceptions=True
            )
            
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": "Connection error occurred"
            })
            
    async def receive_client_audio(self):
        """Receive audio from client and forward to Deepgram"""
        try:
            while True:
                # Receive audio chunk from client
                data = await self.websocket.receive_bytes()
                
                # Forward to Deepgram if not speaking
                if self.stt_websocket and not self.is_speaking:
                    await self.stt_websocket.send(data)
                    
        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Audio receive error: {e}")
            
    async def process_deepgram_responses(self):
        """Process responses from Deepgram with full insights"""
        while self.stt_websocket:
            try:
                message = await self.stt_websocket.recv()
                response = json.loads(message)
                
                if response.get("type") == "Results":
                    await self.handle_transcript_with_insights(response)
                    
                elif response.get("type") == "SpeechStarted":
                    # User started speaking - stop any TTS
                    self.is_speaking = False
                    await self.websocket.send_json({
                        "type": "user_speaking",
                        "status": "started"
                    })
                    
                elif response.get("type") == "UtteranceEnd":
                    # Natural pause detected
                    await self.websocket.send_json({
                        "type": "user_speaking",
                        "status": "paused"
                    })
                    
            except Exception as e:
                logger.error(f"Deepgram processing error: {e}")
                break
                
    async def handle_transcript_with_insights(self, response: Dict):
        """Process transcript with all Audio Intelligence insights"""
        channel = response.get("channel", {})
        alternatives = channel.get("alternatives", [])
        
        if not alternatives:
            return
            
        best_alt = alternatives[0]
        transcript = best_alt.get("transcript", "").strip()
        is_final = response.get("is_final", False)
        
        if not transcript:
            return
            
        # Send interim results for real-time feedback
        if not is_final:
            await self.websocket.send_json({
                "type": "interim_transcript",
                "text": transcript
            })
            return
            
        # Extract comprehensive insights
        insights = VoiceInsights(
            transcript=transcript,
            confidence=best_alt.get("confidence", 0.0),
            sentiment=None,
            intent=None,
            topics=[],
            entities=[]
        )
        
        # Audio Intelligence data
        if "sentiment_info" in best_alt:
            sentiment_data = best_alt["sentiment_info"]
            insights.sentiment = sentiment_data.get("sentiment", "neutral")
            insights.sentiment_score = sentiment_data.get("confidence", 0.0)
            
        if "intent_info" in best_alt:
            intent_data = best_alt["intent_info"]
            if intent_data:
                insights.intent = intent_data.get("intent")
                insights.intent_confidence = intent_data.get("confidence", 0.0)
                
        if "topics_info" in best_alt:
            topics = best_alt["topics_info"].get("topics", [])
            insights.topics = [t.get("topic") for t in topics]
            
        if "entities_info" in best_alt:
            insights.entities = best_alt["entities_info"].get("entities", [])
            
        # Calculate custom insights
        insights.urgency_score = self._calculate_urgency(transcript, insights.sentiment)
        insights.clarity_score = best_alt.get("confidence", 0.0)
        insights.frustration_indicators = self._detect_frustration(best_alt)
        
        # Update user context
        await self.update_user_context(insights)
        
        # TODO: Publish to Pub/Sub for ML
        # await self.voice_publisher.publish_voice_event({
        #     "session_id": self.session_id,
        #     "type": "user_utterance",
        #     "transcript": transcript,
        #     "insights": insights.to_dict(),
        #     "context": self.user_context,
        #     "timestamp": datetime.utcnow().isoformat()
        # })
        
        # Send final transcript with insights
        await self.websocket.send_json({
            "type": "final_transcript",
            "text": transcript,
            "insights": {
                "sentiment": insights.sentiment,
                "intent": insights.intent,
                "urgency": insights.urgency_score,
                "clarity": insights.clarity_score,
                "confidence": insights.confidence
            }
        })
        
        # Process the query
        await self.process_user_query(transcript, insights)
        
    async def update_user_context(self, insights: VoiceInsights):
        """Update user context based on voice insights"""
        # Track emotional journey
        if insights.sentiment:
            self.user_context["emotional_journey"].append({
                "sentiment": insights.sentiment,
                "score": insights.sentiment_score,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        # Update frustration level
        if insights.frustration_indicators:
            self.user_context["frustration_level"] += 0.2
        elif insights.sentiment == "positive":
            self.user_context["frustration_level"] = max(0, self.user_context["frustration_level"] - 0.1)
            
        # Track intents
        if insights.intent:
            self.user_context["detected_intents"].append(insights.intent)
            
        # Adjust preferred pace based on urgency
        if insights.urgency_score > 0.7:
            self.user_context["preferred_pace"] = "fast"
        elif insights.urgency_score < 0.3:
            self.user_context["preferred_pace"] = "relaxed"
            
    async def process_user_query(self, transcript: str, insights: VoiceInsights):
        """Process query with personalized response based on insights"""
        
        # Determine response style based on context
        response_style = self.determine_response_style(insights)
        
        # Quick responses for high urgency
        if insights.urgency_score > 0.8:
            await self.send_assistant_message(
                "I understand this is urgent. Let me find that right away.",
                emotion="concerned",
                pace="fast"
            )
            
        # Search for products
        try:
            initial_state = self.create_search_state(transcript, insights)
            final_state = await search_graph.ainvoke(initial_state)
            products = final_state.get("search_results", [])
            
            # Generate conversational response
            response = await self.generate_natural_response(
                transcript, products, insights, response_style
            )
            
            # Send response with appropriate emotion
            await self.send_assistant_message(
                response["text"],
                emotion=response["emotion"],
                pace=response["pace"],
                products=products[:5] if products else None
            )
            
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            await self.send_assistant_message(
                "I'm having a moment. Could you say that again?",
                emotion="apologetic",
                pace="normal"
            )
            
    def determine_response_style(self, insights: VoiceInsights) -> Dict[str, Any]:
        """Determine how to respond based on user's emotional state"""
        style = {
            "tone": "friendly",
            "verbosity": "normal",
            "emotion": "neutral",
            "pace": "normal"
        }
        
        # Adjust based on sentiment
        if insights.sentiment == "negative":
            style["tone"] = "empathetic"
            style["emotion"] = "concerned"
        elif insights.sentiment == "positive":
            style["tone"] = "enthusiastic"
            style["emotion"] = "happy"
            
        # Adjust based on frustration
        if self.user_context["frustration_level"] > 0.5:
            style["verbosity"] = "concise"
            style["pace"] = "fast"
            style["tone"] = "helpful"
            
        # Adjust based on urgency
        if insights.urgency_score > 0.6:
            style["verbosity"] = "brief"
            style["pace"] = "fast"
            
        return style
        
    async def generate_natural_response(
        self, 
        query: str, 
        products: list, 
        insights: VoiceInsights,
        style: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate natural, conversational response"""
        
        response = {
            "text": "",
            "emotion": style["emotion"],
            "pace": style["pace"]
        }
        
        # No products found
        if not products:
            if self.user_context["frustration_level"] > 0.3:
                response["text"] = f"I'm really sorry, I couldn't find {query}. Let me try searching differently - what specific type are you looking for?"
                response["emotion"] = "apologetic"
            else:
                response["text"] = f"Hmm, I don't see any {query} right now. Would you like me to check for something similar?"
                response["emotion"] = "thoughtful"
            return response
            
        # Found products - vary response based on context
        num_products = len(products)
        
        if style["verbosity"] == "brief":
            # Quick, to the point
            response["text"] = f"Found {num_products} options. "
            top = products[0]
            response["text"] += f"Best match: {top['product_name']} at ${top['price']:.2f}."
            
        elif insights.sentiment == "positive":
            # Enthusiastic
            response["text"] = f"Great choice! I found {num_products} fantastic options for you. "
            response["text"] += self._describe_products_enthusiastic(products[:3])
            
        else:
            # Normal conversational
            response["text"] = f"I found {num_products} {query} options. "
            response["text"] += self._describe_products_natural(products[:3])
            
        return response
        
    def _describe_products_natural(self, products: list) -> str:
        """Natural product description"""
        if len(products) == 1:
            p = products[0]
            return f"{p['product_name']} from {p.get('supplier', 'us')} for ${p['price']:.2f}."
            
        desc = "Here are the top picks: "
        for i, p in enumerate(products):
            if i == len(products) - 1:
                desc += f"and {p['product_name']} at ${p['price']:.2f}."
            else:
                desc += f"{p['product_name']} at ${p['price']:.2f}, "
        return desc
        
    def _describe_products_enthusiastic(self, products: list) -> str:
        """Enthusiastic product description"""
        desc = "You'll love these: "
        for p in products[:2]:
            desc += f"{p['product_name']} is excellent at ${p['price']:.2f}! "
        return desc
        
    async def send_assistant_message(
        self, 
        text: str, 
        emotion: str = "neutral",
        pace: str = "normal",
        products: list = None
    ):
        """Send assistant message with TTS"""
        
        # Update conversation
        self.conversation_history.append({
            "role": "assistant",
            "content": text,
            "emotion": emotion,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Send text response
        await self.websocket.send_json({
            "type": "assistant_message",
            "text": text,
            "emotion": emotion,
            "products": products
        })
        
        # Generate TTS with emotion
        self.is_speaking = True
        
        try:
            # Use Deepgram Aura with voice selection based on emotion
            voice_model = self._select_voice_model(emotion)
            
            # Generate speech
            tts_url = "https://api.deepgram.com/v1/speak"
            params = {
                "model": voice_model,
                "encoding": "linear16",
                "container": "wav",
                "sample_rate": 24000
            }
            
            headers = {
                "Authorization": f"Token {self.deepgram_api_key}",
                "Content-Type": "application/json"
            }
            
            # Adjust speaking rate based on pace
            speed = 1.0
            if pace == "fast":
                speed = 1.2
            elif pace == "relaxed":
                speed = 0.9
                
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    tts_url,
                    params=params,
                    headers=headers,
                    json={
                        "text": text,
                        "speed": speed
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    # Stream audio to client
                    audio_data = response.content
                    
                    # Send in chunks for streaming playback
                    chunk_size = 4096
                    for i in range(0, len(audio_data), chunk_size):
                        chunk = audio_data[i:i + chunk_size]
                        await self.websocket.send_bytes(chunk)
                        await asyncio.sleep(0.01)
                        
        except Exception as e:
            logger.error(f"TTS error: {e}")
            
        finally:
            self.is_speaking = False
            
    def _select_voice_model(self, emotion: str) -> str:
        """Select voice model based on emotion"""
        # Deepgram Aura voices
        voice_map = {
            "friendly": "aura-asteria-en",  # Warm female
            "concerned": "aura-arcas-en",   # Empathetic male
            "happy": "aura-luna-en",        # Cheerful female
            "neutral": "aura-helios-en",    # Professional male
            "apologetic": "aura-stella-en", # Gentle female
            "thoughtful": "aura-orion-en"   # Contemplative male
        }
        
        return voice_map.get(emotion, "aura-helios-en")
        
    def _calculate_urgency(self, transcript: str, sentiment: Optional[str]) -> float:
        """Calculate urgency from voice and text"""
        urgency = 0.0
        
        urgent_phrases = [
            "right now", "immediately", "urgent", "asap", "hurry",
            "running out", "need it today", "emergency", "quickly"
        ]
        
        for phrase in urgent_phrases:
            if phrase in transcript.lower():
                urgency += 0.3
                
        if sentiment == "negative":
            urgency += 0.2
            
        return min(urgency, 1.0)
        
    def _detect_frustration(self, alternative: Dict) -> List[str]:
        """Detect frustration indicators"""
        indicators = []
        
        # Check for repeated words
        words = alternative.get("words", [])
        if words:
            word_list = [w.get("word", "").lower() for w in words]
            if len(set(word_list)) < len(word_list) * 0.7:
                indicators.append("repetition")
                
        # Check for filler words
        filler_words = ["um", "uh", "like", "you know", "I mean"]
        transcript = alternative.get("transcript", "").lower()
        
        filler_count = sum(1 for filler in filler_words if filler in transcript)
        if filler_count > 2:
            indicators.append("high_filler_words")
            
        return indicators
        
    def create_search_state(self, query: str, insights: VoiceInsights) -> Dict:
        """Create search state with voice insights"""
        return {
            "messages": [{
                "role": "human",
                "content": query,
                "tool_calls": None,
                "tool_call_id": None
            }],
            "query": query,
            "request_id": generate_request_id(),
            "timestamp": datetime.utcnow(),
            "alpha_value": 0.5,
            "search_strategy": "hybrid",
            "search_params": {
                "limit": 10,
                "source": "voice"
            },
            "session_id": self.session_id,
            "user_id": "voice_user",
            "source": "voice",
            "voice_context": {
                "sentiment": insights.sentiment,
                "intent": insights.intent,
                "urgency": insights.urgency_score,
                "emotion": self.current_emotion,
                "frustration_level": self.user_context["frustration_level"]
            }
        }

@router.websocket("/stream")
async def streaming_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time conversational AI"""
    await websocket.accept()
    
    session_id = str(uuid.uuid4())
    logger.info(f"Real-time conversation started: {session_id}")
    
    try:
        conversation = RealTimeConversation(session_id, websocket)
        await conversation.process_audio_stream()
        
    except WebSocketDisconnect:
        logger.info(f"Conversation ended: {session_id}")
    except Exception as e:
        logger.error(f"Conversation error: {e}")
        
@router.get("/health")
async def realtime_health():
    """Health check"""
    return {
        "status": "healthy",
        "features": [
            "real-time-streaming",
            "emotion-detection",
            "intent-recognition", 
            "urgency-scoring",
            "natural-tts",
            "conversation-context"
        ]
    }