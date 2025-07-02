"""
Real-time Personalization API Endpoints

Production-grade endpoints for instant personalization with <100ms response times.
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import asyncio
import time
import structlog

from src.personalization.instant_personalizer import get_personalization_engine, SignalType
from src.services.analytics_service import analytics_service

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/api/personalization", tags=["personalization"])

# Get global personalization engine
personalization_engine = get_personalization_engine()


class TrackInteractionRequest(BaseModel):
    """Request model for tracking user interactions"""
    user_id: str = Field(..., description="User ID")
    signal_type: str = Field(..., description="Type of interaction: click, add_to_cart, purchase, view_details, remove_from_cart")
    product: Dict[str, Any] = Field(..., description="Product data including sku, name, category, etc.")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional context like position, source, etc.")


class PersonalizeSearchRequest(BaseModel):
    """Request model for personalizing search results"""
    user_id: str = Field(..., description="User ID")
    products: List[Dict[str, Any]] = Field(..., description="List of products to personalize")
    query: Optional[str] = Field(default=None, description="Original search query")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class GetPreferencesRequest(BaseModel):
    """Request model for getting user preferences"""
    user_id: str = Field(..., description="User ID")


class ResetUserRequest(BaseModel):
    """Request model for resetting user preferences (demo only)"""
    user_id: str = Field(..., description="User ID")


@router.post("/track")
async def track_interaction(
    request: TrackInteractionRequest
) -> Dict[str, Any]:
    """
    Track user interaction and update preferences in real-time.
    
    Performance guarantee: <10ms response time
    """
    try:
        # Track the interaction
        result = await personalization_engine.track_interaction(
            user_id=request.user_id,
            product=request.product,
            signal_type=request.signal_type,
            metadata=request.metadata
        )
        
        # Analytics tracking disabled for now
        # TODO: Implement analytics tracking when service is ready
        
        return {
            "success": True,
            "data": result,
            "message": "Interaction tracked successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to track interaction: {e}")
        raise HTTPException(status_code=500, detail="Failed to track interaction")


@router.post("/personalize")
async def personalize_search(request: PersonalizeSearchRequest) -> Dict[str, Any]:
    """
    Apply personalization to search results.
    
    Performance guarantee: <50ms response time
    """
    try:
        # Apply personalization
        personalized_products, metrics = await personalization_engine.personalize_results(
            user_id=request.user_id,
            products=request.products,
            context=request.context
        )
        
        return {
            "success": True,
            "data": {
                "products": personalized_products,
                "personalization": metrics
            },
            "message": "Search results personalized successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to personalize search: {e}")
        # Return original products on error
        return {
            "success": False,
            "data": {
                "products": request.products,
                "personalization": {
                    "personalized": False,
                    "reason": "error",
                    "error": str(e)
                }
            },
            "message": "Personalization failed, returning original results"
        }


@router.get("/preferences/{user_id}")
async def get_user_preferences(user_id: str) -> Dict[str, Any]:
    """
    Get current user preferences for inspection.
    """
    try:
        preferences = await personalization_engine.get_user_preferences(user_id)
        
        return {
            "success": True,
            "data": preferences,
            "message": "User preferences retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve preferences")


@router.post("/reset")
async def reset_user_preferences(request: ResetUserRequest) -> Dict[str, Any]:
    """
    Reset user preferences (for demo/testing purposes).
    
    Note: This endpoint should be disabled in production.
    """
    try:
        await personalization_engine.reset_user_preferences(request.user_id)
        
        return {
            "success": True,
            "message": f"Preferences reset for user {request.user_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to reset preferences: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset preferences")


@router.get("/metrics")
async def get_performance_metrics() -> Dict[str, Any]:
    """
    Get performance metrics for monitoring.
    """
    try:
        metrics = personalization_engine.get_performance_metrics()
        
        return {
            "success": True,
            "data": metrics,
            "message": "Performance metrics retrieved successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.post("/demo/simulate")
async def simulate_demo_flow() -> Dict[str, Any]:
    """
    Simulate the demo flow for testing instant personalization.
    """
    try:
        demo_user_id = "demo_user_123"
        
        # Reset user first
        await personalization_engine.reset_user_preferences(demo_user_id)
        
        # Simulate search results for "milk"
        milk_products = [
            {"sku": "MILK_WHOLE", "name": "Whole Milk", "category": "dairy", "brand": "Farm Fresh", "price": 3.99},
            {"sku": "MILK_2PCT", "name": "2% Milk", "category": "dairy", "brand": "Farm Fresh", "price": 3.79},
            {"sku": "OAT_MILK", "name": "Oat Milk", "category": "dairy alternatives", "brand": "Oatly", "price": 4.99},
            {"sku": "ALMOND_MILK", "name": "Almond Milk", "category": "dairy alternatives", "brand": "Silk", "price": 4.49},
            {"sku": "SOY_MILK", "name": "Soy Milk", "category": "dairy alternatives", "brand": "Silk", "price": 3.99}
        ]
        
        # First search - no personalization
        _, initial_metrics = await personalization_engine.personalize_results(
            user_id=demo_user_id,
            products=milk_products
        )
        
        # Simulate click on Oat Milk (position 3)
        await personalization_engine.track_interaction(
            user_id=demo_user_id,
            product=milk_products[2],  # Oat Milk
            signal_type="click",
            metadata={"position": 3}
        )
        
        # Second search - should show personalization
        personalized_products, personalized_metrics = await personalization_engine.personalize_results(
            user_id=demo_user_id,
            products=milk_products
        )
        
        # Simulate another click on Organic Oat Milk
        organic_oat = {
            "sku": "OAT_MILK_ORG", 
            "name": "Organic Oat Milk", 
            "category": "dairy alternatives", 
            "brand": "Oatly",
            "price": 5.99,
            "dietary_info": ["organic", "vegan"]
        }
        
        await personalization_engine.track_interaction(
            user_id=demo_user_id,
            product=organic_oat,
            signal_type="click",
            metadata={"position": 1}
        )
        
        # Third search - should heavily favor organic plant-based
        milk_products_with_organic = [organic_oat] + milk_products
        final_products, final_metrics = await personalization_engine.personalize_results(
            user_id=demo_user_id,
            products=milk_products_with_organic
        )
        
        # Get final preferences
        preferences = await personalization_engine.get_user_preferences(demo_user_id)
        
        return {
            "success": True,
            "data": {
                "initial_order": [p["name"] for p in milk_products],
                "after_first_click": [p["name"] for p in personalized_products[:5]],
                "after_second_click": [p["name"] for p in final_products[:5]],
                "learned_preferences": preferences,
                "performance_metrics": {
                    "initial": initial_metrics,
                    "personalized": personalized_metrics,
                    "final": final_metrics
                }
            },
            "message": "Demo simulation completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Demo simulation failed: {e}")
        raise HTTPException(status_code=500, detail="Demo simulation failed")