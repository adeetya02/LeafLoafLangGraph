"""
Working voice test with Deepgram - based on successful patterns
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
import os
import uvicorn
import structlog
import websockets
import base64

logger = structlog.get_logger()
app = FastAPI(title="Working Voice Test")

DEEPGRAM_API_KEY = '36a821d351939023aabad9beeaa68b391caa124a'

@app.get("/")
async def home():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Working Voice Test</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
            button { padding: 15px 25px; margin: 10px; font-size: 18px; cursor: pointer; }
            .status { padding: 15px; margin: 15px 0; border-radius: 5px; font-weight: bold; }
            .connected { background: #d4edda; color: #155724; }
            .listening { background: #fff3cd; color: #856404; }
            .error { background: #f8d7da; color: #721c24; }
            .transcript { 
                background: #e3f2fd; 
                padding: 20px; 
                margin: 20px 0; 
                border-radius: 5px;
                min-height: 100px;
                font-size: 18px;
            }
            .products {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .product {
                background: white;
                padding: 15px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            .log { 
                background: #f5f5f5; 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 5px;
                height: 200px;
                overflow-y: auto;
                font-family: monospace;
                font-size: 12px;
            }
        </style>
    </head>
    <body>
        <h1>🎤 LeafLoaf Voice Assistant</h1>
        <div class="status" id="status">Click "Start Voice" to begin</div>
        
        <button onclick="startVoice()">Start Voice</button>
        <button onclick="stopVoice()">Stop Voice</button>
        
        <div class="transcript" id="transcript">
            <em>Ready to listen...</em>
        </div>
        
        <div class="products" id="products"></div>
        
        <div class="log" id="log"></div>
        
        <script>
            let ws = null;
            let mediaRecorder = null;
            let audioContext = null;
            let processor = null;
            let source = null;
            let stream = null;
            
            function log(msg) {
                const div = document.getElementById('log');
                const time = new Date().toLocaleTimeString();
                div.innerHTML += `${time}: ${msg}<br>`;
                div.scrollTop = div.scrollHeight;
                console.log(msg);
            }
            
            async function startVoice() {
                try {
                    log('Connecting to server...');
                    ws = new WebSocket(`ws://localhost:8002/ws`);
                    
                    ws.onopen = () => {
                        log('Connected to server');
                        document.getElementById('status').textContent = 'Connected - Starting audio...';
                        document.getElementById('status').className = 'status connected';
                        startAudio();
                    };
                    
                    ws.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'transcript') {
                            document.getElementById('transcript').textContent = data.text || 'Listening...';
                            if (data.is_final) {
                                log(`Final transcript: ${data.text}`);
                            }
                        } else if (data.type === 'greeting') {
                            document.getElementById('transcript').innerHTML = 
                                `<strong>${data.text}</strong>`;
                        } else if (data.type === 'products') {
                            showProducts(data.products);
                        } else if (data.type === 'error') {
                            log(`Error: ${data.message}`);
                            document.getElementById('status').className = 'status error';
                            document.getElementById('status').textContent = 'Error: ' + data.message;
                        } else if (data.type === 'ready') {
                            document.getElementById('status').textContent = 'Listening - Speak now!';
                            document.getElementById('status').className = 'status listening';
                        }
                    };
                    
                    ws.onerror = (error) => {
                        log('WebSocket error: ' + error);
                        document.getElementById('status').className = 'status error';
                    };
                    
                    ws.onclose = () => {
                        log('Disconnected from server');
                        document.getElementById('status').textContent = 'Disconnected';
                        document.getElementById('status').className = 'status error';
                        stopVoice();
                    };
                    
                } catch (error) {
                    log('Error: ' + error.message);
                }
            }
            
            async function startAudio() {
                try {
                    // Get microphone
                    stream = await navigator.mediaDevices.getUserMedia({ 
                        audio: {
                            channelCount: 1,
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        } 
                    });
                    
                    log('Got microphone access');
                    
                    // Create audio context for raw PCM
                    audioContext = new (window.AudioContext || window.webkitAudioContext)({
                        sampleRate: 16000
                    });
                    
                    source = audioContext.createMediaStreamSource(stream);
                    processor = audioContext.createScriptProcessor(2048, 1, 1);
                    
                    processor.onaudioprocess = (e) => {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            const inputData = e.inputBuffer.getChannelData(0);
                            
                            // Convert float32 to int16
                            const output = new Int16Array(inputData.length);
                            for (let i = 0; i < inputData.length; i++) {
                                const s = Math.max(-1, Math.min(1, inputData[i]));
                                output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                            }
                            
                            // Send raw binary data
                            ws.send(output.buffer);
                        }
                    };
                    
                    source.connect(processor);
                    processor.connect(audioContext.destination);
                    
                    log('Audio pipeline started');
                    
                } catch (error) {
                    log('Audio error: ' + error.message);
                }
            }
            
            function stopVoice() {
                if (processor) {
                    processor.disconnect();
                    processor = null;
                }
                if (source) {
                    source.disconnect();
                    source = null;
                }
                if (audioContext) {
                    audioContext.close();
                    audioContext = null;
                }
                if (stream) {
                    stream.getTracks().forEach(track => track.stop());
                    stream = null;
                }
                if (ws) {
                    ws.close();
                    ws = null;
                }
                log('Stopped');
            }
            
            function showProducts(products) {
                const container = document.getElementById('products');
                container.innerHTML = products.map(p => `
                    <div class="product">
                        <h3>${p.name}</h3>
                        <p>Price: $${p.price.toFixed(2)}</p>
                        <p>Category: ${p.category}</p>
                    </div>
                `).join('');
            }
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    dg_ws = None
    
    try:
        logger.info("Client connected")
        
        # Send greeting
        await websocket.send_json({
            "type": "greeting",
            "text": "👋 Hello! I'm ready to help you with your grocery shopping. What would you like today?"
        })
        
        # Connect to Deepgram using raw websockets with proper headers
        dg_url = f"wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000&channels=1&model=nova-2&language=en-US&punctuate=true&interim_results=true"
        
        # Create headers with Authorization
        headers = [
            ("Authorization", f"Token {DEEPGRAM_API_KEY}")
        ]
        
        logger.info("Connecting to Deepgram...")
        dg_ws = await websockets.connect(dg_url, subprotocols=[], additional_headers=headers)
        logger.info("Connected to Deepgram")
        
        await websocket.send_json({"type": "ready"})
        
        # Handle messages from both client and Deepgram
        async def handle_client():
            try:
                while True:
                    # Receive audio data
                    data = await websocket.receive_bytes()
                    # Forward to Deepgram
                    if dg_ws:
                        await dg_ws.send(data)
            except WebSocketDisconnect:
                logger.info("Client disconnected")
            except Exception as e:
                logger.error(f"Client handler error: {e}")
                
        async def handle_deepgram():
            try:
                while True:
                    # Receive from Deepgram
                    message = await dg_ws.recv()
                    result = json.loads(message)
                    
                    # Extract transcript
                    if result.get("channel") and result["channel"].get("alternatives"):
                        transcript = result["channel"]["alternatives"][0].get("transcript", "")
                        is_final = result.get("is_final", False)
                        
                        # Send to client
                        await websocket.send_json({
                            "type": "transcript",
                            "text": transcript,
                            "is_final": is_final
                        })
                        
                        # Process final transcripts
                        if is_final and transcript:
                            await process_transcript(websocket, transcript)
                            
            except Exception as e:
                logger.error(f"Deepgram handler error: {e}")
        
        # Run both handlers
        await asyncio.gather(
            handle_client(),
            handle_deepgram()
        )
        
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        if dg_ws:
            await dg_ws.close()
        logger.info("Connection closed")


async def process_transcript(websocket: WebSocket, transcript: str):
    """Process the transcript and send appropriate response"""
    logger.info(f"Processing: {transcript}")
    
    # Simple keyword-based responses for testing
    transcript_lower = transcript.lower()
    
    if any(word in transcript_lower for word in ["hello", "hi", "hey"]):
        await websocket.send_json({
            "type": "greeting",
            "text": "Hello! What groceries can I help you find today?"
        })
    elif any(word in transcript_lower for word in ["paneer", "ghee", "dal", "masala"]):
        await websocket.send_json({
            "type": "products",
            "products": [
                {"name": "Fresh Paneer", "price": 7.99, "category": "Dairy"},
                {"name": "Pure Ghee", "price": 12.99, "category": "Dairy"},
                {"name": "Red Lentils (Dal)", "price": 4.99, "category": "Pantry"}
            ]
        })
    elif any(word in transcript_lower for word in ["milk", "eggs", "bread"]):
        await websocket.send_json({
            "type": "products",
            "products": [
                {"name": "Organic Milk", "price": 5.99, "category": "Dairy"},
                {"name": "Free Range Eggs", "price": 4.99, "category": "Dairy"},
                {"name": "Whole Wheat Bread", "price": 3.99, "category": "Bakery"}
            ]
        })
    else:
        # For any other query, acknowledge it
        await websocket.send_json({
            "type": "greeting",
            "text": f"I heard: '{transcript}'. What products are you looking for?"
        })


if __name__ == "__main__":
    print("\n🚀 Starting Working Voice Test")
    print("📍 Open http://localhost:8002")
    print("🔗 Using direct Deepgram WebSocket connection\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8002)