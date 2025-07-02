from typing import Dict, Any, Optional
import asyncio
import time
import os
from langsmith import traceable
from src.agents.memory_aware_base import MemoryAwareAgent
from src.models.state import SearchState
from src.integrations.gemma_optimized_client import GemmaOptimizedClient
from src.memory.memory_manager import memory_manager
from src.memory.graphiti_wrapper import GraphitiMemoryWrapper
from src.config.constants import (
    FAST_MODE, 
    ORDER_INTENT_PATTERNS, 
    SEARCH_TYPE_PATTERNS,
    PRODUCT_KEYWORDS,
    DIETARY_ATTRIBUTES,
    SUPERVISOR_TIMEOUT_MS,
    SUPERVISOR_MAX_REASONING_STEPS
)
from src.agents.conversational_intent import ConversationalIntentRecognizer
from src.services.analytics_service import analytics_service
import structlog

logger = structlog.get_logger()

class SupervisorReactAgent(MemoryAwareAgent):
  """Memory-aware supervisor agent that routes queries - optimized for <300ms responses"""

  def __init__(self):
      super().__init__("supervisor")
      self.gemma = GemmaOptimizedClient()
      self.memory = memory_manager.session_memory
      self.fast_mode = FAST_MODE
      self.conversational_intent = ConversationalIntentRecognizer()
      self.graphiti_wrapper = GraphitiMemoryWrapper()
      
      # Use patterns from constants
      self.patterns = {
          **ORDER_INTENT_PATTERNS,
          **SEARCH_TYPE_PATTERNS
      }
  
  async def _get_agent_specific_context(self, user_id: str, session_id: str, query: str, base_context: Dict) -> Dict[str, Any]:
      """Get supervisor-specific memory context"""
      # Get routing patterns
      routing_patterns = await self.graphiti_wrapper.get_routing_patterns(user_id, query)
      
      # Get learned preferences for better routing
      preferences = await self.graphiti_wrapper.get_learned_preferences(user_id, session_id)
      
      # Get reorder predictions if relevant
      reorder_predictions = []
      if any(word in query.lower() for word in ["usual", "regular", "reorder", "again"]):
          reorder_predictions = await self.graphiti_wrapper.get_reorder_predictions(user_id)
      
      return {
          "routing_patterns": routing_patterns,
          "common_phrases": routing_patterns.get("common_phrases", {}),
          "success_rates": routing_patterns.get("success_rates", {}),
          "user_preferences": preferences,
          "reorder_predictions": reorder_predictions[:5] if reorder_predictions else []
      }

  async def _run(self, state: SearchState) -> SearchState:
      """Analyze query and route - ultra fast in fast mode, full analysis in prod"""
      
      start_time = time.time()
      query = state["query"]
      session_id = state.get("session_id")
      user_id = state.get("user_id")

      # Get memory context for routing decisions (optimized)
      memory_context = {}
      if user_id and not self.fast_mode:
          # Only in non-fast mode
          try:
              memory_context = await asyncio.wait_for(
                  self.get_memory_context(user_id, session_id, query),
                  timeout=0.05  # 50ms timeout
              )
          except asyncio.TimeoutError:
              logger.debug("Memory context fetch timed out")
      
      # Initialize Graphiti if we have user/session
      graphiti_context = {}
      graphiti_entities = []
      
      if user_id and session_id:
          try:
              # Get or create Graphiti memory manager
              from src.memory.memory_registry import MemoryRegistry
              from src.memory.memory_interfaces import MemoryBackend
              
              # Check if Spanner is configured
              backend = MemoryBackend.SPANNER if os.getenv("SPANNER_INSTANCE_ID") else MemoryBackend.IN_MEMORY
              
              memory_manager = MemoryRegistry.get_or_create(
                  "supervisor",
                  config={"backend": backend}
              )
              
              # Process message asynchronously with timeout
              process_task = asyncio.create_task(
                  memory_manager.process_message(
                      message=query,
                      role="user",
                      metadata={
                          "user_id": user_id,
                          "session_id": session_id
                      }
                  )
              )
              
              # Get context asynchronously with timeout
              context_task = asyncio.create_task(
                  memory_manager.get_context(query=query)
              )
              
              # Wait for results with short timeout
              try:
                  process_result = await asyncio.wait_for(process_task, timeout=0.2)
                  graphiti_entities = process_result.get("entities", [])
                  
                  context_result = await asyncio.wait_for(context_task, timeout=0.1)
                  graphiti_context = context_result
                  
                  # Add to state for other agents
                  state["graphiti_context"] = graphiti_context
                  state["graphiti_entities"] = graphiti_entities
                  
                  logger.info(f"Graphiti extracted {len(graphiti_entities)} entities")
              except asyncio.TimeoutError:
                  logger.debug("Graphiti processing timed out in supervisor")
              
          except Exception as e:
              logger.error(f"Graphiti error in supervisor: {e}")

      if self.fast_mode:
          # Use pattern matching as fallback, but try LLM first for cart operations
          pattern_result = self._instant_analysis(query)
          
          # For potential cart operations, always use LLM
          cart_keywords = ["add", "remove", "cart", "order", "take", "want", "yes", "no", "checkout", "done", 
                          "basket", "grab", "throw", "put", "forget", "drop", "double", "instead", 
                          "show", "what", "that", "those", "it", "some", "please", "good", "confirm"]
          
          # Add promotion keywords
          promotion_keywords = ["promotion", "promo", "discount", "deal", "coupon", "code", "save", "offer", 
                               "welcome15", "save5", "bogo", "free"]
          
          # Add Graphiti-aware keywords
          graphiti_keywords = ["usual", "regular", "always", "last time", "like before", "same as", 
                              "my monthly", "reorder", "what did i", "last party", "event", "birthday"]
          
          query_lower = query.lower()
          has_cart_keyword = any(keyword in query_lower for keyword in cart_keywords)
          has_promotion_keyword = any(keyword in query_lower for keyword in promotion_keywords)
          has_graphiti_keyword = any(keyword in query_lower for keyword in graphiti_keywords)
          
          # Graphiti context already processed above
          
          if has_promotion_keyword:
              # Direct route to promotion agent
              intent = "promotion_query"
              confidence = 0.95
              enhanced_query = query
              dynamic_alpha = 0.5
              metadata = {"promotion_detected": True}
              logger.info(f"Detected promotion query: '{query}'")
          elif has_cart_keyword or session_id:
              logger.info(f"Detected potential cart operation: '{query}' (has_keyword: {has_cart_keyword})")
              try:
                  # Get context for better understanding
                  user_context = None
                  if session_id:
                      user_context = await self.memory.get_user_context(session_id)
                      # Add recent products to context
                      recent_products = await self.memory.get_recent_search_results(session_id)
                      if recent_products:
                          user_context = user_context or {}
                          user_context["recent_products"] = recent_products[:5]
                      
                      # Enhance with Graphiti insights
                      if graphiti_context and graphiti_context.get("reorder_patterns"):
                          user_context["reorder_patterns"] = graphiti_context["reorder_patterns"][:5]
                          user_context["has_graphiti_memory"] = True
                  
                  # Quick LLM call with timeout
                  llm_task = asyncio.create_task(self.gemma.analyze_query(query, user_context))
                  gemma_response = await asyncio.wait_for(llm_task, timeout=0.5)  # 500ms timeout
                  
                  intent = gemma_response.intent
                  confidence = gemma_response.confidence
                  enhanced_query = query
                  dynamic_alpha = gemma_response.metadata.get("search_alpha", 0.5)
                  metadata = gemma_response.metadata
                  
                  elapsed = (time.time() - start_time) * 1000
                  logger.info(f"LLM analysis (fast): {elapsed:.2f}ms - Intent: {intent}, Alpha: {dynamic_alpha}")
                  
                  # Track Gemma intent analysis
                  asyncio.create_task(analytics_service.track_intent_analysis(
                      session_id=session_id or "",
                      query=query,
                      intent_result={
                          "intent": intent,
                          "confidence": confidence,
                          "alpha": dynamic_alpha,
                          "routing": self._decide_routing_gemma(intent, confidence),
                          "enhanced_query": enhanced_query,
                          "entities": metadata.get("entities", []),
                          "attributes": metadata.get("attributes", [])
                      },
                      latency_ms=elapsed
                  ))
              except (asyncio.TimeoutError, Exception) as e:
                  # Fallback to conversational pattern matching
                  logger.info(f"LLM failed ({type(e).__name__}), using conversational pattern matching")
                  
                  # Build context for pattern matching
                  pattern_context = {}
                  if user_context and user_context.get("recent_products"):
                      pattern_context["recent_products"] = user_context["recent_products"]
                  
                  # Use conversational intent recognizer
                  conv_result = self.conversational_intent.analyze_query(query, pattern_context)
                  intent = conv_result["intent"]
                  confidence = conv_result["confidence"]
                  enhanced_query = query
                  dynamic_alpha = conv_result["metadata"].get("search_alpha", 0.5)
                  metadata = {
                      "entities": conv_result.get("entities", []),
                      "attributes": conv_result.get("attributes", [])
                  }
          elif has_graphiti_keyword and graphiti_context.get("reorder_patterns"):
              # Handle Graphiti-based queries like "my usual order"
              logger.info(f"Detected Graphiti pattern query: '{query}'")
              
              # Check specific patterns
              if any(word in query_lower for word in ["usual", "regular", "monthly", "always"]):
                  intent = "usual_order"
                  confidence = 0.9
                  enhanced_query = query
                  dynamic_alpha = 0.5
                  metadata = {
                      "graphiti_type": "usual_order",
                      "reorder_patterns": graphiti_context.get("reorder_patterns", [])[:5]
                  }
              elif any(word in query_lower for word in ["last time", "like before", "same as", "again"]):
                  intent = "repeat_order"
                  confidence = 0.9
                  enhanced_query = query
                  dynamic_alpha = 0.5
                  metadata = {
                      "graphiti_type": "repeat_order",
                      "query_entities": graphiti_context.get("query_entities", [])
                  }
              elif any(word in query_lower for word in ["party", "event", "birthday", "celebration"]):
                  intent = "event_order"
                  confidence = 0.85
                  enhanced_query = query
                  dynamic_alpha = 0.7
                  metadata = {
                      "graphiti_type": "event_order",
                      "event_history": graphiti_context.get("user_context", {}).get("recent_orders", [])
                  }
              else:
                  # General Graphiti-enhanced search
                  intent = "product_search"
                  confidence = 0.8
                  enhanced_query = query
                  dynamic_alpha = 0.6
                  metadata = {
                      "graphiti_enhanced": True,
                      "entities": graphiti_entities
                  }
          else:
              # Use pattern matching for simple searches
              intent = pattern_result["intent"]
              confidence = pattern_result["confidence"]
              enhanced_query = query
              dynamic_alpha = pattern_result["alpha"]
              metadata = {"entities": pattern_result.get("entities", []), "attributes": pattern_result.get("attributes", [])}
      else:
          # Full LLM analysis for production
          user_context = None
          if session_id:
              user_context = await self.memory.get_user_context(session_id)
              await self.memory.add_to_conversation(session_id, "human", query)

          try:
              # Parallel LLM calls
              tasks = await asyncio.gather(
                  self.gemma.analyze_query(query, user_context),
                  self.gemma.enhance_search_query(query),
                  self.gemma.calculate_dynamic_alpha(query),
                  return_exceptions=True
              )
              
              gemma_response = tasks[0] if not isinstance(tasks[0], Exception) else None
              enhanced_query = tasks[1] if not isinstance(tasks[1], Exception) else query
              dynamic_alpha = tasks[2] if not isinstance(tasks[2], Exception) else 0.5
              
              intent = gemma_response.intent if gemma_response else None
              confidence = gemma_response.confidence if gemma_response else 0.5
              metadata = gemma_response.metadata if gemma_response else {}
          except Exception as e:
              logger.error(f"LLM error: {e}, using fallback intent analysis")
              # When all LLMs fail, use conversational fallback
              context = {}
              if session_id:
                  recent_products = await self.memory.get_recent_search_results(session_id)
                  if recent_products:
                      context["recent_products"] = recent_products[:5]
              
              intent = self._fallback_intent_analysis(query, context)
              confidence = 0.7
              enhanced_query = query
              dynamic_alpha = 0.5
              metadata = {"entities": [], "attributes": []}

      # Use fallback if needed
      if not intent or intent == "unclear":
          logger.info(f"Using fallback intent analysis for query: '{query}'")
          context = {}
          if session_id:
              recent_products = await self.memory.get_recent_search_results(session_id)
              if recent_products:
                  context["recent_products"] = recent_products[:5]
          intent = self._fallback_intent_analysis(query, context)
          confidence = 0.8

      # Update state
      state["intent"] = intent
      state["confidence"] = confidence
      state["enhanced_query"] = enhanced_query
      state["search_params"]["alpha"] = dynamic_alpha

      # Log timing
      elapsed = (time.time() - start_time) * 1000
      state["reasoning"].append(f"Analysis ({elapsed:.0f}ms) - Intent: {intent}, Alpha: {dynamic_alpha:.2f}")
      
      # Add timing to agent_timings
      if "agent_timings" not in state:
          state["agent_timings"] = {}
      state["agent_timings"]["supervisor"] = elapsed

      # Route based on intent with memory boost
      routing_decision = self._decide_routing_with_memory(intent, confidence, memory_context)
      
      # Record decision for learning
      if user_id:
          asyncio.create_task(self.record_decision({
              "type": "routing",
              "choice": routing_decision,
              "intent": intent,
              "confidence": confidence,
              "memory_influenced": bool(memory_context.get("routing_patterns"))
          }, {
              "query": query,
              "user_id": user_id,
              "session_id": session_id
          }))
      
      # Set routing flags
      state["routing_decision"] = routing_decision
      state["should_search"] = routing_decision == "product_search"

      # Prepare search params if needed
      if state["should_search"]:
          state["search_params"].update({
              "original_query": enhanced_query,
              "intent": intent,
              "alpha": dynamic_alpha,
              "entities": metadata.get("entities", []),
              "attributes": metadata.get("attributes", [])
          })

      # Track preferences if found (async)
      if session_id and metadata.get("attributes") and not self.fast_mode:
          asyncio.create_task(self._track_preferences(session_id, metadata.get("attributes", [])))

      # Add routing message
      state["messages"].append({
          "role": "assistant",
          "content": f"[Routing to {routing_decision}]",
          "tool_calls": None,
          "tool_call_id": None
      })

      return state

  def _decide_routing_with_memory(self, intent: str, confidence: float, memory_context: Dict) -> str:
      """Decide routing with memory boost"""
      
      # Get base routing
      base_routing = self._decide_routing_gemma(intent, confidence)
      
      # Apply memory insights if available
      if memory_context.get("routing_patterns"):
          # Check if user has patterns for this query type
          common_phrases = memory_context.get("common_phrases", {})
          
          # Boost confidence if pattern matches
          if common_phrases.get("casual_order") == "order_agent" and base_routing == "product_search":
              # User often uses casual language for orders
              logger.info("Memory boost: casual order pattern detected")
              return "order_agent"
      
      # Check if user has reorder predictions - strong signal for order agent
      if memory_context.get("reorder_predictions") and base_routing == "product_search":
          # User has items due for reorder
          logger.info(f"Memory boost: {len(memory_context['reorder_predictions'])} items due for reorder")
          return "order_agent"
      
      # Check user preferences for routing hints
      if memory_context.get("user_preferences"):
          prefs = memory_context["user_preferences"]
          # If user has strong shopping behavior patterns, boost confidence
          shopping_behavior = prefs.get("shopping_behavior", {})
          if shopping_behavior.get("frequency") == "weekly" and "usual" in intent:
              logger.info("Memory boost: weekly shopper asking for usual items")
              return "order_agent"
              
      return base_routing

  def _decide_routing_gemma(self, intent: str, confidence: float) -> str:
      """Decide routing based on Gemma's intent analysis"""

      # Low confidence - ask for clarification
      if confidence < 0.4:
          return "response_compiler"  # Will ask for clarification

      # Route based on intent
      routing_map = {
          "product_search": "product_search",
          "add_to_order": "order_agent",
          "update_order": "order_agent",
          "remove_from_order": "order_agent",
          "confirm_order": "order_agent",
          "list_order": "order_agent",
          "promotion_query": "promotion_agent",
          # Graphiti-based intents
          "usual_order": "order_agent",  # Handle "my usual order"
          "repeat_order": "order_agent",  # Handle "like last time"
          "event_order": "order_agent",   # Handle event-based orders
          "apply_promotion": "promotion_agent",
          "meal_planning": "product_search",  # For now, treat as search
          "help": "response_compiler",
          "unclear": "response_compiler"
      }

      return routing_map.get(intent, "product_search")

  def _instant_analysis(self, query: str) -> Dict[str, Any]:
      """Instant pattern-based analysis - 0ms"""
      
      # Check order intents first (highest priority)
      for intent, pattern in [
          ("add_to_order", self.patterns["add_to_order"]),
          ("remove_from_order", self.patterns["remove_from_order"]),
          ("update_order", self.patterns["update_order"]),
          ("confirm_order", self.patterns["confirm_order"]),
          ("list_order", self.patterns["list_order"])
      ]:
          if pattern.search(query):
              return {
                  "intent": intent,
                  "confidence": 0.95,
                  "alpha": 0.5,  # Default - Gemma will override
                  "entities": self._extract_products(query),
                  "attributes": self._extract_attributes(query)
              }
      
      # Default alpha - Gemma will provide the actual value
      return {
          "intent": "product_search",
          "confidence": 0.9,
          "alpha": 0.5,  # Default - Gemma will override
          "entities": self._extract_products(query),
          "attributes": self._extract_attributes(query)
      }

  # Alpha calculation is handled exclusively by Gemma
  # No local calculation - Gemma is the single source of truth

  def _extract_products(self, query: str) -> list:
      """Extract product entities instantly"""
      products = []
      query_lower = query.lower()
      
      for product in PRODUCT_KEYWORDS:
          if product in query_lower:
              products.append(product)
      
      return products

  def _extract_attributes(self, query: str) -> list:
      """Extract attributes instantly"""
      attributes = []
      query_lower = query.lower()
      
      for attr in DIETARY_ATTRIBUTES:
          if attr in query_lower:
              attributes.append(attr)
      
      return attributes

  async def _track_preferences(self, session_id: str, attributes: list):
      """Track preferences asynchronously"""
      try:
          for attr in attributes:
              await self.memory.add_preference(session_id, attr)
      except Exception as e:
          logger.warning(f"Failed to track preferences: {e}")

  def _fallback_intent_analysis(self, query: str, context: Optional[Dict] = None) -> str:
      """Fallback intent analysis if Gemma fails - uses conversational patterns"""
      # Use the conversational intent recognizer
      result = self.conversational_intent.analyze_query(query, context)
      return result["intent"]

  @traceable(name="Supervisor Decision")
  async def analyze_and_route(self, state: SearchState) -> SearchState:
      """Public method for tracing"""
      return await self._run(state)
