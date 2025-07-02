"""
True conversational voice streaming with minimal latency
Uses WebSocket for bidirectional streaming
"""
import asyncio
import json
import base64
import io
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
from google.cloud import speech_v1
from google.cloud import texttospeech_v1
import numpy as np
from pydub import AudioSegment
import time

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/stream")

class StreamingConversation:
    """Manages streaming conversation with minimal latency"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.is_active = True
        
        # Initialize clients
        self.stt_client = speech_v1.SpeechClient()
        self.tts_client = texttospeech_v1.TextToSpeechClient()
        
        # Streaming config
        self.streaming_config = speech_v1.StreamingRecognitionConfig(
            config=speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code="en-US",
                enable_automatic_punctuation=True,
                model="latest_short"  # Optimized for low latency
            ),
            interim_results=True,  # Get partial results
            single_utterance=True  # Stop after pause
        )
        
        # TTS config for streaming
        self.voice = texttospeech_v1.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Journey-F",  # Natural voice
            ssml_gender=texttospeech_v1.SsmlVoiceGender.FEMALE
        )
        
        self.audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.MP3,
            speaking_rate=1.1  # Slightly faster for natural conversation
        )
        
        # Audio buffer for streaming
        self.audio_queue = asyncio.Queue()
        
    async def handle_connection(self):
        """Main WebSocket handler"""
        await self.websocket.accept()
        logger.info("Streaming conversation started")
        
        try:
            # Send initial greeting
            await self.send_response("Hi! What groceries can I help you find?", initial=True)
            
            # Create tasks for concurrent processing
            receive_task = asyncio.create_task(self.receive_audio())
            process_task = asyncio.create_task(self.process_audio_stream())
            
            # Wait for tasks
            await asyncio.gather(receive_task, process_task)
            
        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        finally:
            self.is_active = False
            await self.websocket.close()
    
    async def receive_audio(self):
        """Receive audio chunks from client"""
        while self.is_active:
            try:
                data = await self.websocket.receive()
                
                if "bytes" in data:
                    # Audio data
                    await self.audio_queue.put(data["bytes"])
                elif "text" in data:
                    # Handle text messages (control)
                    msg = json.loads(data["text"])
                    if msg.get("type") == "end_stream":
                        await self.audio_queue.put(None)  # Signal end
                        
            except WebSocketDisconnect:
                self.is_active = False
                break
            except Exception as e:
                logger.error(f"Receive error: {e}")
                break
    
    async def process_audio_stream(self):
        """Process audio stream with STT"""
        audio_generator = self.audio_generator()
        
        # Start streaming recognition
        responses = self.stt_client.streaming_recognize(
            self.streaming_config,
            audio_generator
        )
        
        # Process responses
        for response in responses:
            if not response.results:
                continue
                
            result = response.results[0]
            
            if result.is_final:
                # Final transcript
                transcript = result.alternatives[0].transcript
                logger.info(f"Final transcript: {transcript}")
                
                # Send transcript to client
                await self.websocket.send_json({
                    "type": "transcript",
                    "text": transcript,
                    "is_final": True
                })
                
                # Process query
                await self.process_query(transcript)
                
            else:
                # Interim result
                transcript = result.alternatives[0].transcript
                await self.websocket.send_json({
                    "type": "transcript",
                    "text": transcript,
                    "is_final": False
                })
    
    def audio_generator(self):
        """Generator for audio chunks"""
        while self.is_active:
            try:
                # Get audio chunk with timeout
                chunk = asyncio.run_coroutine_threadsafe(
                    self.audio_queue.get(),
                    asyncio.get_event_loop()
                ).result(timeout=0.1)
                
                if chunk is None:
                    break
                    
                yield speech_v1.StreamingRecognizeRequest(audio_content=chunk)
                
            except:
                continue
    
    async def process_query(self, query: str):
        """Process the query and send response"""
        start_time = time.time()
        
        try:
            # Import supervisor
            from src.agents.supervisor_optimized import OptimizedSupervisorAgent
            
            # Quick intent detection
            supervisor = OptimizedSupervisorAgent()
            intent_result = await supervisor.analyze_query(
                query=query,
                user_id="voice_user",
                session_id="voice_session"
            )
            
            # Route based on intent
            if intent_result.get("is_general_chat"):
                # Quick response for chat
                response = self._get_chat_response(query)
                await self.send_response(response)
                
            elif intent_result.get("intent") == "product_search":
                # Stream product search results
                await self.stream_search_results(query)
                
            elif intent_result.get("intent") == "add_to_cart":
                # Quick cart response
                product = intent_result.get("entities", {}).get("product", "item")
                response = f"I'll add {product} to your cart."
                await self.send_response(response)
                
            else:
                # Default response
                response = "What groceries are you looking for?"
                await self.send_response(response)
                
            # Log latency
            latency = (time.time() - start_time) * 1000
            logger.info(f"Query processed in {latency:.0f}ms")
            
        except Exception as e:
            logger.error(f"Processing error: {e}")
            await self.send_response("I had trouble understanding that. What groceries do you need?")
    
    async def stream_search_results(self, query: str):
        """Stream search results with voice"""
        # Start with quick acknowledgment
        await self.send_response(f"Looking for {query}...")
        
        # Execute search
        from src.core.graph import search_graph
        from src.utils.id_generator import generate_request_id
        
        initial_state = {
            "query": query,
            "user_id": "voice_user",
            "request_id": generate_request_id(),
            "limit": 3,
            "source": "voice_streaming"
        }
        
        result = await search_graph.ainvoke(initial_state)
        
        if result.get("search_results"):
            products = result["search_results"][:3]
            
            # Build response
            response = f"I found {len(products)} options for {query}. "
            
            for i, product in enumerate(products):
                if i == 0:
                    response += f"Top pick: {product['name']} at ${product['price']:.2f}. "
                else:
                    response += f"Also, {product['name']} for ${product['price']:.2f}. "
            
            response += "Would you like to add any to your cart?"
            
            # Send response with product data
            await self.websocket.send_json({
                "type": "search_results",
                "products": products,
                "query": query
            })
            
            await self.send_response(response)
        else:
            await self.send_response(f"I couldn't find {query}. Try searching for something else?")
    
    async def send_response(self, text: str, initial: bool = False):
        """Send TTS response"""
        try:
            # Generate speech
            synthesis_input = texttospeech_v1.SynthesisInput(text=text)
            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=self.voice,
                audio_config=self.audio_config
            )
            
            # Send audio in chunks for streaming
            audio_data = response.audio_content
            chunk_size = 4096  # 4KB chunks
            
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                await self.websocket.send_bytes(chunk)
                await asyncio.sleep(0.01)  # Small delay for smooth playback
            
            # Send text transcript
            await self.websocket.send_json({
                "type": "assistant_response",
                "text": text,
                "initial": initial
            })
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
    
    def _get_chat_response(self, query: str) -> str:
        """Get quick chat response"""
        query_lower = query.lower()
        
        if any(greeting in query_lower for greeting in ["hello", "hi", "hey"]):
            return "Hi there! What groceries can I help you find today?"
        elif "how are you" in query_lower:
            return "I'm great! Ready to help with your grocery shopping. What do you need?"
        elif "thank" in query_lower:
            return "You're welcome! Anything else you need?"
        elif "bye" in query_lower or "goodbye" in query_lower:
            return "Goodbye! Happy shopping!"
        else:
            return "I can help you find groceries. What are you looking for?"

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming conversation"""
    conversation = StreamingConversation(websocket)
    await conversation.handle_connection()

@router.get("/test")
async def test_streaming():
    """Test endpoint"""
    return {
        "status": "Streaming conversation ready",
        "features": [
            "Bidirectional audio streaming",
            "Interim transcripts",
            "Low latency responses",
            "Natural conversation flow"
        ]
    }