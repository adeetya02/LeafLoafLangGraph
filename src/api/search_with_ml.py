"""
Enhanced Search API with ML and Data Capture
"""

import asyncio
from typing import Dict, List, Optional
from fastapi import Request
import structlog
from src.data_capture.capture_strategy import data_capture
from src.ml.recommendation_engine import recommendation_engine

logger = structlog.get_logger()

class SearchWithML:
    """
    Wrapper for search that adds ML and data capture
    without blocking the main flow
    """
    
    @staticmethod
    async def enhanced_search(
        request_data: Dict,
        search_function,
        req: Request
    ) -> Dict:
        """
        Enhanced search with async ML and data capture
        
        Flow:
        1. Execute main search (blocking)
        2. Start async tasks for ML and data capture (non-blocking)
        3. Return results immediately
        """
        
        # Extract user info
        user_id = getattr(req.state, 'user_id', 'anonymous')
        session_id = request_data.get("session_id", getattr(req.state, 'session_id', ''))
        
        # 1. Execute main search
        search_results = await search_function(request_data)
        
        # 2. Start async tasks (fire and forget)
        asyncio.create_task(
            SearchWithML._async_post_processing(
                user_id=user_id,
                session_id=session_id,
                query=request_data.get("query", ""),
                search_results=search_results,
                request_data=request_data
            )
        )
        
        # 3. Try to get recommendations (with short timeout)
        try:
            recommendations = await recommendation_engine.get_recommendations(
                user_id=user_id,
                current_query=request_data.get("query", ""),
                current_results=search_results.get("results", []),
                timeout=0.5  # 500ms max
            )
            
            # Add to response if we got them in time
            if recommendations and recommendations["type"] != "empty":
                search_results["recommendations"] = recommendations
                
        except Exception as e:
            logger.warning(f"Failed to get recommendations: {e}")
        
        # Return results immediately
        return search_results
    
    @staticmethod
    async def _async_post_processing(
        user_id: str,
        session_id: str,
        query: str,
        search_results: Dict,
        request_data: Dict
    ):
        """
        Async post-processing tasks
        Runs in background, doesn't block response
        """
        
        try:
            # 1. Capture search data
            await data_capture.capture_search(
                user_id=user_id,
                session_id=session_id,
                query=query,
                intent=search_results.get("conversation", {}).get("intent", "unclear"),
                results=search_results.get("results", []),
                response_time_ms=search_results.get("execution", {}).get("total_time_ms", 0),
                metadata={
                    "user_uuid": request_data.get("user_uuid", ""),
                    "confidence": search_results.get("conversation", {}).get("confidence", 0.5),
                    "search_config": search_results.get("metadata", {}).get("search_config", {}),
                    "result_count": len(search_results.get("results", []))
                }
            )
            
            # 2. Enrich results with ML scores (async)
            await recommendation_engine.enrich_search_results(
                user_id=user_id,
                query=query,
                results=search_results.get("results", [])
            )
            
            # 3. Track user interactions (if any)
            if search_results.get("results"):
                await data_capture.capture_interaction({
                    "user_id": user_id,
                    "session_id": session_id,
                    "interaction_type": "search_results_shown",
                    "query": query,
                    "results_shown": len(search_results.get("results", [])),
                    "top_results": [r.get("product_id") for r in search_results.get("results", [])[:5]]
                })
            
            logger.info(f"Async post-processing completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Post-processing error: {e}")

class OrderWithML:
    """
    Order management with ML tracking
    """
    
    @staticmethod
    async def capture_order_event(
        user_id: str,
        order_data: Dict,
        event_type: str = "order_placed"
    ):
        """Capture order events for ML"""
        
        try:
            # Capture order data
            await data_capture.capture_order({
                "user_id": user_id,
                "order_id": order_data.get("order_id"),
                "event_type": event_type,
                "items": order_data.get("items", []),
                "total_value": order_data.get("total_value", 0),
                "timestamp": order_data.get("timestamp"),
                "metadata": {
                    "delivery_type": order_data.get("delivery_type"),
                    "payment_method": order_data.get("payment_method"),
                    "discount_applied": order_data.get("discount_applied", 0)
                }
            })
            
            # Update user preferences based on order
            asyncio.create_task(
                OrderWithML._update_user_preferences(user_id, order_data)
            )
            
        except Exception as e:
            logger.error(f"Order capture error: {e}")
    
    @staticmethod
    async def _update_user_preferences(user_id: str, order_data: Dict):
        """Update user preferences based on order"""
        
        # Extract categories and brands from order
        categories = {}
        brands = {}
        
        for item in order_data.get("items", []):
            category = item.get("category", "").lower()
            brand = item.get("brand", "").lower()
            
            if category:
                categories[category] = categories.get(category, 0) + item.get("quantity", 1)
            if brand:
                brands[brand] = brands.get(brand, 0) + item.get("quantity", 1)
        
        # This would update user profile in your database
        logger.info(f"Updated preferences for user {user_id}: {categories}, {brands}")

# Utility functions for easy integration

async def search_with_ml(request_data: Dict, search_function, req: Request) -> Dict:
    """Convenience function for search with ML"""
    return await SearchWithML.enhanced_search(request_data, search_function, req)

async def track_order(user_id: str, order_data: Dict, event_type: str = "order_placed"):
    """Convenience function for order tracking"""
    await OrderWithML.capture_order_event(user_id, order_data, event_type)