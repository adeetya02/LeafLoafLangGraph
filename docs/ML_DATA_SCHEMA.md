# ML Data Schema for LeafLoaf Intelligence

## Core ML Objectives
1. **Search Intent Understanding** - Why are they searching?
2. **Reorder Prediction** - When will they need products again?
3. **User Behavior Profiling** - Complete understanding of preferences
4. **Cold Start Handling** - New users get zip-code based relevance

## 1. Search Intent Classification

### Intent Types (Enhanced)
```python
SEARCH_INTENTS = {
    # Current shopping mission
    "quick_reorder": "Buying same items as before",
    "explore_category": "Browsing a category (e.g., 'breakfast items')",
    "specific_product": "Looking for exact item (e.g., 'Oatly Barista Edition')",
    "meal_planning": "Shopping for a recipe/meal",
    "stock_up": "Bulk buying regular items",
    "try_new": "Exploring new products",
    "urgent_need": "Need it today/immediately",
    "price_shopping": "Comparing prices/deals",
    "dietary_discovery": "Finding items for dietary needs"
}
```

### Search Event Data Structure
```json
{
  "search_id": "search_1234567890_abc123",
  "user_id": "user_123",
  "session_id": "session_abc",
  "timestamp": "2024-01-24T10:30:00Z",
  
  "query_analysis": {
    "raw_query": "oatly barista oat milk",
    "normalized_query": "oatly barista oat milk",
    "tokens": ["oatly", "barista", "oat", "milk"],
    "query_type": "brand_specific",
    
    "extracted_features": {
      "has_brand": true,
      "brand_mentioned": "Oatly",
      "has_size": false,
      "has_urgency": false,
      "specificity_score": 0.9,
      "category": "dairy_alternative"
    }
  },
  
  "intent_classification": {
    "primary_intent": "specific_product",
    "confidence": 0.92,
    "secondary_intents": {
      "quick_reorder": 0.65,
      "stock_up": 0.3
    },
    "intent_signals": [
      "brand_in_query",
      "specific_variant",
      "past_purchase_history"
    ]
  },
  
  "user_context": {
    "search_history_last_7d": ["milk", "bread", "oat milk"],
    "days_since_last_order": 8,
    "avg_order_frequency": 7.2,
    "in_reorder_window": true,
    "usual_order_day": "Sunday",
    "time_until_usual_order": 2,
    
    "cart_context": {
      "has_active_cart": true,
      "cart_value": 45.67,
      "items_in_cart": 6,
      "categories_in_cart": ["produce", "bakery"]
    }
  },
  
  "search_results": {
    "total_results": 8,
    "brands_shown": ["Oatly", "Pacific Foods", "Califia"],
    "price_range": [4.99, 6.99],
    "in_stock_count": 7,
    "out_of_stock": ["SKU_12345"]
  },
  
  "user_interaction": {
    "results_clicked": [
      {"position": 1, "product_id": "OATLY_001", "time_to_click": 2.3},
      {"position": 3, "product_id": "OATLY_002", "time_to_click": 5.7}
    ],
    "filters_applied": [],
    "sort_changed": false,
    "time_on_results": 12.5,
    "scroll_depth": 0.6
  },
  
  "outcome": {
    "added_to_cart": true,
    "product_chosen": "OATLY_001",
    "quantity": 2,
    "substitution_made": false,
    "search_successful": true
  }
}
```

## 2. Reorder Prediction Data

### Product Purchase History
```json
{
  "user_product_history": {
    "user_id": "user_123",
    "product_id": "OATLY_001",
    
    "purchase_pattern": {
      "first_purchase": "2023-10-15",
      "last_purchase": "2024-01-16",
      "total_purchases": 12,
      "purchase_dates": ["2023-10-15", "2023-10-29", ...],
      "intervals_days": [14, 13, 15, 14, 16, ...],
      "avg_interval": 14.5,
      "std_deviation": 1.2,
      "regularity_score": 0.92
    },
    
    "quantity_pattern": {
      "quantities_ordered": [1, 2, 2, 1, 2, ...],
      "avg_quantity": 1.7,
      "last_quantity": 2,
      "quantity_trend": "stable"
    },
    
    "reorder_prediction": {
      "expected_reorder_date": "2024-01-30",
      "confidence": 0.87,
      "days_until_reorder": 6,
      "is_overdue": false,
      "urgency_score": 0.3
    }
  }
}
```

### Category Reorder Patterns
```json
{
  "category_patterns": {
    "user_id": "user_123",
    "category": "dairy_alternative",
    
    "products_in_rotation": [
      {"product_id": "OATLY_001", "frequency": 0.6},
      {"product_id": "PACIFIC_001", "frequency": 0.3},
      {"product_id": "CALIFIA_001", "frequency": 0.1}
    ],
    
    "category_metrics": {
      "avg_products_per_order": 1.2,
      "category_order_frequency": 14,
      "never_out_of_stock": true,
      "price_sensitivity": 0.3
    }
  }
}
```

## 3. Comprehensive User Profile

### Master User Profile
```json
{
  "user_profile": {
    "user_id": "user_123",
    "created_date": "2023-08-01",
    "zip_code": "10001",
    
    "demographics": {
      "inferred_household_size": 3,
      "inferred_life_stage": "family_young_children",
      "shopping_frequency": "weekly"
    },
    
    "brand_preferences": {
      "dairy_alternative": {
        "Oatly": 0.7,
        "Pacific Foods": 0.2,
        "Store Brand": 0.1
      },
      "milk": {
        "Organic Valley": 0.9,
        "Horizon": 0.1
      }
    },
    
    "shopping_behavior": {
      "avg_cart_value": 127.45,
      "avg_items_per_order": 18,
      "price_sensitivity_score": 0.3,
      "organic_preference": 0.8,
      "bulk_buyer": false,
      "coupon_user": 0.2,
      
      "shopping_patterns": {
        "preferred_day": "Sunday",
        "preferred_time": "morning",
        "shops_on_schedule": true,
        "impulse_buy_rate": 0.15
      }
    },
    
    "dietary_profile": {
      "confirmed_restrictions": [],
      "inferred_preferences": ["organic", "non_gmo"],
      "avoided_ingredients": ["high_fructose_corn_syrup"],
      "category_preferences": {
        "plant_based": 0.6,
        "gluten_free": 0.2,
        "sugar_free": 0.1
      }
    },
    
    "search_behavior": {
      "avg_searches_per_session": 4.2,
      "search_specificity": 0.7,
      "uses_brands_in_search": 0.6,
      "browse_vs_search": 0.3,
      "common_search_patterns": [
        "brand + product",
        "category browse",
        "specific variant"
      ]
    },
    
    "ml_features": {
      "churn_risk": 0.1,
      "lifetime_value_percentile": 85,
      "engagement_score": 0.8,
      "personalization_responsive": 0.9
    }
  }
}
```

## 4. Product Attributes (Ordered Items)

### Enhanced Product Data
```json
{
  "product_master": {
    "product_id": "OATLY_001",
    "sku": "7394376616129",
    "name": "Oatly Barista Edition Oat Milk",
    
    "attributes": {
      "brand": "Oatly",
      "category_tree": ["Dairy & Eggs", "Milk & Cream", "Non-Dairy Milk"],
      "size": "32 fl oz",
      "unit_price": 5.99,
      "price_per_unit": 0.19,
      
      "nutritional": {
        "calories_per_serving": 140,
        "protein_g": 3,
        "sugar_g": 7,
        "calcium_dv": 25
      },
      
      "dietary_flags": [
        "vegan",
        "dairy_free",
        "gluten_free",
        "non_gmo"
      ],
      
      "usage_attributes": {
        "best_for": ["coffee", "latte", "cappuccino"],
        "shelf_life_days": 10,
        "storage": "refrigerate_after_opening"
      }
    },
    
    "ml_attributes": {
      "reorder_frequency_days": 14,
      "substitute_products": ["OATLY_002", "PACIFIC_001"],
      "complement_products": ["COFFEE_001", "CEREAL_001"],
      "price_elasticity": -0.3,
      "seasonal_index": {
        "winter": 1.2,
        "summer": 0.8
      },
      "user_loyalty_score": 0.85
    }
  }
}
```

## 5. Zip Code Intelligence

### Zip Code Profile
```json
{
  "zip_profile": {
    "zip_code": "10001",
    "city": "New York",
    "state": "NY",
    
    "demographics": {
      "population": 21049,
      "median_income": 95000,
      "urban_density": "high",
      "predominant_age_group": "25-44"
    },
    
    "shopping_preferences": {
      "organic_index": 1.4,  // vs national average
      "price_sensitivity": 0.3,
      "brand_consciousness": 0.8,
      "health_conscious": 0.9
    },
    
    "popular_products": [
      {"product_id": "OATLY_001", "popularity_score": 0.92},
      {"product_id": "KALE_ORGANIC", "popularity_score": 0.88},
      {"product_id": "KOMBUCHA_GT", "popularity_score": 0.85}
    ],
    
    "dietary_trends": {
      "vegan": 0.15,
      "gluten_free": 0.12,
      "keto": 0.08,
      "organic": 0.45
    },
    
    "supplier_performance": {
      "available_suppliers": ["Whole Foods", "Trader Joes", "Fresh Direct"],
      "avg_delivery_time": 2.5,
      "delivery_reliability": 0.95
    }
  }
}
```

## 6. New User Cold Start

### First Search Enhancement
```json
{
  "new_user_search": {
    "user_id": "new_user_456",
    "first_search": "organic milk",
    "zip_code": "10001",
    
    "zip_based_recommendations": {
      "popular_in_area": [
        {"product": "Organic Valley Milk", "reason": "75% of neighbors buy"},
        {"product": "Horizon Organic", "reason": "Popular alternative"}
      ],
      
      "price_guidance": {
        "typical_price_range": [5.99, 7.99],
        "budget_option": "Store Brand Organic",
        "premium_option": "Maple Hill"
      }
    },
    
    "inferred_preferences": {
      "organic_likelihood": 0.7,
      "price_sensitivity": 0.3,
      "brand_openness": 0.5
    },
    
    "personalization_strategy": "zip_code_based"
  }
}
```

## 7. Real-time ML Features

### Session Intelligence
```json
{
  "session_ml_features": {
    "session_id": "session_abc",
    "real_time_intent": {
      "current_mission": "weekly_shopping",
      "urgency": 0.2,
      "exploration_rate": 0.3,
      "decision_speed": "normal"
    },
    
    "behavior_signals": {
      "is_comparing_prices": false,
      "is_brand_loyal": true,
      "is_list_shopping": true,
      "discovered_new_products": 2
    }
  }
}
```

## 8. Training Data Pipeline

### Daily ML Export Format
```json
{
  "training_batch": {
    "date": "2024-01-24",
    "records": [
      {
        "features": {
          "user_features": [...],
          "query_features": [...],
          "context_features": [...],
          "product_features": [...]
        },
        "labels": {
          "intent": "specific_product",
          "converted": true,
          "reordered_within_30d": true
        }
      }
    ]
  }
}
```

## Implementation Priority

### Phase 1: Core Data Collection
1. Search events with intent
2. Basic user profiles
3. Product purchase history
4. Zip code data

### Phase 2: ML Features
1. Reorder predictions
2. Intent classification model
3. User behavior vectors
4. Cold start handling

### Phase 3: Advanced
1. Real-time personalization
2. Price optimization
3. Inventory-aware recommendations
4. Multi-objective optimization