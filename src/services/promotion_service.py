"""
Promotion service for handling discounts and deals
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import uuid

class PromotionService:
    """Service for managing and applying promotions"""
    
    def __init__(self):
        self.promotions = self._initialize_promotions()
        
    def _initialize_promotions(self) -> List[Dict]:
        """Initialize active promotions"""
        return [
            {
                "promotion_id": "promo_welcome15",
                "promotion_name": "New Customer 15% Off",
                "promotion_type": "percentage_off",
                "discount_value": 15.0,
                "start_date": datetime.now().isoformat(),
                "end_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "applicable_products": [],  # All products
                "applicable_categories": [],  # All categories
                "applicable_suppliers": [],  # All suppliers
                "minimum_purchase": 25.0,
                "maximum_discount": 50.0,
                "usage_limit_per_user": 1,
                "promo_code": "WELCOME15",
                "is_active": True,
                "description": "Get 15% off your first order of $25 or more (max $50 discount)"
            },
            {
                "promotion_id": "promo_organic10",
                "promotion_name": "Organic Products 10% Off",
                "promotion_type": "percentage_off", 
                "discount_value": 10.0,
                "start_date": datetime.now().isoformat(),
                "end_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "applicable_products": [],  # Will check isOrganic flag
                "applicable_categories": [],
                "applicable_suppliers": ["Organic Valley", "Horizon"],
                "minimum_purchase": 0.0,
                "maximum_discount": None,
                "usage_limit_per_user": None,
                "promo_code": None,  # Auto-applied
                "is_active": True,
                "description": "Save 10% on all organic products from Organic Valley and Horizon"
            },
            {
                "promotion_id": "promo_dairy_bogo",
                "promotion_name": "Buy 2 Get 1 Free - Dairy",
                "promotion_type": "bogo",
                "discount_value": 1.0,  # Get 1 free
                "start_date": datetime.now().isoformat(),
                "end_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "applicable_products": [],
                "applicable_categories": ["Dairy"],
                "applicable_suppliers": [],
                "minimum_purchase": 0.0,
                "maximum_discount": None,
                "usage_limit_per_user": 3,
                "promo_code": None,
                "is_active": True,
                "description": "Buy 2 dairy products and get 1 free (lowest priced item)"
            },
            {
                "promotion_id": "promo_save5",
                "promotion_name": "$5 Off Orders Over $50",
                "promotion_type": "dollar_off",
                "discount_value": 5.0,
                "start_date": datetime.now().isoformat(),
                "end_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "applicable_products": [],
                "applicable_categories": [],
                "applicable_suppliers": [],
                "minimum_purchase": 50.0,
                "maximum_discount": 5.0,
                "usage_limit_per_user": None,
                "promo_code": "SAVE5",
                "is_active": True,
                "description": "Get $5 off when you spend $50 or more"
            }
        ]
    
    def get_active_promotions(self) -> List[Dict]:
        """Get all currently active promotions"""
        return [p for p in self.promotions if p["is_active"]]
    
    def get_promotions_summary(self) -> str:
        """Get a formatted summary of all active promotions"""
        active_promos = self.get_active_promotions()
        if not active_promos:
            return "No active promotions at this time."
            
        summary = "🎉 **Current Promotions:**\n\n"
        for promo in active_promos:
            summary += f"**{promo['promotion_name']}**\n"
            summary += f"• {promo['description']}\n"
            if promo['promo_code']:
                summary += f"• Code: `{promo['promo_code']}`\n"
            else:
                summary += f"• Automatically applied at checkout\n"
            summary += "\n"
            
        return summary
    
    def find_promotion_by_code(self, code: str) -> Optional[Dict]:
        """Find a promotion by its code"""
        code_upper = code.upper()
        for promo in self.promotions:
            if promo.get('promo_code') and promo['promo_code'].upper() == code_upper:
                return promo
        return None
    
    def get_applicable_promotions(self, cart_items: List[Dict], promo_codes: List[str] = None) -> List[Dict]:
        """Get all promotions applicable to the cart"""
        applicable = []
        cart_total = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)
        
        for promo in self.get_active_promotions():
            # Check if promo code is required and provided
            if promo['promo_code'] and (not promo_codes or promo['promo_code'] not in promo_codes):
                continue
                
            # Check minimum purchase
            if cart_total < promo['minimum_purchase']:
                continue
                
            # Check if any items are applicable
            has_applicable_items = False
            for item in cart_items:
                if self._is_item_applicable(item, promo):
                    has_applicable_items = True
                    break
                    
            if has_applicable_items or (not promo['applicable_products'] and 
                                     not promo['applicable_categories'] and 
                                     not promo['applicable_suppliers']):
                applicable.append(promo)
                
        return applicable
    
    def _is_item_applicable(self, item: Dict, promotion: Dict) -> bool:
        """Check if an item is applicable for a promotion"""
        # Check specific products
        if promotion['applicable_products']:
            if item.get('sku') not in promotion['applicable_products']:
                return False
                
        # Check categories
        if promotion['applicable_categories']:
            if item.get('category') not in promotion['applicable_categories']:
                return False
                
        # Check suppliers
        if promotion['applicable_suppliers']:
            if item.get('supplier') not in promotion['applicable_suppliers']:
                return False
                
        # Special check for organic products
        if promotion['promotion_id'] == 'promo_organic10':
            return item.get('isOrganic', False) or 'organic' in item.get('name', '').lower()
            
        return True
    
    def calculate_discount(self, promotion: Dict, cart_items: List[Dict]) -> Tuple[float, List[str]]:
        """Calculate discount amount for a promotion"""
        applicable_items = []
        for item in cart_items:
            if self._is_item_applicable(item, promotion):
                applicable_items.append(item)
                
        if not applicable_items:
            return 0.0, []
            
        discount = 0.0
        discounted_items = []
        
        if promotion['promotion_type'] == 'percentage_off':
            for item in applicable_items:
                item_discount = (item['price'] * item.get('quantity', 1)) * (promotion['discount_value'] / 100)
                discount += item_discount
                discounted_items.append(item.get('sku', item.get('name', 'item')))
                
        elif promotion['promotion_type'] == 'dollar_off':
            discount = promotion['discount_value']
            discounted_items = [item.get('sku', item.get('name', 'item')) for item in cart_items]
            
        elif promotion['promotion_type'] == 'bogo':
            # Group by SKU for BOGO
            sku_groups = {}
            for item in applicable_items:
                sku = item.get('sku', item.get('name', 'item'))
                if sku not in sku_groups:
                    sku_groups[sku] = []
                sku_groups[sku].append(item)
                
            for sku, items in sku_groups.items():
                total_qty = sum(item.get('quantity', 1) for item in items)
                free_qty = total_qty // 3  # Buy 2 get 1 free
                if free_qty > 0:
                    # Use the lowest price for free items
                    min_price = min(item['price'] for item in items)
                    discount += min_price * free_qty
                    discounted_items.append(sku)
                    
        # Apply maximum discount cap
        if promotion.get('maximum_discount') and discount > promotion['maximum_discount']:
            discount = promotion['maximum_discount']
            
        return discount, discounted_items
    
    def apply_promotions_to_cart(self, cart_items: List[Dict], promo_codes: List[str] = None) -> Dict:
        """Apply all applicable promotions to cart and return summary"""
        if not cart_items:
            return {
                "subtotal": 0.0,
                "total_discount": 0.0,
                "final_total": 0.0,
                "applied_promotions": [],
                "savings_percentage": 0.0
            }
            
        subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in cart_items)
        applicable_promos = self.get_applicable_promotions(cart_items, promo_codes)
        
        total_discount = 0.0
        applied_promotions = []
        
        for promo in applicable_promos:
            discount, items = self.calculate_discount(promo, cart_items)
            if discount > 0:
                total_discount += discount
                applied_promotions.append({
                    "name": promo['promotion_name'],
                    "discount": discount,
                    "items": items
                })
                
        return {
            "subtotal": subtotal,
            "total_discount": total_discount,
            "final_total": subtotal - total_discount,
            "applied_promotions": applied_promotions,
            "savings_percentage": (total_discount / subtotal * 100) if subtotal > 0 else 0
        }

# Singleton instance
promotion_service = PromotionService()