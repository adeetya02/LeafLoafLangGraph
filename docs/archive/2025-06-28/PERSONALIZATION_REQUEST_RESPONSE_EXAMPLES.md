# Personalization Request/Response Examples

## Overview
This document shows how personalization enhances the LeafLoaf search API responses with user-specific recommendations, usual items, and smart suggestions.

## 1. Basic Search with Personalization

### Request
```json
POST /api/v1/search
{
  "query": "organic milk",
  "user_id": "user_123",
  "session_id": "session_456",
  "limit": 5
}
```

### Response (with personalization)
```json
{
  "success": true,
  "query": "organic milk",
  "products": [
    {
      "sku": "MILK-003",
      "product_name": "Horizon Organic Whole Milk",
      "price": 6.49,
      "category": "Dairy",
      "supplier": "Horizon"
    },
    {
      "sku": "MILK-004",
      "product_name": "Organic Valley Grassmilk",
      "price": 7.99,
      "category": "Dairy",
      "supplier": "Organic Valley"
    }
  ],
  "personalization": {
    "enabled": true,
    "confidence": 0.91,
    "usual_items": [
      {
        "sku": "MILK-001",
        "name": "Oatly Barista Edition",
        "usual_quantity": 2,
        "last_ordered": "3 days ago",
        "order_frequency": "weekly"
      }
    ],
    "reorder_suggestions": [
      {
        "sku": "BREAD-001",
        "name": "Dave's Killer Bread",
        "days_until_reorder": 1,
        "usual_quantity": 1,
        "message": "You usually order this with milk"
      }
    ],
    "complementary_products": [
      {
        "sku": "COFFEE-001",
        "name": "Blue Bottle Three Africas",
        "reason": "Perfect with your Oatly",
        "discount": "10% off when bought together"
      },
      {
        "sku": "CEREAL-001",
        "name": "Nature's Path Heritage Flakes",
        "reason": "Your favorite breakfast combo"
      }
    ],
    "applied_features": ["smart_ranking", "usual_orders", "complementary_items"]
  },
  "metadata": {
    "total_count": 2,
    "categories": ["Dairy"],
    "brands": ["Horizon", "Organic Valley"],
    "personalization_metadata": {
      "features_used": ["purchase_history", "basket_analysis"],
      "processing_time_ms": 42
    }
  },
  "execution": {
    "total_time_ms": 242.5,
    "agent_timings": {
      "supervisor": 50,
      "product_search": 150,
      "response_compiler": 42.5
    }
  }
}
```

## 2. Conversational Reorder Query

### Request
```json
{
  "query": "what should I reorder?",
  "user_id": "user_123",
  "session_id": "session_456"
}
```

### Response
```json
{
  "success": true,
  "query": "what should I reorder?",
  "products": [],
  "personalization": {
    "enabled": true,
    "confidence": 0.93,
    "usual_items": [],
    "reorder_suggestions": [
      {
        "sku": "MILK-001",
        "name": "Oatly Barista Edition",
        "days_until_reorder": 0,
        "usual_quantity": 2,
        "message": "📍 Due today - you order every 5 days",
        "last_ordered": "5 days ago",
        "urgency": "high"
      },
      {
        "sku": "EGGS-001",
        "name": "Vital Farms Pasture Eggs",
        "days_until_reorder": 2,
        "usual_quantity": 1,
        "message": "Running low - order in 2 days",
        "last_ordered": "12 days ago",
        "urgency": "medium"
      },
      {
        "sku": "BREAD-001",
        "name": "Dave's Killer 21 Grain",
        "days_until_reorder": 4,
        "usual_quantity": 1,
        "message": "Stock up this week",
        "urgency": "low"
      }
    ],
    "complementary_products": [],
    "applied_features": ["reorder_reminders", "quantity_memory"]
  },
  "message": "Here are your items due for reorder",
  "metadata": {
    "response_type": "reorder_suggestions",
    "personalization_metadata": {
      "features_used": ["purchase_history", "reorder_patterns"],
      "processing_time_ms": 28
    }
  }
}
```

## 3. Cultural Understanding Query

### Request
```json
{
  "query": "ingredients for dosa",
  "user_id": "user_456",
  "session_id": "session_789"
}
```

### Response
```json
{
  "success": true,
  "query": "ingredients for dosa",
  "products": [
    {
      "sku": "RICE-001",
      "product_name": "Idli Rice",
      "price": 12.99,
      "category": "Grains"
    },
    {
      "sku": "DAL-001",
      "product_name": "Urad Dal",
      "price": 8.99,
      "category": "Lentils"
    }
  ],
  "personalization": {
    "enabled": true,
    "confidence": 0.80,
    "usual_items": [
      {
        "sku": "DOSA-MIX-001",
        "name": "MTR Dosa Mix",
        "usual_quantity": 2,
        "note": "Your quick option"
      }
    ],
    "reorder_suggestions": [],
    "complementary_products": [
      {
        "sku": "CHUTNEY-001",
        "name": "Coconut Chutney Mix",
        "reason": "Essential accompaniment"
      },
      {
        "sku": "SAMBAR-001",
        "name": "MTR Sambar Powder",
        "reason": "Complete the meal"
      },
      {
        "sku": "OIL-001",
        "name": "Coconut Oil",
        "reason": "For authentic taste"
      }
    ],
    "applied_features": ["cultural_awareness", "complementary_items"],
    "cultural_context": {
      "cuisine": "South Indian",
      "meal_type": "Breakfast",
      "recipe_completeness": "Missing fenugreek seeds"
    }
  },
  "metadata": {
    "total_count": 2,
    "categories": ["Grains", "Lentils"],
    "personalization_metadata": {
      "features_used": ["cultural_patterns", "recipe_knowledge"],
      "processing_time_ms": 38
    }
  }
}
```

## 4. Order Operation with Personalization

### Request
```json
{
  "query": "add my usual milk to cart",
  "user_id": "user_123",
  "session_id": "session_456"
}
```

### Response
```json
{
  "success": true,
  "query": "add my usual milk to cart",
  "order": {
    "items": [
      {
        "sku": "MILK-001",
        "name": "Oatly Barista Edition",
        "quantity": 2,
        "price": 5.99,
        "total": 11.98
      }
    ],
    "total": 11.98,
    "item_count": 1
  },
  "message": "Added 2x Oatly Barista Edition to your cart",
  "personalization": {
    "enabled": true,
    "confidence": 0.95,
    "usual_items": [
      {
        "sku": "MILK-001",
        "name": "Oatly Barista Edition",
        "usual_quantity": 2
      }
    ],
    "applied_features": ["usual_orders", "quantity_memory"]
  },
  "metadata": {
    "order_action": "add_usual",
    "personalization_metadata": {
      "features_used": ["order_history", "quantity_patterns"],
      "processing_time_ms": 25
    }
  }
}
```

## 5. Anonymous User (No Personalization)

### Request
```json
{
  "query": "organic milk",
  "session_id": "anonymous_session_123"
  // Note: No user_id
}
```

### Response
```json
{
  "success": true,
  "query": "organic milk",
  "products": [
    {
      "sku": "MILK-003",
      "product_name": "Horizon Organic Whole Milk",
      "price": 6.49,
      "category": "Dairy"
    },
    {
      "sku": "MILK-004",
      "product_name": "Organic Valley Grassmilk",
      "price": 7.99,
      "category": "Dairy"
    }
  ],
  // No personalization section for anonymous users
  "metadata": {
    "total_count": 2,
    "categories": ["Dairy"],
    "brands": ["Horizon", "Organic Valley"]
  },
  "execution": {
    "total_time_ms": 200.5,
    "agent_timings": {
      "supervisor": 50,
      "product_search": 150,
      "response_compiler": 0.5
    }
  }
}
```

## 6. User with Personalization Disabled

### Request
```json
{
  "query": "coffee",
  "user_id": "user_789",
  "session_id": "session_123",
  "preferences": {
    "personalization": {
      "enabled": false
    }
  }
}
```

### Response
```json
{
  "success": true,
  "query": "coffee",
  "products": [
    {
      "sku": "COFFEE-001",
      "product_name": "Blue Bottle Three Africas",
      "price": 18.99
    },
    {
      "sku": "COFFEE-002",
      "product_name": "Intelligentsia Black Cat",
      "price": 16.99
    }
  ],
  "personalization": {
    "enabled": false
    // No personalization data when disabled
  },
  "metadata": {
    "total_count": 2,
    "user_preference": "personalization_disabled"
  }
}
```

## Key Features Demonstrated

### 1. **Confidence Scoring**
- Based on data points, recency, and consistency
- Higher confidence = more reliable personalization

### 2. **Feature Flags**
- `smart_ranking`: Re-ranks results based on preferences
- `usual_orders`: Shows user's regular purchases
- `reorder_reminders`: Proactive restocking suggestions
- `cultural_awareness`: Understands cultural contexts
- `complementary_items`: Suggests related products
- `quantity_memory`: Remembers typical quantities

### 3. **Performance Tracking**
- Personalization adds <50ms to response time
- Features used are tracked for optimization
- Total response time stays under 300ms

### 4. **Privacy First**
- Users can disable personalization entirely
- Anonymous users get no personalization
- All features are opt-in with granular control

## Integration Notes

1. **Backward Compatible**: Existing clients work without changes
2. **Progressive Enhancement**: Personalization enhances but doesn't break base functionality
3. **Graceful Degradation**: Works perfectly without personalization data
4. **Single Endpoint**: All features through `/api/v1/search`
5. **OpenAPI 3.0 Compliant**: Fully documented and typed