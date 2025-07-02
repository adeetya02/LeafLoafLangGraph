#!/bin/bash

# Add sample promotions to LeafLoaf
# Usage: ./add_sample_promotions.sh [API_URL]

API_URL=${1:-"http://localhost:8000"}

echo "🎯 Adding Sample Promotions to LeafLoaf"
echo "API URL: $API_URL"
echo "========================================"

# 1. Valentine's Day Special
echo -e "\n1. Creating Valentine's Day promotion..."
curl -X POST "$API_URL/promotions/create" \
  -H "Content-Type: application/json" \
  -d '{
    "promotion_name": "Valentine Special - 20% Off Chocolates & Wine",
    "promotion_type": "percentage_off",
    "discount_value": 20.0,
    "days_valid": 14,
    "applicable_categories": ["Beverages", "Snacks"],
    "minimum_purchase": 30.0,
    "promo_code": "LOVE20",
    "description": "Celebrate Valentine with 20% off select beverages and treats"
  }' | jq '.'

# 2. Organic Tuesday
echo -e "\n2. Creating Organic Tuesday promotion..."
curl -X POST "$API_URL/promotions/create" \
  -H "Content-Type: application/json" \
  -d '{
    "promotion_name": "Organic Tuesday - Extra 15% Off",
    "promotion_type": "percentage_off",
    "discount_value": 15.0,
    "days_valid": 7,
    "applicable_suppliers": ["Organic Valley", "Horizon", "Applegate"],
    "minimum_purchase": 0,
    "description": "Every Tuesday get an extra 15% off all organic products"
  }' | jq '.'

# 3. Bulk Buy Savings
echo -e "\n3. Creating Bulk Buy promotion..."
curl -X POST "$API_URL/promotions/create" \
  -H "Content-Type: application/json" \
  -d '{
    "promotion_name": "Bulk Buy - $10 Off Orders Over $75",
    "promotion_type": "dollar_off",
    "discount_value": 10.0,
    "days_valid": 30,
    "minimum_purchase": 75.0,
    "promo_code": "BULK10",
    "description": "Stock up and save! Get $10 off when you spend $75 or more"
  }' | jq '.'

# 4. Free Delivery Equivalent
echo -e "\n4. Creating Free Delivery promotion..."
curl -X POST "$API_URL/promotions/create" \
  -H "Content-Type: application/json" \
  -d '{
    "promotion_name": "Free Delivery Credit",
    "promotion_type": "dollar_off",
    "discount_value": 7.99,
    "days_valid": 30,
    "minimum_purchase": 50.0,
    "promo_code": "FREEDELIVERY",
    "description": "Get $7.99 off (equivalent to free delivery) on orders over $50"
  }' | jq '.'

# 5. Meat & Seafood Special
echo -e "\n5. Creating Meat & Seafood promotion..."
curl -X POST "$API_URL/promotions/create" \
  -H "Content-Type: application/json" \
  -d '{
    "promotion_name": "Fresh Protein Pack - Buy 3 Get 1 Free",
    "promotion_type": "bogo",
    "discount_value": 1.0,
    "days_valid": 7,
    "applicable_categories": ["Meat", "Seafood"],
    "minimum_purchase": 0,
    "description": "Buy any 3 meat or seafood items and get the 4th free (lowest priced)"
  }' | jq '.'

# List all promotions
echo -e "\n\n📋 All Active Promotions:"
echo "========================="
curl -s "$API_URL/promotions/list" | jq '.[] | {name: .promotion_name, code: .promo_code, type: .promotion_type, value: .discount_value}'

echo -e "\n✅ Sample promotions added successfully!"
echo -e "\n🧪 Test a promotion code:"
echo "curl '$API_URL/promotions/test/LOVE20?cart_total=50'"