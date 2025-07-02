# LeafLoaf API Documentation

## Overview
LeafLoaf provides a unified AI-powered grocery shopping API with advanced personalization features. All interactions go through a single endpoint that intelligently routes requests to specialized agents.

## Base URL
```
Production: https://leafloaf-api.com
Development: http://localhost:8000
```

## Authentication
Currently using API keys. Future: Google IAM integration.

```bash
Authorization: Bearer YOUR_API_KEY
```

## Main Endpoint

### POST /graph/invoke
The primary endpoint for all shopping interactions.

#### Request Body
```json
{
  "query": "string",
  "user_id": "string",
  "session_id": "string (optional)",
  "context": {
    "preferences": {
      "personalization_enabled": true,
      "features": {
        "smart_search_ranking": true,
        "my_usual_orders": true,
        "reorder_reminders": true,
        "dietary_filters": true,
        "cultural_understanding": true,
        "complementary_products": true,
        "quantity_memory": true,
        "budget_awareness": true,
        "household_intelligence": true,
        "seasonal_patterns": true
      }
    }
  }
}
```

#### Response Structure (Enhanced with Personalization)
```json
{
  "success": true,
  "query": "organic milk",
  "intent": "search",
  "products": [
    {
      "id": "prod_123",
      "name": "Organic Valley Whole Milk",
      "price": 5.99,
      "unit": "gallon",
      "personalization_score": 0.95,
      "reasons": ["frequently_purchased", "preferred_brand"]
    }
  ],
  "personalization": {
    "enabled": true,
    "usual_items": [
      {
        "sku": "MILK-001",
        "name": "Organic Valley Whole Milk",
        "usual_quantity": 2,
        "confidence": 0.92,
        "last_ordered": "2025-06-20"
      }
    ],
    "reorder_suggestions": [
      {
        "sku": "EGGS-001",
        "name": "Free Range Eggs",
        "days_until_due": 2,
        "urgency": "due_soon",
        "message": "You usually order eggs every 14 days"
      }
    ],
    "complementary_products": [
      {
        "sku": "CEREAL-001",
        "name": "Organic Granola",
        "reason": "frequently_bought_together"
      }
    ],
    "bundles": [
      {
        "items": ["MILK-001", "EGGS-001", "BREAD-001"],
        "savings": 5.00,
        "message": "Order your weekly staples together"
      }
    ],
    "applied_features": ["smart_ranking", "usual_orders", "reorder_intelligence"],
    "confidence": 0.88
  },
  "cart": {
    "items": [],
    "total": 0,
    "suggested_additions": []
  },
  "metadata": {
    "agent": "product_search",
    "processing_time_ms": 245,
    "personalization_time_ms": 42,
    "search_method": "hybrid",
    "alpha": 0.75,
    "total_results": 15
  }
}
```

## Query Types & Examples

### 1. Product Search
```json
{
  "query": "organic oat milk barista",
  "user_id": "user_123"
}
```

**Response includes:**
- Personalized product ranking based on purchase history
- Brand preferences applied
- Price sensitivity considered
- Dietary filters respected

### 2. My Usual Orders
```json
{
  "query": "show my usual items",
  "user_id": "user_123"
}
```

**Response includes:**
- Frequently purchased items with confidence scores
- Typical quantities
- One-click reorder basket
- Seasonal variations

### 3. Reorder Management
```json
{
  "query": "what do I need to reorder?",
  "user_id": "user_123"
}
```

**Response includes:**
- Items due for reordering
- Urgency levels (due_now, due_soon, upcoming)
- Smart bundle suggestions
- Holiday-adjusted recommendations

### 4. Cart Operations
```json
{
  "query": "add 2 gallons of milk to cart",
  "user_id": "user_123",
  "session_id": "session_456"
}
```

**Response includes:**
- Updated cart state
- Complementary product suggestions
- Running total
- Quantity memory applied

### 5. Order Confirmation
```json
{
  "query": "confirm my order",
  "user_id": "user_123",
  "session_id": "session_456"
}
```

**Response includes:**
- Order summary
- Delivery options
- Reorder cycle updates
- Next suggested order date

## Personalization Features

### 1. Smart Search Ranking
Products are re-ranked based on:
- Purchase frequency
- Brand affinity
- Price preferences
- Category preferences
- Dietary requirements

### 2. My Usual Functionality
- Detects regular purchase patterns
- Remembers typical quantities
- Creates one-click reorder baskets
- Adapts to seasonal changes

### 3. Reorder Intelligence
- Calculates item-specific reorder cycles
- Sends proactive reminders
- Adjusts for holidays
- Suggests bundle opportunities

### 4. User Preferences
All personalization features can be toggled:
```json
{
  "context": {
    "preferences": {
      "personalization_enabled": false
    }
  }
}
```

## Voice Integration

### POST /webhooks/elevenlabs
Handles voice input from 11Labs agent.

```json
{
  "user_id": "user_123",
  "audio_url": "https://...",
  "transcript": "add milk to my cart"
}
```

## Error Responses

### Standard Error Format
```json
{
  "success": false,
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Could not find the requested product",
    "details": {}
  }
}
```

### Common Error Codes
- `INVALID_REQUEST`: Malformed request
- `AUTHENTICATION_FAILED`: Invalid API key
- `PRODUCT_NOT_FOUND`: Product search failed
- `CART_OPERATION_FAILED`: Cart update failed
- `PERSONALIZATION_ERROR`: Personalization service error

## Performance Targets

| Operation | Target | Current |
|-----------|--------|---------|
| Search Response | <300ms | 245ms |
| Personalization Overhead | <100ms | 42ms |
| Cart Operations | <150ms | 120ms |
| Reorder Analysis | <100ms | 85ms |

## Rate Limits

- 100 requests per minute per user
- 10,000 requests per day per API key
- Burst allowance: 20 requests

## Webhooks

### Order Confirmation Webhook
```json
POST https://your-endpoint.com/order-confirmed
{
  "order_id": "order_789",
  "user_id": "user_123",
  "total": 45.67,
  "items": [...],
  "delivery_date": "2025-06-28"
}
```

## SDK Examples

### Python
```python
from leafloaf import LeafLoafClient

client = LeafLoafClient(api_key="YOUR_KEY")

# Search with personalization
response = client.search(
    query="organic milk",
    user_id="user_123",
    enable_personalization=True
)

# Get reorder suggestions
reorders = client.get_reorder_suggestions(user_id="user_123")
```

### JavaScript
```javascript
const leafloaf = new LeafLoafClient({ apiKey: 'YOUR_KEY' });

// Search products
const results = await leafloaf.search({
  query: 'organic milk',
  userId: 'user_123',
  personalization: true
});

// Add to cart
const cart = await leafloaf.addToCart({
  userId: 'user_123',
  items: [{ sku: 'MILK-001', quantity: 2 }]
});
```

## Testing

### Test Endpoint
```
POST /test/graph/invoke
```
Same as production but with test data.

### Test User IDs
- `test_user_premium`: Premium shopper profile
- `test_user_budget`: Budget-conscious profile
- `test_user_dietary`: Special dietary needs
- `test_user_family`: Large family profile

## Migration Guide

### From v1 to v2 (with Personalization)
1. No breaking changes - personalization is additive
2. Add `user_id` to all requests for personalization
3. Configure feature flags in context
4. Monitor new response fields

## Support

- Documentation: https://docs.leafloaf.com
- Issues: https://github.com/leafloaf/api/issues
- Email: support@leafloaf.com