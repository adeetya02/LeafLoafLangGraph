# API Response Examples with Personalization

## Table of Contents
1. [Product Search Responses](#product-search-responses)
2. [My Usual Orders](#my-usual-orders)
3. [Reorder Intelligence](#reorder-intelligence)
4. [Cart Operations](#cart-operations)
5. [Mixed Intent Responses](#mixed-intent-responses)

---

## Product Search Responses

### Basic Search with Personalization
**Request:**
```json
{
  "query": "milk",
  "user_id": "user_123",
  "session_id": "session_456"
}
```

**Response:**
```json
{
  "success": true,
  "query": "milk",
  "intent": "search",
  "products": [
    {
      "id": "prod_001",
      "sku": "MILK-001",
      "name": "Organic Valley Whole Milk",
      "price": 5.99,
      "unit": "gallon",
      "in_stock": true,
      "personalization_score": 0.95,
      "boost_reasons": ["frequently_purchased", "preferred_brand"],
      "original_rank": 3,
      "personalized_rank": 1
    },
    {
      "id": "prod_002",
      "sku": "MILK-002",
      "name": "Horizon Organic 2% Milk",
      "price": 5.49,
      "unit": "gallon",
      "in_stock": true,
      "personalization_score": 0.75,
      "boost_reasons": ["price_match_preference"],
      "original_rank": 1,
      "personalized_rank": 2
    }
  ],
  "personalization": {
    "enabled": true,
    "usual_items": [
      {
        "sku": "MILK-001",
        "name": "Organic Valley Whole Milk",
        "usual_quantity": 2,
        "frequency": "weekly",
        "confidence": 0.92,
        "last_ordered": "2025-06-20",
        "message": "Your usual milk - ordered every week"
      }
    ],
    "reorder_suggestions": [
      {
        "sku": "MILK-001",
        "name": "Organic Valley Whole Milk",
        "days_since_last_order": 7,
        "usual_frequency_days": 7,
        "urgency": "due_now",
        "message": "Time to reorder - you usually buy milk weekly"
      }
    ],
    "complementary_products": [
      {
        "sku": "CEREAL-001",
        "name": "Honey Nut Cheerios",
        "reason": "frequently_bought_together",
        "confidence": 0.78
      }
    ],
    "applied_features": ["smart_search_ranking", "usual_detection", "reorder_check"],
    "confidence": 0.88
  },
  "metadata": {
    "agent": "product_search",
    "processing_time_ms": 245,
    "personalization_time_ms": 42,
    "search_method": "hybrid",
    "alpha": 0.3,
    "total_results": 15,
    "personalization_impact": "high"
  }
}
```

### Search with Dietary Preferences Applied
**Request:**
```json
{
  "query": "ice cream",
  "user_id": "user_456",
  "context": {
    "preferences": {
      "dietary_restrictions": ["dairy_free", "vegan"]
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "query": "ice cream",
  "products": [
    {
      "id": "prod_101",
      "name": "Ben & Jerry's Non-Dairy Cherry Garcia",
      "price": 6.99,
      "dietary_tags": ["dairy_free", "vegan"],
      "personalization_score": 0.98,
      "boost_reasons": ["dietary_match", "frequently_purchased"]
    },
    {
      "id": "prod_102",
      "name": "Oatly Vanilla Ice Cream",
      "price": 5.99,
      "dietary_tags": ["dairy_free", "vegan", "gluten_free"],
      "personalization_score": 0.85,
      "boost_reasons": ["dietary_match", "brand_preference"]
    }
  ],
  "personalization": {
    "filters_applied": ["dairy_free", "vegan"],
    "excluded_count": 23,
    "message": "Showing only dairy-free and vegan options"
  }
}
```

---

## My Usual Orders

### Get Usual Items
**Request:**
```json
{
  "query": "show my usual items",
  "user_id": "user_789"
}
```

**Response:**
```json
{
  "success": true,
  "query": "show my usual items",
  "intent": "usual_order",
  "usual_basket": {
    "items": [
      {
        "sku": "MILK-001",
        "name": "Organic Valley Whole Milk",
        "usual_quantity": 2,
        "unit": "gallon",
        "price": 5.99,
        "frequency": "weekly",
        "confidence": 0.95,
        "last_ordered": "2025-06-20",
        "days_since": 7
      },
      {
        "sku": "BREAD-001",
        "name": "Dave's Killer Bread",
        "usual_quantity": 1,
        "unit": "loaf",
        "price": 4.99,
        "frequency": "weekly",
        "confidence": 0.88,
        "last_ordered": "2025-06-20",
        "days_since": 7
      },
      {
        "sku": "EGGS-001",
        "name": "Vital Farms Pasture-Raised Eggs",
        "usual_quantity": 2,
        "unit": "dozen",
        "price": 6.99,
        "frequency": "bi-weekly",
        "confidence": 0.82,
        "last_ordered": "2025-06-13",
        "days_since": 14
      }
    ],
    "total_items": 3,
    "total_price": 24.96,
    "confidence_score": 0.88,
    "quick_add_available": true
  },
  "personalization": {
    "pattern_summary": {
      "shopping_frequency": "weekly",
      "typical_day": "Sunday",
      "average_basket_size": 15,
      "staple_items": ["MILK-001", "BREAD-001", "EGGS-001"],
      "seasonal_items": []
    },
    "suggestions": [
      {
        "message": "You usually order bananas with these items",
        "sku": "BANANA-001",
        "confidence": 0.65
      }
    ]
  },
  "actions": [
    {
      "type": "quick_add",
      "label": "Add all usual items to cart",
      "action_id": "add_usual_basket"
    },
    {
      "type": "modify",
      "label": "Customize quantities",
      "action_id": "modify_usual"
    }
  ]
}
```

### Add Usual Items to Cart
**Request:**
```json
{
  "query": "add my usual items to cart",
  "user_id": "user_789"
}
```

**Response:**
```json
{
  "success": true,
  "intent": "add_usual_to_cart",
  "cart": {
    "items": [
      {
        "sku": "MILK-001",
        "name": "Organic Valley Whole Milk",
        "quantity": 2,
        "price": 5.99,
        "subtotal": 11.98,
        "added_from": "usual_order"
      },
      {
        "sku": "BREAD-001",
        "name": "Dave's Killer Bread",
        "quantity": 1,
        "price": 4.99,
        "subtotal": 4.99,
        "added_from": "usual_order"
      },
      {
        "sku": "EGGS-001",
        "name": "Vital Farms Pasture-Raised Eggs",
        "quantity": 2,
        "price": 6.99,
        "subtotal": 13.98,
        "added_from": "usual_order"
      }
    ],
    "items_count": 3,
    "total_quantity": 5,
    "subtotal": 30.95,
    "tax": 2.48,
    "total": 33.43
  },
  "personalization": {
    "items_added": 3,
    "from_usual": true,
    "quantity_memory_applied": true,
    "missing_usual_items": [
      {
        "sku": "BANANA-001",
        "name": "Organic Bananas",
        "reason": "out_of_stock",
        "message": "Your usual bananas are out of stock"
      }
    ]
  },
  "message": "Added 3 usual items to your cart"
}
```

---

## Reorder Intelligence

### Check What Needs Reordering
**Request:**
```json
{
  "query": "what do I need to reorder?",
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "success": true,
  "intent": "reorder_check",
  "reorder_analysis": {
    "due_now": [
      {
        "sku": "MILK-001",
        "name": "Organic Valley Whole Milk",
        "days_since_last_order": 7,
        "usual_cycle_days": 7,
        "urgency": "due_now",
        "confidence": 0.95,
        "message": "You usually order milk every 7 days",
        "suggested_quantity": 2,
        "last_quantity": 2
      },
      {
        "sku": "BREAD-001",
        "name": "Dave's Killer Bread",
        "days_since_last_order": 8,
        "usual_cycle_days": 7,
        "urgency": "overdue",
        "confidence": 0.88,
        "message": "Overdue! Usually ordered weekly",
        "suggested_quantity": 1,
        "last_quantity": 1
      }
    ],
    "due_soon": [
      {
        "sku": "EGGS-001",
        "name": "Vital Farms Eggs",
        "days_until_due": 2,
        "usual_cycle_days": 14,
        "urgency": "due_soon",
        "confidence": 0.82,
        "message": "Due in 2 days - usually ordered bi-weekly",
        "suggested_quantity": 2
      }
    ],
    "upcoming": [
      {
        "sku": "COFFEE-001",
        "name": "Blue Bottle Coffee",
        "days_until_due": 5,
        "usual_cycle_days": 21,
        "urgency": "upcoming",
        "confidence": 0.75,
        "message": "Due next week"
      }
    ]
  },
  "bundles": [
    {
      "bundle_id": "weekly_staples",
      "name": "Weekly Staples Bundle",
      "items": ["MILK-001", "BREAD-001", "BANANA-001"],
      "total_price": 17.97,
      "savings": 5.00,
      "message": "Save $5 on delivery by ordering together",
      "cycle_alignment": "weekly"
    }
  ],
  "reminders": [
    {
      "type": "holiday",
      "message": "Thanksgiving is in 5 days - order early to avoid delays",
      "suggested_order_date": "2025-11-25",
      "affected_items": ["MILK-001", "EGGS-001", "BUTTER-001"]
    }
  ],
  "actions": [
    {
      "type": "quick_reorder",
      "label": "Reorder all due items",
      "items": ["MILK-001", "BREAD-001"],
      "total": 16.97
    }
  ]
}
```

### Proactive Reorder Reminders
**Request:**
```json
{
  "query": "show my reorder schedule",
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "success": true,
  "intent": "reorder_schedule",
  "schedule": {
    "today": {
      "date": "2025-06-27",
      "items": [
        {
          "sku": "MILK-001",
          "name": "Milk",
          "action": "reorder_now",
          "urgency": "critical"
        }
      ]
    },
    "next_3_days": [
      {
        "date": "2025-06-29",
        "items": [
          {
            "sku": "EGGS-001",
            "name": "Eggs",
            "action": "reorder_recommended",
            "urgency": "high"
          }
        ]
      }
    ],
    "next_week": [
      {
        "date": "2025-07-02",
        "items": [
          {
            "sku": "COFFEE-001",
            "name": "Coffee",
            "action": "plan_to_reorder",
            "urgency": "medium"
          },
          {
            "sku": "CEREAL-001", 
            "name": "Cereal",
            "action": "plan_to_reorder",
            "urgency": "low"
          }
        ]
      }
    ]
  },
  "optimization": {
    "suggestion": "Order milk and eggs together on Friday to save on delivery",
    "potential_savings": 5.00,
    "recommended_date": "2025-06-29"
  }
}
```

---

## Cart Operations

### Add to Cart with Personalization
**Request:**
```json
{
  "query": "add 2 gallons of milk",
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "success": true,
  "intent": "add_to_cart",
  "cart_update": {
    "added_item": {
      "sku": "MILK-001",
      "name": "Organic Valley Whole Milk",
      "quantity": 2,
      "unit": "gallon",
      "price": 5.99,
      "subtotal": 11.98,
      "personalization_applied": true,
      "selection_reason": "your_usual_brand"
    }
  },
  "cart": {
    "items": [
      {
        "sku": "MILK-001",
        "name": "Organic Valley Whole Milk",
        "quantity": 2,
        "price": 5.99,
        "subtotal": 11.98
      }
    ],
    "total_items": 1,
    "subtotal": 11.98,
    "tax": 0.96,
    "total": 12.94
  },
  "personalization": {
    "quantity_memory": {
      "applied": true,
      "usual_quantity": 2,
      "message": "Added your usual quantity"
    },
    "complementary_suggestions": [
      {
        "sku": "CEREAL-001",
        "name": "Honey Nut Cheerios",
        "message": "You often buy cereal with milk",
        "confidence": 0.76
      }
    ],
    "reorder_update": {
      "sku": "MILK-001",
      "next_reorder_date": "2025-07-04",
      "cycle_updated": true
    }
  }
}
```

### Smart Cart Suggestions
**Request:**
```json
{
  "query": "show my cart",
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "success": true,
  "intent": "view_cart",
  "cart": {
    "items": [
      {
        "sku": "MILK-001",
        "name": "Organic Valley Whole Milk",
        "quantity": 2,
        "price": 5.99,
        "subtotal": 11.98
      },
      {
        "sku": "BREAD-001",
        "name": "Dave's Killer Bread",
        "quantity": 1,
        "price": 4.99,
        "subtotal": 4.99
      }
    ],
    "subtotal": 16.97,
    "tax": 1.36,
    "delivery_fee": 5.00,
    "total": 23.33
  },
  "personalization": {
    "missing_usual_items": [
      {
        "sku": "EGGS-001",
        "name": "Eggs",
        "message": "You usually order eggs with milk and bread",
        "confidence": 0.85,
        "quick_add": true
      }
    ],
    "smart_suggestions": [
      {
        "type": "free_delivery",
        "message": "Add $8.03 more for free delivery",
        "suggested_items": [
          {
            "sku": "BANANA-001",
            "name": "Bananas",
            "price": 2.99
          },
          {
            "sku": "EGGS-001",
            "name": "Eggs",
            "price": 6.99
          }
        ]
      }
    ],
    "bundle_opportunity": {
      "detected": true,
      "message": "These items are part of your Weekly Staples bundle",
      "missing_items": ["BANANA-001"],
      "complete_bundle_savings": 2.00
    }
  }
}
```

---

## Mixed Intent Responses

### Search with Implicit Reorder Check
**Request:**
```json
{
  "query": "do I need milk?",
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "success": true,
  "intent": "mixed_search_reorder",
  "answer": "Yes, you usually order milk weekly and it's been 7 days since your last order.",
  "reorder_info": {
    "sku": "MILK-001",
    "name": "Organic Valley Whole Milk",
    "last_ordered": "2025-06-20",
    "days_since": 7,
    "usual_cycle": 7,
    "status": "due_now",
    "usual_quantity": 2
  },
  "products": [
    {
      "sku": "MILK-001",
      "name": "Organic Valley Whole Milk",
      "price": 5.99,
      "in_stock": true,
      "your_usual": true
    }
  ],
  "actions": [
    {
      "type": "quick_add",
      "label": "Add 2 gallons to cart",
      "sku": "MILK-001",
      "quantity": 2
    },
    {
      "type": "view_alternatives",
      "label": "See other milk options"
    }
  ]
}
```

### Conversational Commerce
**Request:**
```json
{
  "query": "I'm making pasta tonight, what do I need?",
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "success": true,
  "intent": "recipe_assistance",
  "suggestions": {
    "essential_items": [
      {
        "sku": "PASTA-001",
        "name": "Barilla Spaghetti",
        "price": 2.49,
        "reason": "pasta_base",
        "in_stock": true
      },
      {
        "sku": "SAUCE-001",
        "name": "Rao's Marinara Sauce",
        "price": 7.99,
        "reason": "your_preferred_brand",
        "personalization_boost": true
      }
    ],
    "complementary_items": [
      {
        "sku": "CHEESE-001",
        "name": "Parmigiano Reggiano",
        "price": 12.99,
        "reason": "frequently_bought_with_pasta"
      },
      {
        "sku": "BREAD-002",
        "name": "French Baguette",
        "price": 2.99,
        "reason": "popular_pairing"
      }
    ],
    "from_your_pantry": [
      {
        "sku": "GARLIC-001",
        "name": "Garlic",
        "last_ordered": "2025-06-15",
        "likely_have": true,
        "confidence": 0.8
      }
    ]
  },
  "personalization": {
    "dietary_considerations": "All suggestions are vegetarian-friendly",
    "budget_check": {
      "total_suggested": 26.46,
      "within_usual_range": true
    },
    "based_on_history": "You've made pasta 3 times in the last month"
  },
  "quick_actions": [
    {
      "label": "Add pasta essentials to cart",
      "items": ["PASTA-001", "SAUCE-001"],
      "total": 10.48
    },
    {
      "label": "Add complete pasta dinner",
      "items": ["PASTA-001", "SAUCE-001", "CHEESE-001", "BREAD-002"],
      "total": 26.46
    }
  ]
}
```

---

## Error Responses with Personalization Context

### Product Not Found with Alternatives
**Request:**
```json
{
  "query": "oatly barista edition",
  "user_id": "user_123"
}
```

**Response:**
```json
{
  "success": false,
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Oatly Barista Edition is currently out of stock"
  },
  "alternatives": {
    "based_on_preferences": [
      {
        "sku": "OATMILK-002",
        "name": "Minor Figures Barista Oat Milk",
        "price": 4.99,
        "similarity_score": 0.92,
        "reason": "similar_product_profile",
        "in_stock": true
      }
    ],
    "based_on_history": [
      {
        "sku": "OATMILK-003",
        "name": "Califia Farms Barista Blend",
        "price": 5.49,
        "reason": "you_ordered_before",
        "last_ordered": "2025-05-15",
        "in_stock": true
      }
    ]
  },
  "personalization": {
    "notification_preference": {
      "enabled": true,
      "message": "We'll notify you when Oatly Barista Edition is back in stock"
    }
  }
}
```

---

## Special Scenarios

### First-Time User (No Personalization History)
**Request:**
```json
{
  "query": "milk",
  "user_id": "new_user_456"
}
```

**Response:**
```json
{
  "success": true,
  "products": [
    {
      "sku": "MILK-001",
      "name": "Organic Valley Whole Milk",
      "price": 5.99,
      "popularity_score": 0.85,
      "rating": 4.8
    }
  ],
  "personalization": {
    "enabled": true,
    "status": "learning",
    "message": "We're learning your preferences. Shop a few times for personalized recommendations!",
    "onboarding_tips": [
      "Try different brands to help us learn your preferences",
      "Use 'my usual' after a few orders for quick reordering"
    ]
  }
}
```

### Privacy-Conscious User (Personalization Disabled)
**Request:**
```json
{
  "query": "organic vegetables",
  "user_id": "privacy_user_789",
  "context": {
    "preferences": {
      "personalization_enabled": false
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "products": [
    {
      "sku": "VEG-001",
      "name": "Organic Carrot Bunch",
      "price": 2.99
    },
    {
      "sku": "VEG-002", 
      "name": "Organic Broccoli Crown",
      "price": 3.49
    }
  ],
  "personalization": {
    "enabled": false,
    "message": "Showing unpersonalized results as requested"
  },
  "metadata": {
    "search_method": "standard",
    "personalization_applied": false
  }
}
```