"""
Promotion agent for handling discount and deal queries
"""
from typing import Dict, Any
from src.agents.base import BaseAgent
from src.models.state import SearchState
from src.services.promotion_service import promotion_service
from src.memory.memory_manager import memory_manager
import structlog

logger = structlog.get_logger()

class PromotionAgent(BaseAgent):
    """Agent for handling promotion-related queries"""
    
    def __init__(self):
        super().__init__("promotion_agent")
        self.promotion_service = promotion_service
        self.session_memory = memory_manager.session_memory
        
    async def _run(self, state: SearchState) -> SearchState:
        """Process promotions - runs automatically in parallel"""
        
        query = state["query"].lower()
        session_id = state.get("session_id")
        routing = state.get("routing_decision", "")
        
        # Always check for applicable promotions when we have a cart
        # or when it's explicitly a promotion query
            
        self.logger.info(f"Promotion agent running for: {query} (routing: {routing})")
        
        # Get current cart if available
        cart_items = []
        if session_id:
            current_order = await self.session_memory.get_current_order(session_id)
            cart_items = current_order.get('items', [])
        
        # Also check if there are items being added in this request
        if state.get("order_response") and state["order_response"].get("items"):
            cart_items = state["order_response"]["items"]
            
        response = ""
        
        # Check if this is an explicit promotion query
        promotion_keywords = ['promotion', 'promo', 'discount', 'deal', 'coupon', 'code', 'save', 'offer']
        is_promotion_query = any(keyword in query for keyword in promotion_keywords)
        
        # Handle different scenarios
        if is_promotion_query and any(word in query for word in ['what', 'show', 'list', 'available', 'current']):
            # Show all promotions
            response = self.promotion_service.get_promotions_summary()
            
        elif 'apply' in query or 'use' in query or 'code' in query:
            # Extract promo code from query
            words = query.split()
            promo_codes = []
            
            # Look for known promo codes
            for word in words:
                word_upper = word.upper()
                if promotion := self.promotion_service.find_promotion_by_code(word_upper):
                    promo_codes.append(word_upper)
                    
            if promo_codes:
                if cart_items:
                    # Apply to current cart
                    result = self.promotion_service.apply_promotions_to_cart(cart_items, promo_codes)
                    response = f"✅ Applied promo code(s): {', '.join(promo_codes)}\n\n"
                    response += f"**Cart Summary:**\n"
                    response += f"• Subtotal: ${result['subtotal']:.2f}\n"
                    response += f"• Discount: -${result['total_discount']:.2f}\n"
                    response += f"• **Total: ${result['final_total']:.2f}**\n"
                    
                    if result['applied_promotions']:
                        response += f"\n**Applied Promotions:**\n"
                        for promo in result['applied_promotions']:
                            response += f"• {promo['name']}: -${promo['discount']:.2f}\n"
                else:
                    response = f"✅ Promo code {promo_codes[0]} is valid! Add items to your cart to see the discount."
            else:
                response = "I couldn't find a valid promo code in your message. Please check the code and try again."
                
        elif any(word in query for word in ['organic', 'dairy', 'milk', 'yogurt']):
            # Check for specific product promotions
            applicable_promos = []
            
            if 'organic' in query:
                applicable_promos.append("**Organic Products 10% Off** - Save on all organic items from Organic Valley and Horizon")
            if any(word in query for word in ['dairy', 'milk', 'yogurt']):
                applicable_promos.append("**Buy 2 Get 1 Free - Dairy** - Mix and match any dairy products")
                
            if applicable_promos:
                response = "🎯 **Relevant Promotions:**\n\n" + "\n".join(applicable_promos)
            else:
                response = "No specific promotions for those items, but check our general discounts!"
                
        elif cart_items and ('discount' in query or 'save' in query or 'total' in query):
            # Show current cart with discounts
            result = self.promotion_service.apply_promotions_to_cart(cart_items)
            response = f"**Your Cart with Discounts:**\n\n"
            response += f"• Subtotal: ${result['subtotal']:.2f}\n"
            
            if result['total_discount'] > 0:
                response += f"• Total Discount: -${result['total_discount']:.2f}\n"
                response += f"• **Final Total: ${result['final_total']:.2f}**\n"
                response += f"• You save: {result['savings_percentage']:.1f}%!\n"
                
                if result['applied_promotions']:
                    response += f"\n**Applied Promotions:**\n"
                    for promo in result['applied_promotions']:
                        response += f"• {promo['name']}: -${promo['discount']:.2f}\n"
            else:
                response += f"• No promotions currently apply to your cart\n"
                response += f"• Add more items or use a promo code to save!"
        
        # ALWAYS calculate discounts if we have cart items (parallel execution)
        if cart_items:
            result = self.promotion_service.apply_promotions_to_cart(cart_items)
            state["cart_discount_info"] = result
            
            # If no explicit response yet, but we have discounts, mention them
            if not response and result.get("total_discount", 0) > 0:
                response = f"🎉 **Great news! You're saving ${result['total_discount']:.2f} on your order!**\n\n"
                for promo in result['applied_promotions']:
                    response += f"• {promo['name']}: -${promo['discount']:.2f}\n"
        
        # Default response if nothing specific
        if not response and is_promotion_query:
            response = self.promotion_service.get_promotions_summary()
        elif not response:
            # Running in parallel - don't generate response unless needed
            response = ""
            
        # Update state with promotion info
        state["promotion_response"] = response
        state["has_promotion_info"] = bool(response) or bool(cart_items)
            
        return state

# Create singleton instance
promotion_agent = PromotionAgent()