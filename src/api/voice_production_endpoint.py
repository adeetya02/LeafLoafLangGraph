"""
Production voice endpoint with health checks, monitoring, and fallbacks
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.responses import HTMLResponse
import asyncio
import json
import time
from typing import Optional, Dict, Any, List
import structlog
from datetime import datetime
import uuid
import os

from src.voice.production_voice_handler import ProductionVoiceHandler, VoiceConfig
from src.core.graph import search_graph
from src.models.state import SearchState
from src.utils.id_generator import generate_request_id, generate_session_id
from src.integrations.elevenlabs_voice import ElevenLabsVoiceHandler
from src.memory.memory_registry import MemoryRegistry
from src.analytics.voice_analytics import VoiceAnalytics

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice")

# Initialize voice analytics
voice_analytics = VoiceAnalytics()

# Active voice sessions (in production, use Redis)
active_sessions: Dict[str, Dict[str, Any]] = {}

class VoiceSession:
    """Manage a voice session lifecycle"""
    
    def __init__(self, session_id: str, user_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id or f"anonymous_{uuid.uuid4().hex[:8]}"
        self.start_time = datetime.utcnow()
        self.websocket: Optional[WebSocket] = None
        self.voice_handler: Optional[ProductionVoiceHandler] = None
        self.conversation_history: List[str] = []
        self.metrics = {
            "transcripts": 0,
            "searches": 0,
            "errors": 0,
            "audio_duration_seconds": 0
        }
        
    async def initialize(self, websocket: WebSocket, config: Optional[VoiceConfig] = None):
        """Initialize the voice session"""
        self.websocket = websocket
        self.voice_handler = ProductionVoiceHandler(config)
        
        # Set up callbacks
        success = await self.voice_handler.connect(
            on_transcript=self.handle_transcript,
            on_error=self.handle_error,
            on_metrics=self.handle_metrics
        )
        
        if not success:
            raise Exception("Failed to initialize voice handler")
            
        # Log session start
        logger.info(
            "Voice session started",
            session_id=self.session_id,
            user_id=self.user_id
        )
        
        # Track in analytics
        await voice_analytics.track_session_start(self.session_id, self.user_id)
        
    async def handle_transcript(self, data: Dict[str, Any]):
        """Process transcript and search for products"""
        transcript = data.get("transcript", "")
        
        if not transcript or not data.get("is_final"):
            # Send interim results for UI feedback
            if transcript:
                await self.send_to_client({
                    "type": "interim",
                    "transcript": transcript
                })
            return
            
        # Update metrics
        self.metrics["transcripts"] += 1
        self.conversation_history.append(transcript)
        
        # Send final transcript to client
        await self.send_to_client({
            "type": "transcript",
            "transcript": transcript,
            "ethnic_products": data.get("ethnic_products", []),
            "confidence": data.get("confidence", 0)
        })
        
        # Process through LangGraph
        try:
            # Get user memory context
            memory = MemoryRegistry.get_memory(self.user_id)
            memory_context = await memory.get_context() if memory else {}
            
            # Create search state
            state = SearchState(
                query=transcript,
                session_id=self.session_id,
                user_id=self.user_id,
                request_id=generate_request_id(),
                timestamp=datetime.utcnow().isoformat(),
                conversation_history=self.conversation_history[-10:],  # Last 10 turns
                memory_context=memory_context
            )
            
            # Run search
            start_time = time.time()
            result = await search_graph.ainvoke(state)
            search_duration = time.time() - start_time
            
            self.metrics["searches"] += 1
            
            # Extract and send results
            products = []
            if result.get("results"):
                products = [
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "price": p.get("price"),
                        "category": p.get("category"),
                        "image": p.get("image_url"),
                        "in_stock": p.get("in_stock", True)
                    }
                    for p in result["results"][:10]
                ]
            
            # Get response text
            response_text = result.get("response", "I found some products for you.")
            
            # Send search results
            await self.send_to_client({
                "type": "search_results",
                "products": products,
                "response_text": response_text,
                "search_duration_ms": int(search_duration * 1000)
            })
            
            # Generate voice response
            if response_text:
                audio_data = await self.voice_handler.synthesize_speech(response_text)
                if audio_data:
                    # Send as base64 for web compatibility
                    import base64
                    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                    
                    await self.send_to_client({
                        "type": "audio_response",
                        "audio": audio_b64,
                        "text": response_text,
                        "format": "mp3"
                    })
            
            # Track analytics
            await voice_analytics.track_search(
                self.session_id,
                transcript,
                len(products),
                search_duration
            )
            
        except Exception as e:
            logger.error(f"Search error: {e}", session_id=self.session_id)
            self.metrics["errors"] += 1
            
            await self.send_to_client({
                "type": "error",
                "message": "Sorry, I couldn't search for products right now."
            })
    
    async def handle_error(self, error: str):
        """Handle voice processing errors"""
        logger.error(f"Voice error: {error}", session_id=self.session_id)
        self.metrics["errors"] += 1
        
        await self.send_to_client({
            "type": "error",
            "message": error,
            "recoverable": True
        })
    
    async def handle_metrics(self, metrics: Dict[str, Any]):
        """Handle voice metrics updates"""
        # Log important metrics
        if metrics.get("session", {}).get("transcripts_count", 0) % 10 == 0:
            logger.info(
                "Voice session metrics",
                session_id=self.session_id,
                metrics=metrics
            )
    
    async def send_to_client(self, data: Dict[str, Any]):
        """Send data to WebSocket client"""
        if self.websocket:
            try:
                await self.websocket.send_json(data)
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
    
    async def process_audio(self, audio_data: bytes):
        """Process incoming audio"""
        if self.voice_handler:
            await self.voice_handler.send_audio(audio_data)
    
    async def cleanup(self):
        """Clean up session resources"""
        try:
            # Disconnect voice handler
            if self.voice_handler:
                await self.voice_handler.disconnect()
            
            # Calculate session duration
            duration = (datetime.utcnow() - self.start_time).total_seconds()
            
            # Log session end
            logger.info(
                "Voice session ended",
                session_id=self.session_id,
                user_id=self.user_id,
                duration_seconds=duration,
                metrics=self.metrics
            )
            
            # Track in analytics
            await voice_analytics.track_session_end(
                self.session_id,
                duration,
                self.metrics
            )
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}", session_id=self.session_id)


@router.websocket("/stream")
async def voice_stream(websocket: WebSocket, user_id: Optional[str] = None):
    """
    Production WebSocket endpoint for voice streaming
    Handles connection lifecycle, errors, and monitoring
    """
    session_id = generate_session_id()
    session = VoiceSession(session_id, user_id)
    
    # Accept connection
    await websocket.accept()
    
    # Store active session
    active_sessions[session_id] = {
        "session": session,
        "connected_at": datetime.utcnow()
    }
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Voice connection established"
        })
        
        # Initialize voice session
        await session.initialize(websocket)
        
        # Process audio stream
        while True:
            # Receive audio data
            data = await websocket.receive_bytes()
            
            # Process audio
            await session.process_audio(data)
            
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", session_id=session_id)
        
        # Try to send error to client
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Connection error occurred",
                "fatal": True
            })
        except:
            pass
            
    finally:
        # Clean up session
        await session.cleanup()
        
        # Remove from active sessions
        active_sessions.pop(session_id, None)
        
        # Close WebSocket
        try:
            await websocket.close()
        except:
            pass


@router.get("/health")
async def voice_health():
    """Health check endpoint for voice services"""
    # Check STT providers
    deepgram_ok = bool(os.getenv("DEEPGRAM_API_KEY"))
    google_ok = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    
    # Check TTS providers
    elevenlabs_ok = bool(os.getenv("ELEVENLABS_API_KEY"))
    
    # Active sessions
    active_count = len(active_sessions)
    
    # Calculate health score
    providers_available = sum([deepgram_ok, google_ok, elevenlabs_ok])
    health_score = providers_available / 3 * 100
    
    return {
        "status": "healthy" if health_score > 50 else "degraded",
        "health_score": health_score,
        "providers": {
            "stt": {
                "deepgram": "configured" if deepgram_ok else "not_configured",
                "google": "configured" if google_ok else "not_configured"
            },
            "tts": {
                "elevenlabs": "configured" if elevenlabs_ok else "not_configured",
                "deepgram": "not_implemented",
                "google": "not_implemented"
            }
        },
        "active_sessions": active_count,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/sessions")
async def get_active_sessions():
    """Get information about active voice sessions"""
    sessions = []
    
    for session_id, info in active_sessions.items():
        session = info["session"]
        duration = (datetime.utcnow() - session.start_time).total_seconds()
        
        sessions.append({
            "session_id": session_id,
            "user_id": session.user_id,
            "duration_seconds": duration,
            "metrics": session.metrics,
            "connected_at": info["connected_at"].isoformat()
        })
    
    return {
        "active_sessions": len(sessions),
        "sessions": sessions
    }


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str):
    """Manually end a voice session"""
    session_info = active_sessions.get(session_id)
    
    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = session_info["session"]
    
    # Clean up session
    await session.cleanup()
    
    # Close WebSocket if still connected
    if session.websocket:
        try:
            await session.websocket.close()
        except:
            pass
    
    # Remove from active sessions
    active_sessions.pop(session_id, None)
    
    return {"message": "Session ended", "session_id": session_id}


@router.get("/test")
async def test_interface():
    """Serve test interface for voice streaming"""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html>
<head>
    <title>LeafLoaf Voice Search - Production</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        h1 {
            color: #2d3748;
            margin-bottom: 30px;
            text-align: center;
        }
        .status {
            text-align: center;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 30px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .status.connected { background: #c6f6d5; color: #22543d; }
        .status.connecting { background: #feebc8; color: #7b341e; }
        .status.disconnected { background: #fed7d7; color: #742a2a; }
        .controls {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-bottom: 30px;
        }
        button {
            padding: 15px 30px;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .start-btn {
            background: #48bb78;
            color: white;
        }
        .start-btn:hover:not(:disabled) {
            background: #38a169;
            transform: translateY(-2px);
        }
        .stop-btn {
            background: #f56565;
            color: white;
        }
        .stop-btn:hover:not(:disabled) {
            background: #e53e3e;
            transform: translateY(-2px);
        }
        .conversation {
            background: #f7fafc;
            border-radius: 15px;
            padding: 20px;
            min-height: 300px;
            max-height: 500px;
            overflow-y: auto;
        }
        .message {
            margin-bottom: 15px;
            padding: 15px;
            border-radius: 10px;
            animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .user-message {
            background: #e6fffa;
            border-left: 4px solid #4fd1c5;
        }
        .assistant-message {
            background: #f0fff4;
            border-left: 4px solid #68d391;
        }
        .error-message {
            background: #fff5f5;
            border-left: 4px solid #fc8181;
            color: #742a2a;
        }
        .products {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        .product {
            background: white;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            text-align: center;
            font-size: 14px;
        }
        .product-name {
            font-weight: 600;
            color: #2d3748;
        }
        .product-price {
            color: #48bb78;
            margin-top: 5px;
        }
        .ethnic-product {
            background: #48bb78;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
            display: inline-block;
            margin: 2px;
        }
        .metrics {
            margin-top: 20px;
            padding: 15px;
            background: #f7fafc;
            border-radius: 10px;
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            text-align: center;
        }
        .metric {
            padding: 10px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #4a5568;
        }
        .metric-label {
            font-size: 12px;
            color: #718096;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛒 LeafLoaf Voice Search</h1>
        
        <div class="status disconnected" id="status">
            Click Start to begin voice search
        </div>
        
        <div class="controls">
            <button class="start-btn" id="startBtn" onclick="startVoiceSearch()">
                <span>🎤</span> Start Voice Search
            </button>
            <button class="stop-btn" id="stopBtn" onclick="stopVoiceSearch()" disabled>
                <span>⏹</span> Stop
            </button>
        </div>
        
        <div class="conversation" id="conversation">
            <div style="text-align: center; color: #a0aec0; padding: 50px;">
                Your conversation will appear here...
            </div>
        </div>
        
        <div class="metrics">
            <div class="metric">
                <div class="metric-value" id="transcriptCount">0</div>
                <div class="metric-label">Transcripts</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="productCount">0</div>
                <div class="metric-label">Products Found</div>
            </div>
            <div class="metric">
                <div class="metric-value" id="sessionTime">0:00</div>
                <div class="metric-label">Session Time</div>
            </div>
        </div>
    </div>

    <script>
        let ws = null;
        let mediaRecorder = null;
        let audioStream = null;
        let sessionStartTime = null;
        let sessionTimer = null;
        let metrics = {
            transcripts: 0,
            products: 0
        };
        
        async function startVoiceSearch() {
            try {
                updateStatus('Requesting microphone access...', 'connecting');
                
                // Get microphone
                audioStream = await navigator.mediaDevices.getUserMedia({ 
                    audio: {
                        channelCount: 1,
                        sampleRate: 16000,
                        echoCancellation: true,
                        noiseSuppression: true
                    } 
                });
                
                updateStatus('Connecting to voice service...', 'connecting');
                
                // Connect WebSocket
                const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
                ws = new WebSocket(`${protocol}//${location.host}/api/v1/voice/stream`);
                
                ws.onopen = () => {
                    updateStatus('Connected - Start speaking!', 'connected');
                    document.getElementById('startBtn').disabled = true;
                    document.getElementById('stopBtn').disabled = false;
                    
                    // Clear conversation
                    document.getElementById('conversation').innerHTML = '';
                    
                    // Start session timer
                    sessionStartTime = Date.now();
                    sessionTimer = setInterval(updateSessionTime, 1000);
                    
                    // Start recording
                    mediaRecorder = new MediaRecorder(audioStream);
                    
                    mediaRecorder.ondataavailable = (event) => {
                        if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                            ws.send(event.data);
                        }
                    };
                    
                    mediaRecorder.start(100); // 100ms chunks
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                };
                
                ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    addMessage('Connection error occurred', 'error');
                    stopVoiceSearch();
                };
                
                ws.onclose = () => {
                    updateStatus('Disconnected', 'disconnected');
                    stopVoiceSearch();
                };
                
            } catch (error) {
                console.error('Error:', error);
                updateStatus('Error: ' + error.message, 'disconnected');
                addMessage('Failed to start voice search: ' + error.message, 'error');
            }
        }
        
        function stopVoiceSearch() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            
            if (audioStream) {
                audioStream.getTracks().forEach(track => track.stop());
            }
            
            if (ws) {
                ws.close();
            }
            
            if (sessionTimer) {
                clearInterval(sessionTimer);
                sessionTimer = null;
            }
            
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
        }
        
        function handleMessage(data) {
            switch (data.type) {
                case 'connected':
                    console.log('Session ID:', data.session_id);
                    break;
                    
                case 'interim':
                    // Could show interim results in UI
                    break;
                    
                case 'transcript':
                    metrics.transcripts++;
                    document.getElementById('transcriptCount').textContent = metrics.transcripts;
                    
                    let transcript = data.transcript;
                    if (data.ethnic_products && data.ethnic_products.length > 0) {
                        data.ethnic_products.forEach(product => {
                            transcript = transcript.replace(
                                new RegExp(product, 'gi'),
                                `<span class="ethnic-product">${product}</span>`
                            );
                        });
                    }
                    
                    addMessage(transcript, 'user');
                    break;
                    
                case 'search_results':
                    if (data.products && data.products.length > 0) {
                        metrics.products += data.products.length;
                        document.getElementById('productCount').textContent = metrics.products;
                        
                        const productsHtml = data.products.map(p => `
                            <div class="product">
                                <div class="product-name">${p.name}</div>
                                <div class="product-price">$${p.price}</div>
                            </div>
                        `).join('');
                        
                        addMessage(
                            data.response_text + '<div class="products">' + productsHtml + '</div>',
                            'assistant'
                        );
                    } else {
                        addMessage(data.response_text || 'No products found', 'assistant');
                    }
                    break;
                    
                case 'audio_response':
                    // Could play audio response
                    break;
                    
                case 'error':
                    addMessage(data.message, 'error');
                    break;
            }
        }
        
        function updateStatus(text, className) {
            const status = document.getElementById('status');
            status.textContent = text;
            status.className = 'status ' + className;
        }
        
        function addMessage(content, type) {
            const conversation = document.getElementById('conversation');
            const message = document.createElement('div');
            message.className = 'message ' + type + '-message';
            message.innerHTML = content;
            conversation.appendChild(message);
            conversation.scrollTop = conversation.scrollHeight;
        }
        
        function updateSessionTime() {
            if (sessionStartTime) {
                const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;
                document.getElementById('sessionTime').textContent = 
                    `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
        }
    </script>
</body>
</html>
    """)