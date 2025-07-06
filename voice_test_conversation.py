"""
Voice Test Server with Conversational Flow
Uses mock transcription for testing the conversation experience
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import asyncio
import json
import os
import uvicorn
import structlog
from typing import Dict, Any
import random

# Set up environment
os.environ['DEEPGRAM_API_KEY'] = '36a821d351939023aabad9beeaa68b391caa124a'

from src.agents.supervisor_dynamic_intents import DynamicIntentSupervisor
from src.voice.deepgram.client_factory import create_streaming_client
from src.utils.id_generator import generate_request_id

logger = structlog.get_logger()
app = FastAPI(title="Voice Conversation Test")

# Global instances
supervisor = None
deepgram_client = None
carts = {}  # Session-based carts

# Ethnic product database
ETHNIC_PRODUCTS = {
    "paneer": {"origin": "Indian", "category": "Dairy", "price": 7.99},
    "ghee": {"origin": "Indian", "category": "Dairy", "price": 12.99},
    "kimchi": {"origin": "Korean", "category": "Fermented", "price": 6.99},
    "gochujang": {"origin": "Korean", "category": "Sauce", "price": 5.99},
    "tahini": {"origin": "Middle Eastern", "category": "Sauce", "price": 8.99},
    "harissa": {"origin": "Middle Eastern", "category": "Sauce", "price": 6.99},
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
        <title>LeafLoaf Voice - Conversational Shopping</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 900px; 
                margin: 40px auto; 
                padding: 20px;
                background: #f0f4f8;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 16px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            }
            h1 { 
                color: #2c3e50; 
                margin-bottom: 10px; 
                display: flex;
                align-items: center;
                gap: 10px;
            }
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
                padding: 14px 28px; 
                font-size: 16px; 
                margin: 5px; 
                cursor: pointer;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                transition: all 0.2s;
            }
            button:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
            button:active { transform: translateY(0); }
            button:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
            
            .primary { background: #007bff; color: white; }
            .success { background: #28a745; color: white; }
            .danger { background: #dc3545; color: white; }
            
            .chat-container {
                background: #f8f9fa;
                border-radius: 12px;
                padding: 20px;
                margin: 20px 0;
                height: 400px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            
            .message {
                padding: 14px 18px;
                border-radius: 18px;
                max-width: 70%;
                word-wrap: break-word;
                animation: fadeIn 0.3s ease-in;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .user-message {
                background: #007bff;
                color: white;
                align-self: flex-end;
                border-bottom-right-radius: 4px;
            }
            
            .assistant-message {
                background: white;
                color: #2c3e50;
                align-self: flex-start;
                border-bottom-left-radius: 4px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }
            
            .typing-indicator {
                display: flex;
                gap: 4px;
                padding: 14px 18px;
                background: white;
                border-radius: 18px;
                border-bottom-left-radius: 4px;
                width: fit-content;
                box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            }
            
            .typing-dot {
                width: 8px;
                height: 8px;
                background: #7f8c8d;
                border-radius: 50%;
                animation: typing 1.4s infinite;
            }
            
            .typing-dot:nth-child(2) { animation-delay: 0.2s; }
            .typing-dot:nth-child(3) { animation-delay: 0.4s; }
            
            @keyframes typing {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-10px); }
            }
            
            .voice-indicator {
                height: 60px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 3px;
                margin: 20px 0;
                padding: 0 40px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 30px;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }
            
            .voice-bar {
                width: 4px;
                background: white;
                border-radius: 2px;
                transition: height 0.1s;
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
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 12px;
                padding: 24px;
                margin: 20px 0;
            }
            
            .cart-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                margin: 8px 0;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            
            .cart-empty {
                text-align: center;
                padding: 40px;
                color: #7f8c8d;
            }
            
            .listening-animation {
                text-align: center;
                padding: 20px;
                font-size: 1.2em;
                color: #007bff;
                font-weight: 500;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>
                <span style="font-size: 1.5em;">🗣️</span>
                LeafLoaf Voice Shopping
            </h1>
            <p class="subtitle">Have a natural conversation about your grocery needs</p>
            
            <div class="status disconnected" id="status">Click Connect to start</div>
            
            <div style="text-align: center;">
                <button class="primary" onclick="connect()" id="connectBtn">Connect</button>
                <button class="danger" onclick="disconnect()" disabled id="disconnectBtn">Disconnect</button>
                <button class="success" onclick="toggleVoice()" disabled id="voiceBtn">🎤 Start Conversation</button>
            </div>
            
            <div class="voice-indicator" id="voiceIndicator" style="display: none;">
                <div class="voice-bar" style="height: 20px;"></div>
                <div class="voice-bar" style="height: 35px;"></div>
                <div class="voice-bar" style="height: 25px;"></div>
                <div class="voice-bar" style="height: 40px;"></div>
                <div class="voice-bar" style="height: 30px;"></div>
                <div class="voice-bar" style="height: 45px;"></div>
                <div class="voice-bar" style="height: 35px;"></div>
                <div class="voice-bar" style="height: 25px;"></div>
                <div class="voice-bar" style="height: 30px;"></div>
                <div class="voice-bar" style="height: 20px;"></div>
            </div>
            
            <div class="chat-container" id="chatContainer">
                <div class="message assistant-message">
                    👋 Hi! I'm your voice shopping assistant. Click "Start Conversation" and tell me what groceries you need. I understand all types of products including ethnic foods!
                </div>
            </div>
            
            <div class="cart-summary">
                <h3>🛒 Your Cart</h3>
                <div id="cartItems">
                    <div class="cart-empty">
                        <p>Your cart is empty</p>
                        <small>Add items by voice!</small>
                    </div>
                </div>
                <hr style="margin: 20px 0; border: none; border-top: 2px solid rgba(255,255,255,0.3);">
                <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 1.1em;">
                    <span>Total:</span>
                    <span>$<span id="cartTotal">0.00</span></span>
                </div>
            </div>
        </div>
        
        <script>
            let ws = null;
            let isVoiceActive = false;
            let sessionId = null;
            let currentAudioLevel = 0;
            let animationFrame = null;
            
            // Simulate voice queries for demo
            const demoQueries = [
                { text: "Hello, how are you?", delay: 2000 },
                { text: "I need paneer and ghee for cooking Indian food", delay: 8000 },
                { text: "Add 2 pounds of kimchi to my cart", delay: 15000 },
                { text: "Show me Middle Eastern ingredients", delay: 22000 },
                { text: "I want tahini and harissa sauce", delay: 28000 }
            ];
            
            function connect() {
                const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${location.host}/ws`);
                
                ws.onopen = () => {
                    console.log('Connected');
                    updateStatus('Connected - Ready for conversation', 'connected');
                    document.getElementById('connectBtn').disabled = true;
                    document.getElementById('disconnectBtn').disabled = false;
                    document.getElementById('voiceBtn').disabled = false;
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
                    document.getElementById('voiceBtn').disabled = true;
                    if (isVoiceActive) stopVoice();
                };
            }
            
            function disconnect() {
                if (ws) ws.close();
            }
            
            async function toggleVoice() {
                if (isVoiceActive) {
                    stopVoice();
                } else {
                    startVoice();
                }
            }
            
            async function startVoice() {
                try {
                    // Request microphone permission
                    const stream = await navigator.mediaDevices.getUserMedia({ 
                        audio: {
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        } 
                    });
                    
                    isVoiceActive = true;
                    document.getElementById('voiceBtn').textContent = '⏹️ Stop Conversation';
                    document.getElementById('voiceBtn').className = 'danger';
                    document.getElementById('voiceIndicator').style.display = 'flex';
                    updateStatus('Listening... Speak naturally!', 'recording');
                    
                    // Start voice animation
                    startVoiceAnimation();
                    
                    // Send greeting
                    setTimeout(() => {
                        addMessage("I'm listening! What groceries can I help you find today?", 'assistant');
                    }, 500);
                    
                    // Notify server
                    ws.send(JSON.stringify({ type: 'start_voice' }));
                    
                    // Simulate conversation for demo
                    if (window.location.search.includes('demo')) {
                        simulateConversation();
                    }
                    
                    // Set up audio context for visualization
                    const audioContext = new AudioContext();
                    const analyser = audioContext.createAnalyser();
                    const microphone = audioContext.createMediaStreamSource(stream);
                    microphone.connect(analyser);
                    analyser.fftSize = 256;
                    
                    window.currentStream = stream;
                    window.audioAnalyser = analyser;
                    
                } catch (error) {
                    console.error('Microphone error:', error);
                    alert('Please allow microphone access to use voice shopping');
                }
            }
            
            function stopVoice() {
                if (window.currentStream) {
                    window.currentStream.getTracks().forEach(track => track.stop());
                }
                
                isVoiceActive = false;
                document.getElementById('voiceBtn').textContent = '🎤 Start Conversation';
                document.getElementById('voiceBtn').className = 'success';
                document.getElementById('voiceIndicator').style.display = 'none';
                updateStatus('Connected - Ready for conversation', 'connected');
                
                // Stop animation
                if (animationFrame) {
                    cancelAnimationFrame(animationFrame);
                }
                
                // Notify server
                ws.send(JSON.stringify({ type: 'stop_voice' }));
                
                addMessage("Conversation ended. Click Start Conversation when you're ready to shop again!", 'assistant');
            }
            
            function startVoiceAnimation() {
                const bars = document.querySelectorAll('.voice-bar');
                
                function animate() {
                    if (!isVoiceActive) return;
                    
                    // Update bars with random heights to simulate voice
                    bars.forEach((bar, i) => {
                        const height = 10 + Math.random() * 35 + (Math.sin(Date.now() * 0.001 + i) * 10);
                        bar.style.height = height + 'px';
                    });
                    
                    animationFrame = requestAnimationFrame(animate);
                }
                
                animate();
            }
            
            function simulateConversation() {
                // Simulate a natural conversation flow
                demoQueries.forEach(({ text, delay }) => {
                    setTimeout(() => {
                        if (isVoiceActive) {
                            ws.send(JSON.stringify({
                                type: 'simulate_voice',
                                text: text
                            }));
                        }
                    }, delay);
                });
            }
            
            function handleMessage(data) {
                switch(data.type) {
                    case 'session':
                        sessionId = data.session_id;
                        break;
                        
                    case 'transcript':
                        addMessage(data.text, 'user');
                        showTypingIndicator();
                        break;
                        
                    case 'response':
                        hideTypingIndicator();
                        addMessage(data.text, 'assistant');
                        if (data.products) {
                            showProductInfo(data.products);
                        }
                        break;
                        
                    case 'cart_update':
                        updateCart(data.cart);
                        break;
                        
                    case 'intent_info':
                        console.log('Intent:', data.intent, 'Confidence:', data.confidence);
                        break;
                }
            }
            
            function showTypingIndicator() {
                const chatContainer = document.getElementById('chatContainer');
                const existing = document.getElementById('typingIndicator');
                if (!existing) {
                    const typing = document.createElement('div');
                    typing.id = 'typingIndicator';
                    typing.className = 'typing-indicator';
                    typing.innerHTML = `
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    `;
                    chatContainer.appendChild(typing);
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            }
            
            function hideTypingIndicator() {
                const typing = document.getElementById('typingIndicator');
                if (typing) {
                    typing.remove();
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
            
            function showProductInfo(products) {
                const info = products.map(p => {
                    if (p.ethnic) {
                        return `<span class="product-tag ethnic-tag">${p.name} (${p.origin})</span>`;
                    }
                    return `<span class="product-tag">${p.name}</span>`;
                }).join('');
                
                const chatContainer = document.getElementById('chatContainer');
                const infoDiv = document.createElement('div');
                infoDiv.style.textAlign = 'center';
                infoDiv.style.margin = '10px 0';
                infoDiv.innerHTML = info;
                chatContainer.appendChild(infoDiv);
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
                    cartItems.innerHTML = `
                        <div class="cart-empty">
                            <p>Your cart is empty</p>
                            <small>Add items by voice!</small>
                        </div>
                    `;
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
                            <div style="font-weight: 600;">$${(item.quantity * item.price).toFixed(2)}</div>
                        </div>
                    `).join('');
                    cartTotal.textContent = cart.total.toFixed(2);
                }
            }
            
            // Add demo mode hint
            if (window.location.pathname === '/') {
                console.log('💡 Tip: Add ?demo to URL to see simulated conversation');
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
            
            if msg_type == "start_voice":
                logger.info(f"Voice conversation started for session {session_id}")
                # Voice is handled on client side for now
                
            elif msg_type == "stop_voice":
                logger.info(f"Voice conversation ended for session {session_id}")
                
            elif msg_type == "simulate_voice":
                # Handle simulated voice input
                query = data.get("text", "")
                
                # Send transcript
                await websocket.send_json({
                    "type": "transcript",
                    "text": query
                })
                
                # Small delay for natural feel
                await asyncio.sleep(0.5)
                
                # Analyze with supervisor
                result = await supervisor.analyze_with_voice_context(
                    query=query,
                    voice_metadata={
                        "pace": "normal",
                        "emotion": "neutral",
                        "urgency": "medium",
                        "volume": "normal"
                    },
                    memory_context={"session_id": session_id}
                )
                
                # Generate contextual response
                response = await generate_conversational_response(
                    query, result, session_id, carts[session_id]
                )
                
                # Send response
                await websocket.send_json({
                    "type": "response",
                    "text": response["text"],
                    "intent": result.get("intent"),
                    "confidence": result.get("confidence"),
                    "products": response.get("products", [])
                })
                
                # Update cart if needed
                if response.get("cart_updated"):
                    await websocket.send_json({
                        "type": "cart_update",
                        "cart": carts[session_id]
                    })
                
                # Learn from the interaction
                await deepgram_client.observe_supervisor_intent(
                    transcript=query,
                    intent=result["intent"],
                    confidence=result["confidence"]
                )
                
    except WebSocketDisconnect:
        logger.info(f"Session {session_id} disconnected")
        if session_id in carts:
            del carts[session_id]
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


async def generate_conversational_response(query: str, analysis: Dict, session_id: str, cart: Dict) -> Dict[str, Any]:
    """Generate natural conversational responses"""
    intent = analysis.get("intent", "unknown")
    entities = analysis.get("entities", {})
    products = entities.get("products", [])
    
    response = {"text": "", "products": [], "cart_updated": False}
    
    # Handle different conversation flows
    if "greeting" in intent.lower() or any(word in query.lower() for word in ["hello", "hi", "hey"]):
        responses = [
            "Hello! I'm doing great, thank you for asking! What groceries can I help you find today?",
            "Hi there! I'm ready to help with your shopping. What are you looking for?",
            "Hey! Great to hear from you. Tell me what's on your grocery list!"
        ]
        response["text"] = random.choice(responses)
        
    elif any(word in intent.lower() for word in ["add", "cart", "want", "need"]):
        if products:
            # Process products and add to cart
            added_items = []
            ethnic_items = []
            
            for product in products:
                # Check ethnic products
                for ethnic_name, info in ETHNIC_PRODUCTS.items():
                    if ethnic_name in product.lower():
                        cart["items"].append({
                            "name": ethnic_name.title(),
                            "quantity": entities.get("quantities", {}).get(product, 1),
                            "unit": "unit",
                            "price": info["price"],
                            "origin": info["origin"]
                        })
                        ethnic_items.append(f"{ethnic_name} ({info['origin']} {info['category']})")
                        added_items.append(ethnic_name)
                        break
                else:
                    # Regular product
                    cart["items"].append({
                        "name": product.title(),
                        "quantity": entities.get("quantities", {}).get(product, 1),
                        "unit": "unit",
                        "price": 4.99
                    })
                    added_items.append(product)
            
            # Update cart total
            cart["total"] = sum(item["quantity"] * item["price"] for item in cart["items"])
            response["cart_updated"] = True
            
            # Generate response
            if ethnic_items:
                response["text"] = f"Great choice! I've added {', '.join(added_items)} to your cart. "
                response["text"] += f"I see you're shopping for {ethnic_items[0].split('(')[1].split(')')[0]} cuisine. "
                response["text"] += "Is there anything else you need for your cooking?"
            else:
                response["text"] = f"I've added {', '.join(added_items)} to your cart. What else can I help you find?"
            
            # Add product info
            response["products"] = [
                {"name": item, "ethnic": item in ETHNIC_PRODUCTS, 
                 "origin": ETHNIC_PRODUCTS.get(item, {}).get("origin")}
                for item in added_items
            ]
        else:
            response["text"] = "I'd be happy to add items to your cart. Could you tell me which specific products you're looking for?"
            
    elif "show" in intent.lower() or "search" in intent.lower() or "find" in intent.lower():
        if any(cuisine in query.lower() for cuisine in ["indian", "korean", "middle eastern", "ethiopian"]):
            # Show cuisine-specific products
            cuisine_products = []
            cuisine_name = ""
            
            if "indian" in query.lower():
                cuisine_products = ["paneer", "ghee", "basmati rice", "dal", "atta flour"]
                cuisine_name = "Indian"
            elif "korean" in query.lower():
                cuisine_products = ["kimchi", "gochujang", "korean rice", "seaweed", "sesame oil"]
                cuisine_name = "Korean"
            elif "middle eastern" in query.lower():
                cuisine_products = ["tahini", "harissa", "pita bread", "hummus", "zaatar"]
                cuisine_name = "Middle Eastern"
            elif "ethiopian" in query.lower():
                cuisine_products = ["injera", "berbere", "teff flour", "mitmita", "shiro"]
                cuisine_name = "Ethiopian"
                
            response["text"] = f"Here are some popular {cuisine_name} ingredients I have: {', '.join(cuisine_products[:3])}. "
            response["text"] += "Would you like me to add any of these to your cart?"
            response["products"] = [{"name": p, "ethnic": True, "origin": cuisine_name} for p in cuisine_products[:3]]
            
        elif products:
            response["text"] = f"Let me find {', '.join(products)} for you. I have several options available. Would you like me to add them to your cart?"
        else:
            response["text"] = "I can help you find any groceries you need, including specialty and ethnic foods. What are you looking for?"
            
    elif "cart" in query.lower() and ("show" in query.lower() or "what" in query.lower()):
        if cart["items"]:
            response["text"] = f"You have {len(cart['items'])} items in your cart totaling ${cart['total']:.2f}. "
            response["text"] += "Would you like to add more items or proceed to checkout?"
        else:
            response["text"] = "Your cart is currently empty. What would you like to shop for today?"
            
    elif "checkout" in query.lower() or "done" in query.lower() or "finish" in query.lower():
        if cart["items"]:
            response["text"] = f"Perfect! You have {len(cart['items'])} items totaling ${cart['total']:.2f}. "
            response["text"] += "Your order is ready for checkout. Thank you for shopping with us!"
        else:
            response["text"] = "Your cart is empty. Would you like to add some items before checking out?"
            
    else:
        # Default conversational response
        response["text"] = "I can help you shop for any groceries, including ethnic and specialty foods. "
        response["text"] += "Just tell me what you need, and I'll add it to your cart!"
    
    return response


if __name__ == "__main__":
    print("\n🚀 Starting Voice Conversation Test Server")
    print("📍 Open http://localhost:8000")
    print("   Add ?demo to see simulated conversation")
    print("\n✨ Features:")
    print("  • Natural conversational flow")
    print("  • Voice-activated shopping")
    print("  • Dynamic intent learning")
    print("  • Ethnic product recognition")
    print("\n🔗 LangSmith: https://smith.langchain.com\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)