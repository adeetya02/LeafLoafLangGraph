"""
Feedback collector for implicit user feedback
"""
from typing import Dict, Any, Optional
import asyncio
import structlog
from src.memory.learning_loop import learning_loop

logger = structlog.get_logger()

class FeedbackCollector:
    """Collects implicit feedback from user actions"""
    
    def __init__(self):
        self.learning_loop = learning_loop
    
    async def collect_search_feedback(self, state: Dict[str, Any], clicked_product: Optional[Dict] = None):
        """Collect feedback from search interactions"""
        user_id = state.get("user_id")
        if not user_id:
            return
            
        query = state.get("query")
        search_results = state.get("search_results", [])
        
        if clicked_product:
            # Find position in results
            position = -1
            for i, result in enumerate(search_results):
                if result.get("sku") == clicked_product.get("sku"):
                    position = i
                    break
            
            if position >= 0:
                await self.learning_loop.record_search_click(
                    user_id=user_id,
                    query=query,
                    clicked_product=clicked_product,
                    position=position
                )
    
    async def collect_cart_feedback(self, state: Dict[str, Any], cart_event: Dict[str, Any]):
        """Collect feedback from cart modifications"""
        user_id = state.get("user_id")
        if not user_id:
            return
        
        event_type = cart_event.get("type")
        
        if event_type == "add":
            for item in cart_event.get("items", []):
                await self.learning_loop.record_cart_addition(
                    user_id=user_id,
                    product=item,
                    quantity=item.get("quantity", 1)
                )
        elif event_type == "remove":
            # Track removals as negative signals
            await self.learning_loop.record_interaction({
                "type": "cart_remove",
                "user_id": user_id,
                "product": cart_event.get("product"),
                "reason": cart_event.get("reason", "unknown")
            })
    
    async def collect_order_feedback(self, state: Dict[str, Any], order: Dict[str, Any]):
        """Collect feedback from order completion"""
        user_id = state.get("user_id")
        if not user_id or not order.get("items"):
            return
        
        await self.learning_loop.record_order_completion(
            user_id=user_id,
            order=order
        )
    
    async def collect_routing_feedback(self, state: Dict[str, Any], routing_result: Dict[str, Any]):
        """Collect feedback on routing decisions"""
        user_id = state.get("user_id")
        if not user_id:
            return
        
        # Record if routing was successful
        await self.learning_loop.record_interaction({
            "type": "routing_feedback",
            "user_id": user_id,
            "query": state.get("query"),
            "intent": state.get("intent"),
            "routing": routing_result.get("routing"),
            "success": routing_result.get("success", True),
            "confidence": state.get("confidence", 0.5)
        })
    
    async def start(self):
        """Start the feedback collector and learning loop"""
        await self.learning_loop.start_background_loop()
        logger.info("Feedback collector started")
    
    async def stop(self):
        """Stop the feedback collector"""
        await self.learning_loop.stop()
        logger.info("Feedback collector stopped")

# Global instance
feedback_collector = FeedbackCollector()