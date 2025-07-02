"""
Google Voice WebSocket Streaming
Real-time STT and TTS
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google.cloud import speech
from google.cloud import texttospeech
import json
import base64
import asyncio
import structlog
from typing import AsyncGenerator
import queue
import threading

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/google-ws")

class GoogleStreamingSession:
    def __init__(self, websocket: WebSocket, language: str = "en-US"):
        self.websocket = websocket
        self.language = language
        self.stt_client = speech.SpeechClient()
        self.tts_client = texttospeech.TextToSpeechClient()
        self.audio_queue = queue.Queue()
        self.is_streaming = False
        
    async def handle_connection(self):
        """Handle the WebSocket connection"""
        await self.websocket.accept()
        
        # Send welcome message
        await self.websocket.send_json({
            "type": "connected",
            "message": "Connected to Google Voice Streaming"
        })
        
        # Start STT streaming in background
        streaming_task = asyncio.create_task(self.stream_recognition())
        
        try:
            while True:
                # Receive messages from client
                data = await self.websocket.receive_json()
                
                if data["type"] == "audio":
                    # Add audio to queue
                    audio_bytes = base64.b64decode(data["data"])
                    self.audio_queue.put(audio_bytes)
                    
                elif data["type"] == "start_streaming":
                    self.is_streaming = True
                    logger.info("Started streaming")
                    
                elif data["type"] == "stop_streaming":
                    self.is_streaming = False
                    self.audio_queue.put(None)  # Sentinel
                    logger.info("Stopped streaming")
                    
        except WebSocketDisconnect:
            logger.info("Client disconnected")
            self.is_streaming = False
            streaming_task.cancel()
            
    async def stream_recognition(self):
        """Run speech recognition in background"""
        def audio_generator():
            """Generate audio chunks from queue"""
            while True:
                chunk = self.audio_queue.get()
                if chunk is None:
                    break
                yield speech.StreamingRecognizeRequest(audio_content=chunk)
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=48000,
            language_code=self.language,
            enable_automatic_punctuation=True,
        )
        
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,
        )
        
        while True:
            if self.is_streaming and not self.audio_queue.empty():
                try:
                    # Run recognition
                    responses = self.stt_client.streaming_recognize(
                        streaming_config,
                        audio_generator()
                    )
                    
                    # Process responses
                    for response in responses:
                        if not response.results:
                            continue
                            
                        result = response.results[0]
                        if not result.alternatives:
                            continue
                            
                        transcript = result.alternatives[0].transcript
                        confidence = result.alternatives[0].confidence
                        
                        # Send transcript to client
                        await self.websocket.send_json({
                            "type": "transcript",
                            "text": transcript,
                            "is_final": result.is_final,
                            "confidence": confidence
                        })
                        
                        # If final, generate response
                        if result.is_final and transcript:
                            response_text = self.generate_response(transcript)
                            
                            # Generate TTS
                            audio_content = await self.text_to_speech(response_text)
                            
                            # Send response
                            await self.websocket.send_json({
                                "type": "response",
                                "text": response_text,
                                "audio": base64.b64encode(audio_content).decode()
                            })
                            
                except Exception as e:
                    logger.error(f"Recognition error: {e}")
                    await self.websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    
            await asyncio.sleep(0.1)
            
    def generate_response(self, transcript: str) -> str:
        """Generate simple response"""
        text = transcript.lower()
        
        if any(greeting in text for greeting in ["hello", "hi", "hey"]):
            return "Hello! Welcome to LeafLoaf. What groceries are you looking for today?"
        elif "milk" in text:
            return "We have several types of milk available - whole milk, 2%, skim, and plant-based options like oat and almond milk."
        elif "help" in text:
            return "I can help you find groceries, check prices, or add items to your cart. What would you like to do?"
        else:
            return f"I heard: {transcript}. How can I help you with that?"
            
    async def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech"""
        synthesis_input = texttospeech.SynthesisInput(text=text)
        
        voice = texttospeech.VoiceSelectionParams(
            language_code=self.language,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        response = self.tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        return response.audio_content

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket, language: str = "en-US"):
    """WebSocket endpoint for streaming voice"""
    session = GoogleStreamingSession(websocket, language)
    await session.handle_connection()