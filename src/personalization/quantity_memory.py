"""
Feature 8: Quantity Memory

Learns and suggests personalized quantities based on user purchase patterns.
Delegates all learning to GraphitiPersonalizationEngine following Pure Graphiti approach.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from src.models.user_preferences import UserPreferences
from src.personalization.graphiti_personalization_engine import GraphitiPersonalizationEngine

logger = logging.getLogger(__name__)


class QuantityMemoryTracker:
    """
    Tracks and suggests personalized quantities using Pure Graphiti Learning.
    
    Features:
    - Learn typical quantities from purchase history
    - Track quantity selections in cart
    - Adjust for household size patterns
    - Handle seasonal variations
    - Convert between units
    - Provide confidence scores
    """
    
    def __init__(self):
        """Initialize with GraphitiPersonalizationEngine"""
        self.engine = GraphitiPersonalizationEngine()
        self.memory = self.engine  # Delegate to engine for compatibility
        
    async def get_typical_quantity(
        self, 
        user_id: str, 
        product_id: str,
        requested_unit: Optional[str] = None,
        current_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get typical quantity for user and product using Pure Graphiti learning.
        
        Args:
            user_id: User identifier
            product_id: Product identifier  
            requested_unit: Preferred unit for result
            current_date: Date for seasonal adjustments
            
        Returns:
            Dict with quantity, unit, confidence, source, and reasoning
        """
        try:
            # Use GraphitiPersonalizationEngine for quantity learning
            result = await self.engine.get_typical_quantity(
                user_id=user_id,
                product_id=product_id,
                requested_unit=requested_unit,
                current_date=current_date or datetime.now()
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting typical quantity: {e}")
            return self._fallback_quantity_response(product_id, requested_unit)
    
    async def track_quantity_selection(
        self,
        user_id: str,
        product_id: str, 
        selected_quantity: float,
        unit: str,
        context: str = "cart_modification"
    ) -> None:
        """
        Track user's quantity selection for learning.
        
        Args:
            user_id: User identifier
            product_id: Product identifier
            selected_quantity: Quantity selected by user
            unit: Unit of measurement
            context: Selection context (cart_addition, cart_modification, etc.)
        """
        try:
            await self.engine.track_quantity_selection(
                user_id=user_id,
                product_id=product_id,
                selected_quantity=selected_quantity,
                unit=unit,
                context=context
            )
            
        except Exception as e:
            logger.error(f"Error tracking quantity selection: {e}")
    
    async def learn_from_purchase(
        self,
        user_id: str,
        product_id: str,
        purchased_quantity: float,
        unit: str,
        purchase_date: datetime
    ) -> None:
        """
        Learn from completed purchase for future quantity suggestions.
        
        Args:
            user_id: User identifier
            product_id: Product identifier
            purchased_quantity: Actual purchased quantity
            unit: Unit of measurement
            purchase_date: When purchase occurred
        """
        try:
            await self.engine.learn_from_purchase(
                user_id=user_id,
                product_id=product_id,
                purchased_quantity=purchased_quantity,
                unit=unit,
                purchase_date=purchase_date
            )
            
        except Exception as e:
            logger.error(f"Error learning from purchase: {e}")
    
    async def get_quantity_suggestion(
        self,
        user_id: str,
        product_id: str,
        user_preferences: Optional[UserPreferences] = None
    ) -> Dict[str, Any]:
        """
        Get quantity suggestion respecting user preferences.
        
        Args:
            user_id: User identifier
            product_id: Product identifier
            user_preferences: User's quantity preferences
            
        Returns:
            Dict with suggestion details and preference influences
        """
        try:
            return await self.engine.get_quantity_suggestion(
                user_id=user_id,
                product_id=product_id,
                user_preferences=user_preferences
            )
            
        except Exception as e:
            logger.error(f"Error getting quantity suggestion: {e}")
            return self._fallback_quantity_response(product_id)
    
    async def suggest_quantity_for_cart(
        self,
        user_id: str,
        product_id: str,
        cart_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Suggest quantity considering current cart context.
        
        Args:
            user_id: User identifier
            product_id: Product identifier
            cart_context: Current cart state and context
            
        Returns:
            Dict with quantity suggestion and cart-aware reasoning
        """
        try:
            return await self.engine.suggest_quantity_for_cart(
                user_id=user_id,
                product_id=product_id,
                cart_context=cart_context
            )
            
        except Exception as e:
            logger.error(f"Error suggesting quantity for cart: {e}")
            return self._fallback_quantity_response(product_id)
    
    def _fallback_quantity_response(
        self, 
        product_id: str, 
        unit: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fallback response when Graphiti learning is unavailable.
        
        Args:
            product_id: Product identifier
            unit: Requested unit
            
        Returns:
            Default quantity response
        """
        return {
            "quantity": 1,
            "unit": unit or "item",
            "confidence": 0.3,
            "source": "default_fallback",
            "reasoning": "Using default quantity - no learning data available",
            "data_points": 0,
            "respects_preferences": False,
            "metadata": {
                "fallback_used": True,
                "learning_available": False
            }
        }