"""
Webhook endpoints for 11Labs Conversational AI
These are called by 11Labs when the agent needs to perform actions
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import structlog

from src.core.graph import search_graph
from src.models.state import SearchState, SearchStrategy, AgentStatus
from src.utils.id_generator import generate_request_id, generate_trace_id
from datetime import datetime
import uuid

# Duplicate SearchRequest model to avoid circular import
class SearchRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    limit: Optional[int] = 10

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/voice/webhook")

# Request/Response models for 11Labs webhooks
class SearchWebhookRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class AddToCartRequest(BaseModel):
    items: List[Dict[str, Any]]
    session_id: Optional[str] = None

class CartRequest(BaseModel):
    session_id: Optional[str] = None

# In-memory session storage (use Redis in production)
voice_sessions = {}


def create_initial_state_for_webhook(request: SearchRequest, alpha: float = 0.5) -> SearchState:
    """Create initial state for webhook search (avoiding circular import)"""
    request_id = generate_request_id()
    trace_id = generate_trace_id()
    
    return {
        "messages": [{
            "role": "human",
            "content": request.query,
            "tool_calls": None,
            "tool_call_id": None
        }],
        "query": request.query,
        "request_id": request_id,
        "timestamp": datetime.utcnow(),
        "alpha_value": alpha,
        "search_strategy": SearchStrategy.HYBRID,
        "next_action": None,
        "reasoning": [],
        "routing_decision": None,
        "should_search": False,
        "search_params": {},
        "search_results": [],
        "search_metadata": {},
        "pending_tool_calls": [],
        "completed_tool_calls": [],
        "session_id": request.session_id or str(uuid.uuid4()),
        "enhanced_query": None,
        "current_order": {"items": []},
        "order_metadata": {},
        "user_context": None,
        "preferences": [],
        "agent_status": {},
        "agent_timings": {},
        "total_execution_time": 0,
        "trace_id": trace_id,
        "span_ids": {},
        "should_continue": True,
        "final_response": {},
        "error": None
    }

@router.post("/search")
async def search_products_webhook(request: SearchWebhookRequest):
    """
    Webhook called by 11Labs when agent needs to search products
    Returns simplified results for voice response
    """
    try:
        # Create search request
        search_req = SearchRequest(
            query=request.query,
            session_id=request.session_id
        )

        # Execute search
        initial_state = create_initial_state_for_webhook(search_req, 0.5)
        final_state = await search_graph.ainvoke(initial_state)

        # Get results
        response_data = final_state.get("final_response", {})
        products = response_data.get("products", [])

        # Store results in session for later reference
        if request.session_id:
            if request.session_id not in voice_sessions:
                voice_sessions[request.session_id] = {"cart": {"items": []}}
            voice_sessions[request.session_id]["last_search"] = products

        # Format for voice response
        if products:
            # Simplify product info for voice
            voice_products = []
            for i, product in enumerate(products[:5]):  # Limit to 5 for voice
                # Include supplier/brand in the name for better identification
                product_name = product.get("product_name", "")
                supplier = product.get("supplier", "")
                
                # Format name with supplier if available
                if supplier and supplier not in product_name:
                    display_name = f"{product_name} - {supplier}"
                else:
                    display_name = product_name
                
                voice_products.append({
                    "position": i + 1,
                    "name": display_name,
                    "price": f"${product.get('price', 0):.2f}",
                    "size": product.get("product_description", ""),
                    "organic": "organic" in product_name.lower(),
                    "supplier": supplier  # Include supplier separately too
                })

            return {
                "success": True,
                "count": len(products),
                "products": voice_products,
                "message": f"I found {len(products)} products. Here are the top options."
            }
        else:
            return {
                "success": True,
                "count": 0,
                "products": [],
                "message": "I couldn't find any products matching your search."
            }

    except Exception as e:
        logger.error(f"Search webhook error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "I had trouble searching. Can you try again?"
        }

@router.post("/add_to_cart")
async def add_to_cart_webhook(request: AddToCartRequest):
    """
    Webhook called by 11Labs when agent needs to add items to cart
    """
    try:
        session_id = request.session_id
        if not session_id or session_id not in voice_sessions:
            return {
                "success": False,
                "message": "I couldn't find your session. Please start over."
            }

        session = voice_sessions[session_id]
        cart = session.get("cart", {"items": []})

        # Add items to cart
        added_count = 0
        for item in request.items:
            # If item references a search result position
            if "position" in item:
                last_search = session.get("last_search", [])
                pos = item["position"] - 1  # Convert to 0-based
                if 0 <= pos < len(last_search):
                    product = last_search[pos]
                    cart["items"].append({
                        "product_id": product.get("sku", ""),
                        "name": product.get("product_name", ""),
                        "quantity": item.get("quantity", 1),
                        "price": product.get("price", 0),
                        "size": product.get("product_description", "")
                    })
                    added_count += 1
            else:
                # Direct item addition
                cart["items"].append(item)
                added_count += 1

        session["cart"] = cart

        return {
            "success": True,
            "items_added": added_count,
            "total_items": len(cart["items"]),
            "message": f"I've added {added_count} items to your cart. You now have {len(cart['items'])} items total."
        }

    except Exception as e:
        logger.error(f"Add to cart webhook error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "I had trouble adding items to your cart."
        }

@router.post("/show_cart")
async def show_cart_webhook(request: CartRequest):
    """
    Webhook called by 11Labs to show current cart
    """
    try:
        session_id = request.session_id
        if not session_id or session_id not in voice_sessions:
            return {
                "success": True,
                "cart": {"items": []},
                "message": "Your cart is empty."
            }

        cart = voice_sessions[session_id].get("cart", {"items": []})

        if not cart["items"]:
            return {
                "success": True,
                "cart": cart,
                "message": "Your cart is empty. What would you like to add?"
            }

        # Format cart for voice
        cart_summary = []
        total = 0
        for item in cart["items"]:
            cart_summary.append(f"{item['quantity']} {item['name']}")
            total += item["quantity"] * item.get("price", 0)

        return {
            "success": True,
            "cart": cart,
            "summary": cart_summary,
            "total": f"${total:.2f}",
            "message": f"You have {len(cart['items'])} items in your cart, totaling {total:.2f} dollars."
        }

    except Exception as e:
        logger.error(f"Show cart webhook error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "I had trouble getting your cart."
        }

@router.post("/confirm_order")
async def confirm_order_webhook(request: CartRequest):
    """
    Webhook called by 11Labs to confirm order
    """
    try:
        session_id = request.session_id
        if not session_id or session_id not in voice_sessions:
            return {
                "success": False,
                "message": "I couldn't find your cart. Please start over."
            }

        cart = voice_sessions[session_id].get("cart", {"items": []})

        if not cart["items"]:
            return {
                "success": False,
                "message": "Your cart is empty. Please add some items first."
            }

        # Calculate total
        total = sum(item["quantity"] * item.get("price", 0) for item in cart["items"])

        # Here you would actually create the order in your system
        # For now, just confirm

        # Clear cart after confirmation
        voice_sessions[session_id]["cart"] = {"items": []}

        return {
            "success": True,
            "order_confirmed": True,
            "total": f"${total:.2f}",
            "message": "Your order has been confirmed. Thank you for shopping with Leaf and Loaf!"
        }

    except Exception as e:
        logger.error(f"Confirm order webhook error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "I had trouble confirming your order."
        }