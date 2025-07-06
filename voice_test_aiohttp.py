"""
Voice test using aiohttp for WebSocket connection to Deepgram
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
import os
import uvicorn
import structlog
import aiohttp
import base64

logger = structlog.get_logger()
app = FastAPI(title="Voice Test with aiohttp")

DEEPGRAM_API_KEY = '36a821d351939023aabad9beeaa68b391caa124a'

@app.get("/")
async def home():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voice Assistant - Deepgram Test</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px; 
                margin: 50px auto; 
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 { color: #2c3e50; }
            button { 
                padding: 15px 30px; 
                margin: 10px; 
                font-size: 18px; 
                cursor: pointer;
                border: none;
                border-radius: 5px;
                background: #4CAF50;
                color: white;
                transition: all 0.3s;
            }
            button:hover { background: #45a049; }
            button:disabled { background: #ccc; }
            .status { 
                padding: 15px; 
                margin: 15px 0; 
                border-radius: 5px; 
                font-weight: bold;
                text-align: center;
            }
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
                border-left: 4px solid #2196F3;
            }
            .response {
                background: #e8f5e9;
                padding: 20px;
                margin: 20px 0;
                border-radius: 5px;
                border-left: 4px solid #4CAF50;
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
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .product h3 { color: #2c3e50; margin-top: 0; }
            .product .price { color: #27ae60; font-size: 20px; font-weight: bold; }
            .log { 
                background: #f5f5f5; 
                padding: 15px; 
                margin: 10px 0; 
                border-radius: 5px;
                height: 200px;
                overflow-y: auto;
                font-family: monospace;
                font-size: 12px;
                border: 1px solid #ddd;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 LeafLoaf Voice Assistant</h1>
            <div class="status" id="status">Click "Start Voice" to begin</div>
            
            <div style="text-align: center;">
                <button onclick="startVoice()" id="startBtn">🎤 Start Voice</button>
                <button onclick="stopVoice()" id="stopBtn" disabled>⏹️ Stop Voice</button>
            </div>
            
            <div class="transcript" id="transcript">
                <em>Ready to listen for your grocery needs...</em>
            </div>
            
            <div class="response" id="response" style="display:none;">
                <div id="responseText"></div>
            </div>
            
            <div class="products" id="products"></div>
            
            <details>
                <summary>Debug Log</summary>
                <div class="log" id="log"></div>
            </details>
        </div>
        
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
                    document.getElementById('startBtn').disabled = true;
                    log('Connecting to server...');
                    
                    ws = new WebSocket(`ws://localhost:8003/ws`);
                    
                    ws.onopen = () => {
                        log('Connected to server');
                        document.getElementById('status').textContent = 'Connected - Starting audio...';
                        document.getElementById('status').className = 'status connected';
                        startAudio();
                    };
                    
                    ws.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'transcript') {
                            document.getElementById('transcript').innerHTML = 
                                data.is_final 
                                ? `<strong>You said:</strong> ${data.text}` 
                                : `<em>${data.text}</em>`;
                            if (data.is_final) {
                                log(`Final: ${data.text}`);
                            }
                        } else if (data.type === 'response') {
                            document.getElementById('response').style.display = 'block';
                            document.getElementById('responseText').innerHTML = data.text;
                        } else if (data.type === 'products') {
                            showProducts(data.products);
                        } else if (data.type === 'error') {
                            log(`Error: ${data.message}`);
                            document.getElementById('status').className = 'status error';
                            document.getElementById('status').textContent = 'Error: ' + data.message;
                        } else if (data.type === 'ready') {
                            document.getElementById('status').textContent = '🎤 Listening - Speak now!';
                            document.getElementById('status').className = 'status listening';
                            document.getElementById('stopBtn').disabled = false;
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
                    document.getElementById('startBtn').disabled = false;
                }
            }
            
            async function startAudio() {
                try {
                    stream = await navigator.mediaDevices.getUserMedia({ 
                        audio: {
                            channelCount: 1,
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        } 
                    });
                    
                    log('Got microphone access');
                    
                    audioContext = new (window.AudioContext || window.webkitAudioContext)({
                        sampleRate: 16000
                    });
                    
                    source = audioContext.createMediaStreamSource(stream);
                    processor = audioContext.createScriptProcessor(2048, 1, 1);
                    
                    processor.onaudioprocess = (e) => {
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            const inputData = e.inputBuffer.getChannelData(0);
                            const output = new Int16Array(inputData.length);
                            for (let i = 0; i < inputData.length; i++) {
                                const s = Math.max(-1, Math.min(1, inputData[i]));
                                output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                            }
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
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                log('Stopped');
            }
            
            function showProducts(products) {
                const container = document.getElementById('products');
                container.innerHTML = products.map(p => `
                    <div class="product">
                        <h3>${p.name}</h3>
                        <div class="price">$${p.price.toFixed(2)}</div>
                        <div>${p.category}</div>
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
    session = None
    dg_ws = None
    
    try:
        logger.info("Client connected")
        
        # Send initial greeting
        await websocket.send_json({
            "type": "response",
            "text": "👋 Hello! I'm ready to help you with your grocery shopping. What would you like today?"
        })
        
        # Connect to Deepgram using aiohttp
        dg_url = "wss://api.deepgram.com/v1/listen"
        params = {
            "encoding": "linear16",
            "sample_rate": "16000", 
            "channels": "1",
            "model": "nova-2",
            "language": "en-US",
            "punctuate": "true",
            "interim_results": "true"
        }
        
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}"
        }
        
        logger.info("Connecting to Deepgram...")
        
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                dg_url, 
                headers=headers,
                params=params
            ) as dg_ws:
                logger.info("Connected to Deepgram")
                
                await websocket.send_json({"type": "ready"})
                
                # Handle messages from both client and Deepgram
                async def handle_client():
                    try:
                        while True:
                            # Receive audio data
                            data = await websocket.receive_bytes()
                            # Forward to Deepgram
                            await dg_ws.send_bytes(data)
                    except WebSocketDisconnect:
                        logger.info("Client disconnected")
                    except Exception as e:
                        logger.error(f"Client handler error: {e}")
                        
                async def handle_deepgram():
                    try:
                        async for msg in dg_ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                result = json.loads(msg.data)
                                
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
                                        
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                logger.error(f'Deepgram error: {dg_ws.exception()}')
                                
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
        logger.info("Connection closed")


async def process_transcript(websocket: WebSocket, transcript: str):
    """Process the transcript and send appropriate response"""
    logger.info(f"Processing: {transcript}")
    
    # Simple keyword-based responses for testing
    transcript_lower = transcript.lower()
    
    if any(word in transcript_lower for word in ["hello", "hi", "hey"]):
        await websocket.send_json({
            "type": "response",
            "text": "Hello! What groceries can I help you find today?"
        })
    elif any(word in transcript_lower for word in ["paneer", "ghee", "dal", "masala", "basmati"]):
        await websocket.send_json({
            "type": "response",
            "text": "Great choice! I found these Indian products for you:"
        })
        await websocket.send_json({
            "type": "products",
            "products": [
                {"name": "Fresh Paneer", "price": 7.99, "category": "Indian Dairy"},
                {"name": "Pure Ghee", "price": 12.99, "category": "Indian Dairy"},
                {"name": "Red Lentils (Masoor Dal)", "price": 4.99, "category": "Indian Pantry"},
                {"name": "Basmati Rice", "price": 15.99, "category": "Indian Pantry"}
            ]
        })
    elif any(word in transcript_lower for word in ["kimchi", "gochujang", "tofu", "miso"]):
        await websocket.send_json({
            "type": "response",
            "text": "I found these Asian products for you:"
        })
        await websocket.send_json({
            "type": "products",
            "products": [
                {"name": "Kimchi", "price": 6.99, "category": "Korean"},
                {"name": "Gochujang Paste", "price": 5.99, "category": "Korean"},
                {"name": "Silken Tofu", "price": 3.99, "category": "Asian"},
                {"name": "Miso Paste", "price": 7.99, "category": "Japanese"}
            ]
        })
    elif any(word in transcript_lower for word in ["milk", "eggs", "bread"]):
        await websocket.send_json({
            "type": "response",
            "text": "Here are your everyday essentials:"
        })
        await websocket.send_json({
            "type": "products",
            "products": [
                {"name": "Organic Whole Milk", "price": 5.99, "category": "Dairy"},
                {"name": "Free Range Eggs (Dozen)", "price": 4.99, "category": "Dairy"},
                {"name": "Whole Wheat Bread", "price": 3.99, "category": "Bakery"}
            ]
        })
    else:
        await websocket.send_json({
            "type": "response",
            "text": f"I heard: '{transcript}'. What specific products are you looking for? Try saying 'milk and eggs' or 'paneer and ghee'."
        })


if __name__ == "__main__":
    print("\n🚀 Starting Voice Assistant with aiohttp")
    print("📍 Open http://localhost:8003")
    print("🔗 Using aiohttp for Deepgram WebSocket\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8003)