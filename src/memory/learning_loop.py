"""
Basic learning loop for Graphiti memory system
Collects feedback and updates patterns
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import structlog
from src.memory.graphiti_wrapper import GraphitiMemoryWrapper
from src.services.analytics_service import analytics_service

logger = structlog.get_logger()

class LearningLoop:
    """Simple learning loop that processes user interactions"""
    
    def __init__(self):
        self.graphiti = GraphitiMemoryWrapper()
        self.pending_feedback = []
        self.is_running = False
        
    async def record_interaction(self, interaction: Dict[str, Any]):
        """Record an interaction for later learning"""
        interaction["timestamp"] = datetime.utcnow().isoformat()
        self.pending_feedback.append(interaction)
        
        # Process immediately if we have enough feedback
        if len(self.pending_feedback) >= 10:
            asyncio.create_task(self._process_batch())
    
    async def record_search_click(self, user_id: str, query: str, clicked_product: Dict[str, Any], position: int):
        """Record when a user clicks on a search result"""
        await self.record_interaction({
            "type": "search_click",
            "user_id": user_id,
            "query": query,
            "clicked_product": {
                "sku": clicked_product.get("sku"),
                "name": clicked_product.get("name"),
                "category": clicked_product.get("category"),
                "brand": clicked_product.get("brand")
            },
            "position": position
        })
    
    async def record_cart_addition(self, user_id: str, product: Dict[str, Any], quantity: int):
        """Record when a user adds to cart"""
        await self.record_interaction({
            "type": "cart_add",
            "user_id": user_id,
            "product": {
                "sku": product.get("sku"),
                "name": product.get("name"),
                "category": product.get("category")
            },
            "quantity": quantity
        })
    
    async def record_order_completion(self, user_id: str, order: Dict[str, Any]):
        """Record when an order is completed"""
        await self.record_interaction({
            "type": "order_complete",
            "user_id": user_id,
            "items": [{
                "sku": item.get("sku"),
                "name": item.get("name"),
                "quantity": item.get("quantity")
            } for item in order.get("items", [])]
        })
    
    async def _process_batch(self):
        """Process a batch of feedback"""
        if not self.pending_feedback:
            return
            
        batch = self.pending_feedback[:50]  # Process up to 50 at a time
        self.pending_feedback = self.pending_feedback[50:]
        
        try:
            # Group by user
            user_feedback = {}
            for feedback in batch:
                user_id = feedback.get("user_id")
                if user_id:
                    if user_id not in user_feedback:
                        user_feedback[user_id] = []
                    user_feedback[user_id].append(feedback)
            
            # Process each user's feedback
            for user_id, feedbacks in user_feedback.items():
                await self._process_user_feedback(user_id, feedbacks)
                
        except Exception as e:
            logger.error(f"Error processing feedback batch: {e}")
    
    async def _process_user_feedback(self, user_id: str, feedbacks: List[Dict[str, Any]]):
        """Process feedback for a single user"""
        try:
            # Get user's Graphiti instance
            memory = await self.graphiti.get_or_create_memory(user_id)
            if not memory:
                return
            
            # Extract patterns
            patterns = self._extract_patterns(feedbacks)
            
            # Update Graphiti with patterns
            for pattern in patterns:
                if pattern["type"] == "search_refinement":
                    # User searches "milk" but clicks "oat milk"
                    await memory.add_episode(
                        content=f"User searched '{pattern['from_query']}' but selected '{pattern['to_product']}'",
                        metadata={
                            "pattern_type": "search_refinement",
                            "confidence": pattern["confidence"]
                        }
                    )
                elif pattern["type"] == "quantity_preference":
                    # User consistently buys 6 bananas
                    await memory.add_episode(
                        content=f"User typically buys {pattern['quantity']} {pattern['product']}",
                        metadata={
                            "pattern_type": "quantity_preference",
                            "product_sku": pattern["sku"]
                        }
                    )
                elif pattern["type"] == "brand_preference":
                    # User prefers specific brands
                    await memory.add_episode(
                        content=f"User prefers {pattern['brand']} for {pattern['category']}",
                        metadata={
                            "pattern_type": "brand_preference",
                            "strength": pattern["strength"]
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Error processing user feedback: {e}")
    
    def _extract_patterns(self, feedbacks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract patterns from feedback"""
        patterns = []
        
        # Search refinement patterns
        search_clicks = [f for f in feedbacks if f["type"] == "search_click"]
        query_groups = {}
        for click in search_clicks:
            query = click["query"].lower()
            if query not in query_groups:
                query_groups[query] = []
            query_groups[query].append(click["clicked_product"])
        
        # Find consistent click patterns
        for query, products in query_groups.items():
            if len(products) >= 2:
                # Check if user consistently clicks different products than query
                product_names = [p["name"].lower() for p in products]
                if all(query not in name for name in product_names):
                    # User searches for X but clicks Y
                    most_common = max(set(product_names), key=product_names.count)
                    patterns.append({
                        "type": "search_refinement",
                        "from_query": query,
                        "to_product": most_common,
                        "confidence": product_names.count(most_common) / len(product_names)
                    })
        
        # Quantity patterns
        cart_adds = [f for f in feedbacks if f["type"] == "cart_add"]
        product_quantities = {}
        for add in cart_adds:
            sku = add["product"]["sku"]
            if sku not in product_quantities:
                product_quantities[sku] = []
            product_quantities[sku].append(add["quantity"])
        
        for sku, quantities in product_quantities.items():
            if len(quantities) >= 2:
                # Check if consistent quantity
                avg_quantity = sum(quantities) / len(quantities)
                if all(abs(q - avg_quantity) <= 1 for q in quantities):
                    patterns.append({
                        "type": "quantity_preference",
                        "sku": sku,
                        "product": cart_adds[0]["product"]["name"],
                        "quantity": int(avg_quantity)
                    })
        
        return patterns
    
    async def start_background_loop(self):
        """Start the background learning loop"""
        if self.is_running:
            return
            
        self.is_running = True
        asyncio.create_task(self._background_processor())
    
    async def _background_processor(self):
        """Background task that processes feedback periodically"""
        while self.is_running:
            try:
                # Process every 30 seconds
                await asyncio.sleep(30)
                await self._process_batch()
            except Exception as e:
                logger.error(f"Background processor error: {e}")
    
    async def stop(self):
        """Stop the learning loop"""
        self.is_running = False
        # Process any remaining feedback
        await self._process_batch()

# Global instance
learning_loop = LearningLoop()