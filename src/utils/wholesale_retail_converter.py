"""
Wholesale to Retail Quantity Converter
Converts Baldor wholesale quantities to consumer-friendly retail quantities
"""

from typing import Dict, Tuple, Optional
import re
import structlog

logger = structlog.get_logger()

# Wholesale to retail conversion mappings
UNIT_CONVERSIONS = {
    # Produce conversions
    "case": {
        "default": 1,  # Default case = 1 retail unit
        "patterns": {
            r"spinach|lettuce|greens": (24, "bunches"),  # Case of greens = 24 bunches
            r"tomato|pepper|cucumber": (25, "lbs"),  # Case = 25 lbs
            r"apple|orange|pear": (40, "lbs"),  # Case = 40 lbs
            r"banana": (40, "lbs"),  # Case = 40 lbs
            r"berries|strawberr": (12, "pints"),  # Case = 12 pints
            r"herbs|basil|cilantro": (12, "bunches"),  # Case = 12 bunches
            r"carrot|radish": (24, "bunches"),  # Case = 24 bunches
            r"potato|onion": (50, "lbs"),  # Case = 50 lbs
        }
    },
    "bag": {
        "default": 5,  # Default bag = 5 lbs
        "patterns": {
            r"spinach|salad|mix": (5, "oz"),  # Bag = 5 oz
            r"potato": (10, "lbs"),  # Bag = 10 lbs
            r"onion": (3, "lbs"),  # Bag = 3 lbs
            r"carrot": (2, "lbs"),  # Bag = 2 lbs
        }
    },
    "crate": {
        "default": 20,  # Default crate = 20 lbs
        "patterns": {
            r"apple|pear": (35, "lbs"),  # Crate = 35 lbs
            r"orange|citrus": (40, "lbs"),  # Crate = 40 lbs
        }
    },
    "pallet": {
        "default": 40,  # Default pallet = 40 cases
        "patterns": {}
    }
}

# Retail-friendly units
RETAIL_UNITS = ["each", "lb", "lbs", "oz", "bunch", "bunches", "pint", "quart", "gallon"]

# Price multipliers for wholesale to retail
PRICE_MARKUP = 2.5  # Typical retail markup from wholesale


class WholesaleRetailConverter:
    """Convert wholesale quantities and prices to retail"""
    
    @staticmethod
    def convert_quantity(quantity: float, unit: str, product_name: str = "") -> Tuple[float, str]:
        """
        Convert wholesale quantity to retail quantity
        
        Args:
            quantity: Wholesale quantity
            unit: Wholesale unit (case, bag, etc.)
            product_name: Product name for context-aware conversion
            
        Returns:
            Tuple of (retail_quantity, retail_unit)
        """
        unit_lower = unit.lower()
        product_lower = product_name.lower()
        
        # Already retail unit
        if unit_lower in RETAIL_UNITS:
            return quantity, unit
        
        # Check for wholesale units
        if unit_lower in UNIT_CONVERSIONS:
            conversion_rules = UNIT_CONVERSIONS[unit_lower]
            
            # Try pattern matching first
            for pattern, (multiplier, new_unit) in conversion_rules["patterns"].items():
                if re.search(pattern, product_lower):
                    retail_quantity = quantity * multiplier
                    logger.info(f"Converted {quantity} {unit} of {product_name} to {retail_quantity} {new_unit}")
                    return retail_quantity, new_unit
            
            # Use default conversion
            default_multiplier = conversion_rules["default"]
            retail_quantity = quantity * default_multiplier
            retail_unit = "units" if unit_lower == "case" else "lbs"
            
            logger.info(f"Default conversion: {quantity} {unit} to {retail_quantity} {retail_unit}")
            return retail_quantity, retail_unit
        
        # Unknown unit - return as is with warning
        logger.warning(f"Unknown wholesale unit: {unit}")
        return quantity, unit
    
    @staticmethod
    def convert_price(price: float, wholesale_unit: str, retail_unit: str, 
                     wholesale_qty: float = 1, retail_qty: float = 1) -> float:
        """
        Convert wholesale price to retail price
        
        Args:
            price: Wholesale price
            wholesale_unit: Original wholesale unit
            retail_unit: Converted retail unit
            wholesale_qty: Original wholesale quantity
            retail_qty: Converted retail quantity
            
        Returns:
            Retail price per unit
        """
        # Calculate price per retail unit
        if retail_qty > 0:
            price_per_unit = (price * PRICE_MARKUP) / retail_qty
        else:
            price_per_unit = price * PRICE_MARKUP
        
        # Round to reasonable retail price
        if price_per_unit < 1:
            return round(price_per_unit, 2)  # Cents precision for items < $1
        else:
            return round(price_per_unit, 1)  # Dime precision for items > $1
    
    @staticmethod
    def format_retail_display(product: Dict) -> Dict:
        """
        Format product for retail display
        
        Args:
            product: Product dict with wholesale data
            
        Returns:
            Product dict formatted for retail display
        """
        # Extract info from Weaviate schema - handle both field names
        product_name = product.get("product_name", product.get("name", ""))
        
        # Extract pack information from product name
        pack_match = re.search(r'(\d+)\s*X\s*(\d+)(CT|PK|PACK)', product_name.upper())
        if pack_match:
            pack_count = pack_match.group(2)
            pack_size = f"pack ({pack_count} count)"
        else:
            # Check for other pack patterns
            if "3CT" in product_name.upper():
                pack_size = "pack (3 count)"
            elif "6CT" in product_name.upper():
                pack_size = "pack (6 count)"
            elif "12CT" in product_name.upper():
                pack_size = "pack (12 count)"
            else:
                pack_size = None
        
        # Clean product name - remove wholesale jargon
        clean_name = product_name
        # Remove patterns like "8 X 3CT CTN", "CASE", "BAG", etc
        clean_name = re.sub(r'\d+\s*X\s*\d+(CT|PK|PACK)\s*(CTN|CASE|BAG)?', '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'\b(CASE|CTN|BAG|SACK|FLAT|BUNCH)\b', '', clean_name, flags=re.IGNORECASE)
        clean_name = re.sub(r'\b\d+\s*(LB|OZ|PT|QT)\b', '', clean_name, flags=re.IGNORECASE)
        # Clean up multiple spaces and title case
        clean_name = ' '.join(clean_name.split()).strip()
        clean_name = clean_name.title()
        
        # Handle Baldor data format
        if "retailPrice" in product:
            # Already has retail price from Weaviate
            retail_price = product.get("retailPrice", 0)
            wholesale_price = product.get("wholesalePrice", retail_price)
            retail_unit = product.get("retailPackSize", "each")
            wholesale_unit = "case"  # Default for Baldor
            wholesale_qty = product.get("caseQuantity", 1)
        else:
            # Legacy format
            wholesale_qty = product.get("quantity", 1)
            wholesale_unit = product.get("unit", "each")
            wholesale_price = product.get("price", 0)
            retail_price = 0
            retail_unit = "each"
        
        # Skip conversion if already has retail data
        if "retailPrice" in product:
            retail_qty = 1  # Display as per unit
        else:
            # Special handling for packs
            if pack_size:
                # For packs, calculate price per pack
                # Example: "8 X 3CT" means 8 3-packs in a case
                case_match = re.search(r'(\d+)\s*X\s*\d+(CT|PK|PACK)', product_name.upper())
                if case_match:
                    packs_per_case = int(case_match.group(1))
                    retail_price = (wholesale_price * PRICE_MARKUP) / packs_per_case
                    retail_qty = packs_per_case
                    retail_unit = pack_size
                else:
                    # Default conversion
                    retail_qty, retail_unit = WholesaleRetailConverter.convert_quantity(
                        wholesale_qty, wholesale_unit, product_name
                    )
                    retail_price = WholesaleRetailConverter.convert_price(
                        wholesale_price, wholesale_unit, retail_unit, wholesale_qty, retail_qty
                    )
            else:
                # Convert to retail normally
                retail_qty, retail_unit = WholesaleRetailConverter.convert_quantity(
                    wholesale_qty, wholesale_unit, product_name
                )
                
                retail_price = WholesaleRetailConverter.convert_price(
                    wholesale_price, wholesale_unit, retail_unit, wholesale_qty, retail_qty
                )
        
        # Create retail-friendly display with proper field mappings
        retail_product = {
            "name": clean_name,  # Use cleaned name
            "description": product.get("usage", ""),  # Baldor uses 'usage' field
            "price": float(retail_price) if retail_price else 0.0,
            "unit": pack_size if pack_size else retail_unit,  # Use pack size if available
            "price_display": f"${retail_price:.2f}/{pack_size if pack_size else retail_unit}",
            "category": product.get("category", ""),
            "supplier_category": product.get("supplierCategory", ""),
            "brand": product.get("brand", ""),
            "sku": product.get("sku", ""),
            "supplier": product.get("supplier", "Baldor"),
            "is_organic": product.get("isOrganic", False),
            "pack_size": pack_size or product.get("packSize", ""),
            "search_terms": product.get("searchTerms", []),
            # Keep wholesale info for reference
            "_wholesale": {
                "quantity": wholesale_qty,
                "unit": wholesale_unit,
                "price": wholesale_price,
                "case_quantity": product.get("caseQuantity", 1)
            }
        }
        
        # Add quantity suggestions for retail
        if retail_unit in ["lb", "lbs"]:
            retail_product["suggested_quantities"] = [0.5, 1, 2, 3, 5]
        elif retail_unit in ["bunch", "bunches"]:
            retail_product["suggested_quantities"] = [1, 2, 3]
        elif retail_unit == "each":
            retail_product["suggested_quantities"] = [1, 3, 6, 12]
        else:
            retail_product["suggested_quantities"] = [1, 2, 3, 4, 5]
        
        return retail_product
    
    @staticmethod
    def parse_user_quantity(user_input: str, product_name: str = "") -> Tuple[float, Optional[str]]:
        """
        Parse user quantity request
        
        Args:
            user_input: User's quantity request (e.g., "2 pounds", "3 bunches")
            product_name: Product context
            
        Returns:
            Tuple of (quantity, unit) or (quantity, None) if no unit specified
        """
        # Common patterns
        patterns = [
            r"(\d+\.?\d*)\s*(pound|lb|lbs)",
            r"(\d+\.?\d*)\s*(ounce|oz)",
            r"(\d+\.?\d*)\s*(bunch|bunches)",
            r"(\d+\.?\d*)\s*(pint|pints)",
            r"(\d+\.?\d*)\s*(quart|quarts)",
            r"(\d+\.?\d*)\s*(each|items?|pieces?)",
            r"(\d+\.?\d*)",  # Just a number
        ]
        
        user_lower = user_input.lower()
        
        for pattern in patterns:
            match = re.search(pattern, user_lower)
            if match:
                quantity = float(match.group(1))
                unit = match.group(2) if len(match.groups()) > 1 else None
                
                # Normalize units
                if unit:
                    if unit in ["pound", "pounds"]:
                        unit = "lb"
                    elif unit in ["ounce", "ounces"]:
                        unit = "oz"
                    elif unit == "bunches":
                        unit = "bunch"
                    elif unit in ["items", "pieces", "each"]:
                        unit = "each"
                
                return quantity, unit
        
        # Default to 1 if no quantity found
        return 1.0, None


# Example usage
if __name__ == "__main__":
    # Test conversions
    converter = WholesaleRetailConverter()
    
    # Test wholesale products
    test_products = [
        {"name": "Organic Spinach", "quantity": 1, "unit": "case", "price": 45.00},
        {"name": "Roma Tomatoes", "quantity": 1, "unit": "case", "price": 28.00},
        {"name": "Fresh Basil", "quantity": 1, "unit": "case", "price": 36.00},
        {"name": "Russet Potatoes", "quantity": 1, "unit": "bag", "price": 18.00},
    ]
    
    print("Wholesale to Retail Conversions:")
    print("-" * 60)
    
    for product in test_products:
        retail = converter.format_retail_display(product)
        print(f"\n{product['name']}:")
        print(f"  Wholesale: {product['quantity']} {product['unit']} @ ${product['price']}")
        print(f"  Retail: {retail['price_display']}")
        print(f"  Suggested quantities: {retail['suggested_quantities']}")