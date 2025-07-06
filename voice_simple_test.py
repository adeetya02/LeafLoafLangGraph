"""
Simplified voice test - just connect and transcribe
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
import os
import uvicorn
import structlog
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
import base64

logger = structlog.get_logger()
app = FastAPI(title="Simple Voice Test")

DEEPGRAM_API_KEY = '36a821d351939023aabad9beeaa68b391caa124a'


@app.get("/")
async def home():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Simple Voice Test</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
            button { padding: 10px 20px; margin: 5px; font-size: 16px; cursor: pointer; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .connected { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
            .transcript { 
                background: #e3f2fd; 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 5px;
                min-height: 50px;
            }
            .messages { 
                background: #f5f5f5; 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 5px;
                height: 300px;
                overflow-y: auto;
            }
        </style>
    </head>
    <body>
        <h1>Simple Voice Test</h1>
        <div class="status" id="status">Not connected</div>
        
        <button onclick="connect()">Connect</button>
        <button onclick="startVoice()">Start Voice</button>
        <button onclick="stopVoice()">Stop Voice</button>
        
        <div class="transcript" id="transcript">
            <em>Transcript will appear here...</em>
        </div>
        
        <div class="messages" id="messages"></div>
        
        <script>
            let ws = null;
            let mediaRecorder = null;
            let isRecording = false;
            
            function log(message) {
                const div = document.getElementById('messages');
                div.innerHTML += message + '<br>';
                div.scrollTop = div.scrollHeight;
                console.log(message);
            }
            
            function connect() {
                ws = new WebSocket(`ws://localhost:8000/ws`);
                
                ws.onopen = () => {
                    document.getElementById('status').textContent = 'Connected';
                    document.getElementById('status').className = 'status connected';
                    log('WebSocket connected');
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    log('Received: ' + JSON.stringify(data));
                    
                    if (data.type === 'transcript') {
                        document.getElementById('transcript').textContent = data.text || 'Listening...';
                    }
                };
                
                ws.onerror = (error) => {
                    log('WebSocket error: ' + error);
                    document.getElementById('status').className = 'status error';
                };
                
                ws.onclose = () => {
                    log('WebSocket closed');
                    document.getElementById('status').textContent = 'Disconnected';
                    document.getElementById('status').className = 'status error';
                };
            }
            
            async function startVoice() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ 
                        audio: {
                            channelCount: 1,
                            echoCancellation: true,
                            noiseSuppression: true,
                            sampleRate: 16000
                        } 
                    });
                    
                    log('Got microphone access');
                    
                    // Use audio/webm which is supported by Chrome
                    const mimeType = 'audio/webm;codecs=opus';
                    mediaRecorder = new MediaRecorder(stream, { 
                        mimeType,
                        audioBitsPerSecond: 16000
                    });
                    
                    mediaRecorder.ondataavailable = async (event) => {
                        if (event.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                            // Convert to base64 for easier handling
                            const reader = new FileReader();
                            reader.onload = () => {
                                const base64Audio = reader.result.split(',')[1];
                                ws.send(JSON.stringify({
                                    type: 'audio',
                                    data: base64Audio
                                }));
                            };
                            reader.readAsDataURL(event.data);
                        }
                    };
                    
                    mediaRecorder.start(250); // Send chunks every 250ms
                    isRecording = true;
                    log('Started recording');
                    
                } catch (error) {
                    log('Microphone error: ' + error.message);
                }
            }
            
            function stopVoice() {
                if (mediaRecorder) {
                    mediaRecorder.stop();
                    mediaRecorder.stream.getTracks().forEach(track => track.stop());
                    isRecording = false;
                    log('Stopped recording');
                }
            }
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    dg_connection = None
    
    logger.info("WebSocket connected")
    
    try:
        # Initialize Deepgram
        deepgram = DeepgramClient(DEEPGRAM_API_KEY)
        dg_connection = deepgram.listen.live.v("1")
        
        transcript_queue = asyncio.Queue()
        
        def on_message(self, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if sentence:
                asyncio.create_task(transcript_queue.put(sentence))
        
        def on_error(self, error, **kwargs):
            logger.error(f"Deepgram error: {error}")
        
        dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
        dg_connection.on(LiveTranscriptionEvents.Error, on_error)
        
        # Start with simpler options
        options = LiveOptions(
            model="nova-2",
            language="en-US",
            encoding="linear16",
            sample_rate=16000,
            channels=1
        )
        
        await dg_connection.start(options)
        logger.info("Deepgram connected")
        
        # Process messages
        async def process_audio():
            while True:
                message = await websocket.receive()
                if "text" in message:
                    data = json.loads(message["text"])
                    if data.get("type") == "audio":
                        # Decode base64 audio
                        audio_data = base64.b64decode(data["data"])
                        # Send to Deepgram
                        await dg_connection.send(audio_data)
                        
        async def send_transcripts():
            while True:
                transcript = await transcript_queue.get()
                await websocket.send_json({
                    "type": "transcript",
                    "text": transcript
                })
                
        # Run both tasks
        await asyncio.gather(
            process_audio(),
            send_transcripts()
        )
        
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if dg_connection:
            await dg_connection.finish()


if __name__ == "__main__":
    print("\n🚀 Starting Simple Voice Test")
    print("📍 Open http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)