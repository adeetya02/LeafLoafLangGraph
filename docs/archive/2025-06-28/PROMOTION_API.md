# Promotion Management API Documentation

## Overview
The LeafLoaf API now includes comprehensive promotion management endpoints for creating, managing, and applying promotional discounts.

## Base URL
- Local: `http://localhost:8000`
- Production: `https://leafloaf-[hash]-uc.a.run.app`

## Promotion Endpoints

### 1. Create Promotion
Create a new promotion and automatically save it to BigQuery.

**Endpoint:** `POST /promotions/create`

**Request Body:**
```json
{
  "promotion_name": "Summer Sale 20% Off",
  "promotion_type": "percentage_off",  // Options: percentage_off, dollar_off, bogo, bundle
  "discount_value": 20.0,
  "days_valid": 30,
  "applicable_products": ["OV_MILK_WH", "HO_YOGURT"],  // Optional: specific SKUs
  "applicable_categories": ["Dairy", "Beverages"],     // Optional: category restrictions
  "applicable_suppliers": ["Organic Valley"],          // Optional: supplier restrictions
  "minimum_purchase": 25.0,
  "maximum_discount": 50.0,    // Optional: cap the discount
  "usage_limit_per_user": 1,   // Optional: limit uses per customer
  "promo_code": "SUMMER20",    // Optional: if not provided, auto-applied
  "description": "Get 20% off select summer items"
}
```

**Response:**
```json
{
  "promotion_id": "promo_a1b2c3d4e5f6",
  "promotion_name": "Summer Sale 20% Off",
  "promotion_type": "percentage_off",
  "discount_value": 20.0,
  "start_date": "2024-01-25T10:00:00",
  "end_date": "2024-02-24T10:00:00",
  "promo_code": "SUMMER20",
  "description": "Get 20% off select summer items",
  "is_active": true,
  "created_at": "2024-01-25T10:00:00"
}
```

### 2. List Promotions
Get all active or all promotions.

**Endpoint:** `GET /promotions/list?active_only=true`

**Response:**
```json
[
  {
    "promotion_id": "promo_welcome15",
    "promotion_name": "New Customer 15% Off",
    "promotion_type": "percentage_off",
    "discount_value": 15.0,
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-12-31T23:59:59",
    "promo_code": "WELCOME15",
    "description": "Get 15% off your first order",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00"
  },
  // ... more promotions
]
```

### 3. Test Promotion Code
Validate a promo code and calculate the discount for a given cart total.

**Endpoint:** `GET /promotions/test/{promo_code}?cart_total=50.00`

**Response (Valid):**
```json
{
  "valid": true,
  "promotion_name": "Summer Sale 20% Off",
  "discount_amount": 10.00,
  "final_total": 40.00,
  "message": "Promo code applied! You save $10.00"
}
```

**Response (Invalid):**
```json
{
  "valid": false,
  "message": "Minimum purchase of $25.00 required"
}
```

### 4. Deactivate Promotion
Deactivate a promotion (soft delete).

**Endpoint:** `DELETE /promotions/{promotion_id}`

**Response:**
```json
{
  "message": "Promotion promo_a1b2c3d4e5f6 deactivated"
}
```

## Promotion Types

### 1. Percentage Off
- Discount is a percentage of eligible items
- Example: 20% off = `discount_value: 20.0`

### 2. Dollar Off
- Fixed dollar amount off the order
- Example: $5 off = `discount_value: 5.0`

### 3. BOGO (Buy One Get One)
- Buy X items, get Y free
- `discount_value: 1.0` means buy 2 get 1 free
- Applied to lowest priced items

### 4. Bundle (Future)
- Special pricing for product bundles
- Implementation pending

## Automatic Promotion Application

When users interact with the chat API, promotions are automatically:
1. Checked when products are searched
2. Applied when items are added to cart
3. Recalculated when cart is modified
4. Shown in the response with savings details

## Example: Create a Dairy BOGO Promotion

```bash
curl -X POST https://your-api.com/promotions/create \
  -H "Content-Type: application/json" \
  -d '{
    "promotion_name": "Dairy Week - Buy 2 Get 1 Free",
    "promotion_type": "bogo",
    "discount_value": 1.0,
    "days_valid": 7,
    "applicable_categories": ["Dairy"],
    "minimum_purchase": 0,
    "description": "Buy any 2 dairy products and get the 3rd free!"
  }'
```

## Example: Create a New Customer Promotion

```bash
curl -X POST https://your-api.com/promotions/create \
  -H "Content-Type: application/json" \
  -d '{
    "promotion_name": "Welcome to LeafLoaf - 25% Off",
    "promotion_type": "percentage_off",
    "discount_value": 25.0,
    "days_valid": 60,
    "minimum_purchase": 40.0,
    "maximum_discount": 75.0,
    "usage_limit_per_user": 1,
    "promo_code": "LEAFLOAF25",
    "description": "New customers get 25% off orders over $40 (max $75 discount)"
  }'
```

## BigQuery Integration

All promotions are automatically:
1. Saved to `promotions.active_promotions` table
2. Usage tracked in `promotions.promotion_usage` table
3. Analytics captured in `analytics.order_events` table

## Web Interface

Use `promotion_manager.html` to:
- Create promotions visually
- Test promo codes
- View all active promotions
- No coding required!

## Best Practices

1. **Promo Codes**: Use memorable, easy-to-type codes
2. **Descriptions**: Clear, concise benefit statements
3. **Limits**: Set reasonable max discounts to protect margins
4. **Categories**: Target specific product groups for better control
5. **Testing**: Always test codes before announcing them