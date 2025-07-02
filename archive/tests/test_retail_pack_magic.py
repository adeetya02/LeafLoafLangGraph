#!/usr/bin/env python3
"""
Test the retail pack conversion magic
Shows how wholesale formats are converted to consumer-friendly displays
"""

from src.utils.wholesale_retail_converter import WholesaleRetailConverter

def test_pack_conversion():
    """Test various pack conversions"""
    
    print("="*80)
    print("🎩 RETAIL PACK CONVERSION MAGIC")
    print("="*80)
    
    converter = WholesaleRetailConverter()
    
    # Test cases showing wholesale → retail conversion
    test_products = [
        {
            "product_name": "TRI-COLOR BELL PEPPERS 8 X 3CT CTN",
            "price": 28.50,
            "unit": "case",
            "sku": "PEP123"
        },
        {
            "product_name": "ORGANIC STRAWBERRIES 12 X 1PT FLAT",
            "price": 48.00,
            "unit": "case",
            "sku": "BER456"
        },
        {
            "product_name": "SPINACH ORGANIC 24 X 1 BUNCH CASE",
            "price": 36.00,
            "unit": "case",
            "sku": "SPN789"
        },
        {
            "product_name": "YELLOW ONIONS 3LB BAG 50 LB SACK",
            "price": 25.00,
            "unit": "bag",
            "sku": "ONI012"
        },
        {
            "product_name": "MINI CUCUMBERS 12 X 1LB CTN",
            "price": 24.00,
            "unit": "case",
            "sku": "CUC345"
        }
    ]
    
    print("\n🔄 Wholesale → Retail Conversions:")
    print("-" * 80)
    
    for product in test_products:
        print(f"\n📦 WHOLESALE: {product['product_name']}")
        print(f"   Price: ${product['price']:.2f} per {product['unit']}")
        
        # Convert to retail
        retail = converter.format_retail_display(product)
        
        print(f"\n🛒 RETAIL:")
        print(f"   Name: {retail['name']}")
        print(f"   Price: {retail['price_display']}")
        print(f"   Unit: {retail['unit']}")
        if 'pack_size' in retail:
            print(f"   Pack Size: {retail['pack_size']}")
        print(f"   Suggested Quantities: {retail.get('suggested_quantities', [])}")
        
        # Show the math
        if '_wholesale' in retail:
            wholesale_info = retail['_wholesale']
            if 'conversion_factor' in wholesale_info:
                print(f"\n   💡 Conversion: 1 {product['unit']} = {wholesale_info['conversion_factor'][0]} {wholesale_info['conversion_factor'][1]}")
                print(f"   💰 Markup: 2.5x wholesale price")
    
    # Test user quantity parsing
    print("\n\n🎯 User Quantity Understanding:")
    print("-" * 80)
    
    user_requests = [
        "2 packs",
        "3 bunches",
        "1 pound",
        "half dozen",
        "5 units"
    ]
    
    for request in user_requests:
        quantity, unit = converter.parse_user_quantity(request)
        print(f"'{request}' → {quantity} {unit}")
    
    # Show voice interaction example
    print("\n\n🎤 Voice Interaction Example:")
    print("-" * 80)
    
    # Simulate a bell pepper search result
    bell_pepper = {
        "product_name": "TRI-COLOR BELL PEPPERS 8 X 3CT CTN",
        "price": 28.50,
        "unit": "case",
        "sku": "PEP123"
    }
    
    retail_pepper = converter.format_retail_display(bell_pepper)
    
    print("User: 'I need some bell peppers'")
    print(f"System: 'I found {retail_pepper['name']} at {retail_pepper['price_display']}'")
    print("\nUser: 'Give me 2 packs'")
    print(f"System: 'Added 2 {retail_pepper['unit']} of {retail_pepper['name']} to your cart'")
    print(f"        (That's 6 peppers total for ${retail_pepper['price'] * 2:.2f})")

if __name__ == "__main__":
    test_pack_conversion()