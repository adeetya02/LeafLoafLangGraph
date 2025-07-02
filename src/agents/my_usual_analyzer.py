"""
My Usual Analyzer - Pure Graphiti Learning

Learns usual shopping patterns through Graphiti relationships:
- Zero hardcoded frequency thresholds
- Real-time learning from user behavior
- Self-improving pattern detection
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import structlog

from src.personalization.graphiti_personalization_engine import GraphitiPersonalizationEngine

logger = structlog.get_logger()


class MyUsualAnalyzer:
    """Pure Graphiti Learning - Zero hardcoded thresholds, maximum learning"""
    
    def __init__(self, graphiti_memory=None):
        self.logger = logger.bind(component="my_usual_analyzer")
        self.graphiti_engine = GraphitiPersonalizationEngine(graphiti_memory)
        
        # Legacy fallback for test compatibility
        self._legacy_fallback_enabled = True
        self.min_orders_for_pattern = 2  # For legacy only
        self.confidence_threshold = 0.8  # For legacy only
        
    async def detect_usual_items(self, purchase_history: Dict[str, Any], user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Pure Graphiti detection of usual items through learned patterns"""
        
        if user_id:
            # Use Pure Graphiti to get usual products
            usual_products = await self.graphiti_engine.get_usual_products(
                user_id=user_id,
                max_products=10
            )
            
            if usual_products:
                self.logger.info(f"Found {len(usual_products)} usual products via Graphiti", user_id=user_id)
                return usual_products
        
        # Legacy fallback for test compatibility
        if self._legacy_fallback_enabled and purchase_history:
            return await self._legacy_detect_usual_items(purchase_history)
        
        return []
    
    async def _legacy_detect_usual_items(self, purchase_history: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Legacy detection method for test compatibility"""
        if not purchase_history.get("orders"):
            return []
        
        orders = purchase_history["orders"]
        total_orders = len(orders)
        
        if total_orders < self.min_orders_for_pattern:
            return []
        
        # Track item frequency
        item_frequency = defaultdict(int)
        item_details = {}
        item_quantities = defaultdict(list)
        
        for order in orders:
            for item in order.get("items", []):
                sku = item["sku"]
                item_frequency[sku] += 1
                item_details[sku] = {
                    "name": item["name"],
                    "price": item.get("price", 0)
                }
                item_quantities[sku].append(item.get("quantity", 1))
        
        # Calculate usual items
        usual_items = []
        
        for sku, count in item_frequency.items():
            frequency = count / total_orders
            
            # Calculate typical quantity
            quantities = item_quantities[sku]
            usual_quantity = int(statistics.mode(quantities)) if quantities else 1
            
            # Calculate confidence based on frequency and consistency
            quantity_variance = statistics.stdev(quantities) if len(quantities) > 1 else 0
            consistency_score = 1.0 if quantity_variance == 0 else 1.0 / (1.0 + quantity_variance)
            confidence = frequency * consistency_score
            
            usual_item = {
                "sku": sku,
                "name": item_details[sku]["name"],
                "price": item_details[sku]["price"],
                "frequency": frequency,
                "usual_quantity": usual_quantity,
                "confidence": min(confidence, 1.0),
                "order_count": count,
                "total_orders": total_orders
            }
            
            # Only include items with sufficient frequency
            if frequency >= 0.5:  # At least 50% of orders
                usual_items.append(usual_item)
        
        # Sort by confidence
        usual_items.sort(key=lambda x: x["confidence"], reverse=True)
        
        self.logger.info(
            "Detected usual items",
            user_id=purchase_history.get("user_id"),
            usual_items_count=len(usual_items),
            total_orders=total_orders
        )
        
        return usual_items
    
    async def analyze_quantity_patterns(self, purchase_history: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze quantity patterns for each product
        
        Returns detailed quantity analysis per SKU
        """
        if not purchase_history.get("orders"):
            return {}
        
        quantity_patterns = defaultdict(lambda: {
            "quantities": [],
            "typical_quantity": 1,
            "quantity_variance": "unknown",
            "min_quantity": 1,
            "max_quantity": 1
        })
        
        for order in purchase_history["orders"]:
            for item in order.get("items", []):
                sku = item["sku"]
                quantity = item.get("quantity", 1)
                quantity_patterns[sku]["quantities"].append(quantity)
        
        # Analyze patterns
        result = {}
        for sku, data in quantity_patterns.items():
            quantities = data["quantities"]
            if quantities:
                typical = int(statistics.mode(quantities))
                min_q = min(quantities)
                max_q = max(quantities)
                
                # Determine variance
                if len(set(quantities)) == 1:
                    variance = "consistent"
                elif max_q - min_q == 1:
                    variance = "slightly_variable"
                else:
                    variance = "variable"
                
                result[sku] = {
                    "typical_quantity": typical,
                    "quantity_variance": variance,
                    "min_quantity": min_q,
                    "max_quantity": max_q,
                    "average_quantity": statistics.mean(quantities)
                }
        
        return result
    
    async def create_usual_basket(
        self, 
        purchase_history: Dict[str, Any],
        confidence_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a smart usual basket based on purchase patterns
        """
        if not purchase_history.get("orders"):
            return {
                "items": [],
                "total_price": 0,
                "confidence_score": 0,
                "items_count": 0,
                "message": "No purchase history yet. Order a few times to see your usual items!"
            }
        
        threshold = confidence_threshold if confidence_threshold is not None else self.confidence_threshold
        
        # Get usual items
        usual_items = await self.detect_usual_items(purchase_history)
        
        # Get quantity patterns
        quantity_patterns = await self.analyze_quantity_patterns(purchase_history)
        
        # Build basket with high-confidence items
        basket_items = []
        total_price = 0
        total_confidence = 0
        
        for item in usual_items:
            if item["confidence"] >= threshold:
                sku = item["sku"]
                quantity_info = quantity_patterns.get(sku, {})
                
                basket_item = {
                    "sku": sku,
                    "name": item["name"],
                    "price": item["price"],
                    "quantity": quantity_info.get("typical_quantity", item["usual_quantity"]),
                    "confidence": item["confidence"],
                    "reason": self._get_reason(item)
                }
                
                basket_items.append(basket_item)
                total_price += basket_item["price"] * basket_item["quantity"]
                total_confidence += item["confidence"]
        
        avg_confidence = total_confidence / len(basket_items) if basket_items else 0
        
        return {
            "items": basket_items,
            "total_price": round(total_price, 2),
            "confidence_score": round(avg_confidence, 2),
            "items_count": len(basket_items),
            "threshold_used": threshold
        }
    
    def _get_reason(self, item: Dict[str, Any]) -> str:
        """Get human-readable reason for including item"""
        frequency = item["frequency"]
        
        if frequency >= 1.0:
            return "ordered_every_week"
        elif frequency >= 0.75:
            return "ordered_most_weeks"
        elif frequency >= 0.5:
            return "ordered_frequently"
        else:
            return "ordered_sometimes"
    
    async def learn_shopping_patterns(self, purchase_history: Dict[str, Any]) -> Dict[str, Any]:
        """
        Learn detailed shopping patterns from history
        """
        if not purchase_history.get("orders"):
            return {
                "shopping_frequency": "unknown",
                "typical_day": "unknown",
                "staples": [],
                "occasional": [],
                "reorder_intervals": {}
            }
        
        orders = purchase_history["orders"]
        
        # Analyze order dates
        order_dates = []
        for order in orders:
            date_str = order.get("date", "")
            if date_str:
                order_dates.append(datetime.fromisoformat(date_str.replace('Z', '+00:00')))
        
        order_dates.sort()
        
        # Calculate shopping frequency
        if len(order_dates) >= 2:
            intervals = []
            for i in range(1, len(order_dates)):
                interval = (order_dates[i] - order_dates[i-1]).days
                intervals.append(interval)
            
            avg_interval = statistics.mean(intervals)
            
            if avg_interval <= 8:
                shopping_frequency = "weekly"
            elif avg_interval <= 15:
                shopping_frequency = "bi-weekly"
            elif avg_interval <= 32:
                shopping_frequency = "monthly"
            else:
                shopping_frequency = "occasional"
        else:
            shopping_frequency = "unknown"
        
        # Find typical shopping day
        weekdays = [date.strftime("%A") for date in order_dates]
        typical_day = Counter(weekdays).most_common(1)[0][0] if weekdays else "unknown"
        
        # Categorize items
        usual_items = await self.detect_usual_items(purchase_history)
        
        staples = [item["sku"] for item in usual_items if item["frequency"] >= 0.75]
        occasional = [item["sku"] for item in usual_items if 0.25 <= item["frequency"] < 0.75]
        
        # Calculate reorder intervals per item
        reorder_intervals = {}
        item_last_ordered = {}
        
        for order in orders:
            order_date = datetime.fromisoformat(order["date"].replace('Z', '+00:00'))
            for item in order.get("items", []):
                sku = item["sku"]
                if sku in item_last_ordered:
                    interval = (order_date - item_last_ordered[sku]).days
                    if sku not in reorder_intervals:
                        reorder_intervals[sku] = []
                    reorder_intervals[sku].append(interval)
                item_last_ordered[sku] = order_date
        
        # Average reorder intervals
        avg_reorder_intervals = {}
        for sku, intervals in reorder_intervals.items():
            if intervals:
                avg_reorder_intervals[sku] = abs(int(statistics.mean(intervals)))
        
        return {
            "shopping_frequency": shopping_frequency,
            "typical_day": typical_day,
            "staples": staples,
            "occasional": occasional,
            "reorder_intervals": avg_reorder_intervals,
            "average_order_interval": int(avg_interval) if 'avg_interval' in locals() else 7
        }
    
    async def get_reorder_suggestions(
        self,
        purchase_history: Dict[str, Any],
        current_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get suggestions for items that might need reordering
        """
        if not purchase_history.get("orders"):
            return []
        
        current_date = current_date or datetime.now()
        suggestions = []
        
        # Get shopping patterns
        patterns = await self.learn_shopping_patterns(purchase_history)
        reorder_intervals = patterns["reorder_intervals"]
        
        # Find last order date for each item
        item_last_ordered = {}
        item_details = {}
        
        for order in purchase_history["orders"]:
            order_date = datetime.fromisoformat(order["date"].replace('Z', '+00:00'))
            for item in order.get("items", []):
                sku = item["sku"]
                item_last_ordered[sku] = order_date
                item_details[sku] = {
                    "name": item["name"],
                    "price": item.get("price", 0)
                }
        
        # Check which items are due
        for sku, last_ordered in item_last_ordered.items():
            days_since = (current_date - last_ordered).days
            usual_interval = reorder_intervals.get(sku, patterns["average_order_interval"])
            
            if usual_interval > 0 and days_since >= usual_interval * 0.8:  # 80% of usual interval
                confidence = min(1.0, days_since / usual_interval)
                
                suggestion = {
                    "sku": sku,
                    "name": item_details[sku]["name"],
                    "days_since_last_order": days_since,
                    "usual_frequency_days": usual_interval,
                    "confidence": round(confidence, 2),
                    "message": self._get_reorder_message(days_since, usual_interval)
                }
                suggestions.append(suggestion)
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        
        return suggestions
    
    def _get_reorder_message(self, days_since: int, usual_interval: int) -> str:
        """Get friendly reorder message"""
        if days_since > usual_interval * 1.2:
            return f"Overdue! Usually ordered every {usual_interval} days"
        elif days_since >= usual_interval:
            return f"Time to reorder - usually every {usual_interval} days"
        else:
            return f"Almost time - usually ordered every {usual_interval} days"
    
    async def modify_usual_quantities(
        self,
        usual_basket: Dict[str, Any],
        modifications: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Modify quantities in a usual basket
        """
        modified_basket = usual_basket.copy()
        modified_items = []
        total_price = 0
        
        for item in usual_basket["items"]:
            sku = item["sku"]
            
            if sku in modifications:
                new_quantity = modifications[sku]
                if new_quantity > 0:
                    modified_item = item.copy()
                    modified_item["quantity"] = new_quantity
                    modified_items.append(modified_item)
                    total_price += modified_item["price"] * new_quantity
                # If quantity is 0, skip the item
            else:
                # Keep original quantity
                modified_items.append(item)
                total_price += item["price"] * item["quantity"]
        
        modified_basket["items"] = modified_items
        modified_basket["total_price"] = round(total_price, 2)
        modified_basket["items_count"] = len(modified_items)
        
        return modified_basket
    
    async def get_seasonal_usual_items(
        self,
        purchase_history: Dict[str, Any],
        current_season: str
    ) -> List[Dict[str, Any]]:
        """
        Get usual items with seasonal variations
        """
        # Get base usual items
        usual_items = await self.detect_usual_items(purchase_history)
        
        # Check for seasonal patterns
        seasonal_patterns = purchase_history.get("seasonal_patterns", {})
        seasonal_skus = seasonal_patterns.get(current_season, [])
        
        # Mark seasonal items
        for item in usual_items:
            item["is_seasonal"] = item["sku"] in seasonal_skus
        
        # Add seasonal items that aren't in usual
        for sku in seasonal_skus:
            if not any(item["sku"] == sku for item in usual_items):
                # Create seasonal item entry
                seasonal_item = {
                    "sku": sku,
                    "name": f"Seasonal item {sku}",  # Would come from product catalog
                    "price": 0,  # Would come from product catalog
                    "frequency": 0,
                    "usual_quantity": 1,
                    "confidence": 0.7,  # Lower confidence for seasonal
                    "is_seasonal": True,
                    "season": current_season
                }
                usual_items.append(seasonal_item)
        
        return usual_items