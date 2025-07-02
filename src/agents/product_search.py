from typing import Dict, Any, List, Optional

from langsmith import traceable
from src.agents.memory_aware_base import MemoryAwareAgent
from src.models.state import SearchState, Message
from src.tools.tool_executor import tool_executor
from src.memory.memory_manager import memory_manager
from src.services.analytics_service import analytics_service
from src.agents.personalized_ranker import PersonalizedRanker
from src.services.preference_service import get_preference_service
from src.personalization.instant_personalizer import get_personalization_engine
# Removed CategoryMapper - trusting AI for relevance
from src.integrations.graphiti_search_enhancer import GraphitiSearchEnhancer
from src.config.constants import SEARCH_DEFAULT_LIMIT
from src.tracing.voice_tracer import trace_search_parameters, trace_agent_processing, trace_final_results
import asyncio
import json

class ProductSearchAgent(MemoryAwareAgent):
  """Simple Product Search agent wrapper for testing"""
  
  def __init__(self, weaviate_client=None, preference_service=None):
      super().__init__("product_search")
      self.weaviate_client = weaviate_client
      self.preference_service = preference_service or get_preference_service()
      self.personalized_ranker = PersonalizedRanker()
      
  async def _get_agent_specific_context(self, user_id: str, session_id: str, query: str, base_context: Dict) -> Dict[str, Any]:
      """Get search-specific memory context - simplified version"""
      # Simple implementation for basic ProductSearchAgent
      return {
          "search_patterns": {},
          "user_preferences": {},
          "product_associations": {}
      }
      
  async def _run(self, state: SearchState) -> SearchState:
      """Run search with personalization"""
      # Mock search results from weaviate
      if self.weaviate_client:
          search_result = await self.weaviate_client.search(state["query"])
          products = search_result.get("products", [])
      else:
          products = []
      
      # Apply personalization
      user_id = state.get("user_id")
      if user_id and products:
          purchase_history = state.get("personalization_data", {}).get("purchase_history")
          user_prefs = await self.preference_service.get_preferences(user_id)
          
          products = await self.personalized_ranker.rerank_products(
              products=products,
              purchase_history=purchase_history,
              user_id=user_id,
              user_preferences=user_prefs
          )
      
      state["search_results"] = products
      state["search_metadata"] = {
          "personalization_applied": user_id is not None
      }
      
      return state


class ProductSearchReactAgent(MemoryAwareAgent):
  """Memory-aware Product Search agent with Graphiti integration"""
  
  def __init__(self):
      super().__init__("product_search")
      self.tool_executor = tool_executor
      self.session_memory = memory_manager.session_memory
      self.max_iterations = 3
      self.personalized_ranker = PersonalizedRanker()
      self.preference_service = get_preference_service()
      self.graphiti_enhancer = None  # Created per request with mode
  
  async def _get_agent_specific_context(self, user_id: str, session_id: str, query: str, base_context: Dict) -> Dict[str, Any]:
      """Get search-specific memory context"""
      from src.memory.graphiti_wrapper import GraphitiMemoryWrapper
      wrapper = GraphitiMemoryWrapper()
      
      # Get search patterns
      search_patterns = await wrapper.get_search_patterns(user_id, query)
      
      # Get user preferences for personalization
      preferences = await wrapper.get_learned_preferences(user_id, session_id)
      
      # Extract products from query and get associations
      product_associations = {}
      query_words = query.lower().split()
      for word in query_words:
          if len(word) > 3:  # Skip short words
              associations = await wrapper.get_product_associations(f"product:{word}")
              if associations.get("complementary") or associations.get("frequently_bought_together"):
                  product_associations[word] = associations
      
      return {
          "search_patterns": search_patterns,
          "refinements": search_patterns.get("refinements", {}),
          "click_patterns": search_patterns.get("click_patterns", {}),
          "preferred_categories": search_patterns.get("preferred_categories", {}),
          "user_preferences": preferences,
          "product_associations": product_associations
      }
      
  async def _run(self, state: SearchState) -> SearchState:
      """Simple single-pass product search"""
      start_time = asyncio.get_event_loop().time()
      
      # Check routing
      routing = state.get("routing_decision")
      if routing != "product_search":
          self.logger.info(f"Not routed to product search (routing={routing}), skipping")
          return state
      
      # Get search parameters
      search_params = state.get("search_params", {})
      query = search_params.get("original_query", state["query"])
      alpha = search_params.get("alpha", 0.5)
      limit = search_params.get("limit", SEARCH_DEFAULT_LIMIT)
      
      # Get Graphiti mode from search params (app-controlled)
      graphiti_mode = search_params.get("graphiti_mode")
      show_all = search_params.get("show_all", False)
      
      # Get user/session for personalization
      user_id = state.get("user_id")
      session_id = state.get("session_id")
      
      # Get trace ID and voice metadata for tracing
      trace_id = state.get("trace_id")
      voice_metadata = state.get("voice_metadata", {})
      
      # Trace search parameters
      if trace_id:
          trace_search_parameters(trace_id, {
              "query": query,
              "alpha": alpha,
              "limit": limit,
              "graphiti_mode": graphiti_mode,
              "voice_influenced": bool(voice_metadata),
              "voice_metadata": voice_metadata
          })
      
      self.logger.info(f"🔍 Executing search",
                      query=query,
                      alpha=alpha,
                      mode=graphiti_mode,
                      trace_id=trace_id)
      
      # Get memory context if available
      memory_context = {}
      if user_id:
          try:
              memory_context = await asyncio.wait_for(
                  self.get_memory_context(user_id, session_id, query),
                  timeout=0.1  # 100ms timeout
              )
          except asyncio.TimeoutError:
              self.logger.debug("Memory context fetch timed out")
      
      # Trust the user's query and Weaviate's understanding
      # No query refinements - let semantic search handle variations
      
      # Single search call - no iterations
      tool_call = {
          "id": "search_1",
          "name": "product_search",
          "args": {
              "query": query,
              "limit": limit,  # Use configured limit from constants
              "alpha": alpha
          }
      }
      
      # Execute search
      result = await self.tool_executor.execute_tool_call(tool_call)
      
      # Initialize variables
      original_count = 0
      products = []
      
      # Process results
      if result.get("result", {}).get("success"):
          products = result["result"].get("products", [])
          self.logger.info(f"Search found {len(products)} products")
          
          # Trust Weaviate's semantic search and Gemma's understanding
          # No hardcoded category filtering - let AI handle relevance
          original_count = len(products)
          
          # Apply Graphiti-based personalization if mode is set
          enhanced_results = {}
          personalization_metrics = {}
          
          if graphiti_mode and graphiti_mode != "off":
              try:
                  # Create enhancer with the requested mode
                  self.graphiti_enhancer = GraphitiSearchEnhancer(mode=graphiti_mode)
                  
                  # Process search with Graphiti enhancement
                  enhanced_results = await self.graphiti_enhancer.process_search(
                      query=query,
                      user_id=user_id,
                      session_id=session_id,
                      limit=limit,
                      show_all=show_all,
                      alpha=alpha,
                      graphiti_mode=graphiti_mode
                  )
                  
                  # Store enhanced results
                  state["graphiti_results"] = enhanced_results
                  personalization_metrics = enhanced_results.get("personalization_metadata", {})
                  
                  # Use the active view's products
                  active_view = enhanced_results.get("active_view", "all")
                  if active_view == "personalized" and enhanced_results.get("personalized_results"):
                      products = enhanced_results["personalized_results"]
                  else:
                      products = enhanced_results.get("all_results", products)
                  
                  self.logger.info(
                      f"Graphiti enhancement applied",
                      mode=graphiti_mode,
                      active_view=active_view,
                      latency_ms=personalization_metrics.get("latency_ms", 0)
                  )
                  
              except Exception as e:
                  self.logger.warning(f"Graphiti enhancement failed: {e}")
                  # Continue with unenhanced products
          
          # Apply instant personalization as fallback if no Graphiti
          elif user_id and products:
              try:
                  # Use instant personalization engine
                  personalization_engine = get_personalization_engine()
                  
                  # Apply personalization
                  personalized_products, metrics = await personalization_engine.personalize_results(
                      user_id=user_id,
                      products=products,
                      context={
                          "query": query,
                          "session_id": state.get("session_id")
                      }
                  )
                  
                  # Update products with personalized order
                  products = personalized_products
                  personalization_metrics = metrics
                  
                  self.logger.info(
                      f"Instant personalization applied",
                      user_id=user_id,
                      time_ms=metrics.get("time_ms", 0),
                      reranked=metrics.get("reranked", False)
                  )
                  
              except Exception as e:
                  self.logger.warning(f"Instant personalization failed, using original order: {e}")
          
          # Trust Gemma's query understanding and Weaviate's semantic ranking
          # No artificial reordering - let the AI handle relevance
          
          # Limit products after filtering (use configured limit)
          final_products = products[:limit]
          
          # Store filtered and limited products in state
          state["search_results"] = final_products
          state["search_metadata"] = {
              "query": query,
              "alpha": alpha,
              "count": len(final_products),
              "original_count": original_count,
              "filtered_count": len(products),
              "category_filtered": original_count > len(products),
              "excluded_categories": [],  # No category filtering - trust AI
              "search_type": result["result"].get("search_config", {}).get("search_type", "hybrid"),
              "search_config": result["result"].get("search_config", {}),
              "personalization_applied": user_id is not None and len(products) > 0,
              "personalization_metrics": personalization_metrics,
              "graphiti_mode": graphiti_mode,
              "graphiti_applied": bool(enhanced_results),
              "show_all": show_all
          }
          
          # Store in session memory for contextual access
          session_id = state.get("session_id")
          if session_id and products:
              # TODO: Implement add_search_results method in SessionMemory
              # await self.session_memory.add_search_results(session_id, query, products)
              pass
          
          # Add to completed tool calls
          if "completed_tool_calls" not in state:
              state["completed_tool_calls"] = []
          state["completed_tool_calls"].append(result)
          
          # Log performance
          elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
          
          # Trace agent processing
          if trace_id:
              trace_agent_processing(trace_id, "product_search", elapsed_ms, {
                  "products_found": len(final_products),
                  "original_count": original_count,
                  "personalization_applied": bool(personalization_metrics),
                  "graphiti_applied": bool(enhanced_results),
                  "search_type": result["result"].get("search_config", {}).get("search_type", "hybrid")
              })
          
          self.logger.info(f"🛍️ Product search completed",
                          elapsed_ms=elapsed_ms,
                          products_found=len(final_products),
                          original_count=original_count,
                          trace_id=trace_id)
          
          # Track search event
          categories = list(set(p.get("category", "") for p in products if p.get("category")))
          suppliers = list(set(p.get("supplier", "") for p in products if p.get("supplier")))
          
          asyncio.create_task(analytics_service.track_search_event({
              "session_id": session_id or "",
              "query": query,
              "intent": state.get("intent", "product_search"),
              "alpha": alpha,
              "results_count": len(products),
              "categories": categories,
              "suppliers": suppliers,
              "response_time_ms": elapsed_ms,
              "weaviate_latency_ms": result["result"].get("search_config", {}).get("latency_ms", elapsed_ms)
          }))
          
          # Add timing to agent_timings
          if "agent_timings" not in state:
              state["agent_timings"] = {}
          state["agent_timings"]["product_search"] = elapsed_ms
      else:
          self.logger.error(f"Search failed: {result.get('error', 'Unknown error')}")
          state["search_results"] = []
          state["search_metadata"] = {"error": result.get("error", "Search failed")}
      
      return state
