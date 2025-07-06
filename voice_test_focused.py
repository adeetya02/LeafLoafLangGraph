"""
Focused Voice Test for Core Features
- Voice-native supervisor with dynamic intents
- Deepgram streaming with ethnic products
- Cart operations
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
import os
import uvicorn
import structlog
from datetime import datetime

# Set up environment
os.environ['DEEPGRAM_API_KEY'] = '36a821d351939023aabad9beeaa68b391caa124a'

from src.agents.supervisor_dynamic_intents import DynamicIntentSupervisor
from src.voice.deepgram.client_factory import create_streaming_client
from src.utils.id_generator import generate_request_id

logger = structlog.get_logger()
app = FastAPI(title="Voice Features Test")

# Global instances
supervisor = None
deepgram_client = None
cart_items = {}  # Simple in-memory cart per session


@app.on_event("startup")
async def startup():
    global supervisor, deepgram_client
    
    logger.info("Initializing voice components...")
    
    # Create voice-native supervisor
    supervisor = DynamicIntentSupervisor()
    
    # Create Deepgram streaming client with dynamic intents
    deepgram_client = create_streaming_client()
    
    logger.info("Voice components initialized")


@app.get("/")
async def home():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voice Native Test - Supervisor & Cart</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 1000px; 
                margin: 40px auto; 
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .status { 
                padding: 10px; 
                margin: 10px 0; 
                border-radius: 5px; 
                text-align: center;
                font-weight: bold;
            }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
            .recording { background: #fff3cd; color: #856404; }
            
            button { 
                padding: 12px 24px; 
                font-size: 16px; 
                margin: 5px; 
                cursor: pointer;
                border: none;
                border-radius: 5px;
                transition: all 0.3s;
            }
            .primary { background: #007bff; color: white; }
            .success { background: #28a745; color: white; }
            .danger { background: #dc3545; color: white; }
            .warning { background: #ffc107; color: black; }
            button:hover { opacity: 0.9; }
            button:disabled { opacity: 0.5; cursor: not-allowed; }
            
            .grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin: 20px 0;
            }
            
            .box {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 5px;
                border: 1px solid #dee2e6;
            }
            
            .box h3 { margin-top: 0; }
            
            .intent-box {
                background: #e7f3ff;
                border-color: #b3d9ff;
            }
            
            .cart-box {
                background: #f8f9fa;
                border-color: #dee2e6;
            }
            
            .transcript {
                background: #fff;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border: 1px solid #ddd;
                min-height: 60px;
            }
            
            .cart-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px;
                margin: 5px 0;
                background: white;
                border-radius: 5px;
                border: 1px solid #e0e0e0;
            }
            
            .ethnic-tag {
                background: #ff6b6b;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.85em;
                margin-left: 5px;
            }
            
            .stats {
                font-family: monospace;
                font-size: 0.9em;
                background: #f0f0f0;
                padding: 10px;
                border-radius: 5px;
                margin-top: 10px;
            }
            
            #visualizer {
                height: 60px;
                background: #f0f0f0;
                margin: 10px 0;
                border-radius: 5px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 2px;
            }
            
            .bar {
                width: 4px;
                background: #007bff;
                transition: height 0.1s;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎤 Voice Native Supervisor Test</h1>
            <p>Test voice recognition, dynamic intents, ethnic products, and cart operations</p>
            
            <div class="status disconnected" id="status">Click Connect to start</div>
            
            <div style="text-align: center; margin: 20px 0;">
                <button class="primary" onclick="connect()">Connect</button>
                <button class="danger" onclick="disconnect()" disabled id="disconnectBtn">Disconnect</button>
                <button class="success" onclick="startRecording()" disabled id="recordBtn">🎤 Start Recording</button>
                <button class="warning" onclick="getStats()">📊 Intent Stats</button>
            </div>
            
            <div id="visualizer"></div>
            
            <div class="grid">
                <div class="box intent-box">
                    <h3>🧠 Voice Analysis</h3>
                    <div class="transcript" id="transcript">
                        <em>Speak to see transcription...</em>
                    </div>
                    <div id="intentInfo">
                        <p><strong>Intent:</strong> <span id="intent">-</span></p>
                        <p><strong>Confidence:</strong> <span id="confidence">-</span></p>
                        <p><strong>Entities:</strong> <span id="entities">-</span></p>
                        <p><strong>Voice Metadata:</strong> <span id="voiceMeta">-</span></p>
                    </div>
                    <div class="stats" id="stats" style="display: none;"></div>
                </div>
                
                <div class="box cart-box">
                    <h3>🛒 Cart Operations</h3>
                    <div id="cartItems">
                        <em>Cart is empty</em>
                    </div>
                    <div style="margin-top: 20px;">
                        <strong>Total Items:</strong> <span id="cartCount">0</span><br>
                        <strong>Total Price:</strong> $<span id="cartTotal">0.00</span>
                    </div>
                </div>
            </div>
            
            <div class="box" style="margin-top: 20px;">
                <h3>🧪 Test Scenarios</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 10px;">
                    <div>
                        <h4>Product Search</h4>
                        <button onclick="sendTestQuery('I need organic milk')">Organic Milk</button>
                        <button onclick="sendTestQuery('Show me gluten free bread')">Gluten Free</button>
                        <button onclick="sendTestQuery('I want fresh vegetables')">Vegetables</button>
                    </div>
                    <div>
                        <h4>Ethnic Products</h4>
                        <button onclick="sendTestQuery('I need paneer and ghee')">🇮🇳 Indian</button>
                        <button onclick="sendTestQuery('Get me kimchi and gochujang')">🇰🇷 Korean</button>
                        <button onclick="sendTestQuery('I want tahini and harissa')">🌍 Middle Eastern</button>
                        <button onclick="sendTestQuery('Show me injera bread')">🇪🇹 Ethiopian</button>
                    </div>
                    <div>
                        <h4>Cart Operations</h4>
                        <button onclick="sendTestQuery('Add 2 pounds of paneer to cart')">Add w/ Quantity</button>
                        <button onclick="sendTestQuery('Remove milk from cart')">Remove Item</button>
                        <button onclick="sendTestQuery('Show my cart')">View Cart</button>
                        <button onclick="sendTestQuery('Clear my cart')">Clear Cart</button>
                    </div>
                    <div>
                        <h4>Other Intents</h4>
                        <button onclick="sendTestQuery('Hello how are you')">Greeting</button>
                        <button onclick="sendTestQuery('What deals do you have')">Promotions</button>
                        <button onclick="sendTestQuery('Help me plan dinner')">Planning</button>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            let ws = null;
            let mediaRecorder = null;
            let audioContext = null;
            let analyser = null;
            let isRecording = false;
            let sessionId = null;
            
            // Create audio visualizer
            const visualizer = document.getElementById('visualizer');
            for (let i = 0; i < 50; i++) {
                const bar = document.createElement('div');
                bar.className = 'bar';
                bar.style.height = '2px';
                visualizer.appendChild(bar);
            }
            const bars = visualizer.querySelectorAll('.bar');
            
            function connect() {
                const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${location.host}/ws`);
                
                ws.onopen = () => {
                    console.log('Connected');
                    document.getElementById('status').className = 'status connected';
                    document.getElementById('status').textContent = 'Connected - Ready';
                    document.getElementById('disconnectBtn').disabled = false;
                    document.getElementById('recordBtn').disabled = false;
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    console.log('Received:', data);
                    
                    switch(data.type) {
                        case 'session':
                            sessionId = data.session_id;
                            break;
                            
                        case 'transcript':
                            document.getElementById('transcript').textContent = data.text;
                            break;
                            
                        case 'analysis':
                            displayAnalysis(data);
                            break;
                            
                        case 'cart_update':
                            updateCartDisplay(data.cart);
                            break;
                            
                        case 'stats':
                            displayStats(data.data);
                            break;
                    }
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    updateStatus('Error', 'danger');
                };
                
                ws.onclose = () => {
                    console.log('Disconnected');
                    updateStatus('Disconnected', 'disconnected');
                    document.getElementById('disconnectBtn').disabled = true;
                    document.getElementById('recordBtn').disabled = true;
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                }
                if (mediaRecorder && isRecording) {
                    stopRecording();
                }
            }
            
            async function startRecording() {
                if (isRecording) {
                    stopRecording();
                    return;
                }
                
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ 
                        audio: {
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        } 
                    });
                    
                    // Set up audio context for visualization
                    audioContext = new AudioContext();
                    analyser = audioContext.createAnalyser();
                    const source = audioContext.createMediaStreamSource(stream);
                    source.connect(analyser);
                    analyser.fftSize = 128;
                    
                    // Start visualization
                    visualize();
                    
                    // Notify server we're starting audio
                    ws.send(JSON.stringify({ type: 'start_audio' }));
                    
                    // Use MediaRecorder for audio capture
                    const options = { mimeType: 'audio/webm' };
                    mediaRecorder = new MediaRecorder(stream, options);
                    
                    mediaRecorder.ondataavailable = async (event) => {
                        if (event.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                            // Send audio data as blob
                            event.data.arrayBuffer().then(buffer => {
                                ws.send(buffer);
                            });
                        }
                    };
                    
                    mediaRecorder.start(250); // Send chunks every 250ms
                    isRecording = true;
                    
                    document.getElementById('recordBtn').textContent = '⏹️ Stop Recording';
                    document.getElementById('recordBtn').className = 'danger';
                    updateStatus('Recording...', 'recording');
                    
                } catch (error) {
                    console.error('Error accessing microphone:', error);
                    alert('Failed to access microphone: ' + error.message);
                }
            }
            
            function stopRecording() {
                if (mediaRecorder && isRecording) {
                    mediaRecorder.stop();
                    mediaRecorder.stream.getTracks().forEach(track => track.stop());
                    mediaRecorder = null;
                }
                
                if (audioContext) {
                    audioContext.close();
                    audioContext = null;
                }
                
                // Notify server we're stopping audio
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'stop_audio' }));
                }
                
                isRecording = false;
                document.getElementById('recordBtn').textContent = '🎤 Start Recording';
                document.getElementById('recordBtn').className = 'success';
                updateStatus('Connected - Ready', 'connected');
                
                // Reset visualizer
                bars.forEach(bar => bar.style.height = '2px');
            }
            
            function visualize() {
                if (!isRecording || !analyser) return;
                
                const dataArray = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(dataArray);
                
                bars.forEach((bar, i) => {
                    const value = dataArray[Math.floor(i * dataArray.length / bars.length)];
                    bar.style.height = Math.max(2, (value / 255) * 50) + 'px';
                });
                
                requestAnimationFrame(visualize);
            }
            
            function sendTestQuery(text) {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({
                        type: 'test_query',
                        text: text
                    }));
                } else {
                    alert('Not connected! Click Connect first.');
                }
            }
            
            function displayAnalysis(data) {
                document.getElementById('intent').textContent = data.intent || '-';
                document.getElementById('confidence').textContent = 
                    data.confidence ? (data.confidence * 100).toFixed(1) + '%' : '-';
                
                // Display entities
                if (data.entities && Object.keys(data.entities).length > 0) {
                    const entities = data.entities;
                    let entityText = '';
                    if (entities.products && entities.products.length > 0) {
                        entityText += 'Products: ' + entities.products.join(', ');
                    }
                    if (entities.quantities && Object.keys(entities.quantities).length > 0) {
                        entityText += ' | Quantities: ' + JSON.stringify(entities.quantities);
                    }
                    document.getElementById('entities').textContent = entityText || 'None';
                } else {
                    document.getElementById('entities').textContent = 'None';
                }
                
                // Display voice metadata
                if (data.voice_metadata) {
                    const meta = data.voice_metadata;
                    document.getElementById('voiceMeta').textContent = 
                        `Pace: ${meta.pace}, Emotion: ${meta.emotion}`;
                }
            }
            
            function updateCartDisplay(cart) {
                const cartDiv = document.getElementById('cartItems');
                const items = cart.items || [];
                
                if (items.length === 0) {
                    cartDiv.innerHTML = '<em>Cart is empty</em>';
                } else {
                    cartDiv.innerHTML = items.map(item => `
                        <div class="cart-item">
                            <div>
                                <strong>${item.name}</strong>
                                ${item.is_ethnic ? '<span class="ethnic-tag">Ethnic</span>' : ''}
                                <br>
                                <small>Qty: ${item.quantity} ${item.unit || ''} @ $${item.price}/ea</small>
                            </div>
                            <div>$${(item.quantity * item.price).toFixed(2)}</div>
                        </div>
                    `).join('');
                }
                
                document.getElementById('cartCount').textContent = cart.total_items || 0;
                document.getElementById('cartTotal').textContent = cart.total_price?.toFixed(2) || '0.00';
            }
            
            function getStats() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'get_stats' }));
                } else {
                    alert('Not connected!');
                }
            }
            
            function displayStats(stats) {
                const statsDiv = document.getElementById('stats');
                statsDiv.style.display = 'block';
                statsDiv.innerHTML = `
                    <strong>Intent Learning Stats:</strong><br>
                    Total Observations: ${stats.total_observations}<br>
                    Unique Intents: ${stats.unique_intents}<br>
                    New Intents: ${stats.new_intents_count}<br>
                    <br>
                    <strong>Intent Distribution:</strong><br>
                    ${Object.entries(stats.intent_counts)
                        .map(([intent, count]) => `${intent}: ${count}`)
                        .join('<br>')}
                `;
            }
            
            function updateStatus(text, className) {
                const status = document.getElementById('status');
                status.textContent = text;
                status.className = 'status ' + className;
            }
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = generate_request_id()
    cart_items[session_id] = []
    
    # Send session info
    await websocket.send_json({
        "type": "session",
        "session_id": session_id
    })
    
    logger.info(f"WebSocket session started: {session_id}")
    
    try:
        # For tracking Deepgram connection
        deepgram_connected = False
        
        while True:
            # Receive either text (JSON) or binary (audio) data
            message = await websocket.receive()
            
            if "bytes" in message:
                # Audio data - would send to Deepgram here
                # For now, simulate transcription
                pass
                
            elif "text" in message:
                # JSON control message
                data = json.loads(message["text"])
                msg_type = data.get("type")
                
                if msg_type == "test_query":
                    # Simulate a voice query for testing
                    query = data.get("text", "")
                    
                    # Send transcript
                    await websocket.send_json({
                        "type": "transcript",
                        "text": query
                    })
                    
                    # Analyze with supervisor
                    voice_metadata = {
                        "pace": "normal",
                        "emotion": "neutral",
                        "urgency": "medium",
                        "volume": "normal"
                    }
                    
                    result = await supervisor.analyze_with_voice_context(
                        query=query,
                        voice_metadata=voice_metadata,
                        memory_context={"session_id": session_id}
                    )
                    
                    # Send analysis
                    await websocket.send_json({
                        "type": "analysis",
                        "intent": result.get("intent"),
                        "confidence": result.get("confidence"),
                        "entities": result.get("entities", {}),
                        "voice_metadata": voice_metadata,
                        "search_alpha": result.get("search_alpha", 0.5)
                    })
                    
                    # Handle cart operations
                    await handle_cart_operation(
                        websocket, session_id, query, result
                    )
                    
                    # Feed to Deepgram learner
                    await deepgram_client.observe_supervisor_intent(
                        transcript=query,
                        intent=result["intent"],
                        confidence=result["confidence"]
                    )
                    
                elif msg_type == "get_stats":
                    # Get learning statistics
                    supervisor_stats = await supervisor.export_learned_intents()
                    
                    await websocket.send_json({
                        "type": "stats",
                        "data": {
                            "total_observations": supervisor_stats["total_observations"],
                            "unique_intents": len(supervisor_stats["intent_statistics"]),
                            "intent_counts": supervisor_stats["intent_statistics"],
                            "new_intents_count": len(supervisor_stats["discovered_intents"])
                        }
                    })
                    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        if session_id in cart_items:
            del cart_items[session_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


async def handle_cart_operation(websocket, session_id, query, analysis):
    """Handle cart operations based on intent"""
    intent = analysis.get("intent", "")
    entities = analysis.get("entities", {})
    
    cart = cart_items.get(session_id, [])
    
    # Check for cart-related intents
    if "cart" in intent.lower() or "add" in intent.lower():
        # Extract products and quantities
        products = entities.get("products", [])
        quantities = entities.get("quantities", {})
        
        # Add items to cart
        for product in products:
            # Check if it's an ethnic product
            is_ethnic = any(ethnic in product.lower() for ethnic in [
                "paneer", "ghee", "dal", "kimchi", "gochujang", 
                "tahini", "harissa", "injera", "miso", "tofu"
            ])
            
            quantity = quantities.get(product, 1)
            
            cart.append({
                "name": product.title(),
                "quantity": quantity,
                "unit": "unit",
                "price": 5.99,  # Mock price
                "is_ethnic": is_ethnic
            })
        
        cart_items[session_id] = cart
        
    elif "remove" in intent.lower():
        # Remove items from cart
        products = entities.get("products", [])
        for product in products:
            cart = [item for item in cart if product.lower() not in item["name"].lower()]
        cart_items[session_id] = cart
        
    elif "clear" in intent.lower() and "cart" in query.lower():
        # Clear cart
        cart_items[session_id] = []
        cart = []
    
    # Calculate totals
    total_items = sum(item["quantity"] for item in cart)
    total_price = sum(item["quantity"] * item["price"] for item in cart)
    
    # Send cart update
    await websocket.send_json({
        "type": "cart_update",
        "cart": {
            "items": cart,
            "total_items": total_items,
            "total_price": total_price
        }
    })


if __name__ == "__main__":
    print("\n🚀 Starting Voice Native Test Server")
    print("📍 Open http://localhost:8000 in your browser")
    print("\n🎯 Focus Areas:")
    print("  1. Voice-native supervisor with dynamic intents")
    print("  2. Deepgram streaming (simulated)")
    print("  3. Ethnic product recognition")
    print("  4. Cart operations through voice")
    print("\n🔗 LangSmith: https://smith.langchain.com\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)