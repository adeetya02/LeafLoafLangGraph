#!/bin/bash

# Add Indian product promotions
API_URL="https://leafloaf-v2srnrkkhq-uc.a.run.app"

echo "🎯 Adding Indian Product Promotions"
echo "==================================="

# 1. Diwali Special
echo -e "\n1. Creating Diwali Festival promotion..."
curl -X POST "$API_URL/promotions/create" \
  -H "Content-Type: application/json" \
  -d '{
    "promotion_name": "Diwali Festival - 20% Off Indian Groceries",
    "promotion_type": "percentage_off",
    "discount_value": 20.0,
    "days_valid": 30,
    "applicable_suppliers": ["Laxmi", "Vistar", "Shakti Foods"],
    "minimum_purchase": 35.0,
    "promo_code": "DIWALI20",
    "description": "Celebrate Diwali with 20% off all Indian groceries"
  }'

echo -e "\n\n2. Creating Rice & Dal Bundle promotion..."
curl -X POST "$API_URL/promotions/create" \
  -H "Content-Type: application/json" \
  -d '{
    "promotion_name": "Indian Staples Bundle - Buy 2 Get 10% Off",
    "promotion_type": "percentage_off",
    "discount_value": 10.0,
    "days_valid": 60,
    "applicable_products": ["LX_RICE_BAS_10", "VS_RICE_SONA_20", "LX_DAL_TOOR_4", "LX_DAL_MOONG_4", "VS_DAL_URAD_4"],
    "minimum_purchase": 20.0,
    "description": "Stock up on rice and dal with 10% off when you buy any 2"
  }'

echo -e "\n\n3. Creating New Customer Indian Special..."
curl -X POST "$API_URL/promotions/create" \
  -H "Content-Type: application/json" \
  -d '{
    "promotion_name": "Welcome to Indian Groceries - 15% Off",
    "promotion_type": "percentage_off",
    "discount_value": 15.0,
    "days_valid": 45,
    "applicable_categories": ["Indian Grocery"],
    "minimum_purchase": 25.0,
    "usage_limit_per_user": 1,
    "promo_code": "NAMASTE15",
    "description": "New to Indian cooking? Get 15% off your first Indian grocery order"
  }'

echo -e "\n\n✅ Indian promotions added!"
echo -e "\nTest the promotions:"
echo "curl '$API_URL/promotions/test/DIWALI20?cart_total=50'"