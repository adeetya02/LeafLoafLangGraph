# Baseline Voice API Specification (Ship-Ready)

## 🚀 Overview

This is the baseline specification for the voice/natural language API that includes essential features only. Purchase history is included as a core feature.

---

## 📡 API Endpoint

**POST** `/api/v1/analyze`

---

## 📥 Voice Request Format

```json
POST /api/v1/analyze
Content-Type: application/json

{
  "input_type": "voice",
  "text": "hey can you get me some rice I need about 20 pounds for my restaurant",
  "voice_metadata": {
    "duration": 4.2,
    "confidence": 0.94
  },
  "user_id": "user123",
  "session_id": "voice_session_789",
  "context": {
    "user_type": "restaurant"
  }
}
```

---

## 📤 Voice Response Format

```json
{
  "status": "success",
  "data": {
    "extracted_items": [
      {
        "extraction": {
          "raw_text": "rice I need about 20 pounds",
          "normalized_text": "rice",
          "quantity_detected": {
            "amount": 20,
            "unit": "pounds",
            "confidence": 0.95
          },
          "extraction_confidence": 0.92
        },
        "product_matches": [
          {
            "product": {
              "product_id": "uuid-123",
              "sku": "LX_RICE_001",
              "product_name": "Laxmi Basmati Rice Premium",
              "brand": "Laxmi",
              "size": "20 LB",
              "price": 35.00
            },
            "match_score": 0.98,
            "match_reason": "exact_size_match",
            "purchase_history": {
              "previously_purchased": true,
              "times_purchased": 12,
              "last_purchased": "2025-06-10",
              "typical_quantity": 2,
              "days_since_last_order": 16,
              "is_regular_item": true
            }
          },
          {
            "product": {
              "product_id": "uuid-456",
              "sku": "VS_RICE_001",
              "product_name": "Vistar Jasmine Rice",
              "brand": "Vistar",
              "size": "25 LB",
              "price": 42.50
            },
            "match_score": 0.85,
            "purchase_history": {
              "previously_purchased": false,
              "times_purchased": 0,
              "is_regular_item": false
            }
          }
        ]
      }
    ],
    "suggestions": {
      "message": "Found rice options. You usually order Laxmi Basmati Rice (bought 12 times). Ready to add your regular 2 bags?",
      "quick_actions": [
        {
          "text": "Add 2 bags (usual order)",
          "action": "add_to_cart",
          "sku": "LX_RICE_001",
          "quantity": 2,
          "reason": "typical_quantity"
        },
        {
          "text": "Add 1 bag only",
          "action": "add_to_cart",
          "sku": "LX_RICE_001",
          "quantity": 1
        }
      ],
      "reorder_context": {
        "pattern_detected": "regular_reorder",
        "usual_frequency": "every 2 weeks",
        "timing": "on_schedule"
      }
    }
  },
  "meta": {
    "session_id": "voice_session_789",
    "turn": 1,
    "performance": {
      "total_ms": 420
    }
  }
}
```

---

## ✅ Baseline Features (To Ship)

1. **Extract grocery items** from voice/text/image
2. **Match products** with confidence scores
3. **Handle quantities** and units
4. **Purchase history** for each matched product
   - Previously purchased flag
   - Purchase count & frequency
   - Last purchase date
   - Typical quantity ordered
5. **Smart suggestions** based on history
6. **Reorder patterns** (simple version)

---

## ❌ Features Deferred (Post-Launch)

1. Complex ML predictions
2. Inventory predictions
3. Cross-sell recommendations
4. Advanced personalization layers
5. Predictive reorder timing
6. Menu correlation analysis

---

## 📝 Core Implementation

### 1. Purchase History Enrichment

```python
async def enrich_with_purchase_history(products, user_id):
    """Add purchase history to each product"""
    
    for product in products:
        # Query purchase history (cached)
        history = await get_purchase_history(
            user_id=user_id,
            sku=product['sku']
        )
        
        product['purchase_history'] = {
            'previously_purchased': history.count > 0,
            'times_purchased': history.count,
            'last_purchased': history.last_date,
            'typical_quantity': history.avg_quantity,
            'days_since_last_order': calculate_days(history.last_date),
            'is_regular_item': history.count >= 3  # 3+ purchases = regular
        }
    
    # Sort by purchase history (regular items first)
    products.sort(key=lambda p: (
        -p['purchase_history']['times_purchased'],
        -p['match_score']
    ))
    
    return products
```

### 2. Main Processing Flow

```python
async def process_voice_input(request):
    # 1. Extract items from text
    items = await extract_with_llm(request.text)
    
    # 2. Search products for each item
    results = []
    for item in items:
        products = await search_products(
            query=item.normalized_text,
            size_filter=item.quantity
        )
        
        # 3. Enrich with purchase history
        products = await enrich_with_purchase_history(
            products[:5],  # Top 5
            request.user_id
        )
        
        results.append({
            "extraction": item,
            "product_matches": products
        })
    
    # 4. Create suggestions based on history
    suggestions = create_history_aware_suggestions(results)
    
    return {
        "extracted_items": results,
        "suggestions": suggestions
    }
```

---

## 🗄️ Data Model

### Purchase History Table

```sql
-- Simple purchase history table
CREATE TABLE purchase_history (
    user_id VARCHAR(50),
    sku VARCHAR(50),
    product_name VARCHAR(200),
    quantity INTEGER,
    purchase_date TIMESTAMP,
    order_id VARCHAR(50),
    PRIMARY KEY (user_id, sku, order_id)
);

-- Aggregated view for fast queries
CREATE MATERIALIZED VIEW user_product_stats AS
SELECT 
    user_id,
    sku,
    COUNT(*) as times_purchased,
    MAX(purchase_date) as last_purchased,
    AVG(quantity) as avg_quantity,
    COUNT(*) >= 3 as is_regular
FROM purchase_history
GROUP BY user_id, sku;

-- Index for fast lookups
CREATE INDEX idx_user_product ON user_product_stats(user_id, sku);
```

---

## 🔄 Multi-Turn Conversation Support

For voice conversations that span multiple turns:

```json
{
  "session_id": "voice_session_789",
  "conversation_context": {
    "previous_turn": 1,
    "accumulated_items": ["LX_RICE_001"],
    "pending_actions": ["quantity_confirmation"]
  }
}
```

The system maintains conversation state across turns but keeps it simple - just track what's been discussed and what's pending.

---

## 🚀 Performance Targets

- **Total Response Time**: <500ms
- **LLM Extraction**: <200ms
- **Product Search**: <150ms
- **History Lookup**: <50ms (cached)
- **Response Compilation**: <100ms

---

## 📊 Success Metrics

1. **Extraction Accuracy**: >90% for common items
2. **Regular Item Recognition**: >95% accuracy
3. **Quantity Suggestion Acceptance**: >70%
4. **Response Time**: <500ms p95

---

This is the complete baseline specification - ready to ship!