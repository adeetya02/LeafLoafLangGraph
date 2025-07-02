"""
Voice Demo Simulation - Shows how the system works without external dependencies
"""
import asyncio
import json
import base64
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
from datetime import datetime
import random

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/demo")

# Simulated product database
PRODUCTS = [
    {"name": "Organic Gala Apples", "price": 3.99, "unit": "lb", "category": "produce"},
    {"name": "Organic Honeycrisp Apples", "price": 4.99, "unit": "lb", "category": "produce"},
    {"name": "Organic Fuji Apples", "price": 3.49, "unit": "lb", "category": "produce"},
    {"name": "Organic Granny Smith Apples", "price": 3.79, "unit": "lb", "category": "produce"},
    {"name": "Organic Bananas", "price": 0.79, "unit": "lb", "category": "produce"},
    {"name": "Organic Strawberries", "price": 5.99, "unit": "container", "category": "produce"},
    {"name": "Whole Milk", "price": 4.29, "unit": "gallon", "category": "dairy"},
    {"name": "Organic Eggs", "price": 6.99, "unit": "dozen", "category": "dairy"},
]

class VoiceSimulator:
    """Simulates the voice processing pipeline"""
    
    def __init__(self):
        self.cart = []
        
    async def process_text(self, text: str):
        """Simulate processing text through the pipeline"""
        # Simulate processing delay
        await asyncio.sleep(0.5)
        
        # 1. Voice Metadata Extraction (simulated)
        voice_metadata = {
            "pace": random.choice(["slow", "normal", "fast"]),
            "emotion": "neutral",
            "confidence": 0.95,
            "duration": len(text) * 0.1
        }
        
        # 2. Supervisor Analysis (simulated)
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["hi", "hello", "hey"]):
            intent = "greeting"
            confidence = 0.98
            response_text = "Hello! Welcome to LeafLoaf. I can help you find groceries. What are you looking for today?"
            
        elif any(word in text_lower for word in ["add", "want", "need", "get"]):
            intent = "add_to_cart"
            confidence = 0.9
            # Simple product matching
            products_found = []
            for product in PRODUCTS:
                if any(word in product["name"].lower() for word in text_lower.split()):
                    products_found.append(product)
            
            if products_found:
                # Add first match to cart
                self.cart.append(products_found[0])
                response_text = f"Added {products_found[0]['name']} (${products_found[0]['price']}/{products_found[0]['unit']}) to your cart."
            else:
                response_text = "I couldn't find that product. Try searching for apples, bananas, or milk."
                
        elif "cart" in text_lower or "order" in text_lower:
            intent = "view_cart"
            confidence = 0.95
            if self.cart:
                total = sum(item["price"] for item in self.cart)
                items = ", ".join(item["name"] for item in self.cart)
                response_text = f"Your cart has {len(self.cart)} items: {items}. Total: ${total:.2f}"
            else:
                response_text = "Your cart is empty. What would you like to add?"
                
        else:
            # Default to product search
            intent = "product_search"
            confidence = 0.85
            products_found = []
            for product in PRODUCTS:
                if any(word in product["name"].lower() for word in text_lower.split()):
                    products_found.append(product)
            
            if products_found:
                response_text = f"I found {len(products_found)} products:\n"
                for p in products_found[:3]:  # Show top 3
                    response_text += f"- {p['name']} (${p['price']}/{p['unit']})\n"
            else:
                response_text = "I couldn't find any matching products. Try searching for apples, bananas, milk, or eggs."
        
        # 3. Simulated voice synthesis parameters
        voice_params = {
            "speaking_rate": 1.0 if voice_metadata["pace"] == "normal" else (0.9 if voice_metadata["pace"] == "slow" else 1.1),
            "pitch": 0.0,
            "voice_type": "friendly"
        }
        
        return {
            "intent": intent,
            "confidence": confidence,
            "response_text": response_text,
            "voice_metadata": voice_metadata,
            "voice_params": voice_params,
            "products_found": len(products_found) if 'products_found' in locals() else 0
        }

@router.websocket("/ws")
async def demo_websocket(websocket: WebSocket):
    """Demo WebSocket that simulates the full voice pipeline"""
    await websocket.accept()
    
    session_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    simulator = VoiceSimulator()
    
    try:
        # Send welcome
        await websocket.send_json({
            "type": "session_started",
            "session_id": session_id,
            "message": "🎤 Voice Demo Started - Try saying 'I need apples' or 'Show my cart'",
            "demo_mode": True
        })
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "text":
                text = data.get("text", "")
                
                # Send processing status
                await websocket.send_json({
                    "type": "processing",
                    "message": "🤔 Understanding your request..."
                })
                
                # Process through simulator
                result = await simulator.process_text(text)
                
                # Send analysis results
                await websocket.send_json({
                    "type": "analysis",
                    "intent": result["intent"],
                    "confidence": result["confidence"],
                    "voice_metadata": result["voice_metadata"]
                })
                
                # Simulate search if needed
                if result["intent"] == "product_search":
                    await asyncio.sleep(0.3)  # Simulate search time
                    await websocket.send_json({
                        "type": "search_complete",
                        "products_found": result["products_found"]
                    })
                
                # Send final response
                await websocket.send_json({
                    "type": "response",
                    "text": result["response_text"],
                    "voice_params": result["voice_params"]
                })
                
                # Simulate audio response (base64 encoded silence)
                fake_audio = base64.b64encode(b'\x00' * 1000).decode()
                await websocket.send_json({
                    "type": "audio_response",
                    "audio": fake_audio,
                    "format": "wav",
                    "duration": len(result["response_text"]) * 0.05  # Rough estimate
                })
                
    except WebSocketDisconnect:
        logger.info(f"Demo session ended: {session_id}")
    except Exception as e:
        logger.error(f"Demo error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })