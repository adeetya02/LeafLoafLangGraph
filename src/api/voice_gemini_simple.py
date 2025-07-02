"""
Simple Voice Implementation with Gemini
Uses browser's speech recognition + Gemini for responses
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import google.generativeai as genai
import json
import asyncio
import structlog
import os

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/simple")

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyAGLGwNEXgoksFCawjU_x3pWMC-RFTlhPA")
genai.configure(api_key=GEMINI_API_KEY)

class SimpleVoiceSession:
    """Simple voice session using browser STT + Gemini"""
    
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.model = None
        self.chat = None
        
    async def initialize(self):
        """Initialize Gemini"""
        try:
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction="""You are LeafLoaf, a friendly grocery shopping assistant.

Keep responses brief and natural (2-3 sentences).
Be conversational and helpful.
Focus on grocery shopping needs.

You can help with:
- Finding products
- Suggesting recipes
- Managing shopping lists
- Providing nutritional info"""
            )
            
            self.chat = self.model.start_chat(history=[])
            
            await self.websocket.send_json({
                "type": "connected",
                "message": "Connected to LeafLoaf Assistant"
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": str(e)
            })
            return False
            
    async def handle_connection(self):
        """Main WebSocket handler"""
        await self.websocket.accept()
        logger.info("Simple voice connection accepted")
        
        if not await self.initialize():
            return
            
        try:
            while True:
                message = await self.websocket.receive()
                
                if message["type"] == "websocket.receive":
                    if "text" in message:
                        data = json.loads(message["text"])
                        await self.handle_message(data)
                        
        except WebSocketDisconnect:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            
    async def handle_message(self, data: dict):
        """Handle messages"""
        msg_type = data.get("type")
        
        if msg_type == "transcript":
            text = data.get("text", "")
            if text:
                await self.process_text(text)
                
    async def process_text(self, text: str):
        """Process text with Gemini"""
        try:
            logger.info(f"Processing: {text}")
            
            # Send processing status
            await self.websocket.send_json({
                "type": "processing"
            })
            
            # Get Gemini response
            response = await self.chat.send_message_async(text)
            response_text = response.text
            
            logger.info(f"Gemini response: {response_text[:100]}...")
            
            # Send response
            await self.websocket.send_json({
                "type": "response",
                "text": response_text
            })
            
        except Exception as e:
            logger.error(f"Processing error: {e}")
            await self.websocket.send_json({
                "type": "error",
                "message": "Sorry, I couldn't process that. Please try again."
            })

@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for simple voice"""
    session = SimpleVoiceSession(websocket)
    await session.handle_connection()

@router.get("/test")
async def test_endpoint():
    """Test Gemini availability"""
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say hello")
        
        return {
            "status": "ok",
            "model": "gemini-1.5-flash",
            "response": response.text[:100]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}