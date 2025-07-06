"""
Clean Voice Test Server - Auto-detects all products including ethnic
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
import os
import uvicorn
import structlog

# Set up environment
os.environ['DEEPGRAM_API_KEY'] = '36a821d351939023aabad9beeaa68b391caa124a'

from src.agents.supervisor_dynamic_intents import DynamicIntentSupervisor
from src.voice.deepgram.client_factory import create_streaming_client
from src.utils.id_generator import generate_request_id

logger = structlog.get_logger()
app = FastAPI(title="Voice Native Test")

# Global instances
supervisor = None
deepgram_client = None
carts = {}  # Session-based carts

# Ethnic product database (in real app, this would be in Weaviate)
ETHNIC_PRODUCTS = {
    # Indian
    "paneer": {"origin": "Indian", "category": "Dairy", "price": 7.99},
    "ghee": {"origin": "Indian", "category": "Dairy", "price": 12.99},
    "dal": {"origin": "Indian", "category": "Legumes", "price": 4.99},
    "basmati": {"origin": "Indian", "category": "Rice", "price": 15.99},
    "atta": {"origin": "Indian", "category": "Flour", "price": 8.99},
    # Korean
    "kimchi": {"origin": "Korean", "category": "Fermented", "price": 6.99},
    "gochujang": {"origin": "Korean", "category": "Sauce", "price": 5.99},
    # Middle Eastern
    "tahini": {"origin": "Middle Eastern", "category": "Sauce", "price": 8.99},
    "harissa": {"origin": "Middle Eastern", "category": "Sauce", "price": 6.99},
    "zaatar": {"origin": "Middle Eastern", "category": "Spice", "price": 4.99},
    # Ethiopian
    "injera": {"origin": "Ethiopian", "category": "Bread", "price": 3.99},
    "berbere": {"origin": "Ethiopian", "category": "Spice", "price": 7.99},
}


@app.on_event("startup")
async def startup():
    global supervisor, deepgram_client
    
    logger.info("Initializing voice components...")
    supervisor = DynamicIntentSupervisor()
    deepgram_client = create_streaming_client()
    logger.info("Voice components initialized")


@app.get("/")
async def home():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>LeafLoaf Voice - Auto Product Recognition</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 900px; 
                margin: 40px auto; 
                padding: 20px;
                background: #f8f9fa;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            }
            h1 { color: #2c3e50; margin-bottom: 10px; }
            .subtitle { color: #7f8c8d; margin-bottom: 30px; }
            
            .status { 
                padding: 12px 20px; 
                margin: 20px 0; 
                border-radius: 8px; 
                text-align: center;
                font-weight: 600;
                transition: all 0.3s;
            }
            .connected { background: #d4edda; color: #155724; }
            .disconnected { background: #f8d7da; color: #721c24; }
            .recording { 
                background: #fff3cd; 
                color: #856404;
                animation: pulse 1.5s infinite;
            }
            
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }
            
            button { 
                padding: 12px 24px; 
                font-size: 16px; 
                margin: 5px; 
                cursor: pointer;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.2s;
            }
            button:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
            button:active { transform: translateY(0); }
            button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
            
            .primary { background: #007bff; color: white; }
            .success { background: #28a745; color: white; }
            .danger { background: #dc3545; color: white; }
            
            .chat-container {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                height: 400px;
                overflow-y: auto;
            }
            
            .message {
                margin: 10px 0;
                padding: 12px 16px;
                border-radius: 18px;
                max-width: 70%;
                word-wrap: break-word;
            }
            
            .user-message {
                background: #007bff;
                color: white;
                margin-left: auto;
                text-align: right;
            }
            
            .assistant-message {
                background: #e9ecef;
                color: #2c3e50;
            }
            
            .intent-badge {
                display: inline-block;
                background: #6c757d;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.85em;
                margin: 0 4px;
            }
            
            .product-tag {
                display: inline-block;
                background: #17a2b8;
                color: white;
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 0.85em;
                margin: 2px;
            }
            
            .ethnic-tag {
                background: #e91e63;
            }
            
            .cart-summary {
                background: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
            }
            
            .cart-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 0;
                border-bottom: 1px solid #dee2e6;
            }
            
            .cart-item:last-child {
                border-bottom: none;
            }
            
            .input-area {
                display: flex;
                gap: 10px;
                margin-top: 20px;
            }
            
            .input-area input {
                flex: 1;
                padding: 12px 16px;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                font-size: 16px;
            }
            
            .input-area input:focus {
                outline: none;
                border-color: #007bff;
            }
            
            .stats {
                background: #f0f0f0;
                padding: 15px;
                border-radius: 8px;
                font-family: monospace;
                font-size: 0.9em;
                margin-top: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛒 LeafLoaf Voice Assistant</h1>
            <p class="subtitle">Speak naturally - I understand all products including ethnic groceries</p>
            
            <div class="status disconnected" id="status">Click Connect to start</div>
            
            <div style="text-align: center;">
                <button class="primary" onclick="connect()" id="connectBtn">Connect</button>
                <button class="danger" onclick="disconnect()" disabled id="disconnectBtn">Disconnect</button>
                <button class="success" onclick="toggleRecording()" disabled id="recordBtn">🎤 Start Voice</button>
            </div>
            
            <div class="chat-container" id="chatContainer">
                <div class="message assistant-message">
                    👋 Hi! I'm your voice-enabled grocery assistant. I can help you find products, manage your cart, and understand ethnic groceries in multiple languages.
                </div>
            </div>
            
            <div class="input-area">
                <input type="text" id="textInput" placeholder="Type a message or use voice..." 
                       onkeypress="if(event.key==='Enter') sendText()">
                <button class="primary" onclick="sendText()">Send</button>
            </div>
            
            <div class="cart-summary" id="cartSummary">
                <h3>🛒 Your Cart</h3>
                <div id="cartItems">
                    <em>Cart is empty</em>
                </div>
                <hr style="margin: 15px 0;">
                <div style="display: flex; justify-content: space-between; font-weight: bold;">
                    <span>Total:</span>
                    <span>$<span id="cartTotal">0.00</span></span>
                </div>
            </div>
            
            <details>
                <summary style="cursor: pointer; margin-top: 20px;">📊 View Intent Learning Stats</summary>
                <div class="stats" id="stats"></div>
            </details>
        </div>
        
        <script>
            let ws = null;
            let isRecording = false;
            let mediaRecorder = null;
            let sessionId = null;
            
            function connect() {
                const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${location.host}/ws`);
                
                ws.onopen = () => {
                    console.log('Connected');
                    updateStatus('Connected - Ready', 'connected');
                    document.getElementById('connectBtn').disabled = true;
                    document.getElementById('disconnectBtn').disabled = false;
                    document.getElementById('recordBtn').disabled = false;
                    
                    // Get initial stats
                    setTimeout(() => ws.send(JSON.stringify({ type: 'get_stats' })), 500);
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    console.log('Received:', data);
                    handleMessage(data);
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    addMessage('Connection error occurred', 'assistant');
                };
                
                ws.onclose = () => {
                    console.log('Disconnected');
                    updateStatus('Disconnected', 'disconnected');
                    document.getElementById('connectBtn').disabled = false;
                    document.getElementById('disconnectBtn').disabled = true;
                    document.getElementById('recordBtn').disabled = true;
                    if (isRecording) stopRecording();
                };
            }
            
            function disconnect() {
                if (ws) ws.close();
            }
            
            async function toggleRecording() {
                if (isRecording) {
                    stopRecording();
                } else {
                    startRecording();
                }
            }
            
            async function startRecording() {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ 
                        audio: {
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        } 
                    });
                    
                    const options = { mimeType: 'audio/webm' };
                    mediaRecorder = new MediaRecorder(stream, options);
                    
                    mediaRecorder.ondataavailable = async (event) => {
                        if (event.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) {
                            // Send audio data to server for Deepgram processing
                            const reader = new FileReader();
                            reader.onload = function() {
                                if (ws && ws.readyState === WebSocket.OPEN) {
                                    ws.send(reader.result);
                                }
                            };
                            reader.readAsArrayBuffer(event.data);
                        }
                    };
                    
                    mediaRecorder.start(1000);
                    isRecording = true;
                    
                    document.getElementById('recordBtn').textContent = '⏹️ Stop Voice';
                    updateStatus('Listening...', 'recording');
                    
                    // Send greeting message
                    addMessage("I'm listening! How can I help you find groceries today?", 'assistant');
                    
                } catch (error) {
                    console.error('Microphone error:', error);
                    alert('Failed to access microphone');
                }
            }
            
            function stopRecording() {
                if (mediaRecorder && isRecording) {
                    mediaRecorder.stop();
                    mediaRecorder.stream.getTracks().forEach(track => track.stop());
                    mediaRecorder = null;
                }
                isRecording = false;
                document.getElementById('recordBtn').textContent = '🎤 Start Voice';
                updateStatus('Connected - Ready', 'connected');
            }
            
            function simulateVoiceInput() {
                // Simulate some voice queries for testing
                const testQueries = [
                    "I need paneer and ghee for cooking",
                    "Add 2 pounds of kimchi to my cart",
                    "Show me tahini and harissa",
                    "I want injera bread"
                ];
                const query = testQueries[Math.floor(Math.random() * testQueries.length)];
                sendQuery(query);
                stopRecording();
            }
            
            function sendText() {
                const input = document.getElementById('textInput');
                const text = input.value.trim();
                if (text && ws && ws.readyState === WebSocket.OPEN) {
                    sendQuery(text);
                    input.value = '';
                }
            }
            
            function sendQuery(text) {
                addMessage(text, 'user');
                ws.send(JSON.stringify({
                    type: 'query',
                    text: text
                }));
            }
            
            function handleMessage(data) {
                switch(data.type) {
                    case 'session':
                        sessionId = data.session_id;
                        break;
                        
                    case 'analysis':
                        const intentBadge = `<span class="intent-badge">${data.intent}</span>`;
                        const confidence = `(${(data.confidence * 100).toFixed(0)}% confident)`;
                        
                        let response = `I understood that as ${intentBadge} ${confidence}`;
                        
                        if (data.products && data.products.length > 0) {
                            const productTags = data.products.map(p => {
                                const isEthnic = data.ethnic_info && data.ethnic_info[p];
                                const className = isEthnic ? 'product-tag ethnic-tag' : 'product-tag';
                                const origin = isEthnic ? ` (${data.ethnic_info[p].origin})` : '';
                                return `<span class="${className}">${p}${origin}</span>`;
                            }).join('');
                            response += `<br><br>Products detected: ${productTags}`;
                        }
                        
                        addMessage(response, 'assistant');
                        break;
                        
                    case 'cart_update':
                        updateCart(data.cart);
                        if (data.message) {
                            addMessage(data.message, 'assistant');
                        }
                        break;
                        
                    case 'stats':
                        updateStats(data.stats);
                        break;
                }
            }
            
            function addMessage(text, sender) {
                const chatContainer = document.getElementById('chatContainer');
                const message = document.createElement('div');
                message.className = `message ${sender}-message`;
                message.innerHTML = text;
                chatContainer.appendChild(message);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            
            function updateStatus(text, className) {
                const status = document.getElementById('status');
                status.textContent = text;
                status.className = 'status ' + className;
            }
            
            function updateCart(cart) {
                const cartItems = document.getElementById('cartItems');
                const cartTotal = document.getElementById('cartTotal');
                
                if (!cart.items || cart.items.length === 0) {
                    cartItems.innerHTML = '<em>Cart is empty</em>';
                    cartTotal.textContent = '0.00';
                } else {
                    cartItems.innerHTML = cart.items.map(item => `
                        <div class="cart-item">
                            <div>
                                <strong>${item.name}</strong>
                                ${item.origin ? `<span class="product-tag ethnic-tag">${item.origin}</span>` : ''}
                                <br>
                                <small>${item.quantity} ${item.unit} @ $${item.price.toFixed(2)}</small>
                            </div>
                            <div>$${(item.quantity * item.price).toFixed(2)}</div>
                        </div>
                    `).join('');
                    cartTotal.textContent = cart.total.toFixed(2);
                }
            }
            
            function updateStats(stats) {
                const statsDiv = document.getElementById('stats');
                statsDiv.innerHTML = `
                    <strong>Intent Learning Progress:</strong><br>
                    Total Queries: ${stats.total_observations}<br>
                    Unique Intents Discovered: ${stats.unique_intents}<br>
                    <br>
                    <strong>Intent Distribution:</strong><br>
                    ${Object.entries(stats.intent_counts || {})
                        .sort((a, b) => b[1] - a[1])
                        .map(([intent, count]) => `${intent}: ${count} times`)
                        .join('<br>')}
                `;
            }
        </script>
    </body>
    </html>
    """)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = generate_request_id()
    carts[session_id] = {"items": [], "total": 0}
    
    await websocket.send_json({
        "type": "session",
        "session_id": session_id
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            
            if msg_type == "query":
                query = data.get("text", "")
                
                # Analyze with supervisor
                result = await supervisor.analyze_with_voice_context(
                    query=query,
                    voice_metadata={"pace": "normal", "emotion": "neutral"},
                    memory_context={}
                )
                
                # Extract products and check if they're ethnic
                products = result.get("entities", {}).get("products", [])
                ethnic_info = {}
                
                for product in products:
                    # Check against ethnic database
                    for ethnic_name, info in ETHNIC_PRODUCTS.items():
                        if ethnic_name in product.lower():
                            ethnic_info[product] = info
                            break
                
                # Send analysis
                await websocket.send_json({
                    "type": "analysis",
                    "intent": result["intent"],
                    "confidence": result["confidence"],
                    "products": products,
                    "ethnic_info": ethnic_info
                })
                
                # Handle cart operations
                await process_cart_action(websocket, session_id, query, result, ethnic_info)
                
                # Feed to Deepgram learner
                await deepgram_client.observe_supervisor_intent(
                    transcript=query,
                    intent=result["intent"],
                    confidence=result["confidence"]
                )
                
            elif msg_type == "get_stats":
                stats = await supervisor.export_learned_intents()
                await websocket.send_json({
                    "type": "stats",
                    "stats": {
                        "total_observations": stats["total_observations"],
                        "unique_intents": len(stats["intent_statistics"]),
                        "intent_counts": stats["intent_statistics"]
                    }
                })
                
    except WebSocketDisconnect:
        if session_id in carts:
            del carts[session_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


async def process_cart_action(websocket, session_id, query, analysis, ethnic_info):
    """Process cart operations based on intent"""
    intent = analysis.get("intent", "").lower()
    entities = analysis.get("entities", {})
    cart = carts.get(session_id, {"items": [], "total": 0})
    
    message = None
    
    if "add" in intent or "cart" in intent:
        products = entities.get("products", [])
        quantities = entities.get("quantities", {})
        
        for product in products:
            # Get product info
            product_lower = product.lower()
            ethnic_match = None
            
            for ethnic_name, info in ETHNIC_PRODUCTS.items():
                if ethnic_name in product_lower:
                    ethnic_match = (ethnic_name, info)
                    break
            
            # Add to cart
            quantity = quantities.get(product, 1)
            
            if ethnic_match:
                name, info = ethnic_match
                cart_item = {
                    "name": name.title(),
                    "quantity": quantity,
                    "unit": "unit",
                    "price": info["price"],
                    "origin": info["origin"]
                }
                message = f"Added {quantity} {name} to your cart - {info['origin']} {info['category']}"
            else:
                # Regular product
                cart_item = {
                    "name": product.title(),
                    "quantity": quantity,
                    "unit": "unit",
                    "price": 4.99  # Default price
                }
                message = f"Added {quantity} {product} to your cart"
            
            cart["items"].append(cart_item)
    
    elif "remove" in intent:
        products = entities.get("products", [])
        for product in products:
            original_count = len(cart["items"])
            cart["items"] = [
                item for item in cart["items"] 
                if product.lower() not in item["name"].lower()
            ]
            if len(cart["items"]) < original_count:
                message = f"Removed {product} from your cart"
    
    elif "clear" in intent and "cart" in query.lower():
        cart["items"] = []
        message = "Cart cleared"
    
    elif "show" in intent and "cart" in query.lower():
        if cart["items"]:
            message = f"You have {len(cart['items'])} items in your cart"
        else:
            message = "Your cart is empty"
    
    # Calculate total
    cart["total"] = sum(item["quantity"] * item["price"] for item in cart["items"])
    carts[session_id] = cart
    
    # Send update
    await websocket.send_json({
        "type": "cart_update",
        "cart": cart,
        "message": message
    })


if __name__ == "__main__":
    print("\n🚀 Starting Clean Voice Test Server")
    print("📍 Open http://localhost:8000")
    print("\n✨ Features:")
    print("  • Auto-detects ALL products (no separate buttons)")
    print("  • Recognizes ethnic products automatically")
    print("  • Dynamic intent learning")
    print("  • Natural cart operations")
    print("\n🔗 LangSmith: https://smith.langchain.com\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)