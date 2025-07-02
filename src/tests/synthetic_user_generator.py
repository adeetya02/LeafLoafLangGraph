"""
Synthetic User Generator for Graphiti Testing

Creates realistic user profiles with:
- Diverse shopping patterns (restaurant, family, event planner, etc.)
- 3+ months of purchase history
- Realistic product relationships
- Temporal patterns for reordering
- Event-based shopping
"""

import random
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
import asyncio
import uuid
from enum import Enum

from src.integrations.neo4j_config import get_graphiti_neo4j


class UserType(Enum):
    """Different user personas with distinct shopping patterns"""
    RESTAURANT_OWNER = "restaurant_owner"
    FAMILY_SHOPPER = "family_shopper"
    EVENT_PLANNER = "event_planner"
    HEALTH_CONSCIOUS = "health_conscious"
    BUDGET_SHOPPER = "budget_shopper"
    CONVENIENCE_SHOPPER = "convenience_shopper"
    BULK_BUYER = "bulk_buyer"
    SPECIALTY_COOK = "specialty_cook"


@dataclass
class Product:
    """Product definition"""
    sku: str
    name: str
    category: str
    subcategory: str
    brand: str
    price: float
    unit: str
    tags: List[str]


@dataclass
class OrderItem:
    """Item in an order"""
    product: Product
    quantity: int
    price: float
    
    @property
    def total(self) -> float:
        return self.quantity * self.price


@dataclass
class Order:
    """Order definition"""
    order_id: str
    user_id: str
    timestamp: datetime
    items: List[OrderItem]
    order_type: str
    metadata: Dict[str, Any]
    
    @property
    def total_amount(self) -> float:
        return sum(item.total for item in self.items)
    
    @property
    def item_count(self) -> int:
        return len(self.items)


class ProductCatalog:
    """Realistic product catalog for Indian grocery"""
    
    def __init__(self):
        self.products = self._create_catalog()
        self.product_relationships = self._create_relationships()
    
    def _create_catalog(self) -> Dict[str, Product]:
        """Create comprehensive product catalog"""
        products = {}
        
        # Rice varieties
        rice_products = [
            Product("SKU001", "Daawat Basmati Rice", "Staples", "Rice", "Daawat", 280.0, "5kg", ["premium", "long-grain"]),
            Product("SKU002", "India Gate Classic Basmati", "Staples", "Rice", "India Gate", 250.0, "5kg", ["basmati", "aged"]),
            Product("SKU003", "Fortune Everyday Basmati", "Staples", "Rice", "Fortune", 180.0, "5kg", ["budget", "basmati"]),
            Product("SKU004", "Organic Brown Rice", "Staples", "Rice", "24 Mantra", 120.0, "1kg", ["organic", "healthy"]),
            Product("SKU005", "Sona Masoori Rice", "Staples", "Rice", "Heritage", 200.0, "5kg", ["south-indian", "daily-use"]),
        ]
        
        # Dal varieties
        dal_products = [
            Product("SKU011", "Tata Sampann Toor Dal", "Staples", "Dal", "Tata Sampann", 155.0, "1kg", ["unpolished", "protein"]),
            Product("SKU012", "Organic Moong Dal", "Staples", "Dal", "24 Mantra", 180.0, "1kg", ["organic", "split"]),
            Product("SKU013", "Chana Dal Premium", "Staples", "Dal", "Fortune", 120.0, "1kg", ["bengal-gram"]),
            Product("SKU014", "Masoor Dal", "Staples", "Dal", "Tata Sampann", 140.0, "1kg", ["red-lentil", "quick-cook"]),
            Product("SKU015", "Urad Dal", "Staples", "Dal", "Heritage", 160.0, "1kg", ["black-gram", "south-indian"]),
        ]
        
        # Atta/Flour
        flour_products = [
            Product("SKU021", "Aashirvaad Whole Wheat Atta", "Staples", "Flour", "Aashirvaad", 220.0, "10kg", ["chakki-atta", "whole-wheat"]),
            Product("SKU022", "Pillsbury Multigrain Atta", "Staples", "Flour", "Pillsbury", 250.0, "5kg", ["multigrain", "healthy"]),
            Product("SKU023", "Besan (Gram Flour)", "Staples", "Flour", "Fortune", 90.0, "1kg", ["gluten-free", "protein"]),
            Product("SKU024", "Rice Flour", "Staples", "Flour", "Aashirvaad", 60.0, "1kg", ["gluten-free"]),
            Product("SKU025", "Maida (All Purpose Flour)", "Staples", "Flour", "Fortune", 50.0, "1kg", ["refined"]),
        ]
        
        # Oils
        oil_products = [
            Product("SKU031", "Fortune Sunflower Oil", "Cooking", "Oil", "Fortune", 180.0, "1L", ["refined", "vitamin-e"]),
            Product("SKU032", "Saffola Gold Oil", "Cooking", "Oil", "Saffola", 220.0, "1L", ["healthy", "blend"]),
            Product("SKU033", "Organic Coconut Oil", "Cooking", "Oil", "24 Mantra", 280.0, "500ml", ["organic", "cold-pressed"]),
            Product("SKU034", "Mustard Oil", "Cooking", "Oil", "Fortune", 150.0, "1L", ["kachi-ghani", "pungent"]),
            Product("SKU035", "Olive Oil Extra Virgin", "Cooking", "Oil", "Figaro", 450.0, "500ml", ["imported", "salad"]),
        ]
        
        # Dairy
        dairy_products = [
            Product("SKU041", "Amul Toned Milk", "Dairy", "Milk", "Amul", 56.0, "1L", ["toned", "daily"]),
            Product("SKU042", "Mother Dairy Full Cream Milk", "Dairy", "Milk", "Mother Dairy", 62.0, "1L", ["full-cream"]),
            Product("SKU043", "Amul Butter", "Dairy", "Butter", "Amul", 52.0, "100g", ["salted"]),
            Product("SKU044", "Epigamia Greek Yogurt", "Dairy", "Yogurt", "Epigamia", 40.0, "90g", ["greek", "protein"]),
            Product("SKU045", "Amul Cheese Slices", "Dairy", "Cheese", "Amul", 125.0, "200g", ["processed"]),
            Product("SKU046", "Paneer Fresh", "Dairy", "Paneer", "Amul", 85.0, "200g", ["fresh", "protein"]),
        ]
        
        # Vegetables
        vegetable_products = [
            Product("SKU051", "Onion", "Fresh", "Vegetables", "Fresh", 40.0, "1kg", ["daily-use"]),
            Product("SKU052", "Tomato", "Fresh", "Vegetables", "Fresh", 30.0, "1kg", ["daily-use"]),
            Product("SKU053", "Potato", "Fresh", "Vegetables", "Fresh", 35.0, "1kg", ["staple"]),
            Product("SKU054", "Green Chilli", "Fresh", "Vegetables", "Fresh", 80.0, "250g", ["spicy"]),
            Product("SKU055", "Ginger", "Fresh", "Vegetables", "Fresh", 120.0, "250g", ["aromatic"]),
            Product("SKU056", "Garlic", "Fresh", "Vegetables", "Fresh", 200.0, "250g", ["aromatic"]),
            Product("SKU057", "Coriander Leaves", "Fresh", "Herbs", "Fresh", 20.0, "100g", ["herb"]),
            Product("SKU058", "Curry Leaves", "Fresh", "Herbs", "Fresh", 10.0, "1bunch", ["south-indian"]),
        ]
        
        # Fruits
        fruit_products = [
            Product("SKU061", "Banana", "Fresh", "Fruits", "Fresh", 50.0, "1dozen", ["energy"]),
            Product("SKU062", "Apple Kashmir", "Fresh", "Fruits", "Fresh", 180.0, "1kg", ["premium"]),
            Product("SKU063", "Orange", "Fresh", "Fruits", "Fresh", 80.0, "1kg", ["vitamin-c"]),
            Product("SKU064", "Mango Alphonso", "Fresh", "Fruits", "Fresh", 250.0, "1dozen", ["seasonal", "premium"]),
            Product("SKU065", "Grapes", "Fresh", "Fruits", "Fresh", 120.0, "500g", ["seedless"]),
        ]
        
        # Spices
        spice_products = [
            Product("SKU071", "MDH Garam Masala", "Spices", "Blends", "MDH", 65.0, "100g", ["blend"]),
            Product("SKU072", "Everest Turmeric Powder", "Spices", "Ground", "Everest", 45.0, "200g", ["essential"]),
            Product("SKU073", "Red Chilli Powder", "Spices", "Ground", "MDH", 55.0, "200g", ["spicy"]),
            Product("SKU074", "Cumin Seeds", "Spices", "Whole", "Catch", 120.0, "100g", ["whole"]),
            Product("SKU075", "Coriander Powder", "Spices", "Ground", "Everest", 40.0, "200g", ["essential"]),
        ]
        
        # Snacks
        snack_products = [
            Product("SKU081", "Lays Classic Chips", "Snacks", "Chips", "Lays", 20.0, "52g", ["party"]),
            Product("SKU082", "Haldiram Bhujia", "Snacks", "Namkeen", "Haldiram", 85.0, "400g", ["traditional"]),
            Product("SKU083", "Britannia Marie Gold", "Snacks", "Biscuits", "Britannia", 30.0, "250g", ["tea-time"]),
            Product("SKU084", "Oreo Cookies", "Snacks", "Cookies", "Oreo", 30.0, "120g", ["sweet"]),
            Product("SKU085", "Kurkure Masala Munch", "Snacks", "Namkeen", "Kurkure", 20.0, "90g", ["spicy"]),
        ]
        
        # Beverages
        beverage_products = [
            Product("SKU091", "Red Label Tea", "Beverages", "Tea", "Red Label", 190.0, "500g", ["black-tea"]),
            Product("SKU092", "Nescafe Classic Coffee", "Beverages", "Coffee", "Nescafe", 325.0, "200g", ["instant"]),
            Product("SKU093", "Bournvita", "Beverages", "Health Drink", "Cadbury", 210.0, "500g", ["chocolate"]),
            Product("SKU094", "Tang Orange", "Beverages", "Juice", "Tang", 135.0, "500g", ["instant"]),
            Product("SKU095", "Coca Cola", "Beverages", "Soft Drink", "Coca Cola", 40.0, "750ml", ["party"]),
        ]
        
        # Combine all products
        all_products = (
            rice_products + dal_products + flour_products + oil_products +
            dairy_products + vegetable_products + fruit_products + 
            spice_products + snack_products + beverage_products
        )
        
        for product in all_products:
            products[product.sku] = product
        
        return products
    
    def _create_relationships(self) -> Dict[str, List[str]]:
        """Define products frequently bought together"""
        return {
            # Rice combinations
            "SKU001": ["SKU011", "SKU031", "SKU071", "SKU051"],  # Basmati + Toor Dal + Oil + Onion
            "SKU002": ["SKU012", "SKU032", "SKU072", "SKU052"],  # Basmati + Moong Dal + Oil + Tomato
            "SKU005": ["SKU015", "SKU033", "SKU058", "SKU056"],  # Sona Masoori + Urad Dal + Coconut Oil + Curry Leaves
            
            # Dal combinations
            "SKU011": ["SKU001", "SKU051", "SKU052", "SKU073"],  # Toor Dal + Rice + Onion + Tomato + Chilli
            "SKU012": ["SKU004", "SKU054", "SKU055", "SKU074"],  # Moong Dal + Brown Rice + Green Chilli + Ginger
            
            # Atta combinations
            "SKU021": ["SKU031", "SKU043", "SKU041", "SKU053"],  # Atta + Oil + Butter + Milk + Potato
            "SKU022": ["SKU032", "SKU044", "SKU062", "SKU065"],  # Multigrain + Healthy Oil + Yogurt + Apple
            
            # Party combinations
            "SKU081": ["SKU082", "SKU084", "SKU095"],  # Chips + Namkeen + Cookies + Cola
            "SKU064": ["SKU062", "SKU065", "SKU044"],  # Mango + Apple + Grapes + Yogurt
            
            # Daily essentials
            "SKU041": ["SKU042", "SKU043", "SKU083", "SKU091"],  # Milk + Butter + Biscuits + Tea
            "SKU051": ["SKU052", "SKU053", "SKU054", "SKU055"],  # Onion + Tomato + Potato + Chilli + Ginger
        }
    
    def get_product(self, sku: str) -> Product:
        """Get product by SKU"""
        return self.products.get(sku)
    
    def get_products_by_category(self, category: str) -> List[Product]:
        """Get all products in a category"""
        return [p for p in self.products.values() if p.category == category]
    
    def get_related_products(self, sku: str) -> List[Product]:
        """Get products frequently bought together"""
        related_skus = self.product_relationships.get(sku, [])
        return [self.products[sku] for sku in related_skus if sku in self.products]
    
    def get_random_products(self, count: int, category: str = None) -> List[Product]:
        """Get random products, optionally filtered by category"""
        available = list(self.products.values())
        if category:
            available = [p for p in available if p.category == category]
        
        return random.sample(available, min(count, len(available)))


class UserProfile:
    """User profile with shopping preferences"""
    
    def __init__(self, user_type: UserType, user_id: str = None):
        self.user_id = user_id or str(uuid.uuid4())
        self.user_type = user_type
        self.email = f"{user_type.value}_{self.user_id[:8]}@leafloaf.com"
        self.name = self._generate_name()
        self.preferences = self._generate_preferences()
        self.shopping_pattern = self._generate_shopping_pattern()
        self.favorite_products = []
        self.avoided_products = []
        self.special_events = self._generate_events()
    
    def _generate_name(self) -> str:
        """Generate realistic name based on user type"""
        names = {
            UserType.RESTAURANT_OWNER: ["Raj's Kitchen", "Sharma Restaurant", "Delhi Darbar", "Sagar Ratna"],
            UserType.FAMILY_SHOPPER: ["Priya Sharma", "Anjali Gupta", "Sunita Verma", "Kavita Singh"],
            UserType.EVENT_PLANNER: ["Elite Events", "Celebration Planners", "Party Perfect", "Dream Events"],
            UserType.HEALTH_CONSCIOUS: ["Dr. Amit Kumar", "Yoga Wellness", "FitLife Studio", "Green Living"],
            UserType.BUDGET_SHOPPER: ["Value Mart", "Smart Shopper", "Budget Bazaar", "Thrifty Buyer"],
            UserType.CONVENIENCE_SHOPPER: ["Quick Mart", "Express Buy", "Time Saver", "Busy Bee"],
            UserType.BULK_BUYER: ["Wholesale King", "Bulk Depot", "Mega Store", "Stock Up Shop"],
            UserType.SPECIALTY_COOK: ["Chef's Choice", "Gourmet Kitchen", "Fusion Foods", "Masterchef Home"]
        }
        
        return random.choice(names.get(self.user_type, ["Generic User"]))
    
    def _generate_preferences(self) -> Dict[str, Any]:
        """Generate preferences based on user type"""
        prefs = {
            UserType.RESTAURANT_OWNER: {
                "bulk_buying": True,
                "quality": "premium",
                "delivery": "scheduled",
                "payment": "credit",
                "brands": ["Daawat", "India Gate", "Fortune", "Tata Sampann"],
                "categories": ["Staples", "Spices", "Cooking", "Fresh"]
            },
            UserType.FAMILY_SHOPPER: {
                "bulk_buying": False,
                "quality": "balanced",
                "delivery": "flexible",
                "payment": "mixed",
                "brands": ["Aashirvaad", "Amul", "Fortune", "Britannia"],
                "categories": ["Staples", "Dairy", "Fresh", "Snacks"]
            },
            UserType.EVENT_PLANNER: {
                "bulk_buying": True,
                "quality": "premium",
                "delivery": "urgent",
                "payment": "credit",
                "brands": ["Premium", "Imported"],
                "categories": ["Snacks", "Beverages", "Fresh", "Dairy"]
            },
            UserType.HEALTH_CONSCIOUS: {
                "bulk_buying": False,
                "quality": "organic",
                "delivery": "scheduled",
                "payment": "online",
                "brands": ["24 Mantra", "Organic India", "Epigamia"],
                "categories": ["Staples", "Fresh", "Dairy"]
            },
            UserType.BUDGET_SHOPPER: {
                "bulk_buying": True,
                "quality": "value",
                "delivery": "standard",
                "payment": "cash",
                "brands": ["Fortune", "Generic", "Local"],
                "categories": ["Staples", "Fresh"]
            }
        }
        
        return prefs.get(self.user_type, {})
    
    def _generate_shopping_pattern(self) -> Dict[str, Any]:
        """Generate shopping pattern based on user type"""
        patterns = {
            UserType.RESTAURANT_OWNER: {
                "frequency": "weekly",
                "avg_order_value": 15000,
                "order_size": "large",
                "time_preference": "morning",
                "day_preference": ["monday", "thursday"],
                "seasonal_variation": 0.2
            },
            UserType.FAMILY_SHOPPER: {
                "frequency": "biweekly", 
                "avg_order_value": 3000,
                "order_size": "medium",
                "time_preference": "evening",
                "day_preference": ["saturday", "sunday"],
                "seasonal_variation": 0.1
            },
            UserType.EVENT_PLANNER: {
                "frequency": "event_based",
                "avg_order_value": 8000,
                "order_size": "large",
                "time_preference": "any",
                "day_preference": ["any"],
                "seasonal_variation": 0.5
            },
            UserType.HEALTH_CONSCIOUS: {
                "frequency": "weekly",
                "avg_order_value": 2500,
                "order_size": "small",
                "time_preference": "morning",
                "day_preference": ["sunday"],
                "seasonal_variation": 0.1
            },
            UserType.BUDGET_SHOPPER: {
                "frequency": "monthly",
                "avg_order_value": 5000,
                "order_size": "large",
                "time_preference": "any",
                "day_preference": ["monthend"],
                "seasonal_variation": 0.3
            }
        }
        
        return patterns.get(self.user_type, {})
    
    def _generate_events(self) -> List[Dict[str, Any]]:
        """Generate special events for the user"""
        events = []
        
        if self.user_type == UserType.RESTAURANT_OWNER:
            events = [
                {"name": "Weekend Rush Prep", "frequency": "weekly", "products": ["vegetables", "spices"]},
                {"name": "Monthly Stock Up", "frequency": "monthly", "products": ["rice", "dal", "oil"]},
                {"name": "Festival Special Menu", "frequency": "seasonal", "products": ["premium", "sweets"]}
            ]
        elif self.user_type == UserType.FAMILY_SHOPPER:
            events = [
                {"name": "Kids Birthday", "frequency": "yearly", "products": ["snacks", "beverages", "cake"]},
                {"name": "Festival Shopping", "frequency": "seasonal", "products": ["sweets", "dry fruits"]},
                {"name": "Guest Visit", "frequency": "monthly", "products": ["snacks", "tea", "premium"]}
            ]
        elif self.user_type == UserType.EVENT_PLANNER:
            events = [
                {"name": "Corporate Event", "frequency": "biweekly", "products": ["snacks", "beverages"]},
                {"name": "Wedding Season", "frequency": "seasonal", "products": ["premium", "bulk"]},
                {"name": "Birthday Parties", "frequency": "weekly", "products": ["cake", "snacks", "drinks"]}
            ]
        
        return events


class SyntheticDataGenerator:
    """Generate synthetic shopping data"""
    
    def __init__(self):
        self.catalog = ProductCatalog()
        self.users: Dict[str, UserProfile] = {}
        self.orders: List[Order] = []
    
    def create_users(self, count_per_type: int = 2) -> Dict[str, UserProfile]:
        """Create diverse user profiles"""
        for user_type in UserType:
            for i in range(count_per_type):
                user = UserProfile(user_type)
                self.users[user.user_id] = user
                
                # Set favorite products based on preferences
                if "Staples" in user.preferences.get("categories", []):
                    user.favorite_products.extend(
                        random.sample([p.sku for p in self.catalog.get_products_by_category("Staples")], 3)
                    )
                
                if user.preferences.get("quality") == "organic":
                    organic_products = [p for p in self.catalog.products.values() if "organic" in p.tags]
                    user.favorite_products.extend([p.sku for p in random.sample(organic_products, 2)])
        
        return self.users
    
    def generate_order_history(
        self, 
        user: UserProfile, 
        start_date: datetime,
        end_date: datetime
    ) -> List[Order]:
        """Generate realistic order history for a user"""
        orders = []
        current_date = start_date
        
        pattern = user.shopping_pattern
        frequency = pattern.get("frequency", "biweekly")
        
        # Determine order dates based on frequency
        order_dates = self._generate_order_dates(frequency, start_date, end_date, pattern)
        
        for order_date in order_dates:
            # Check for special events
            event_order = self._check_event_order(user, order_date)
            
            if event_order:
                order = self._create_event_order(user, order_date, event_order)
            else:
                order = self._create_regular_order(user, order_date)
            
            orders.append(order)
            self.orders.append(order)
        
        # Add some spontaneous orders
        spontaneous_count = random.randint(2, 5)
        for _ in range(spontaneous_count):
            random_date = start_date + timedelta(
                days=random.randint(0, (end_date - start_date).days)
            )
            order = self._create_spontaneous_order(user, random_date)
            orders.append(order)
            self.orders.append(order)
        
        return sorted(orders, key=lambda x: x.timestamp)
    
    def _generate_order_dates(
        self,
        frequency: str,
        start_date: datetime,
        end_date: datetime,
        pattern: Dict[str, Any]
    ) -> List[datetime]:
        """Generate order dates based on frequency pattern"""
        dates = []
        current = start_date
        
        if frequency == "daily":
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=1)
        
        elif frequency == "weekly":
            while current <= end_date:
                # Find next preferred day
                day_prefs = pattern.get("day_preference", ["any"])
                if "any" not in day_prefs:
                    days_map = {
                        "monday": 0, "tuesday": 1, "wednesday": 2,
                        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
                    }
                    target_days = [days_map.get(d, 0) for d in day_prefs]
                    
                    # Find next occurrence of preferred day
                    days_ahead = min((d - current.weekday()) % 7 for d in target_days)
                    if days_ahead == 0:
                        days_ahead = 7
                    current += timedelta(days=days_ahead)
                else:
                    current += timedelta(days=7)
                
                if current <= end_date:
                    dates.append(current)
        
        elif frequency == "biweekly":
            while current <= end_date:
                dates.append(current)
                current += timedelta(days=14)
        
        elif frequency == "monthly":
            while current <= end_date:
                # Check for monthend preference
                if "monthend" in pattern.get("day_preference", []):
                    # Last week of month
                    next_month = current.replace(day=28) + timedelta(days=4)
                    last_day = next_month - timedelta(days=next_month.day)
                    dates.append(last_day)
                    current = last_day + timedelta(days=1)
                else:
                    dates.append(current)
                    # Add roughly a month
                    current += timedelta(days=30)
        
        elif frequency == "event_based":
            # Generate random event dates
            num_events = random.randint(8, 15)
            for _ in range(num_events):
                random_date = start_date + timedelta(
                    days=random.randint(0, (end_date - start_date).days)
                )
                dates.append(random_date)
        
        return sorted(dates)
    
    def _check_event_order(self, user: UserProfile, order_date: datetime) -> Optional[Dict[str, Any]]:
        """Check if this order date corresponds to a special event"""
        for event in user.special_events:
            if event["frequency"] == "weekly" and order_date.weekday() in [5, 6]:  # Weekend
                return event
            elif event["frequency"] == "monthly" and order_date.day > 25:  # Month end
                return event
            elif event["frequency"] == "seasonal":
                # Check for festival seasons (simplified)
                if order_date.month in [10, 11]:  # Diwali season
                    return event
        
        return None
    
    def _create_regular_order(self, user: UserProfile, order_date: datetime) -> Order:
        """Create a regular order based on user preferences"""
        items = []
        
        # Always include favorite products
        for fav_sku in user.favorite_products[:3]:
            product = self.catalog.get_product(fav_sku)
            if product:
                quantity = self._get_quantity_for_product(product, user)
                items.append(OrderItem(product, quantity, product.price))
        
        # Add products from preferred categories
        for category in user.preferences.get("categories", [])[:2]:
            category_products = self.catalog.get_products_by_category(category)
            if category_products:
                selected = random.sample(category_products, min(2, len(category_products)))
                for product in selected:
                    if product.sku not in [item.product.sku for item in items]:
                        quantity = self._get_quantity_for_product(product, user)
                        items.append(OrderItem(product, quantity, product.price))
        
        # Add related products
        if items:
            main_product = items[0].product
            related = self.catalog.get_related_products(main_product.sku)
            for rel_product in related[:2]:
                if rel_product.sku not in [item.product.sku for item in items]:
                    quantity = self._get_quantity_for_product(rel_product, user)
                    items.append(OrderItem(rel_product, quantity, rel_product.price))
        
        order_id = f"ORD-{user.user_id[:8]}-{order_date.strftime('%Y%m%d%H%M%S')}"
        
        return Order(
            order_id=order_id,
            user_id=user.user_id,
            timestamp=order_date,
            items=items,
            order_type="regular",
            metadata={
                "user_type": user.user_type.value,
                "shopping_pattern": user.shopping_pattern
            }
        )
    
    def _create_event_order(self, user: UserProfile, order_date: datetime, event: Dict[str, Any]) -> Order:
        """Create an order for a special event"""
        items = []
        
        # Get products related to the event
        event_products = []
        for product_type in event.get("products", []):
            if product_type == "vegetables":
                event_products.extend(self.catalog.get_products_by_category("Fresh"))
            elif product_type == "spices":
                event_products.extend(self.catalog.get_products_by_category("Spices"))
            elif product_type == "snacks":
                event_products.extend(self.catalog.get_products_by_category("Snacks"))
            elif product_type == "beverages":
                event_products.extend(self.catalog.get_products_by_category("Beverages"))
            elif product_type == "premium":
                event_products.extend([p for p in self.catalog.products.values() if "premium" in p.tags])
        
        # Select products for the event
        selected = random.sample(event_products, min(8, len(event_products)))
        for product in selected:
            # Event orders typically have larger quantities
            quantity = self._get_quantity_for_product(product, user) * 2
            items.append(OrderItem(product, quantity, product.price))
        
        order_id = f"ORD-EVENT-{user.user_id[:8]}-{order_date.strftime('%Y%m%d%H%M%S')}"
        
        return Order(
            order_id=order_id,
            user_id=user.user_id,
            timestamp=order_date,
            items=items,
            order_type="event",
            metadata={
                "user_type": user.user_type.value,
                "event": event["name"],
                "event_type": event.get("frequency")
            }
        )
    
    def _create_spontaneous_order(self, user: UserProfile, order_date: datetime) -> Order:
        """Create a small spontaneous order"""
        # Spontaneous orders are typically small and focused
        num_items = random.randint(1, 3)
        products = self.catalog.get_random_products(num_items)
        
        items = []
        for product in products:
            quantity = 1  # Small quantities for spontaneous orders
            items.append(OrderItem(product, quantity, product.price))
        
        order_id = f"ORD-SPON-{user.user_id[:8]}-{order_date.strftime('%Y%m%d%H%M%S')}"
        
        return Order(
            order_id=order_id,
            user_id=user.user_id,
            timestamp=order_date,
            items=items,
            order_type="spontaneous",
            metadata={
                "user_type": user.user_type.value,
                "trigger": random.choice(["urgent_need", "forgot_item", "special_offer"])
            }
        )
    
    def _get_quantity_for_product(self, product: Product, user: UserProfile) -> int:
        """Determine quantity based on product type and user profile"""
        base_quantities = {
            UserType.RESTAURANT_OWNER: {
                "Rice": 25,  # 25kg
                "Dal": 10,   # 10kg
                "Oil": 5,    # 5L
                "Vegetables": 5,  # 5kg
                "Spices": 3,  # 300g
                "default": 5
            },
            UserType.FAMILY_SHOPPER: {
                "Rice": 5,   # 5kg
                "Dal": 2,    # 2kg
                "Oil": 1,    # 1L
                "Vegetables": 1,  # 1kg
                "Milk": 2,   # 2L
                "default": 1
            },
            UserType.BULK_BUYER: {
                "Rice": 50,  # 50kg
                "Dal": 20,   # 20kg
                "Oil": 10,   # 10L
                "default": 10
            }
        }
        
        user_quantities = base_quantities.get(user.user_type, {"default": 1})
        quantity = user_quantities.get(product.subcategory, user_quantities.get("default", 1))
        
        # Add some variation
        variation = random.uniform(0.8, 1.2)
        return max(1, int(quantity * variation))
    
    async def save_to_neo4j(self):
        """Save all generated data to Neo4j"""
        neo4j = await get_graphiti_neo4j()
        
        # Save users
        for user in self.users.values():
            await neo4j.create_user({
                "user_id": user.user_id,
                "email": user.email,
                "name": user.name,
                "preferences": user.preferences,
                "shopping_pattern": user.user_type.value
            })
        
        # Save products
        for product in self.catalog.products.values():
            await neo4j.create_product({
                "sku": product.sku,
                "name": product.name,
                "category": product.category,
                "subcategory": product.subcategory,
                "brand": product.brand,
                "price": product.price,
                "unit": product.unit,
                "description": f"{product.brand} {product.name}",
                "tags": product.tags
            })
        
        # Save orders
        for order in self.orders:
            order_data = {
                "order_id": order.order_id,
                "user_id": order.user_id,
                "timestamp": order.timestamp.isoformat(),
                "total_amount": order.total_amount,
                "item_count": order.item_count,
                "order_type": order.order_type,
                "metadata": order.metadata,
                "items": [
                    {
                        "sku": item.product.sku,
                        "quantity": item.quantity,
                        "price": item.price,
                        "total": item.total
                    }
                    for item in order.items
                ]
            }
            await neo4j.create_order(order_data)
        
        # Create product relationships
        for sku, related_skus in self.catalog.product_relationships.items():
            for related_sku in related_skus:
                await neo4j.create_relationship(
                    from_node=("Product", "sku", sku),
                    to_node=("Product", "sku", related_sku),
                    relationship="BOUGHT_WITH",
                    properties={"confidence": 0.8}
                )


async def generate_test_data():
    """Generate comprehensive test data"""
    generator = SyntheticDataGenerator()
    
    # Create users (2 of each type)
    users = generator.create_users(count_per_type=2)
    print(f"Created {len(users)} users across {len(UserType)} user types")
    
    # Generate 3 months of order history
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    for user in users.values():
        orders = generator.generate_order_history(user, start_date, end_date)
        print(f"Generated {len(orders)} orders for {user.name} ({user.user_type.value})")
    
    print(f"\nTotal orders generated: {len(generator.orders)}")
    
    # Save to Neo4j
    print("\nSaving to Neo4j...")
    await generator.save_to_neo4j()
    print("Data saved successfully!")
    
    return generator


if __name__ == "__main__":
    # Run the generator
    asyncio.run(generate_test_data())