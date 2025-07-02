from typing import Dict, Any, List
from src.agents.memory_aware_base import MemoryAwareAgent
from src.models.state import SearchState
from src.services.analytics_service import analytics_service
from src.memory.graphiti_wrapper import GraphitiMemoryWrapper
import asyncio
import json
import time

class ResponseCompilerAgent(MemoryAwareAgent):
  """Memory-aware agent that compiles final response from search results"""
  
  def __init__(self):
      super().__init__("response_compiler")
      self.graphiti_wrapper = GraphitiMemoryWrapper()
  
  async def _get_agent_specific_context(self, user_id: str, session_id: str, query: str, base_context: Dict) -> Dict[str, Any]:
      """Get response compiler-specific memory context"""
      # Get communication style preferences
      comm_style = await self.graphiti_wrapper.get_communication_style(user_id)
      
      # Get user preferences for response formatting
      preferences = await self.graphiti_wrapper.get_learned_preferences(user_id, session_id)
      
      return {
          "communication_style": comm_style,
          "user_preferences": preferences,
          "preferred_response_format": comm_style.get("format", "list")
      }
      
  async def _run(self, state: SearchState) -> SearchState:
      """Compile final response from all agent outputs"""
      start_time = time.time()
      
      # Check what type of response we need to compile
      routing = state.get("routing_decision", "")
      has_promotions = state.get("has_promotion_info", False)
      has_products = len(state.get("search_results", [])) > 0
      has_order = state.get("order_response") is not None
      
      # If we have multiple types of data, compile a merged response
      if (has_promotions and has_products) or (has_promotions and has_order):
          return await self._compile_merged_response(state)
      # Check if this is an order operation
      elif routing == "order_agent" or has_order:
          return await self._compile_order_response(state)
      # Check if this is a promotion query
      elif routing == "promotion_agent":
          return await self._compile_promotion_response(state)
      # Check if this is general chat
      elif routing == "general_chat" or state.get("is_general_chat"):
          return await self._compile_chat_response(state)
      
      # Otherwise compile search response
      self.logger.info(f"Response Compiler received state with {len(state.get('search_results', []))} products")    
      # Get search results
      products = state.get("search_results", [])
      search_metadata = state.get("search_metadata", {})
      
      # Get execution metadata
      agent_timings = state.get("agent_timings", {})
      reasoning_steps = list(dict.fromkeys(state.get("reasoning", [])))  # Deduplicate reasoning
      
      # Build final response
      final_response = {
          "success": len(products) > 0,
          "query": state["query"],
          "products": self._format_products(products),
          "metadata": {
              "total_count": len(products),
              "original_count": search_metadata.get("original_count", len(products)),
              "category_filtered": search_metadata.get("category_filtered", False),
              "excluded_categories": search_metadata.get("excluded_categories", []),
              "categories": search_metadata.get("categories", []),
              "brands": search_metadata.get("brands", []),
              "search_metadata": search_metadata,  # Include all search metadata
              "search_config": {
                  **search_metadata.get("search_config", {}),
                  "alpha": search_metadata.get("alpha", 0)
              }
          },
          "execution": {
              "total_time_ms": sum(agent_timings.values()),
              "agent_timings": agent_timings,
              "reasoning_steps": reasoning_steps,
              "agents_run": [agent for agent, status in state["agent_status"].items() 
                           if status == "completed"]
          },
          "langsmith_trace_id": state.get("trace_id")
      }
      
      # Add personalization if user_id present and data available
      if state.get("user_id") and state.get("personalization_data"):
          final_response["personalization"] = self._compile_personalization_section(state)
          
          # Add personalization metadata
          if "personalization_metadata" not in final_response["metadata"]:
              final_response["metadata"]["personalization_metadata"] = {}
          
          pers_data = state.get("personalization_data", {})
          final_response["metadata"]["personalization_metadata"].update({
              "features_used": pers_data.get("features_used", []),
              "processing_time_ms": pers_data.get("processing_time_ms", 0)
          })
      
      # Add pattern-based insights if available
      user_id = state.get("user_id")
      session_id = state.get("session_id")
      if user_id:
          try:
              # Get memory context
              memory_context = await asyncio.wait_for(
                  self.get_memory_context(user_id, session_id, state["query"]),
                  timeout=0.1  # 100ms timeout
              )
              
              # Add reorder reminders if available
              if memory_context.get("reorder_predictions"):
                  final_response["reorder_reminders"] = [
                      {
                          "sku": item["sku"],
                          "name": item["name"],
                          "days_since_last": item["days_since_last"],
                          "usual_quantity": item["usual_quantity"]
                      }
                      for item in memory_context["reorder_predictions"][:3]
                  ]
              
              # Format response based on communication style
              comm_style = memory_context.get("communication_style", {})
              if comm_style.get("style") == "concise":
                  # Simplify the response structure
                  final_response["simplified"] = True
                  
          except asyncio.TimeoutError:
              self.logger.debug("Memory context fetch timed out")
      
      # Add helpful message
      if len(products) == 0:
          final_response["message"] = "No products found. Try broadening your search."
      elif len(products) == 1:
          final_response["message"] = "Found 1 product matching your search."
      else:
          final_response["message"] = f"Found {len(products)} products matching your search."
      
      state["final_response"] = final_response
      
      # Add timing
      elapsed = (time.time() - start_time) * 1000
      if "agent_timings" not in state:
          state["agent_timings"] = {}
      state["agent_timings"]["response_compiler"] = elapsed
      
      # Update total time in response
      final_response["execution"]["total_time_ms"] = sum(state["agent_timings"].values())
      
      # Log summary
      self.logger.info(
          "Response compiled",
          products_found=len(products),
          total_time_ms=final_response["execution"]["total_time_ms"]
      )
      
      # Track complete agent flow
      asyncio.create_task(analytics_service.track_agent_execution(state))
      
      return state
  
  def _format_products(self, products: List[Dict]) -> List[Dict]:
      """Format products for response - includes SKU for cart operations"""
      formatted_products = []
      
      for product in products[:15]:  # Limit to 15 products as requested
          formatted_product = {
              "sku": product.get("sku", ""),  # Unique identifier for cart operations
              "product_name": product.get("name", ""),
              "product_description": product.get("description", ""),
              "price": product.get("price", 0.0),
              "unit": product.get("unit", "each"),
              "price_display": product.get("price_display", ""),
              "category": product.get("category", ""),
              "supplier": product.get("supplier", ""),
              "is_organic": product.get("is_organic", False),
              "in_stock": product.get("in_stock", True)
          }
          
          # Keep all fields including SKU (don't remove empty ones)
          formatted_products.append(formatted_product)
      
      return formatted_products
  
  def _compile_personalization_section(self, state: SearchState) -> Dict[str, Any]:
      """Compile personalization section with user preferences and recommendations"""
      pers_data = state.get("personalization_data", {})
      user_prefs = state.get("user_preferences", {})
      
      # Check if personalization is enabled
      enabled = True
      if user_prefs:
          enabled = user_prefs.get("personalization", {}).get("enabled", True)
      
      # Get feature flags
      feature_flags = {}
      if user_prefs and "personalization" in user_prefs:
          feature_flags = user_prefs["personalization"].get("features", {})
      
      # Build personalization section
      personalization = {
          "enabled": enabled,
          "usual_items": [],
          "reorder_suggestions": [],
          "complementary_products": [],
          "applied_features": pers_data.get("applied_features", []),
          "confidence": self._calculate_confidence(pers_data)
      }
      
      # Add usual items if feature enabled
      if feature_flags.get("usual_orders", True):
          personalization["usual_items"] = pers_data.get("usual_items", [])
      
      # Add reorder suggestions if feature enabled
      if feature_flags.get("reorder_reminders", True):
          personalization["reorder_suggestions"] = pers_data.get("reorder_suggestions", [])
      
      # Add complementary products if feature enabled
      if feature_flags.get("complementary_items", True):
          personalization["complementary_products"] = pers_data.get("complementary_products", [])
      
      # Filter applied features based on what's enabled
      if feature_flags:
          enabled_features = [f for f in feature_flags.keys() if feature_flags.get(f, True)]
          personalization["applied_features"] = [
              f for f in personalization["applied_features"] 
              if f in enabled_features or f.replace("_", " ").replace(" ", "_") in enabled_features
          ]
      
      return personalization
  
  def _calculate_confidence(self, pers_data: Dict[str, Any]) -> float:
      """Calculate personalization confidence score based on available data"""
      confidence_factors = pers_data.get("confidence_factors", {})
      
      if confidence_factors:
          # Use provided confidence factors
          data_points = confidence_factors.get("data_points", 0)
          recency = confidence_factors.get("recency", 0.5)
          consistency = confidence_factors.get("consistency", 0.5)
          
          # Weight the factors
          if data_points >= 50:
              data_score = 0.9
          elif data_points >= 20:
              data_score = 0.7
          elif data_points >= 10:
              data_score = 0.5
          else:
              data_score = 0.3
          
          # Calculate weighted confidence
          confidence = (data_score * 0.5) + (recency * 0.3) + (consistency * 0.2)
          return round(confidence, 2)
      
      # Fallback: estimate based on available data
      has_usual = len(pers_data.get("usual_items", [])) > 0
      has_reorder = len(pers_data.get("reorder_suggestions", [])) > 0
      history_count = pers_data.get("purchase_history_count", 0)
      
      if history_count >= 20 and (has_usual or has_reorder):
          return 0.85
      elif history_count >= 10:
          return 0.65
      elif history_count >= 5:
          return 0.45
      else:
          return 0.25
  
  async def _compile_order_response(self, state: SearchState) -> SearchState:
      """Compile response for order operations"""
      start_time = time.time()
      self.logger.info("Compiling order operation response")
      
      # Get order data
      current_order = state.get("current_order", {})
      order_metadata = state.get("order_metadata", {})
      agent_timings = state.get("agent_timings", {})
      reasoning_steps = list(dict.fromkeys(state.get("reasoning", [])))  # Deduplicate reasoning
      
      # Extract the last tool result for message
      message = "Order processed."
      for msg in reversed(state.get("messages", [])):
          if msg.get("role") == "tool" and msg.get("content"):
              try:
                  tool_result = json.loads(msg["content"])
                  if "message" in tool_result:
                      message = tool_result["message"]
                      break
              except:
                  pass
      
      # Build order response
      final_response = {
          "success": True,
          "query": state["query"],
          "order": current_order,
          "message": message,
          "metadata": order_metadata,
          "execution": {
              "total_time_ms": sum(agent_timings.values()),
              "agent_timings": agent_timings,
              "reasoning_steps": reasoning_steps,
              "agents_run": [agent for agent, status in state["agent_status"].items() 
                           if status == "completed"]
          },
          "langsmith_trace_id": state.get("trace_id")
      }
      
      # Add personalization to order responses too
      if state.get("user_id") and state.get("personalization_data"):
          final_response["personalization"] = self._compile_personalization_section(state)
      
      state["final_response"] = final_response
      
      # Add timing
      elapsed = (time.time() - start_time) * 1000
      if "agent_timings" not in state:
          state["agent_timings"] = {}
      state["agent_timings"]["response_compiler"] = elapsed
      
      # Update total time in response
      final_response["execution"]["total_time_ms"] = sum(state["agent_timings"].values())
      
      self.logger.info(
          "Order response compiled",
          items_in_order=len(current_order.get("items", [])),
          total_time_ms=final_response["execution"]["total_time_ms"]
      )
      
      return state
  
  async def _fallback(self, state: SearchState, error: Exception) -> SearchState:
      """Fallback response compilation"""
      state["final_response"] = {
          "success": False,
          "error": f"Failed to compile response: {str(error)}",
          "query": state.get("query", ""),
          "products": [],
          "metadata": {},
          "execution": {
              "error": str(error),
              "agent_timings": state.get("agent_timings", {})
          }
      }
      return state
  
  async def _compile_promotion_response(self, state: SearchState) -> SearchState:
      """Compile response for promotion queries"""
      start_time = time.time()
      
      promotion_response = state.get("promotion_response", "")
      cart_discount_info = state.get("cart_discount_info", {})
      
      self.logger.info(f"Compiling promotion response")
      
      # Build the response
      response_parts = []
      
      # Add promotion information
      if promotion_response:
          response_parts.append(promotion_response)
      
      # Add cart discount information if available
      if cart_discount_info and cart_discount_info.get("total_discount", 0) > 0:
          response_parts.append(f"\n💰 **Your current cart savings: ${cart_discount_info['total_discount']:.2f}**")
      
      # Create the final response text
      response_text = "\n".join(response_parts) if response_parts else "No promotion information available."
      
      # Build structured response
      final_response = {
          "success": True,
          "query": state["query"],
          "response": response_text,
          "promotion_info": {
              "has_promotions": state.get("has_promotion_info", False),
              "cart_discount": cart_discount_info.get("total_discount", 0) if cart_discount_info else 0,
              "applied_promotions": cart_discount_info.get("applied_promotions", []) if cart_discount_info else []
          },
          "metadata": {
              "response_type": "promotion",
              "routing": state.get("routing_decision", ""),
              "intent": state.get("intent", "")
          },
          "execution": {
              "total_time_ms": sum(state.get("agent_timings", {}).values()),
              "agent_timings": state.get("agent_timings", {}),
              "agents_run": [agent for agent, status in state["agent_status"].items() 
                           if status == "completed"]
          }
      }
      
      state["final_response"] = final_response
      
      # Log completion
      elapsed = (time.time() - start_time) * 1000
      self.logger.info(f"Promotion response compiled in {elapsed:.0f}ms")
      
      return state
  
  async def _compile_merged_response(self, state: SearchState) -> SearchState:
      """Compile response merging results from multiple agents"""
      start_time = time.time()
      
      self.logger.info("Compiling merged response from multiple agents")
      
      # Determine primary response type
      routing = state.get("routing_decision", "")
      
      if routing == "order_agent":
          # Order operation with promotions
          base_response = await self._compile_order_response(state)
          
          # Add promotion info if available
          if state.get("cart_discount_info"):
              discount_info = state["cart_discount_info"]
              if discount_info.get("total_discount", 0) > 0:
                  # Enhance order response with discount info
                  order_text = base_response["final_response"]["response"]
                  promo_text = f"\n\n💰 **Promotions Applied:**\n"
                  promo_text += f"• Discount: -${discount_info['total_discount']:.2f}\n"
                  promo_text += f"• You save {discount_info['savings_percentage']:.1f}%!"
                  
                  for promo in discount_info.get("applied_promotions", []):
                      promo_text += f"\n• {promo['name']}"
                  
                  base_response["final_response"]["response"] = order_text + promo_text
                  base_response["final_response"]["promotion_info"] = discount_info
          
          return base_response
          
      elif routing == "product_search":
          # Product search with promotions
          products = state.get("search_results", [])
          
          # Build enhanced response
          response_parts = []
          
          # Product results
          if products:
              response_parts.append(f"Found {len(products)} products:")
              for i, product in enumerate(products[:5], 1):
                  response_parts.append(f"{i}. **{product.get('name', '')}** - ${product.get('price', 0):.2f}")
          
          # Add applicable promotions
          if state.get("promotion_response"):
              response_parts.append(f"\n{state['promotion_response']}")
          
          # Create structured response
          final_response = {
              "success": True,
              "query": state["query"],
              "response": "\n".join(response_parts),
              "products": self._format_products(products),
              "promotion_info": state.get("cart_discount_info", {}),
              "metadata": {
                  "response_type": "search_with_promotions",
                  "total_products": len(products),
                  "has_promotions": state.get("has_promotion_info", False)
              },
              "execution": {
                  "total_time_ms": sum(state.get("agent_timings", {}).values()),
                  "agent_timings": state.get("agent_timings", {}),
                  "agents_run": [agent for agent, status in state["agent_status"].items() 
                               if status == "completed"]
              }
          }
          
          state["final_response"] = final_response
          return state
      
      # Default: just merge available info
      else:
          return await self._compile_promotion_response(state)
  
  async def _compile_chat_response(self, state: SearchState) -> SearchState:
      """Compile response for general chat/greetings"""
      start_time = time.time()
      
      self.logger.info("Compiling general chat response")
      
      # Get the query and intent analysis
      query = state.get("query", "")
      intent = state.get("intent", "general_chat")
      confidence = state.get("confidence", 0.8)
      
      # Generate appropriate response based on query
      query_lower = query.lower()
      
      # Greetings
      if any(word in query_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
          responses = [
              "Hello! Welcome to LeafLoaf. What can I help you find today?",
              "Hi there! I'm here to help with your grocery shopping. What are you looking for?",
              "Good to hear from you! What groceries can I help you with today?",
              "Hello! Ready to help you shop. What's on your list today?"
          ]
          import random
          response_text = random.choice(responses)
      
      # How are you
      elif any(phrase in query_lower for phrase in ["how are you", "how's it going", "what's up", "how do you do"]):
          response_text = "I'm doing great, thank you for asking! I'm here to help you find the best groceries. What can I search for you?"
      
      # Thanks
      elif any(word in query_lower for word in ["thank", "thanks", "appreciate", "cheers"]):
          response_text = "You're very welcome! Is there anything else you'd like to shop for?"
      
      # Goodbye
      elif any(word in query_lower for word in ["bye", "goodbye", "see you", "later", "farewell"]):
          response_text = "Goodbye! Thanks for shopping with LeafLoaf. Have a great day!"
      
      # What can you do
      elif any(phrase in query_lower for phrase in ["what can you do", "help me", "how do you work", "what do you do"]):
          response_text = "I can help you search for groceries, manage your shopping cart, and find the best products for your needs. Just tell me what you're looking for!"
      
      # Default friendly response
      else:
          response_text = "I'm here to help you with grocery shopping. What would you like me to search for?"
      
      # Build final response
      final_response = {
          "success": True,
          "query": query,
          "response": response_text,
          "is_general_chat": True,
          "metadata": {
              "response_type": "general_chat",
              "intent": intent,
              "confidence": confidence,
              "routing": state.get("routing_decision", "general_chat")
          },
          "execution": {
              "total_time_ms": sum(state.get("agent_timings", {}).values()),
              "agent_timings": state.get("agent_timings", {}),
              "reasoning_steps": state.get("reasoning", []),
              "agents_run": [agent for agent, status in state.get("agent_status", {}).items() 
                           if status == "completed"]
          }
      }
      
      state["final_response"] = final_response
      
      # Add timing
      elapsed = (time.time() - start_time) * 1000
      if "agent_timings" not in state:
          state["agent_timings"] = {}
      state["agent_timings"]["response_compiler"] = elapsed
      
      self.logger.info(f"General chat response compiled in {elapsed:.0f}ms")
      
      return state