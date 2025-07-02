"""
Optimized parallel execution graph for sub-300ms performance
"""
import asyncio
import time
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import threading
from functools import lru_cache

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage

from src.state.graph_state import GraphState
from src.agents.supervisor import supervisor_chain
from src.agents.product_search import search_products
from src.agents.order import create_order_agent
from src.agents.response_compiler import compile_response
from src.integrations.gemma_client_v2 import GemmaClient
from src.utils.search_strategy import SearchStrategy
from src.memory.session_memory import get_memory_store
from src.config.settings import settings
from src.config.constants import (
    SEARCH_DEFAULT_LIMIT,
    ALPHA_KEYWORD_FOCUSED,
    ALPHA_BALANCED,
    ALPHA_SEMANTIC_FOCUSED,
    MAX_CONTEXT_PRODUCTS
)

import logging
logger = logging.getLogger(__name__)

# Global thread pool for parallel execution
executor = ThreadPoolExecutor(max_workers=4)

# Intent cache (LRU with 1000 items)
@lru_cache(maxsize=1000)
def cached_intent_analysis(query: str) -> tuple:
    """Cache intent analysis results"""
    # This will be populated by actual calls
    pass

class ParallelOrchestrator:
    """Orchestrates parallel execution of Gemma and Weaviate"""
    
    def __init__(self):
        self.gemma_client = GemmaClient()
        self.search_strategy = SearchStrategy()
        
    async def analyze_intent_and_search(self, state: GraphState) -> GraphState:
        """Execute Gemma intent analysis and Weaviate search in parallel"""
        start_time = time.time()
        
        query = state["query"]
        session_id = state.get("session_id", "default")
        
        # Check intent cache first
        cache_key = f"{query.lower().strip()}"
        cached_result = self._check_intent_cache(cache_key)
        
        if cached_result:
            intent, confidence, alpha = cached_result
            gemma_time = 0  # Cache hit
        else:
            # Start both operations in parallel
            intent_future = executor.submit(self._analyze_intent, query, state)
            
            # Use default alpha for initial search
            initial_alpha = self._estimate_alpha_fast(query)
            search_future = executor.submit(
                self._search_products, 
                query, 
                initial_alpha,
                session_id
            )
            
            # Wait for intent analysis (with timeout)
            try:
                intent_result = intent_future.result(timeout=0.3)  # 300ms timeout
                intent = intent_result["intent"]
                confidence = intent_result["confidence"]
                alpha = intent_result.get("alpha", initial_alpha)
                gemma_time = intent_result.get("time_ms", 0)
                
                # Cache the result
                self._cache_intent(cache_key, (intent, confidence, alpha))
            except:
                # Fallback on timeout
                intent = "product_search"
                confidence = 0.7
                alpha = initial_alpha
                gemma_time = 300  # Timeout
                
            # Get search results
            search_results = search_future.result()
        
        # If we have a better alpha from Gemma and it's significantly different,
        # we could re-search, but for latency we'll use the initial results
        if not cached_result:
            search_results = search_future.result()
        else:
            # Cached intent, do search with known alpha
            search_results = self._search_products(query, alpha, session_id)
        
        # Update state
        state["intent"] = intent
        state["confidence"] = confidence
        state["alpha"] = alpha
        state["products"] = search_results.get("products", [])
        state["messages"].append(HumanMessage(content=query))
        
        # Add timing info
        total_time = (time.time() - start_time) * 1000
        state["execution_time_ms"] = total_time
        state["gemma_time_ms"] = gemma_time
        
        logger.info(f"Parallel execution completed in {total_time:.0f}ms (Gemma: {gemma_time:.0f}ms)")
        
        return state
    
    def _analyze_intent(self, query: str, state: GraphState) -> Dict[str, Any]:
        """Analyze intent using Gemma"""
        start = time.time()
        
        try:
            # Get memory for context
            memory = get_memory_store()
            session_id = state.get("session_id", "default")
            
            # Build context from recent interactions
            context_entries = []
            
            # Previous query context
            prev_query = memory.get_session_data(session_id, "last_query")
            if prev_query and prev_query != query:
                context_entries.append(f"Previous query: {prev_query}")
            
            # Recent products viewed
            products = state.get("products", [])
            if products:
                product_names = [p.get("retail_name", p.get("name", "")) for p in products[:3]]
                context_entries.append(f"Recently viewed: {', '.join(product_names)}")
            
            # Current cart
            order = state.get("order", {})
            if order.get("items"):
                context_entries.append(f"Cart has {len(order['items'])} items")
            
            # Analyze with Gemma
            result = self.gemma_client.analyze_intent(query, context_entries)
            
            # Calculate dynamic alpha
            alpha = self._calculate_dynamic_alpha(query, result.get("intent", ""))
            result["alpha"] = alpha
            
            result["time_ms"] = (time.time() - start) * 1000
            return result
            
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}")
            # Return fallback
            return {
                "intent": "product_search",
                "confidence": 0.5,
                "alpha": self._estimate_alpha_fast(query),
                "time_ms": (time.time() - start) * 1000
            }
    
    def _search_products(self, query: str, alpha: float, session_id: str) -> Dict[str, Any]:
        """Search products using Weaviate"""
        try:
            results = self.search_strategy.search(
                query=query,
                alpha=alpha,
                limit=SEARCH_DEFAULT_LIMIT,
                session_id=session_id
            )
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"products": []}
    
    def _estimate_alpha_fast(self, query: str) -> float:
        """Fast alpha estimation without LLM"""
        query_lower = query.lower()
        words = query_lower.split()
        
        # Brand/specific product indicators
        if any(brand in query_lower for brand in ["oatly", "chobani", "organic valley", "annie's"]):
            return ALPHA_KEYWORD_FOCUSED
        
        # Exploratory indicators
        if any(word in words for word in ["ideas", "suggestions", "recommend", "what", "which"]):
            return ALPHA_SEMANTIC_FOCUSED
        
        # Default balanced
        return ALPHA_BALANCED
    
    def _calculate_dynamic_alpha(self, query: str, intent: str) -> float:
        """Calculate alpha based on query and intent"""
        if intent == "order_management":
            return ALPHA_BALANCED  # Balanced for cart operations
        
        # Use the search strategy's alpha calculation
        return self.search_strategy.calculate_alpha(query)
    
    def _check_intent_cache(self, cache_key: str) -> Optional[tuple]:
        """Check intent cache"""
        # In production, this would use Redis
        # For now, use in-memory cache
        try:
            return cached_intent_analysis.__wrapped__(cache_key)
        except:
            return None
    
    def _cache_intent(self, cache_key: str, result: tuple):
        """Cache intent result"""
        # Update the cache
        cached_intent_analysis.cache_clear()
        cached_intent_analysis.__wrapped__ = lambda k: result if k == cache_key else None


# Create the optimized graph
def create_parallel_graph():
    """Create the optimized parallel execution graph"""
    
    # Create orchestrator
    orchestrator = ParallelOrchestrator()
    
    # Define the graph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("parallel_execution", lambda state: asyncio.run(orchestrator.analyze_intent_and_search(state)))
    workflow.add_node("order_agent", lambda state: create_order_agent().invoke(state))
    workflow.add_node("response_compiler", compile_response)
    
    # Define edges
    workflow.set_entry_point("parallel_execution")
    
    # Route based on intent
    def route_intent(state: GraphState) -> str:
        intent = state.get("intent", "product_search")
        
        if intent in ["add_to_order", "remove_from_order", "update_order", "show_order"]:
            return "order_agent"
        else:
            return "response_compiler"
    
    workflow.add_conditional_edges(
        "parallel_execution",
        route_intent,
        {
            "order_agent": "order_agent",
            "response_compiler": "response_compiler"
        }
    )
    
    # Order agent always goes to response compiler
    workflow.add_edge("order_agent", "response_compiler")
    
    # Response compiler ends
    workflow.add_edge("response_compiler", END)
    
    # Compile
    app = workflow.compile()
    
    return app


# Export the optimized graph
parallel_graph = create_parallel_graph()