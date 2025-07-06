"""
Voice Streaming with TTS - Building on working STT
Step 1: Add Text-to-Speech capability
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

# Deepgram API key
DEEPGRAM_API_KEY = "36a821d351939023aabad9beeaa68b391caa124a"

app = FastAPI(title="Voice with TTS")

class VoiceSessionWithTTS:
    def __init__(self, websocket: WebSocket, session_id: str):
        self.websocket = websocket
        self.session_id = session_id
        self.deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        self.dg_connection = None
        self.audio_chunks_received = 0
        self.audio_bytes_received = 0
        
    async def initialize(self) -> bool:
        try:
            logger.info("Creating Deepgram STT connection...")
            self.dg_connection = self.deepgram.listen.asyncwebsocket.v("1")
            
            # Register STT handlers
            self.dg_connection.on("open", self.on_open)
            self.dg_connection.on("transcript", self.on_transcript)
            self.dg_connection.on("Results", self.on_results)  # Capital R like in the logs
            self.dg_connection.on("utterance_end", self.on_utterance_end)
            self.dg_connection.on("UtteranceEnd", self.on_utterance_end)  # Also try capital
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
                    "message": "Voice recognition ready - start speaking!",
                    "tts_enabled": True
                })
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Initialize error: {e}", exc_info=True)
            return False
    
    async def on_open(self, *args, **kwargs):
        logger.info("=== DEEPGRAM OPEN EVENT FIRED ===")
    
    async def on_transcript(self, *args, **kwargs):
        logger.info(f"=== TRANSCRIPT EVENT === Args: {args}, Kwargs keys: {list(kwargs.keys())}")
        
        # The event data might be in args[0] or kwargs
        if args and hasattr(args[0], 'channel'):
            result = args[0]
        else:
            result = kwargs.get("result")
        
        if result and hasattr(result, 'channel') and result.channel:
            alternatives = result.channel.alternatives
            if alternatives and len(alternatives) > 0:
                transcript = alternatives[0].transcript
                logger.info(f"Transcript text: '{transcript}', is_final: {result.is_final}")
                
                await self.websocket.send_json({
                    "type": "transcript",
                    "text": transcript,
                    "is_final": result.is_final
                })
    
    async def on_results(self, *args, **kwargs):
        """Handle Results event (what Deepgram actually sends)"""
        logger.info(f"=== RESULTS EVENT === Args: {args}, Kwargs keys: {list(kwargs.keys())}")
        
        # Parse the result
        if args and hasattr(args[0], 'channel'):
            result = args[0]
        else:
            result = kwargs.get("result")
            
        if result:
            try:
                # Results structure is different from transcript
                if hasattr(result, 'channel') and result.channel:
                    alternatives = result.channel.alternatives
                    if alternatives and len(alternatives) > 0:
                        transcript = alternatives[0].transcript
                        is_final = result.is_final if hasattr(result, 'is_final') else True
                        
                        logger.info(f"Results text: '{transcript}', is_final: {is_final}")
                        
                        if transcript:  # Only send if there's actual text
                            await self.websocket.send_json({
                                "type": "transcript",
                                "text": transcript,
                                "is_final": is_final
                            })
            except Exception as e:
                logger.error(f"Error parsing results: {e}", exc_info=True)
    
    async def on_utterance_end(self, *args, **kwargs):
        """When user stops speaking, respond with TTS"""
        logger.info("=== UTTERANCE END EVENT ===")
        
        # For now, just send a simple response that we'll convert to speech
        response_text = "I heard you! You can speak again."
        
        # Convert text to speech using Deepgram TTS
        try:
            audio_data = await self.text_to_speech(response_text)
            if audio_data:
                # Send the audio back to client
                await self.websocket.send_json({
                    "type": "tts_audio",
                    "text": response_text,
                    "audio": base64.b64encode(audio_data).decode('utf-8')
                })
                logger.info(f"Sent TTS response: {response_text}")
        except Exception as e:
            logger.error(f"TTS error: {e}")
    
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
        
        logger.info(f"Calling TTS API for: {text}")
        
        # Make synchronous request (we'll make it async later)
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
        <title>Voice with TTS</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
            .status { padding: 20px; margin: 20px 0; border-radius: 10px; }
            .connected { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            button { padding: 15px 30px; font-size: 18px; margin: 10px; }
            #log { background: #f0f0f0; padding: 20px; height: 300px; overflow-y: auto; font-family: monospace; }
            .transcript { margin: 20px 0; padding: 20px; background: #e3f2fd; }
            .tts-response { margin: 20px 0; padding: 20px; background: #e8f5e9; }
        </style>
    </head>
    <body>
        <h1>Voice STT + TTS Test</h1>
        <div class="status" id="status">Click Start to test</div>
        <button onclick="startTest()" id="startBtn">Start Test</button>
        <button onclick="stopTest()" id="stopBtn" disabled>Stop</button>
        <div class="transcript" id="transcript">Transcript will appear here...</div>
        <div class="tts-response" id="ttsResponse">TTS responses will appear here...</div>
        <audio id="audioPlayer" style="display: none;"></audio>
        <div id="log"></div>
        
        <script>
            let ws, stream, audioContext, processor;
            let audioEnabled = false;
            
            // Enable audio on first user interaction
            document.addEventListener('click', function() {
                if (!audioEnabled) {
                    audioEnabled = true;
                    log('Audio playback enabled');
                    // Create and play silent audio to unlock autoplay
                    const audioPlayer = document.getElementById('audioPlayer');
                    audioPlayer.play().catch(() => {});
                }
            });
            
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
                    };
                    
                    ws.onmessage = (e) => {
                        const data = JSON.parse(e.data);
                        log('Message: ' + data.type);
                        
                        if (data.type === 'system' && data.message.includes('ready')) {
                            document.getElementById('status').textContent = 'Ready - Speak now!';
                            log('System ready for audio');
                            startAudioCapture();
                        } else if (data.type === 'transcript') {
                            document.getElementById('transcript').textContent = 
                                (data.is_final ? 'You said: ' : 'Hearing: ') + data.text;
                        } else if (data.type === 'tts_audio') {
                            log('Received TTS audio');
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
                    
                    // Try to play with user gesture context
                    const playPromise = audioPlayer.play();
                    
                    if (playPromise !== undefined) {
                        playPromise
                            .then(() => log('Playing TTS audio'))
                            .catch(e => {
                                log('Error playing audio: ' + e);
                                // Show alert to user
                                if (e.name === 'NotAllowedError') {
                                    log('Browser blocked autoplay - click anywhere on the page to enable audio');
                                    document.getElementById('status').textContent = 'Click anywhere to enable audio';
                                    document.getElementById('status').className = 'status error';
                                }
                            });
                    }
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
    session_id = f"tts_{int(time.time())}"
    logger.info(f"=== NEW SESSION: {session_id} ===")
    
    session = VoiceSessionWithTTS(websocket, session_id)
    
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
    print("\n🔍 Voice with TTS - Step 1")
    print("📍 http://localhost:7777")
    print("\nAdding TTS to working STT implementation")
    print("When you stop speaking, you'll hear a response\n")
    
    uvicorn.run(app, host="0.0.0.0", port=7777, log_level="info")