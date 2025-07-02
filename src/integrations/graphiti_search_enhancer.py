"""
Graphiti Search Enhancer - Intelligently enhances search with personalization
Optimized for <300ms latency with parallel processing
"""
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
import structlog
from src.config.constants import (
    GRAPHITI_SEARCH_MODE,
    GRAPHITI_ENHANCE_STRENGTH,
    GRAPHITI_MAX_RECOMMENDATIONS,
    GRAPHITI_RECOMMENDATION_SECTIONS,
    PERSONALIZATION_CONTROL,
    SEARCH_DEFAULT_LIMIT
)
from src.memory.graphiti_wrapper import GraphitiMemoryWrapper
from src.integrations.weaviate_client_optimized import get_optimized_client

logger = structlog.get_logger()

class GraphitiSearchEnhancer:
    """Enhances search with Graphiti-based personalization - optimized for latency"""
    
    def __init__(self, mode: Optional[str] = None):
        self.mode = mode or GRAPHITI_SEARCH_MODE
        self.enhance_strength = GRAPHITI_ENHANCE_STRENGTH
        self.graphiti = GraphitiMemoryWrapper()
        self.weaviate = get_optimized_client()
        
    async def process_search(
        self,
        query: str,
        user_id: Optional[str],
        session_id: Optional[str],
        limit: int = SEARCH_DEFAULT_LIMIT,
        show_all: bool = False,  # Explicit override from UI/API
        alpha: float = 0.5,
        graphiti_mode: Optional[str] = None  # App can override mode
    ) -> Dict[str, Any]:
        """
        Process search with configurable personalization - optimized for <100ms overhead
        
        Returns dual results for instant UI toggle without re-querying
        """
        start_time = time.time()
        
        # Use app-provided mode or instance default
        mode = graphiti_mode or self.mode
        
        # Skip personalization if no user_id or explicitly disabled
        if not user_id or mode == "off":
            results = await self._run_base_search(query, alpha, limit)
            return self._format_response(
                personalized_results=[],
                all_results=results,
                active_view="all",
                metadata={"applied": False, "latency_ms": (time.time() - start_time) * 1000}
            )
        
        # Parallel execution for speed
        tasks = []
        
        # Always get base results (for toggle)
        base_task = asyncio.create_task(self._run_base_search(query, alpha, limit))
        tasks.append(base_task)
        
        # Get Graphiti context with timeout
        context_task = asyncio.create_task(
            self._get_graphiti_context_fast(user_id, session_id, query)
        )
        tasks.append(context_task)
        
        # Wait for both with timeout
        done, pending = await asyncio.wait(tasks, timeout=0.2)  # 200ms max
        
        # Get results
        base_results = base_task.result() if base_task.done() else []
        graphiti_context = context_task.result() if context_task.done() else {}
        
        # Cancel any pending tasks
        for task in pending:
            task.cancel()
        
        # Process based on mode
        personalized_results = []
        recommendations = {}
        
        if mode in ["enhance", "both"] and graphiti_context:
            # Quick enhancement
            enhanced_query = self._quick_enhance_query(query, graphiti_context)
            if enhanced_query != query:
                # Only run personalized search if query actually changed
                personalized_results = await self._run_base_search(
                    enhanced_query, 
                    alpha, 
                    limit
                )
            else:
                # Re-rank existing results based on preferences
                personalized_results = self._rerank_with_preferences(
                    base_results, 
                    graphiti_context
                )
        
        if mode in ["supplement", "both"] and graphiti_context:
            # Quick recommendations
            recommendations = self._get_quick_recommendations(
                graphiti_context, 
                base_results
            )
        
        # Determine active view
        active_view = "all" if show_all else "personalized"
        if mode == "supplement":
            active_view = "all"  # Supplement always shows all
        
        latency_ms = (time.time() - start_time) * 1000
        logger.info(f"Graphiti search enhancement took {latency_ms:.1f}ms", mode=mode)
        
        return self._format_response(
            personalized_results=personalized_results,
            all_results=base_results,
            active_view=active_view,
            recommendations=recommendations,
            metadata={
                "applied": True,
                "mode": mode,
                "latency_ms": latency_ms,
                "query_enhanced": enhanced_query != query if mode in ["enhance", "both"] else False,
                "original_query": query,
                "enhanced_query": enhanced_query if mode in ["enhance", "both"] else query
            }
        )
    
    async def _get_graphiti_context_fast(
        self, 
        user_id: str, 
        session_id: Optional[str],
        query: str
    ) -> Dict[str, Any]:
        """Get user context from Graphiti with timeout - optimized for speed"""
        try:
            # Quick context fetch with essential data only
            context = await asyncio.wait_for(
                self.graphiti.get_user_context(user_id, session_id),
                timeout=0.1  # 100ms timeout
            )
            
            # Return only essential patterns for search
            return {
                "preferences": {
                    "dietary": context.get("dietary_restrictions", [])[:3],  # Top 3
                    "brands": context.get("preferred_brands", [])[:5],  # Top 5
                },
                "refinements": context.get("search_refinements", {}),
                "reorder_patterns": context.get("reorder_patterns", [])[:5]
            }
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(f"Graphiti context fetch failed/timed out: {e}")
            return {}
    
    def _quick_enhance_query(self, query: str, context: Dict[str, Any]) -> str:
        """Fast query enhancement - no async, pure logic"""
        if not context:
            return query
            
        # Check refinements first (fastest)
        refinements = context.get("refinements", {})
        query_lower = query.lower()
        
        # Direct refinement match
        if query_lower in refinements:
            return refinements[query_lower]
            
        # Dietary preferences for key categories
        dietary = context.get("preferences", {}).get("dietary", [])
        if dietary and "milk" in query_lower and "dairy-free" in dietary:
            return query.replace("milk", "oat milk")
            
        return query
    
    def _rerank_with_preferences(self, results: List[Dict], context: Dict[str, Any]) -> List[Dict]:
        """Fast re-ranking based on preferences - no external calls"""
        if not context or not results:
            return results
            
        # Score each result
        scored_results = []
        preferred_brands = set(context.get("preferences", {}).get("brands", []))
        
        for result in results:
            score = result.get("score", 0.5)
            
            # Boost for preferred brands
            if result.get("brand") in preferred_brands:
                score *= 1.2
                
            # Boost for reorder patterns
            for pattern in context.get("reorder_patterns", []):
                if pattern.get("sku") == result.get("sku"):
                    score *= 1.5
                    break
                    
            scored_results.append({**result, "personalized_score": score})
        
        # Sort by personalized score
        scored_results.sort(key=lambda x: x["personalized_score"], reverse=True)
        return scored_results
    
    def _get_quick_recommendations(self, context: Dict[str, Any], search_results: List[Dict]) -> Dict[str, List[Dict]]:
        """Fast recommendation extraction - no async"""
        recommendations = {}
        
        # Extract reorder items
        reorder_patterns = context.get("reorder_patterns", [])
        if reorder_patterns:
            # Get SKUs from search results
            result_skus = {r.get("sku") for r in search_results}
            
            # Find reorder items not in search results
            reorder_items = []
            for pattern in reorder_patterns[:3]:  # Top 3
                if pattern.get("sku") not in result_skus:
                    reorder_items.append({
                        "sku": pattern.get("sku"),
                        "name": pattern.get("product_name"),
                        "reason": "You order this regularly"
                    })
            
            if reorder_items:
                recommendations["frequently_bought"] = reorder_items
                
        return recommendations
    
    async def _run_base_search(self, query: str, alpha: float, limit: int) -> List[Dict]:
        """Run standard Weaviate search"""
        try:
            results = await self.weaviate.search(
                query=query,
                alpha=alpha,
                limit=limit
            )
            return results.get("products", []) if isinstance(results, dict) else results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def _format_response(
        self,
        personalized_results: List[Dict],
        all_results: List[Dict],
        active_view: str,
        recommendations: Dict[str, List[Dict]] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Format the final response structure"""
        response = {
            "personalized_results": personalized_results,
            "all_results": all_results,
            "active_view": active_view,
            "personalization_metadata": metadata or {},
            "ui_controls": {
                "show_toggle": bool(personalized_results),
                "toggle_labels": PERSONALIZATION_CONTROL["ui_controls"]["toggle_labels"],
                "default_state": active_view
            }
        }
        
        if recommendations:
            response["recommendations"] = recommendations
            
        return response