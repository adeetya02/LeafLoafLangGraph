"""
Voice Streaming with LLM - Building on working STT + TTS
Step 2: Add LLM integration for grocery queries
"""
import asyncio
import json
import os
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import structlog
import requests
import base64

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

# Configure logging
import logging
logging.basicConfig(level=logging.DEBUG)
logger = structlog.get_logger()

# Import the supervisor
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.agents.supervisor_optimized import OptimizedSupervisorAgent

# Deepgram API key
DEEPGRAM_API_KEY = "36a821d351939023aabad9beeaa68b391caa124a"

app = FastAPI(title="Voice with LLM")

class VoiceSessionWithLLM:
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        self.dg_connection = None
        self.audio_chunks_received = 0
        self.audio_bytes_received = 0
        
        # Initialize supervisor
        self.supervisor = OptimizedSupervisorAgent()
        self.user_id = f"voice_user_{session_id}"
        
        # Track conversation
        self.current_utterance = ""
        self.utterance_start_time = None
        self.word_count = 0
        self.speech_duration = 0
        
    async def initialize(self) -> bool:
        try:
            logger.info("Creating Deepgram STT connection...")
            self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")
            
            # Register STT handlers
            self.dg_connection.on("open", self.on_open)
            self.dg_connection.on("transcript", self.on_transcript)
            self.dg_connection.on("Results", self.on_results)
            self.dg_connection.on("utterance_end", self.on_utterance_end)
            self.dg_connection.on("UtteranceEnd", self.on_utterance_end)
            self.dg_connection.on("SpeechStarted", self.on_speech_started)
            self.dg_connection.on("error", self.on_error)
            
            options = LiveOptions(
                model="nova-3",
                language="en-US",
                encoding="linear16",
                sample_rate=16000,
                channels=1,
                smart_format=True,
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True
            )
            
            logger.info("Starting Deepgram connection...")
            success = await self.dg_connection.start(options)
            logger.info(f"Deepgram start result: {success}")
            
            if success:
                await asyncio.sleep(0.5)
                await self.websocket.send_json({
                    "type": "system",
                    "message": "Voice assistant ready! Ask me about groceries.",
                    "llm_enabled": True
                })
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Initialize error: {e}", exc_info=True)
            return False
    
    async def on_open(self, *args, **kwargs):
        logger.info("=== DEEPGRAM OPEN EVENT FIRED ===")
    
    async def on_speech_started(self, *args, **kwargs):
        """Track when speech starts"""
        logger.info("=== SPEECH STARTED ===")
        self.utterance_start_time = time.time()
    
    async def on_transcript(self, *args, **kwargs):
        logger.info(f"=== TRANSCRIPT EVENT ===")
        # Handle if needed
    
    async def on_results(self, *args, **kwargs):
        """Handle Results event with utterance tracking"""
        logger.info(f"=== RESULTS EVENT ===")
        
        # Parse the result
        if args and hasattr(args[0], 'channel'):
            result = args[0]
        else:
            result = kwargs.get("result")
            
        if result:
            try:
                if hasattr(result, 'channel') and result.channel:
                    alternatives = result.channel.alternatives
                    if alternatives and len(alternatives) > 0:
                        transcript = alternatives[0].transcript
                        is_final = result.is_final if hasattr(result, 'is_final') else True
                        
                        # Update current utterance
                        if transcript:
                            self.current_utterance = transcript
                            self.word_count = len(transcript.split())
                            
                            await self.websocket.send_json({
                                "type": "transcript",
                                "text": transcript,
                                "is_final": is_final
                            })
            except Exception as e:
                logger.error(f"Error parsing results: {e}", exc_info=True)
    
    async def on_utterance_end(self, *args, **kwargs):
        """When user stops speaking, process with LLM"""
        logger.info(f"=== UTTERANCE END EVENT === Current: {self.current_utterance}")
        
        if self.current_utterance and len(self.current_utterance.strip()) > 0:
            # Calculate voice metadata
            voice_metadata = self._calculate_voice_metadata()
            
            # Send processing indicator
            await self.websocket.send_json({
                "type": "processing",
                "text": self.current_utterance,
                "voice_metadata": voice_metadata
            })
            
            try:
                # Process with supervisor
                logger.info(f"Processing with supervisor: {self.current_utterance}")
                result = await self.supervisor.analyze_with_voice_context(
                    query=self.current_utterance,
                    user_id=self.user_id,
                    session_id=self.session_id,
                    voice_metadata=voice_metadata
                )
                
                # For now, create a simple response based on intent
                intent = result.get("intent", "unknown")
                confidence = result.get("confidence", 0)
                
                if intent == "greeting":
                    response_text = "Hello! Welcome to LeafLoaf. What groceries can I help you find today?"
                elif intent == "product_search":
                    products = result.get("entities", {}).get("products", [])
                    if products:
                        response_text = f"I'll help you find {', '.join(products)}. Let me search for those items."
                    else:
                        response_text = "I can help you search for products. What are you looking for?"
                elif intent == "add_to_cart":
                    response_text = "I'll add that to your cart. What else do you need?"
                elif intent == "checkout":
                    response_text = "Ready to checkout? I can help you review your cart."
                else:
                    response_text = "I can help you find groceries. What are you looking for?"
                
                logger.info(f"LLM response: {response_text}")
                
                # Convert response to speech
                audio_data = await self.text_to_speech(response_text)
                if audio_data:
                    await self.websocket.send_json({
                        "type": "assistant_response",
                        "text": response_text,
                        "intent": intent,
                        "confidence": confidence,
                        "audio": base64.b64encode(audio_data).decode('utf-8')
                    })
                    
            except Exception as e:
                logger.error(f"LLM processing error: {e}", exc_info=True)
                # Fallback response
                response_text = "I'm sorry, I had trouble understanding that. Could you please repeat?"
                audio_data = await self.text_to_speech(response_text)
                if audio_data:
                    await self.websocket.send_json({
                        "type": "assistant_response",
                        "text": response_text,
                        "error": True,
                        "audio": base64.b64encode(audio_data).decode('utf-8')
                    })
            
            # Reset for next utterance
            self.current_utterance = ""
            self.utterance_start_time = None
            self.word_count = 0
            self.speech_duration = 0
    
    def _calculate_voice_metadata(self):
        """Calculate voice metadata from speech patterns"""
        if self.utterance_start_time and self.utterance_start_time > 0:
            self.speech_duration = time.time() - self.utterance_start_time
        
        # Calculate speaking pace
        if self.speech_duration > 0 and self.word_count > 0:
            words_per_minute = (self.word_count / self.speech_duration) * 60
            
            if words_per_minute > 180:
                pace = "fast"
            elif words_per_minute < 120:
                pace = "slow"
            else:
                pace = "normal"
        else:
            pace = "normal"
        
        # Estimate urgency based on pace and duration
        if pace == "fast" and self.speech_duration < 3:
            urgency = "high"
        elif pace == "slow" and self.speech_duration > 5:
            urgency = "low"
        else:
            urgency = "medium"
        
        return {
            "pace": pace,
            "duration": round(self.speech_duration, 2),
            "word_count": self.word_count,
            "urgency": urgency,
            "emotion": "neutral",
            "volume": "normal"
        }
    
    async def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech using Deepgram TTS API"""
        url = "https://api.deepgram.com/v1/speak"
        
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }
        
        params = {
            "model": "aura-asteria-en",
            "encoding": "mp3"
        }
        
        payload = {"text": text}
        
        logger.info(f"Calling TTS API for: {text[:50]}...")
        
        response = requests.post(url, headers=headers, params=params, json=payload)
        
        if response.status_code == 200:
            logger.info("TTS API returned audio successfully")
            return response.content
        else:
            logger.error(f"TTS API error: {response.status_code} - {response.text}")
            return None
    
    async def on_error(self, *args, **kwargs):
        error = kwargs.get("error")
        logger.error(f"=== DEEPGRAM ERROR === {error}")
        await self.websocket.send_json({
            "type": "error",
            "message": str(error)
        })
    
    async def send_audio(self, audio_data: bytes):
        self.audio_chunks_received += 1
        self.audio_bytes_received += len(audio_data)
        
        if self.audio_chunks_received % 10 == 0:
            logger.info(f"Audio stats: {self.audio_chunks_received} chunks, {self.audio_bytes_received} bytes")
        
        if self.dg_connection:
            await self.dg_connection.send(audio_data)
    
    async def cleanup(self):
        logger.info(f"Cleanup: Received {self.audio_chunks_received} chunks, {self.audio_bytes_received} bytes total")
        if self.dg_connection:
            await self.dg_connection.finish()


@app.get("/")
async def home():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voice Assistant with LLM</title>
        <style>
            body { 
                font-family: -apple-system, Arial, sans-serif; 
                max-width: 900px; 
                margin: 50px auto; 
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 15px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #2c3e50; margin-bottom: 10px; }
            .subtitle { color: #7f8c8d; margin-bottom: 30px; }
            
            .status { 
                padding: 15px 25px; 
                margin: 20px 0; 
                border-radius: 10px;
                text-align: center;
                font-weight: 600;
            }
            .ready { background: #e8f5e9; color: #2e7d32; }
            .connected { background: #d4edda; color: #155724; }
            .processing { background: #fff3cd; color: #856404; }
            .error { background: #f8d7da; color: #721c24; }
            
            button { 
                padding: 15px 30px; 
                font-size: 18px; 
                margin: 10px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
            }
            button:hover { opacity: 0.9; }
            .primary { background: #007bff; color: white; }
            .danger { background: #dc3545; color: white; }
            
            .conversation {
                background: #f8f9fa;
                padding: 20px;
                margin: 20px 0;
                border-radius: 10px;
                height: 400px;
                overflow-y: auto;
            }
            
            .message {
                margin: 10px 0;
                padding: 15px;
                border-radius: 10px;
                animation: fadeIn 0.3s;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .user-message {
                background: #e3f2fd;
                border-left: 4px solid #2196f3;
            }
            
            .assistant-message {
                background: #e8f5e9;
                border-left: 4px solid #4caf50;
            }
            
            .transcript-live {
                background: #fff9c4;
                padding: 20px;
                margin: 20px 0;
                border-radius: 10px;
                font-size: 1.1em;
                min-height: 60px;
            }
            
            .metadata {
                background: #f5f5f5;
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
                font-family: monospace;
                font-size: 0.9em;
            }
            
            #log {
                background: #263238;
                color: #aed581;
                padding: 15px;
                margin: 20px 0;
                border-radius: 8px;
                font-family: monospace;
                font-size: 12px;
                height: 150px;
                overflow-y: auto;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎙️ LeafLoaf Voice Assistant</h1>
            <p class="subtitle">Powered by Deepgram + Gemini Pro</p>
            
            <div class="status ready" id="status">Click Start to begin</div>
            
            <div style="text-align: center;">
                <button class="primary" onclick="startVoice()" id="startBtn">🎤 Start Voice</button>
                <button class="danger" onclick="stopVoice()" id="stopBtn" disabled>⏹️ Stop</button>
            </div>
            
            <div class="transcript-live" id="transcript">
                <span id="transcriptText">Ready to listen...</span>
            </div>
            
            <div class="conversation" id="conversation"></div>
            
            <audio id="audioPlayer" style="display: none;"></audio>
            <div id="log"></div>
        </div>
        
        <script>
            let ws, stream, audioContext, processor;
            let isProcessing = false;
            
            function log(msg) {
                const logDiv = document.getElementById('log');
                const time = new Date().toLocaleTimeString();
                logDiv.innerHTML += time + ': ' + msg + '<br>';
                logDiv.scrollTop = logDiv.scrollHeight;
                console.log(msg);
            }
            
            function addMessage(text, type = 'user', metadata = null) {
                const conversation = document.getElementById('conversation');
                const message = document.createElement('div');
                message.className = `message ${type}-message`;
                
                let content = `<strong>${type === 'user' ? 'You' : 'Assistant'}:</strong> ${text}`;
                if (metadata) {
                    content += `<div class="metadata">${JSON.stringify(metadata, null, 2)}</div>`;
                }
                message.innerHTML = content;
                
                conversation.appendChild(message);
                conversation.scrollTop = conversation.scrollHeight;
            }
            
            async function startVoice() {
                try {
                    log('Getting microphone...');
                    stream = await navigator.mediaDevices.getUserMedia({
                        audio: {
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        }
                    });
                    log('Got microphone');
                    
                    log('Connecting WebSocket...');
                    ws = new WebSocket('ws://localhost:7777/ws');
                    
                    ws.onopen = () => {
                        log('WebSocket connected');
                        document.getElementById('status').textContent = 'Connected - Initializing...';
                        document.getElementById('status').className = 'status connected';
                    };
                    
                    ws.onmessage = (e) => {
                        const data = JSON.parse(e.data);
                        handleMessage(data);
                    };
                    
                    ws.onerror = (e) => {
                        log('WebSocket error: ' + e);
                        document.getElementById('status').textContent = 'Connection error';
                        document.getElementById('status').className = 'status error';
                    };
                    
                    ws.onclose = () => {
                        log('WebSocket closed');
                        stopVoice();
                    };
                    
                } catch (error) {
                    log('Error: ' + error);
                    alert('Please allow microphone access to use voice assistant.');
                }
            }
            
            function startAudioCapture() {
                log('Starting audio capture...');
                
                audioContext = new AudioContext({ sampleRate: 16000 });
                const source = audioContext.createMediaStreamSource(stream);
                processor = audioContext.createScriptProcessor(4096, 1, 1);
                
                let audioPackets = 0;
                processor.onaudioprocess = (e) => {
                    if (ws && ws.readyState === WebSocket.OPEN && !isProcessing) {
                        const inputData = e.inputBuffer.getChannelData(0);
                        
                        // Convert to int16
                        const output = new Int16Array(inputData.length);
                        for (let i = 0; i < inputData.length; i++) {
                            const s = Math.max(-1, Math.min(1, inputData[i]));
                            output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                        }
                        
                        ws.send(output.buffer);
                        audioPackets++;
                        
                        if (audioPackets % 50 === 0) {
                            log(`Sent ${audioPackets} audio packets`);
                        }
                    }
                };
                
                source.connect(processor);
                processor.connect(audioContext.destination);
                log('Audio pipeline connected');
                
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
            }
            
            function playAudio(base64Audio) {
                try {
                    const audioPlayer = document.getElementById('audioPlayer');
                    const audioBlob = base64ToBlob(base64Audio, 'audio/mp3');
                    const audioUrl = URL.createObjectURL(audioBlob);
                    
                    audioPlayer.src = audioUrl;
                    audioPlayer.play()
                        .then(() => {
                            log('Playing assistant response');
                            isProcessing = false;
                        })
                        .catch(e => {
                            log('Error playing audio: ' + e);
                            isProcessing = false;
                        });
                } catch (error) {
                    log('Error in playAudio: ' + error);
                    isProcessing = false;
                }
            }
            
            function base64ToBlob(base64, mimeType) {
                const byteCharacters = atob(base64);
                const byteNumbers = new Array(byteCharacters.length);
                
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                
                const byteArray = new Uint8Array(byteNumbers);
                return new Blob([byteArray], { type: mimeType });
            }
            
            function handleMessage(data) {
                switch(data.type) {
                    case 'system':
                        log('System: ' + data.message);
                        if (data.message.includes('ready')) {
                            document.getElementById('status').textContent = '🎤 Listening...';
                            document.getElementById('status').className = 'status ready';
                            startAudioCapture();
                            addMessage("Voice assistant ready! Try saying 'I need milk and eggs'", 'assistant');
                        }
                        break;
                        
                    case 'transcript':
                        document.getElementById('transcriptText').textContent = data.text || 'Listening...';
                        if (data.is_final && data.text) {
                            addMessage(data.text, 'user');
                        }
                        break;
                        
                    case 'processing':
                        isProcessing = true;
                        document.getElementById('status').textContent = '🤔 Processing...';
                        document.getElementById('status').className = 'status processing';
                        log('Processing with LLM: ' + data.text);
                        break;
                        
                    case 'assistant_response':
                        document.getElementById('status').textContent = '🎤 Listening...';
                        document.getElementById('status').className = 'status ready';
                        
                        const metadata = {
                            intent: data.intent,
                            confidence: data.confidence
                        };
                        addMessage(data.text, 'assistant', metadata);
                        
                        if (data.audio) {
                            playAudio(data.audio);
                        }
                        break;
                        
                    case 'error':
                        log('Error: ' + data.message);
                        document.getElementById('status').textContent = 'Error occurred';
                        document.getElementById('status').className = 'status error';
                        isProcessing = false;
                        break;
                }
            }
            
            function stopVoice() {
                if (processor) processor.disconnect();
                if (audioContext) audioContext.close();
                if (stream) stream.getTracks().forEach(t => t.stop());
                if (ws) ws.close();
                
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                document.getElementById('status').textContent = 'Stopped';
                document.getElementById('status').className = 'status ready';
                document.getElementById('transcriptText').textContent = 'Ready to listen...';
                isProcessing = false;
                
                log('Stopped');
            }
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = f"llm_{int(time.time())}"
    logger.info(f"=== NEW SESSION: {session_id} ===")
    
    session = VoiceSessionWithLLM(websocket, session_id)
    
    try:
        if not await session.initialize():
            logger.error("Failed to initialize")
            await websocket.close()
            return
        
        while True:
            message = await websocket.receive()
            
            if "bytes" in message:
                await session.send_audio(message["bytes"])
            elif "text" in message:
                data = json.loads(message["text"])
                logger.info(f"Control message: {data}")
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await session.cleanup()


if __name__ == "__main__":
    print("\n🚀 Voice with LLM - Step 2")
    print("📍 http://localhost:7777")
    print("\nAdding LLM (Supervisor) to STT + TTS")
    print("Ask about groceries and get intelligent responses\n")
    
    uvicorn.run(app, host="0.0.0.0", port=7777, log_level="info")