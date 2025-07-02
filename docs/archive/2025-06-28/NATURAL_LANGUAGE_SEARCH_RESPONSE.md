# Natural Language Search Response Structure

## 🎯 Overview

When users provide natural language input (photos, notes, voice), the Supervisor analyzes and returns structured product suggestions with confidence scores and ML metadata.

---

## 📊 Complete Response Structure

```json
{
  "status": "success",
  "data": {
    // Original user input analysis
    "input_analysis": {
      "original_text": "2 bags rice\ndal (toor)\nmilk oatly\nfrozen okra\nsamosa 2 packs",
      "input_type": "text",  // text | image | voice | mixed
      "language": "en",
      "processing_method": "gemma_extraction"
    },
    
    // Extracted items with product matches
    "extracted_items": [
      {
        // What the LLM extracted
        "extraction": {
          "raw_text": "2 bags rice",
          "normalized_text": "rice",
          "quantity_detected": {
            "amount": 2,
            "unit": "bags",
            "confidence": 0.95
          },
          "modifiers": ["basmati", "long grain"],  // If any detected
          "extraction_confidence": 0.92
        },
        
        // Product matches for this extraction
        "product_matches": [
          {
            // Core product data
            "product": {
              "product_id": "uuid-123",
              "sku": "LX_RICE_001",
              "upc": "851975003123",
              "product_name": "Laxmi Basmati Rice Premium",
              "brand": "Laxmi",
              "supplier": "Laxmi"
            },
            
            // Detailed attributes
            "attributes": {
              "category": "Rice & Grains",
              "subcategory": "Basmati Rice",
              "cuisine": "Indian",
              "ethnic_category": "South Asian",
              
              // Physical attributes
              "packaging": {
                "size": "10 LB",
                "size_value": 10.0,
                "size_unit": "lb",
                "format": "bag",
                "case_pack": 1,
                "units_per_case": 1
              },
              
              // Dietary & Certifications
              "dietary": {
                "is_organic": false,
                "is_gluten_free": true,
                "is_vegan": true,
                "is_vegetarian": true,
                "is_halal": true,
                "is_kosher": false,
                "is_non_gmo": true
              },
              
              // Search & Display
              "search_terms": [
                "basmati", "rice", "long grain", "aged", 
                "indian", "biryani", "pulao", "premium"
              ],
              "display_tags": ["Premium", "Aged", "Long Grain"],
              
              // Additional attributes
              "preparation_time": "20 minutes",
              "shelf_life": "24 months",
              "storage": "Store in cool, dry place",
              "country_of_origin": "India"
            },
            
            // Pricing node
            "pricing": {
              "base_price": 35.00,
              "currency": "USD",
              "price_per_unit": 3.50,  // per lb
              "price_unit": "lb",
              "tier_pricing": [
                {"min_qty": 1, "max_qty": 4, "price": 35.00},
                {"min_qty": 5, "max_qty": 9, "price": 33.25},
                {"min_qty": 10, "max_qty": null, "price": 31.50}
              ],
              "promotion": {
                "active": true,
                "type": "percentage_off",
                "value": 10,
                "description": "10% off Rice & Grains",
                "valid_until": "2025-06-30"
              }
            },
            
            // ML/Analytics node
            "ml_metadata": {
              "match_score": 0.95,  // How well this matches the extraction
              "match_reason": "exact_category_match",
              "ranking_factors": {
                "text_similarity": 0.92,
                "popularity_score": 0.88,
                "user_preference_match": 0.90,
                "price_competitiveness": 0.85
              },
              "recommendation_context": {
                "frequently_bought_together": ["LX_DAL_001", "LX_GHEE_001"],
                "alternative_products": ["LX_RICE_002", "VS_RICE_001"],
                "upgrade_suggestion": "LX_RICE_PREMIUM_001"
              },
              "personalization": {
                "previously_purchased": true,
                "purchase_frequency": "monthly",
                "last_purchased": "2025-05-15",
                "user_rating": 4.5
              }
            },
            
            // Inventory & Fulfillment
            "availability": {
              "in_stock": true,
              "stock_level": "high",  // high | medium | low | out_of_stock
              "available_quantity": 150,
              "warehouse_locations": ["NYC-01", "NJ-02"],
              "delivery_estimate": {
                "standard": "2025-06-28",
                "express": "2025-06-27"
              }
            },
            
            // Rich media
            "media": {
              "thumbnail": "https://cdn.leafloaf.com/products/LX_RICE_001_thumb.jpg",
              "main_image": "https://cdn.leafloaf.com/products/LX_RICE_001_main.jpg",
              "images": [
                "https://cdn.leafloaf.com/products/LX_RICE_001_1.jpg",
                "https://cdn.leafloaf.com/products/LX_RICE_001_2.jpg"
              ],
              "video": null,
              "cooking_instructions_url": "https://leafloaf.com/recipes/perfect-basmati"
            }
          },
          // ... more product matches with decreasing scores
        ],
        
        // Suggested action for this item
        "suggested_action": {
          "type": "add_to_cart",
          "recommended_product": "LX_RICE_001",
          "recommended_quantity": 2,
          "reasoning": "Matches your request for '2 bags rice' with high confidence"
        }
      },
      
      {
        // Second extraction example
        "extraction": {
          "raw_text": "dal (toor)",
          "normalized_text": "toor dal",
          "quantity_detected": {
            "amount": 1,
            "unit": "package",
            "confidence": 0.70  // Lower confidence, no quantity specified
          },
          "modifiers": ["toor", "arhar"],
          "extraction_confidence": 0.88
        },
        
        "product_matches": [
          // Similar structure as above
        ],
        
        "suggested_action": {
          "type": "add_to_cart",
          "recommended_product": "LX_DAL_001",
          "recommended_quantity": 1,
          "reasoning": "Popular toor dal option, 4lb bag suitable for home use"
        }
      }
      // ... more extracted items
    ],
    
    // Overall suggestions and actions
    "suggestions": {
      "quick_add_all": {
        "description": "Add all recommended items to cart",
        "items": [
          {"sku": "LX_RICE_001", "quantity": 2},
          {"sku": "LX_DAL_001", "quantity": 1},
          {"sku": "LX_OKRA_FROZEN_001", "quantity": 1},
          {"sku": "OATLY_BARISTA_001", "quantity": 1},
          {"sku": "LX_SAMOSA_001", "quantity": 2}
        ],
        "total_items": 7,
        "estimated_total": 125.50
      },
      
      "alternatives": {
        "budget_friendly": [
          {"original": "LX_RICE_001", "alternative": "VS_RICE_VALUE_001", "savings": 5.50}
        ],
        "premium_upgrade": [
          {"original": "LX_RICE_001", "alternative": "LX_RICE_ROYAL_001", "difference": 8.00}
        ]
      },
      
      "missing_items": [
        {
          "extracted_text": "cooking oil",
          "confidence": 0.65,
          "reason": "Commonly needed with rice and dal",
          "suggestions": ["LX_OIL_001", "VS_GHEE_001"]
        }
      ]
    },
    
    // Analytics tracking
    "analytics": {
      "extraction_quality": {
        "total_items_detected": 5,
        "high_confidence_items": 4,  // >0.8 confidence
        "low_confidence_items": 1,
        "failed_extractions": 0
      },
      "matching_quality": {
        "exact_matches": 3,
        "fuzzy_matches": 2,
        "no_matches": 0,
        "average_match_score": 0.89
      },
      "user_context": {
        "session_id": "user123_session456",
        "user_type": "retail",
        "meal_planning_detected": true,
        "cuisine_preference": ["Indian"],
        "estimated_servings": 20
      }
    }
  },
  
  "meta": {
    "performance": {
      "total_ms": 450,
      "breakdown": {
        "text_extraction": 120,
        "llm_analysis": 150,
        "product_matching": 100,
        "enrichment": 80
      }
    },
    "model_used": "gemma-2-9b",
    "confidence_threshold": 0.70,
    "max_products_per_item": 5,
    "request_id": "req_abc123",
    "timestamp": "2025-06-26T10:30:00Z"
  }
}
```

---

## 🔍 Key Design Decisions

### 1. **Extraction Structure**
- Separates what was extracted from what was matched
- Includes confidence at both extraction and matching levels
- Preserves original text for debugging/improvement

### 2. **Product Attributes Node**
- Comprehensive attributes for filtering/display
- Hierarchical organization (category → subcategory)
- Rich dietary and certification info
- Search terms for improving future matches

### 3. **ML Metadata Node**
- Match scoring with reasoning
- Ranking factors for transparency
- Personalization data
- Recommendation context for upsell/cross-sell

### 4. **Pricing Node**
- Base price with tier pricing
- Active promotions
- Per-unit calculations
- Future: real-time pricing agent integration

### 5. **Availability Node**
- Real-time stock levels
- Delivery estimates
- Multi-warehouse support
- Future: predictive availability

---

## 📱 Usage Examples

### Example 1: Photo of Handwritten List
```python
# User uploads photo
POST /api/v1/analyze
{
  "input_type": "image",
  "image_url": "data:image/jpeg;base64,...",
  "user_id": "user123",
  "context": {
    "user_type": "restaurant",
    "location": "NYC"
  }
}

# Response includes extracted items with visual confidence
{
  "extracted_items": [
    {
      "extraction": {
        "raw_text": "2 bags rice",
        "bounding_box": [100, 50, 200, 80],  // Location in image
        "ocr_confidence": 0.95,
        "extraction_confidence": 0.92
      },
      // ... rest of structure
    }
  ]
}
```

### Example 2: Voice Input
```python
# Voice transcription
POST /api/v1/analyze
{
  "input_type": "voice",
  "text": "I need rice and dal for my restaurant about 20 pounds each",
  "voice_metadata": {
    "duration": 3.5,
    "language": "en-US",
    "accent_detected": "Indian"
  }
}

# Response includes quantity understanding
{
  "extracted_items": [
    {
      "extraction": {
        "raw_text": "rice for my restaurant about 20 pounds",
        "normalized_text": "rice",
        "quantity_detected": {
          "amount": 20,
          "unit": "pounds",
          "confidence": 0.85
        },
        "context_clues": ["restaurant", "bulk_quantity"]
      },
      "product_matches": [
        // Prioritizes restaurant-sized packages
      ]
    }
  ]
}
```

### Example 3: Apple Notes Paste
```python
# Structured list from notes
POST /api/v1/analyze
{
  "input_type": "text",
  "text": "Grocery List:\n- Basmati rice (2 bags)\n- Toor dal\n- Oat milk (Oatly brand)\n- Frozen vegetables\n- Samosas for party",
  "source": "apple_notes"
}

# Response preserves structure and context
{
  "extracted_items": [
    {
      "extraction": {
        "raw_text": "Samosas for party",
        "context_hints": ["party", "bulk_needed"],
        "suggested_quantity": {
          "amount": 3,
          "unit": "packages",
          "reasoning": "party context suggests larger quantity"
        }
      }
    }
  ]
}
```

---

## 🚀 Implementation Notes

1. **LLM Processing**:
   ```python
   # Prompt for Gemma
   Extract grocery items with quantities from: {text}
   Return: item, quantity, unit, modifiers, confidence
   ```

2. **Product Matching**:
   - Use Weaviate hybrid search with extracted terms
   - Apply user context for ranking
   - Include fuzzy matching for misspellings

3. **ML Enrichment**:
   - Pull from user history
   - Apply collaborative filtering
   - Calculate real-time scores

4. **Response Building**:
   - Parallel fetch all product data
   - Enrich with pricing/inventory
   - Generate suggestions based on context

---

## 🎯 Success Metrics

1. **Extraction Accuracy**: >90% for common items
2. **Match Relevance**: >85% top match is correct
3. **Response Time**: <500ms end-to-end
4. **Cart Conversion**: >70% use quick-add suggestions