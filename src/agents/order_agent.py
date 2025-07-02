from typing import Dict, Any, List, Optional
from langsmith import traceable
from src.agents.memory_aware_base import MemoryAwareAgent
from src.models.state import SearchState
from src.tools.tool_executor import tool_executor
from src.memory.memory_manager import memory_manager
from src.memory.graphiti_wrapper import GraphitiMemoryWrapper
from src.services.analytics_service import analytics_service
import asyncio
import json
import structlog

logger = structlog.get_logger()

class OrderReactAgent(MemoryAwareAgent):
    """Memory-aware Order management agent with tool calling capabilities"""
    
    def __init__(self):
        super().__init__("order_agent")
        self.tool_executor = tool_executor
        self.session_memory = memory_manager.session_memory
        self.max_iterations = 3
        self.graphiti_wrapper = GraphitiMemoryWrapper()
    
    async def _get_agent_specific_context(self, user_id: str, session_id: str, query: str, base_context: Dict) -> Dict[str, Any]:
        """Get order-specific memory context"""
        # Get order patterns for mentioned products
        order_patterns = {}
        
        # Extract product from query (simple for now)
        query_lower = query.lower()
        for word in query_lower.split():
            if len(word) > 3:  # Skip short words
                patterns = await self.graphiti_wrapper.get_order_patterns(user_id, word)
                if patterns.get("usual_quantity", 1) > 1:
                    order_patterns[word] = patterns
        
        # Get reorder predictions for proactive suggestions
        reorder_predictions = await self.graphiti_wrapper.get_reorder_predictions(user_id)
        
        # Get user preferences for quantity and brand suggestions
        preferences = await self.graphiti_wrapper.get_learned_preferences(user_id, session_id)
        
        # Get product associations for the query
        product_associations = {}
        for word in query_lower.split():
            if len(word) > 3:
                associations = await self.graphiti_wrapper.get_product_associations(f"product:{word}")
                if associations.get("complementary"):
                    product_associations[word] = associations["complementary"][:3]  # Top 3
        
        return {
            "order_patterns": order_patterns,
            "has_quantity_preferences": bool(order_patterns),
            "reorder_predictions": reorder_predictions[:5],  # Top 5 items due for reorder
            "user_preferences": preferences,
            "product_suggestions": product_associations
        }
        
    async def _run(self, state: SearchState) -> SearchState:
        """Autonomous order management with React pattern"""
        
        # Check if we should run
        routing = state.get("routing_decision")
        if routing != "order_agent":
            self.logger.info(f"Not routed to order agent (routing={routing}), skipping")
            return state
            
        # Get context
        query = state["query"]
        session_id = state.get("session_id")
        user_id = state.get("user_id")
        search_results = state.get("search_results", [])
        iterations = 0
        intent = state.get("intent", "")
        metadata = state.get("search_params", {}).get("metadata", {})
        
        self.logger.info(f"Order agent starting - session_id: {session_id}, intent: {intent}, initial search_results: {len(search_results)}")
        
        # Get memory context for better quantity suggestions
        memory_context = {}
        if user_id:
            try:
                memory_context = await asyncio.wait_for(
                    self.get_memory_context(user_id, session_id, query),
                    timeout=0.1  # 100ms timeout
                )
            except asyncio.TimeoutError:
                logger.debug("Memory context fetch timed out")
        
        # Handle Graphiti-based intents
        if intent in ["usual_order", "repeat_order", "event_order"] and user_id and session_id:
            search_results = await self._handle_graphiti_intent(
                intent, user_id, session_id, metadata, state
            )
            self.logger.info(f"Graphiti intent {intent} resolved to {len(search_results)} products")
        
        # Load current order from session
        current_order = {}
        if session_id:
            current_order = await self.session_memory.get_current_order(session_id)
            
            # If no search results in state, check session memory for recent searches
            if not search_results:
                self.logger.info(f"No search results in state, checking session memory for session_id: {session_id}")
                session_search_results = await self.session_memory.get_recent_search_results(session_id)
                if session_search_results:
                    self.logger.info(f"Using {len(session_search_results)} products from recent search")
                    search_results = session_search_results  # Update the search_results variable!
                else:
                    self.logger.info("No search results found in session memory either")
            
        state["messages"].append({
            "role": "assistant",
            "content": f"Processing order request: {query}",
            "tool_calls": None,
            "tool_call_id": None
        })
        
        while iterations < self.max_iterations:
            iterations += 1
            
            # REASON: What order tools should we call?
            self.logger.info(f"Planning tools - iteration {iterations}, search_results: {len(search_results)} products")
            tool_plan = self._plan_order_tools(state, query, current_order, search_results, iterations, memory_context)
            state["reasoning"].append(f"Order iteration {iterations}: {tool_plan['reasoning']}")
            
            if not tool_plan["tool_calls"]:
                break
                
            # ACT: Execute tools
            state["messages"].append({
                "role": "assistant",
                "content": tool_plan["reasoning"],
                "tool_calls": tool_plan["tool_calls"],
                "tool_call_id": None
            })
            
            # Execute all tool calls
            results = await self._execute_parallel_tools(tool_plan["tool_calls"])
            
            # OBSERVE: Process results
            for result in results:
                state["messages"].append({
                    "role": "tool",
                    "content": json.dumps(result["result"]),
                    "tool_calls": None,
                    "tool_call_id": result["tool_call_id"]
                })
                state["completed_tool_calls"].append(result)
                
                # Update current order from tool results
                if result["result"].get("success") and result["result"].get("order"):
                    current_order = result["result"]["order"]
                    
                    # Track cart events
                    if result["name"] == "add_to_cart" and result["result"].get("items_added"):
                        for item in result["result"]["items_added"]:
                            asyncio.create_task(analytics_service.track_cart_event({
                                "session_id": session_id or "",
                                "event_type": "add",
                                "product_sku": item.get("sku", ""),
                                "product_name": item.get("name", ""),
                                "quantity": item.get("quantity", 1),
                                "price": item.get("price", 0),
                                "cart_total_after": current_order.get("total", 0),
                                "promotions_applied": current_order.get("promotions", []),
                                "discount_total": current_order.get("discount_total", 0),
                                "savings_percentage": current_order.get("savings_percentage", 0)
                            }))
                    
                    elif result["name"] == "remove_from_cart" and result["result"].get("items_removed"):
                        for item in result["result"]["items_removed"]:
                            asyncio.create_task(analytics_service.track_cart_event({
                                "session_id": session_id or "",
                                "event_type": "remove",
                                "product_sku": item.get("sku", ""),
                                "product_name": item.get("name", ""),
                                "quantity": item.get("quantity", 1),
                                "price": item.get("price", 0),
                                "cart_total_after": current_order.get("total", 0)
                            }))
                    
            # Analyze if we need more iterations
            analysis = self._analyze_order_results(results, query, current_order)
            state["reasoning"].append(analysis["reasoning"])
            
            if analysis["complete"]:
                # Save order to session
                if session_id:
                    await self.session_memory.update_order(session_id, current_order)
                    
                # Update state with final order
                state["current_order"] = current_order
                state["order_metadata"] = {
                    "total_items": len(current_order.get("items", [])),
                    "last_action": analysis.get("action", "unknown"),
                    "session_id": session_id
                }
                break
                
        return state
    
    @traceable(name="Order Tool Planning")    
    def _plan_order_tools(self, state: SearchState, query: str, current_order: Dict, 
                         search_results: List[Dict], iteration: int, memory_context: Dict = None) -> Dict:
        """Plan which order tools to call based on current state"""
        tool_calls = []
        query_lower = query.lower()
        
        # Analyze query intent
        intent = self._analyze_order_intent(query_lower, current_order, search_results)
        
        if iteration == 1:
            if intent["action"] == "add":
                if search_results:
                    # We have search results to work with
                    # Add memory context for quantity suggestions
                    args = {
                        "query": query,
                        "search_results": search_results,
                        "current_order": current_order
                    }
                    
                    # Add quantity suggestions from memory
                    if memory_context and memory_context.get("order_patterns"):
                        quantity_suggestions = {}
                        for product in search_results[:5]:  # Top 5 results
                            product_name = product.get("name", "").lower()
                            for pattern_key, pattern in memory_context["order_patterns"].items():
                                if pattern_key in product_name:
                                    quantity_suggestions[product.get("sku", product.get("product_id"))] = pattern["usual_quantity"]
                        if quantity_suggestions:
                            args["quantity_suggestions"] = quantity_suggestions
                            reasoning = f"Adding items with your usual quantities based on: '{query}'"
                        else:
                            reasoning = f"Adding items to cart based on: '{query}'"
                    else:
                        reasoning = f"Adding items to cart based on: '{query}'"
                    
                    # Add complementary product suggestions
                    if memory_context.get("product_suggestions"):
                        args["complementary_suggestions"] = memory_context["product_suggestions"]
                        reasoning += " (with complementary suggestions)"
                    
                    # Add reorder reminders if available
                    if memory_context.get("reorder_predictions"):
                        args["reorder_reminders"] = [
                            {
                                "name": item["name"],
                                "days_since": item["days_since_last"],
                                "usual_qty": item["usual_quantity"]
                            }
                            for item in memory_context["reorder_predictions"][:3]
                        ]
                    
                    tool_calls = [{
                        "id": f"call_add_to_cart_{iteration}",
                        "name": "add_to_cart",
                        "args": args
                    }]
                else:
                    # Need product info first
                    tool_calls = [{
                        "id": f"call_get_product_info_{iteration}",
                        "name": "get_product_for_order",
                        "args": {"query": query}
                    }]
                    reasoning = "Need to get product information first"
                    
            elif intent["action"] == "remove":
                tool_calls = [{
                    "id": f"call_remove_from_cart_{iteration}",
                    "name": "remove_from_cart",
                    "args": {
                        "query": query,
                        "current_order": current_order
                    }
                }]
                reasoning = f"Removing items from cart based on: '{query}'"
                
            elif intent["action"] == "update":
                tool_calls = [{
                    "id": f"call_update_cart_{iteration}",
                    "name": "update_cart_quantity",
                    "args": {
                        "query": query,
                        "current_order": current_order
                    }
                }]
                reasoning = f"Updating cart quantities based on: '{query}'"
                
            elif intent["action"] == "show":
                tool_calls = [{
                    "id": f"call_show_cart_{iteration}",
                    "name": "show_cart",
                    "args": {"current_order": current_order}
                }]
                reasoning = "Showing current cart contents"
                
            elif intent["action"] == "clear":
                tool_calls = [{
                    "id": f"call_clear_cart_{iteration}",
                    "name": "clear_cart",
                    "args": {}
                }]
                reasoning = "Clearing all items from cart"
                
            elif intent["action"] == "confirm":
                tool_calls = [{
                    "id": f"call_confirm_order_{iteration}",
                    "name": "confirm_order",
                    "args": {
                        "current_order": current_order,
                        "session_id": state.get("session_id")
                    }
                }]
                reasoning = "Confirming order for checkout"
                
        elif iteration == 2:
            # Second iteration - might need to refine or get more info
            if intent["action"] == "add" and not current_order.get("items"):
                # First attempt didn't add items, try again
                reasoning = "Retrying to add items with more specific search"
            else:
                reasoning = "Order action completed"
                
        return {
            "tool_calls": tool_calls,
            "reasoning": reasoning,
            "intent": intent
        }
    
    def _analyze_order_intent(self, query_lower: str, current_order: Dict, 
                             search_results: List[Dict]) -> Dict:
        """Analyze what order action the user wants"""
        
        # Check for specific action keywords
        if any(word in query_lower for word in ["add", "want", "need", "get"]):
            return {"action": "add", "confidence": 0.9}
        elif any(word in query_lower for word in ["remove", "delete", "don't want", "take out"]):
            return {"action": "remove", "confidence": 0.9}
        elif any(word in query_lower for word in ["update", "change", "instead of", "make it"]):
            return {"action": "update", "confidence": 0.8}
        elif any(word in query_lower for word in ["show", "what's in", "list", "my cart", "my order"]):
            return {"action": "show", "confidence": 0.9}
        elif any(word in query_lower for word in ["clear", "empty", "start over", "new order"]):
            return {"action": "clear", "confidence": 0.9}
        elif any(word in query_lower for word in ["confirm", "checkout", "place order", "done", "that's it"]):
            return {"action": "confirm", "confidence": 0.9}
        else:
            # Default to add if we have search results
            if search_results:
                return {"action": "add", "confidence": 0.6}
            else:
                return {"action": "show", "confidence": 0.5}
    
    async def _execute_parallel_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        """Execute multiple tool calls in parallel"""
        tasks = []
        for tool_call in tool_calls:
            task = self.tool_executor.execute_tool_call(tool_call)
            tasks.append(task)
            
        # Execute all tools in parallel
        results = await asyncio.gather(*tasks)
        return results
    
    def _analyze_order_results(self, results: List[Dict], query: str, current_order: Dict) -> Dict:
        """Analyze tool results and decide next steps"""
        
        if not results:
            return {
                "complete": True,
                "reasoning": "No tool results to process",
                "action": "none"
            }
            
        # Check first result
        result = results[0]
        tool_name = result.get("name", "")
        success = result.get("result", {}).get("success", False)
        
        if tool_name == "add_to_cart" and success:
            items_added = result["result"].get("items_added", 0)
            return {
                "complete": True,
                "reasoning": f"Successfully added {items_added} item(s) to cart",
                "action": "add"
            }
        elif tool_name == "remove_from_cart" and success:
            return {
                "complete": True,
                "reasoning": "Successfully removed item(s) from cart",
                "action": "remove"
            }
        elif tool_name == "show_cart":
            return {
                "complete": True,
                "reasoning": "Cart contents displayed",
                "action": "show"
            }
        elif tool_name == "confirm_order" and success:
            return {
                "complete": True,
                "reasoning": "Order confirmed and ready for checkout",
                "action": "confirm"
            }
        else:
            return {
                "complete": False,
                "reasoning": f"Tool {tool_name} needs another iteration",
                "action": tool_name
            }
    
    async def _handle_graphiti_intent(
        self, 
        intent: str, 
        user_id: str, 
        session_id: str, 
        metadata: Dict[str, Any],
        state: SearchState
    ) -> List[Dict]:
        """Handle Graphiti-based intents like 'usual order', 'repeat order', etc."""
        
        try:
            # Get or create Graphiti memory manager
            from src.memory.memory_registry import MemoryRegistry
            from src.memory.memory_interfaces import MemoryBackend
            import os
            
            # Check if Spanner is configured
            backend = MemoryBackend.SPANNER if os.getenv("SPANNER_INSTANCE_ID") else MemoryBackend.IN_MEMORY
            
            memory_manager = MemoryRegistry.get_or_create(
                "order_agent",
                config={"backend": backend}
            )
            
            # For Graphiti operations, we need the actual instance
            from src.memory.graphiti_memory_spanner import GraphitiMemorySpanner
            graphiti_memory = GraphitiMemorySpanner(user_id=user_id, session_id=session_id)
            await graphiti_memory.initialize()
            
            if not graphiti_memory:
                self.logger.warning("Graphiti memory not available")
                return []
            
            products = []
            
            if intent == "usual_order":
                # Get reorder patterns from metadata or fetch fresh
                reorder_patterns = metadata.get("reorder_patterns", [])
                if not reorder_patterns:
                    # Use the wrapper to get reorder predictions
                    reorder_patterns = await self.graphiti_wrapper.get_reorder_predictions(user_id)
                
                # Convert patterns to product format - patterns already have the right structure
                for pattern in reorder_patterns[:10]:  # Top 10 usual items
                    product = {
                        "sku": pattern.get("sku"),
                        "name": pattern.get("name"),
                        "usual_quantity": pattern.get("usual_quantity", 1),
                        "days_since_last_order": pattern.get("days_since_last", 0),
                        "is_due": True,  # Already filtered by wrapper
                        "confidence": pattern.get("confidence", 0)
                    }
                    products.append(product)
                
                # Add message about usual order
                state["messages"].append({
                    "role": "assistant",
                    "content": f"Found your usual order with {len(products)} regular items",
                    "tool_calls": None,
                    "tool_call_id": None
                })
                
            elif intent == "repeat_order":
                # Get last order details
                query_entities = metadata.get("query_entities", [])
                
                # Find specific product mentioned or get last order
                if query_entities:
                    # Look for specific product in entities
                    for entity in query_entities:
                        if entity.get("type") == "PRODUCT":
                            # Get last order of this product
                            product_name = entity.get("value")
                            # Query for last order of this product
                            # (simplified - in production would query Neo4j)
                            products.append({
                                "name": product_name,
                                "repeat_request": True
                            })
                else:
                    # Get last complete order
                    user_context = await graphiti_memory.get_context("")
                    recent_orders = user_context.get("user_context", {}).get("recent_orders", [])
                    
                    if recent_orders:
                        # Get items from most recent order
                        # (simplified - would parse order details)
                        state["messages"].append({
                            "role": "assistant",
                            "content": "Getting items from your last order",
                            "tool_calls": None,
                            "tool_call_id": None
                        })
            
            elif intent == "event_order":
                # Get previous event orders
                event_history = metadata.get("event_history", [])
                
                # Find similar events
                state["messages"].append({
                    "role": "assistant",
                    "content": "Looking up your previous event orders",
                    "tool_calls": None,
                    "tool_call_id": None
                })
                
                # Would query for event-specific orders
                # (simplified for now)
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error handling Graphiti intent: {e}")
            return []