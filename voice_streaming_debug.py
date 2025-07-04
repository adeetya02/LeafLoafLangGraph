"""
Debug version of voice streaming with TTS added
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

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "voice-debug-intent"
os.environ["LANGCHAIN_API_KEY"] = "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"

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
)

# Configure logging with more detail
import logging
logging.basicConfig(level=logging.DEBUG)
logger = structlog.get_logger()

# API Keys
DEEPGRAM_API_KEY = "36a821d351939023aabad9beeaa68b391caa124a"
GEMINI_API_KEY = "AIzaSyCdbX90Q337x0dg2MIF2g0id7CMnGQSVgg"

app = FastAPI(title="Voice Debug with TTS + LLM")

class DebugVoiceSession:
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        self.dg_connection = None
        self.audio_chunks_received = 0
        self.audio_bytes_received = 0
        
        # Track conversation for LLM
        self.current_utterance = ""
        self.conversation_history = []
        
        # Voice metadata tracking for native awareness
        self.speech_started_time = None
        self.speech_duration = 0
        self.word_count = 0
        self.speech_pace = "normal"
        self.voice_metadata = {}
        
    async def initialize(self) -> bool:
        try:
            logger.info("Creating Deepgram connection...")
            self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")
            
            # Register handlers - try both ways
            logger.info("Registering event handlers...")
            
            # Method 1: String events
            self.dg_connection.on("open", self.on_open)
            self.dg_connection.on("transcript", self.on_transcript)
            self.dg_connection.on("error", self.on_error)
            
            # Method 2: Also try LiveTranscriptionEvents
            self.dg_connection.on(LiveTranscriptionEvents.Open, self.on_open)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, self.on_transcript)
            
            # Add speech event handlers for voice-native awareness
            self.dg_connection.on("SpeechStarted", self.on_speech_started)
            self.dg_connection.on("utterance_end", self.on_utterance_end)
            self.dg_connection.on("UtteranceEnd", self.on_utterance_end)
            
            # Multi-language options for code-switching
            # Nova-3 supports multilingual with better accuracy
            options = LiveOptions(
                model="nova-3",          # Nova-3 with multilingual
                language="multi",        # Enable code-switching for mixed languages
                encoding="linear16",
                sample_rate=16000,
                channels=1,
                smart_format=True,
                punctuate=True,
                interim_results=True,
                utterance_end_ms=1000,
                vad_events=True,
                endpointing=300,
                # For mixed language scenarios (English + mother tongue)
                # The model will auto-detect and transcribe mixed languages
            )
            
            logger.info("Starting Deepgram connection...")
            success = await self.dg_connection.start(options)
            logger.info(f"Deepgram start result: {success}")
            
            if success:
                # Send a manual ready message since on_open might not fire
                await asyncio.sleep(0.5)  # Give it a moment
                await self.websocket.send_json({
                    "type": "system",
                    "message": "Voice recognition ready - start speaking!",
                    "debug": "Manual ready message sent"
                })
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Initialize error: {e}", exc_info=True)
            return False
    
    async def on_open(self, *args, **kwargs):
        logger.info("=== DEEPGRAM OPEN EVENT FIRED ===")
        await self.websocket.send_json({
            "type": "system",
            "message": "Deepgram connected - ready for audio"
        })
    
    async def on_speech_started(self, *args, **kwargs):
        """Track when speech starts for voice metadata"""
        logger.info("=== SPEECH STARTED EVENT ===")
        self.speech_started_time = time.time()
        self.word_count = 0
        
        await self.websocket.send_json({
            "type": "speech_started",
            "timestamp": time.time()
        })
    
    async def on_transcript(self, *args, **kwargs):
        logger.info(f"=== TRANSCRIPT EVENT FIRED === Args: {args}, Kwargs: {kwargs}")
        result = kwargs.get("result")
        
        if result and result.channel:
            transcript = result.channel.alternatives[0].transcript
            
            # Track the current utterance
            if transcript:
                self.current_utterance = transcript
            
            await self.websocket.send_json({
                "type": "transcript",
                "text": transcript,
                "is_final": result.is_final
            })
    
    async def on_utterance_end(self, *args, **kwargs):
        """Handle utterance end - respond with LLM + TTS"""
        logger.info(f"=== UTTERANCE END EVENT === Current: {self.current_utterance}")
        
        if not self.current_utterance or len(self.current_utterance.strip()) == 0:
            return
        
        try:
            # Get LLM response with intent
            full_response = await self.get_llm_response(self.current_utterance)
            
            # Parse intent from response
            intent = "unknown"
            response_text = full_response
            
            if full_response.startswith("[") and "]" in full_response:
                intent_end = full_response.index("]")
                intent = full_response[1:intent_end]
                response_text = full_response[intent_end + 1:].strip()
            
            logger.info(f"Detected intent: {intent}")
            
            # Send intent to client
            await self.websocket.send_json({
                "type": "intent_detected",
                "intent": intent,
                "utterance": self.current_utterance
            })
            
            # Add to conversation history
            self.conversation_history.append({
                "user": self.current_utterance,
                "assistant": response_text,
                "intent": intent
            })
            
            # Convert to speech
            audio_data = await self.text_to_speech(response_text)
            if audio_data:
                # Send audio back to client
                await self.websocket.send_json({
                    "type": "tts_audio",
                    "text": response_text,
                    "audio": base64.b64encode(audio_data).decode('utf-8'),
                    "intent": intent
                })
                logger.info(f"Sent TTS response: {response_text[:50]}...")
                
            # Reset for next utterance
            self.current_utterance = ""
            
        except Exception as e:
            logger.error(f"Error in utterance_end: {e}", exc_info=True)
    
    async def text_to_speech(self, text: str) -> bytes:
        """Convert text to speech using Deepgram TTS API"""
        url = "https://api.deepgram.com/v1/speak"
        
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # TODO: Add language detection and use appropriate voice
        # For now using English voice, but in production:
        # - Hindi: Use Hindi TTS voice when available
        # - Gujarati: Use Gujarati TTS voice when available
        # - Korean: Use Korean TTS voice when available
        # - Mixed: Use primary language voice or English
        
        params = {
            "model": "aura-asteria-en",  # English voice for now
            "encoding": "mp3"
        }
        
        payload = {"text": text}
        
        logger.info(f"Calling TTS API for: {text}")
        
        # Make synchronous request
        response = requests.post(url, headers=headers, params=params, json=payload)
        
        if response.status_code == 200:
            logger.info("TTS API returned audio successfully")
            return response.content
        else:
            logger.error(f"TTS API error: {response.status_code} - {response.text}")
            return None
    
    async def get_llm_response(self, user_input: str) -> str:
        """Get response from Gemini Pro with intent detection"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={GEMINI_API_KEY}"
        
        # Build conversation context - multilingual aware with intent
        conversation = """You are a helpful multilingual grocery shopping assistant for LeafLoaf. 
You can understand and respond in English, Hindi, Gujarati, Korean, and other languages.
When someone speaks in a specific language, respond in the same language.
Be conversational and friendly. Keep responses short.

IMPORTANT: For EVERY user query, start your response with the intent in square brackets.
Intents are: [greeting], [product_search], [add_to_cart], [view_cart], [checkout], [help], [unknown]

Examples:
User: "Hello"
Assistant: [greeting] Hello! How can I help you with your grocery shopping today?

User: "I need milk and eggs"
Assistant: [product_search] I'll help you find milk and eggs. We have several options available.

User: "Add 2 liters of milk to cart"
Assistant: [add_to_cart] I'll add 2 liters of milk to your cart.

For ethnic groceries, you have deep knowledge of:
- Indian groceries (दाल, पनीर, घी, मसाला)
- Korean groceries (김치, 고추장, 된장)
- And groceries from many other cultures

Mix languages naturally if the user does.\n\n"""
        
        # Add recent history (last 3 exchanges)
        for exchange in self.conversation_history[-3:]:
            conversation += f"User: {exchange['user']}\nAssistant: {exchange['assistant']}\n\n"
        
        conversation += f"User: {user_input}\nAssistant:"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": conversation
                }]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 150,
                "topP": 0.8
            }
        }
        
        logger.info(f"Calling Gemini Pro for: {user_input}")
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                llm_response = data["candidates"][0]["content"]["parts"][0]["text"]
                logger.info(f"Gemini Pro response: {llm_response[:50]}...")
                return llm_response
            else:
                logger.error(f"Unexpected Gemini response: {data}")
                return "I'm having trouble understanding. Could you say that again?"
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "I'm having trouble connecting. Please try again."
    
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
        
        # Log every 10th chunk
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
        <title>Voice Debug</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
            .status { padding: 20px; margin: 20px 0; border-radius: 10px; }
            .connected { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            button { padding: 15px 30px; font-size: 18px; margin: 10px; }
            #log { background: #f0f0f0; padding: 20px; height: 300px; overflow-y: auto; font-family: monospace; }
        </style>
    </head>
    <body>
        <h1>Voice Debug Test with TTS + LLM + Intent</h1>
        <div class="status" id="status">Click Start to test</div>
        <button onclick="startTest()" id="startBtn">Start Test</button>
        <button onclick="stopTest()" id="stopBtn" disabled>Stop</button>
        <div id="transcript" style="margin: 20px 0; padding: 20px; background: #e3f2fd;">
            Transcript will appear here...
        </div>
        <div id="intent" style="margin: 20px 0; padding: 20px; background: #fff3cd; display: none;">
            <strong>Intent:</strong> <span id="intentValue">-</span>
        </div>
        <div id="ttsResponse" style="margin: 20px 0; padding: 20px; background: #e8f5e9; display: none;">
            TTS response will appear here...
        </div>
        <audio id="audioPlayer" style="display: none;"></audio>
        <div id="log"></div>
        
        <script>
            let ws, stream, mediaRecorder, audioContext, processor;
            
            function log(msg) {
                const logDiv = document.getElementById('log');
                const time = new Date().toLocaleTimeString();
                logDiv.innerHTML += time + ': ' + msg + '<br>';
                logDiv.scrollTop = logDiv.scrollHeight;
                console.log(msg);
            }
            
            async function startTest() {
                try {
                    log('Getting microphone...');
                    stream = await navigator.mediaDevices.getUserMedia({audio: true});
                    log('Got microphone');
                    
                    log('Connecting WebSocket...');
                    ws = new WebSocket('ws://localhost:7777/ws');
                    
                    ws.onopen = () => {
                        log('WebSocket connected');
                        document.getElementById('status').textContent = 'Connected - waiting for Deepgram...';
                        document.getElementById('status').className = 'status connected';
                        
                        // Start sending audio immediately
                        startAudioCapture();
                    };
                    
                    ws.onmessage = (e) => {
                        const data = JSON.parse(e.data);
                        log('Message: ' + JSON.stringify(data));
                        
                        if (data.type === 'system' && data.message.includes('ready')) {
                            document.getElementById('status').textContent = 'Ready - Speak now!';
                            log('System ready for audio');
                        } else if (data.type === 'transcript') {
                            document.getElementById('transcript').textContent = 
                                (data.is_final ? 'Final: ' : 'Interim: ') + data.text;
                        } else if (data.type === 'intent_detected') {
                            log('Intent detected: ' + data.intent);
                            document.getElementById('intent').style.display = 'block';
                            document.getElementById('intentValue').textContent = data.intent;
                        } else if (data.type === 'tts_audio') {
                            log('Received TTS audio (intent: ' + data.intent + ')');
                            document.getElementById('ttsResponse').style.display = 'block';
                            document.getElementById('ttsResponse').textContent = 'Assistant: ' + data.text;
                            playAudio(data.audio);
                        }
                    };
                    
                    ws.onerror = (e) => {
                        log('WebSocket error: ' + e);
                    };
                    
                    ws.onclose = () => {
                        log('WebSocket closed');
                        stopTest();
                    };
                    
                } catch (error) {
                    log('Error: ' + error);
                    alert(error);
                }
            }
            
            function startAudioCapture() {
                log('Starting audio capture...');
                
                // Method 1: Using AudioContext (more reliable)
                audioContext = new AudioContext({ sampleRate: 16000 });
                const source = audioContext.createMediaStreamSource(stream);
                processor = audioContext.createScriptProcessor(4096, 1, 1);
                
                let audioPackets = 0;
                processor.onaudioprocess = (e) => {
                    if (ws && ws.readyState === WebSocket.OPEN) {
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
                        .then(() => log('Playing TTS audio'))
                        .catch(e => {
                            log('Error playing audio: ' + e);
                            // Enable audio on user interaction
                            document.addEventListener('click', function enableAudio() {
                                audioPlayer.play();
                                document.removeEventListener('click', enableAudio);
                                log('Audio enabled after click');
                            });
                            log('Click anywhere to enable audio playback');
                        });
                } catch (error) {
                    log('Error in playAudio: ' + error);
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
            
            function stopTest() {
                if (processor) processor.disconnect();
                if (audioContext) audioContext.close();
                if (stream) stream.getTracks().forEach(t => t.stop());
                if (ws) ws.close();
                
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                document.getElementById('status').textContent = 'Stopped';
                log('Stopped');
            }
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = f"debug_{int(time.time())}"
    logger.info(f"=== NEW SESSION: {session_id} ===")
    
    session = DebugVoiceSession(websocket, session_id)
    
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
    print("\n🔍 Voice Debug Server")
    print("📍 http://localhost:7777")
    print("\nThis will help diagnose the audio streaming issue\n")
    
    uvicorn.run(app, host="0.0.0.0", port=7777, log_level="info")