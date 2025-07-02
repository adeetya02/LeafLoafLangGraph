"""
Order management tools for the Order Agent
"""
from typing import Dict, List, Any, Optional
import re
import structlog
from datetime import datetime
import asyncio

logger = structlog.get_logger()


class BaseTool:
    """Base class for tools"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        
    async def run(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool"""
        raise NotImplementedError


class AddToCartTool(BaseTool):
    """Tool to add items to shopping cart"""
    def __init__(self):
        super().__init__(
            "add_to_cart",
            "Add items from search results to the shopping cart"
        )
        
    async def run(self, query: str, search_results: List[Dict], current_order: Dict) -> Dict[str, Any]:
        return await add_to_cart(query, search_results, current_order)


class RemoveFromCartTool(BaseTool):
    """Tool to remove items from cart"""
    def __init__(self):
        super().__init__(
            "remove_from_cart",
            "Remove items from the shopping cart"
        )
        
    async def run(self, query: str, current_order: Dict) -> Dict[str, Any]:
        return await remove_from_cart(query, current_order)


class UpdateCartQuantityTool(BaseTool):
    """Tool to update quantities in cart"""
    def __init__(self):
        super().__init__(
            "update_cart_quantity",
            "Update item quantities in the shopping cart"
        )
        
    async def run(self, query: str, current_order: Dict) -> Dict[str, Any]:
        return await update_cart_quantity(query, current_order)


class ShowCartTool(BaseTool):
    """Tool to display cart contents"""
    def __init__(self):
        super().__init__(
            "show_cart",
            "Display current shopping cart contents"
        )
        
    async def run(self, current_order: Dict) -> Dict[str, Any]:
        return await show_cart(current_order)


class ClearCartTool(BaseTool):
    """Tool to clear the cart"""
    def __init__(self):
        super().__init__(
            "clear_cart",
            "Clear all items from the shopping cart"
        )
        
    async def run(self) -> Dict[str, Any]:
        return await clear_cart()


class ConfirmOrderTool(BaseTool):
    """Tool to confirm order for checkout"""
    def __init__(self):
        super().__init__(
            "confirm_order",
            "Confirm order and prepare for checkout"
        )
        
    async def run(self, current_order: Dict, session_id: Optional[str] = None) -> Dict[str, Any]:
        return await confirm_order(current_order, session_id)


class GetProductForOrderTool(BaseTool):
    """Tool to get product info for ordering"""
    def __init__(self):
        super().__init__(
            "get_product_for_order",
            "Get product information for adding to order"
        )
        
    async def run(self, query: str) -> Dict[str, Any]:
        return await get_product_for_order(query)

async def add_to_cart(
    query: str,
    search_results: List[Dict],
    current_order: Dict
) -> Dict[str, Any]:
    """
    Add items from search results to cart based on user query
    
    Args:
        query: User's natural language request
        search_results: Products found by search agent
        current_order: Current order state
        
    Returns:
        Updated order with success status
    """
    try:
        if not search_results:
            return {
                "success": False,
                "error": "No products available to add",
                "order": current_order
            }
            
        # Parse the query to identify which products and quantities
        items_to_add = _parse_add_request(query, search_results)
        
        if not items_to_add:
            return {
                "success": False,
                "error": "Could not identify which products to add",
                "order": current_order
            }
            
        # Initialize order items if needed
        if "items" not in current_order:
            current_order["items"] = []
            
        # Add items to order
        items_added = 0
        for item in items_to_add:
            # Check if item already exists in cart
            existing_item = next(
                (order_item for order_item in current_order["items"] 
                 if order_item.get("product_id") == item["product_id"]),
                None
            )
            
            if existing_item:
                # Update quantity
                existing_item["quantity"] += item["quantity"]
                logger.info(f"Updated quantity for {item['name']} to {existing_item['quantity']}")
            else:
                # Add new item
                current_order["items"].append({
                    "product_id": item["product_id"],
                    "sku": item.get("sku", ""),
                    "name": item["name"],
                    "quantity": item["quantity"],
                    "unit": item.get("unit", "each"),
                    "price": item.get("price", 0),
                    "added_at": datetime.utcnow().isoformat()
                })
                items_added += 1
                logger.info(f"Added {item['quantity']} {item['name']} to cart")
                
        return {
            "success": True,
            "message": f"Added {items_added} item(s) to your cart",
            "items_added": items_added,
            "order": current_order,
            "total_items": len(current_order["items"])
        }
        
    except Exception as e:
        logger.error(f"Error adding to cart: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "order": current_order
        }


async def remove_from_cart(
    query: str,
    current_order: Dict
) -> Dict[str, Any]:
    """Remove items from cart based on query"""
    try:
        if not current_order.get("items"):
            return {
                "success": False,
                "error": "Cart is empty",
                "order": current_order
            }
            
        # Parse what to remove
        items_to_remove = _parse_remove_request(query, current_order["items"])
        
        if not items_to_remove:
            return {
                "success": False,
                "error": "Could not identify which items to remove",
                "order": current_order
            }
            
        # Remove items
        removed_count = 0
        for item_id in items_to_remove:
            current_order["items"] = [
                item for item in current_order["items"]
                if item.get("product_id") != item_id
            ]
            removed_count += 1
            
        return {
            "success": True,
            "message": f"Removed {removed_count} item(s) from your cart",
            "items_removed": removed_count,
            "order": current_order,
            "remaining_items": len(current_order["items"])
        }
        
    except Exception as e:
        logger.error(f"Error removing from cart: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "order": current_order
        }


async def update_cart_quantity(
    query: str,
    current_order: Dict
) -> Dict[str, Any]:
    """Update quantities in cart"""
    try:
        if not current_order.get("items"):
            return {
                "success": False,
                "error": "Cart is empty",
                "order": current_order
            }
            
        # Parse update request
        updates = _parse_update_request(query, current_order["items"])
        
        if not updates:
            return {
                "success": False,
                "error": "Could not understand the update request",
                "order": current_order
            }
            
        # Apply updates
        updated_count = 0
        for update in updates:
            for item in current_order["items"]:
                if item["product_id"] == update["product_id"]:
                    item["quantity"] = update["new_quantity"]
                    updated_count += 1
                    break
                    
        return {
            "success": True,
            "message": f"Updated {updated_count} item(s) in your cart",
            "updates_made": updated_count,
            "order": current_order
        }
        
    except Exception as e:
        logger.error(f"Error updating cart: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "order": current_order
        }


async def show_cart(current_order: Dict) -> Dict[str, Any]:
    """Display current cart contents"""
    try:
        if not current_order.get("items"):
            return {
                "success": True,
                "message": "Your cart is empty",
                "order": current_order,
                "cart_summary": {
                    "total_items": 0,
                    "total_quantity": 0,
                    "estimated_total": 0
                }
            }
            
        # Create cart summary
        total_quantity = sum(item.get("quantity", 0) for item in current_order["items"])
        estimated_total = sum(
            item.get("quantity", 0) * item.get("price", 0) 
            for item in current_order["items"]
        )
        
        cart_display = []
        for item in current_order["items"]:
            cart_display.append({
                "name": item["name"],
                "quantity": item["quantity"],
                "unit": item.get("unit", "each"),
                "price": item.get("price", 0),
                "subtotal": item["quantity"] * item.get("price", 0)
            })
            
        return {
            "success": True,
            "message": f"You have {len(current_order['items'])} item(s) in your cart",
            "order": current_order,
            "cart_summary": {
                "total_items": len(current_order["items"]),
                "total_quantity": total_quantity,
                "estimated_total": estimated_total,
                "items": cart_display
            }
        }
        
    except Exception as e:
        logger.error(f"Error showing cart: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "order": current_order
        }


async def clear_cart() -> Dict[str, Any]:
    """Clear all items from cart"""
    return {
        "success": True,
        "message": "Cart has been cleared",
        "order": {"items": []}
    }


async def confirm_order(
    current_order: Dict,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Confirm order for checkout"""
    try:
        if not current_order.get("items"):
            return {
                "success": False,
                "error": "Cannot confirm an empty order",
                "order": current_order
            }
            
        # Calculate totals
        total_quantity = sum(item.get("quantity", 0) for item in current_order["items"])
        estimated_total = sum(
            item.get("quantity", 0) * item.get("price", 0) 
            for item in current_order["items"]
        )
        
        # Add order metadata
        current_order["confirmed_at"] = datetime.utcnow().isoformat()
        current_order["status"] = "confirmed"
        current_order["session_id"] = session_id
        current_order["total"] = estimated_total  # Add direct total field
        current_order["totals"] = {
            "item_count": len(current_order["items"]),
            "total_quantity": total_quantity,
            "estimated_total": estimated_total
        }
        
        # Generate order ID if not present
        if "order_id" not in current_order:
            from src.utils.id_generator import generate_order_id
            current_order["order_id"] = generate_order_id()
        
        # Get user_id from session or order
        user_id = current_order.get("user_id") or session_id or "anonymous"
        
        # Send order to Graphiti for memory and knowledge graph
        try:
            from src.memory.memory_registry import MemoryRegistry
            from src.memory.memory_interfaces import MemoryBackend
            import os
            
            # Get or create Graphiti memory manager
            backend = MemoryBackend.SPANNER if os.getenv("SPANNER_INSTANCE_ID") else MemoryBackend.IN_MEMORY
            memory_manager = MemoryRegistry.get_or_create(
                "order_confirmation",
                config={"backend": backend}
            )
            
            # Process the order in Graphiti
            order_data = {
                "order_id": current_order["order_id"],
                "user_id": user_id,
                "session_id": session_id,
                "items": current_order["items"],
                "totals": current_order["totals"],
                "timestamp": current_order["confirmed_at"],
                "status": "confirmed"
            }
            
            # Send to Graphiti (non-blocking)
            asyncio.create_task(
                memory_manager.process_order(order_data)
            )
            logger.info(f"Order {current_order['order_id']} sent to Graphiti")
            
        except Exception as e:
            logger.error(f"Failed to send order to Graphiti: {e}")
            # Continue - don't fail the order confirmation
        
        # Send order to data capture pipeline (BigQuery)
        try:
            from src.data_capture.capture_strategy import FlexibleDataCapture
            data_capture = FlexibleDataCapture()
            
            # Capture order event (non-blocking)
            asyncio.create_task(
                data_capture.capture_order({
                    "order_id": current_order["order_id"],
                    "user_id": user_id,
                    "session_id": session_id,
                    "items": current_order["items"],
                    "totals": current_order["totals"],
                    "timestamp": current_order["confirmed_at"],
                    "metadata": {
                        "source": "order_tools",
                        "version": "1.0"
                    }
                })
            )
            logger.info(f"Order {current_order['order_id']} sent to data pipeline")
            
        except Exception as e:
            logger.error(f"Failed to capture order data: {e}")
            # Continue - don't fail the order confirmation
        
        # Voice confirmation message
        voice_message = "Your order has been confirmed. Thank you for shopping with Leaf and Loaf."
        
        # Try to speak the confirmation (if 11Labs is configured)
        try:
            from src.integrations.elevenlabs_voice import ElevenLabsClient
            voice_client = ElevenLabsClient()
            # This will be async - the UI can play the audio
            audio_data = await voice_client.text_to_speech(voice_message)
            voice_enabled = bool(audio_data)
        except Exception as e:
            logger.info(f"Voice confirmation not available: {e}")
            voice_enabled = False
        
        return {
            "success": True,
            "message": voice_message,
            "order": current_order,
            "order_id": current_order["order_id"],
            "next_steps": "Proceed to payment and delivery details",
            "voice_enabled": voice_enabled,
            "voice_message": voice_message
        }
        
    except Exception as e:
        logger.error(f"Error confirming order: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "order": current_order
        }


async def get_product_for_order(query: str) -> Dict[str, Any]:
    """
    Get product information for order (placeholder for when we need to search)
    In production, this would call the product search
    """
    return {
        "success": False,
        "error": "Product search from order agent not implemented yet",
        "message": "Please search for products first, then add them to your cart"
    }


# Helper functions
def _parse_add_request(query: str, search_results: List[Dict]) -> List[Dict]:
    """Parse which items and quantities to add from the query"""
    query_lower = query.lower()
    items_to_add = []
    
    # Extract quantity patterns
    quantity_pattern = r'(\d+)\s*(gallons?|gal|liters?|l|pounds?|lbs?|kg|items?|bottles?|cans?|boxes?|packs?)?'
    quantity_matches = re.findall(quantity_pattern, query_lower)
    default_quantity = 1
    
    if quantity_matches:
        # Use the first quantity found
        default_quantity = int(quantity_matches[0][0])
        
    # Try to match specific products mentioned
    for product in search_results:
        product_name_lower = product.get("name", "").lower()
        
        # Check if product name or key words are in query
        name_words = product_name_lower.split()
        matches = sum(1 for word in name_words if len(word) > 3 and word in query_lower)
        
        # If significant match, add to cart
        if matches >= 2 or (matches == 1 and len(name_words) <= 2):
            items_to_add.append({
                "product_id": product.get("sku", ""),
                "sku": product.get("sku", ""),
                "name": product.get("name", ""),
                "quantity": default_quantity,
                "unit": product.get("pack_size", product.get("unit", "each")),
                "price": product.get("price", 0)
            })
            
            # If query mentions specific product, only add that one
            if any(brand in query_lower for brand in ["organic valley", "pacific", "califia"]):
                break
                
    # If no specific matches but user said "add milk" or similar, add first relevant item
    if not items_to_add and search_results:
        items_to_add.append({
            "product_id": search_results[0].get("sku", ""),
            "sku": search_results[0].get("sku", ""),
            "name": search_results[0].get("name", ""),
            "quantity": default_quantity,
            "unit": search_results[0].get("pack_size", "each"),
            "price": search_results[0].get("price", 0)
        })
        
    return items_to_add


def _parse_remove_request(query: str, cart_items: List[Dict]) -> List[str]:
    """Parse which items to remove from the query"""
    query_lower = query.lower()
    items_to_remove = []
    
    # Check each cart item
    for item in cart_items:
        item_name_lower = item.get("name", "").lower()
        
        # Check if item is mentioned in remove query
        name_words = item_name_lower.split()
        if any(word in query_lower for word in name_words if len(word) > 3):
            items_to_remove.append(item.get("product_id"))
            
    # If "all" or "everything" mentioned, remove all
    if any(word in query_lower for word in ["all", "everything", "entire"]):
        items_to_remove = [item.get("product_id") for item in cart_items]
        
    return items_to_remove


def _parse_update_request(query: str, cart_items: List[Dict]) -> List[Dict]:
    """Parse quantity updates from the query"""
    query_lower = query.lower()
    updates = []
    
    # Extract new quantity
    quantity_pattern = r'(\d+)\s*(gallons?|gal|liters?|l|pounds?|lbs?|kg|items?|bottles?|cans?|boxes?|packs?)?'
    quantity_matches = re.findall(quantity_pattern, query_lower)
    
    if not quantity_matches:
        return updates
        
    new_quantity = int(quantity_matches[0][0])
    
    # Find which item to update
    for item in cart_items:
        item_name_lower = item.get("name", "").lower()
        name_words = item_name_lower.split()
        
        if any(word in query_lower for word in name_words if len(word) > 3):
            updates.append({
                "product_id": item.get("product_id"),
                "new_quantity": new_quantity
            })
            
    return updates


# Tool instances
add_to_cart_tool = AddToCartTool()
remove_from_cart_tool = RemoveFromCartTool()
update_cart_quantity_tool = UpdateCartQuantityTool()
show_cart_tool = ShowCartTool()
clear_cart_tool = ClearCartTool()
confirm_order_tool = ConfirmOrderTool()
get_product_for_order_tool = GetProductForOrderTool()

# Export all order tools
ORDER_TOOLS = {
    "add_to_cart": add_to_cart_tool,
    "remove_from_cart": remove_from_cart_tool,
    "update_cart_quantity": update_cart_quantity_tool,
    "show_cart": show_cart_tool,
    "clear_cart": clear_cart_tool,
    "confirm_order": confirm_order_tool,
    "get_product_for_order": get_product_for_order_tool
}