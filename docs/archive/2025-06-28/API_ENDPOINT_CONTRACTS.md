# API Endpoint Contracts - Request/Response Definitions

## 🎯 Design Principles
1. **Minimal Payloads** - Only send/receive what's needed
2. **Predictable Structure** - Same format across all endpoints
3. **Latency Optimized** - Designed for <300ms total response
4. **Cache Friendly** - Requests that can be cached are clearly marked

---

## 1️⃣ Product Search Endpoint
**POST** `/api/v1/products/search`

### Purpose
Direct product search without natural language processing. Bypasses supervisor for speed.

### Request
```json
{
  // Required
  "query": "rice",                    // Search query (max 100 chars)
  
  // Optional filters
  "filters": {
    "categories": ["Rice & Grains"],  // Array of category names
    "suppliers": ["Laxmi", "Vistar"], // Array of supplier names
    "cuisines": ["Indian", "Korean"],  // Array of cuisines
    "priceRange": {
      "min": 10.00,                   // Minimum price
      "max": 50.00                    // Maximum price
    },
    "dietary": {                      // Dietary restrictions
      "isOrganic": true,
      "isGlutenFree": true,
      "isVegan": true,
      "isNonGMO": true
    },
    "inStock": true                   // Only show in-stock items
  },
  
  // Pagination
  "page": 1,                          // Page number (default: 1)
  "pageSize": 20,                     // Items per page (default: 20, max: 50)
  
  // Sorting
  "sortBy": "relevance",              // relevance | price_asc | price_desc | name_asc
  
  // Search config
  "searchConfig": {
    "alpha": 0.5,                     // Keyword vs semantic weight (0-1)
    "boostCategories": true,          // Boost exact category matches
    "includeSimilar": false           // Include similar products
  },
  
  // Session (optional)
  "sessionId": "user123_session456"   // For personalization
}
```

### Response
```json
{
  "status": "success",
  "data": {
    "products": [
      {
        "id": "uuid-here",
        "sku": "LX_RICE_001",
        "name": "Laxmi Basmati Rice",
        "description": "Premium aged basmati rice, extra long grain",
        "category": "Rice & Grains",
        "supplier": "Laxmi",
        "brand": "Laxmi",
        
        // Pricing - No markup calculation here
        "price": {
          "amount": 35.00,            // Wholesale price
          "currency": "USD",
          "unit": "case",
          "caseSize": 1
        },
        
        // Pack information
        "packaging": {
          "size": "10 LB",
          "format": "bag",
          "unitsPerCase": 1,
          "weight": {
            "amount": 10.0,
            "unit": "lb"
          }
        },
        
        // Attributes for filtering
        "attributes": {
          "cuisine": "Indian",
          "isOrganic": false,
          "isGlutenFree": true,
          "isNonGMO": true,
          "isVegetarian": true,
          "isVegan": true
        },
        
        // Availability
        "availability": {
          "inStock": true,
          "quantity": 100           // Optional, if we show inventory
        },
        
        // Search relevance
        "searchScore": 0.95         // 0-1, higher is more relevant
      }
    ],
    
    // Facets for filtering UI
    "facets": {
      "categories": [
        {"name": "Rice & Grains", "count": 45},
        {"name": "Dal & Lentils", "count": 23}
      ],
      "suppliers": [
        {"name": "Laxmi", "count": 68},
        {"name": "Vistar", "count": 12}
      ],
      "priceRanges": [
        {"range": "0-25", "count": 20},
        {"range": "25-50", "count": 35},
        {"range": "50+", "count": 13}
      ],
      "dietary": [
        {"name": "organic", "count": 15},
        {"name": "glutenFree", "count": 42}
      ]
    },
    
    // Pagination info
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "totalPages": 4,
      "totalItems": 68,
      "hasNext": true,
      "hasPrev": false
    }
  },
  
  // Metadata
  "meta": {
    "query": {
      "original": "rice",
      "normalized": "rice",           // After cleaning
      "searchType": "hybrid"          // keyword | semantic | hybrid
    },
    "performance": {
      "totalMs": 145,
      "breakdown": {
        "search": 140,
        "postProcessing": 5
      },
      "cached": false
    },
    "requestId": "req_abc123",
    "timestamp": "2025-06-26T10:30:00Z"
  }
}
```

---

## 2️⃣ Cart Management Endpoints

### 2.1 Add to Cart
**POST** `/api/v1/cart/items`

#### Request
```json
{
  "sessionId": "user123_session456",  // Required
  "items": [                          // Can add multiple items
    {
      "productId": "uuid-here",       // Product UUID
      "sku": "LX_RICE_001",          // SKU (alternative to productId)
      "quantity": 2                   // Quantity to add
    }
  ],
  "merge": true                       // Merge with existing quantity (default: true)
}
```

#### Response
```json
{
  "status": "success",
  "data": {
    "cart": {
      "id": "cart_789",
      "sessionId": "user123_session456",
      "items": [
        {
          "cartItemId": "item_123",
          "productId": "uuid-here",
          "sku": "LX_RICE_001",
          "name": "Laxmi Basmati Rice",
          "quantity": 2,
          "price": 35.00,             // Unit price
          "subtotal": 70.00,          // quantity * price
          "availability": "in_stock"
        }
      ],
      "itemCount": 2,                 // Total quantity
      "uniqueItems": 1,               // Unique products
      "subtotal": 70.00,
      "lastUpdated": "2025-06-26T10:30:00Z"
    },
    "added": [                        // What was actually added
      {
        "sku": "LX_RICE_001",
        "quantity": 2,
        "newTotal": 2                 // New quantity for this item
      }
    ]
  },
  "meta": {
    "performance": {
      "totalMs": 45
    }
  }
}
```

### 2.2 Update Cart Item
**PATCH** `/api/v1/cart/items/{cartItemId}`

#### Request
```json
{
  "sessionId": "user123_session456",
  "quantity": 5                       // New quantity (not increment)
}
```

### 2.3 Remove from Cart
**DELETE** `/api/v1/cart/items/{cartItemId}`

#### Request
```json
{
  "sessionId": "user123_session456"
}
```

### 2.4 Get Cart
**GET** `/api/v1/cart?sessionId={sessionId}`

#### Response
Same as cart object in Add to Cart response

### 2.5 Clear Cart
**DELETE** `/api/v1/cart?sessionId={sessionId}`

---

## 3️⃣ Natural Language Chat
**POST** `/api/v1/chat`

### Purpose
Handle complex natural language queries that need intent analysis and potentially multiple agents.

### Request
```json
{
  "message": "I need rice and dal for 20 people, add to cart",
  "sessionId": "user123_session456",
  "context": {
    "userType": "restaurant",         // retail | restaurant | wholesale
    "location": {
      "zipCode": "10001",
      "city": "New York",
      "state": "NY"
    },
    "preferences": {                  // Optional user preferences
      "cuisines": ["Indian", "Korean"],
      "dietary": ["vegetarian"]
    }
  },
  "includeRecommendations": true,     // Include ML recommendations
  "maxProducts": 20                  // Max products to return
}
```

### Response
```json
{
  "status": "success",
  "data": {
    // Intent analysis
    "interpretation": {
      "intent": "search_and_add_to_cart",
      "confidence": 0.92,
      "entities": {
        "products": ["rice", "dal"],
        "quantity": "for 20 people",
        "action": "add to cart"
      },
      "suggestedQuantities": {
        "rice": "2 x 10lb bags",
        "dal": "1 x 4lb bag"
      }
    },
    
    // Products found (if search was performed)
    "products": [...],  // Same format as search endpoint
    
    // Cart state (if cart was modified)
    "cart": {...},      // Same format as cart endpoints
    
    // Natural language response
    "message": "I found 5 rice and 3 dal products suitable for 20 people. Based on typical servings, I recommend 2 bags of Laxmi Basmati Rice (10lb each) and 1 bag of Toor Dal (4lb). Would you like me to add these to your cart?",
    
    // Suggested actions
    "suggestions": [
      {
        "type": "add_to_cart",
        "text": "Add recommended items to cart",
        "action": {
          "items": [
            {"sku": "LX_RICE_001", "quantity": 2},
            {"sku": "LX_DAL_001", "quantity": 1}
          ]
        }
      },
      {
        "type": "search",
        "text": "Show more rice options",
        "action": {
          "query": "rice",
          "filters": {"suppliers": ["Laxmi"]}
        }
      }
    ],
    
    // ML Recommendations (if requested)
    "recommendations": {
      "basedOn": "rice and dal selection",
      "products": [...],  // 5 complementary products
      "reason": "Customers who buy rice and dal often need these"
    }
  },
  
  "meta": {
    "agents": {
      "executed": ["supervisor", "search", "recommendation"],
      "skipped": ["cart", "order"]
    },
    "performance": {
      "totalMs": 380,
      "breakdown": {
        "supervisor": 50,
        "search": 200,
        "recommendation": 80,
        "responseCompiler": 50
      }
    },
    "session": {
      "id": "user123_session456",
      "conversationLength": 3,
      "context": ["previous: looking for Indian groceries"]
    }
  }
}
```

---

## 4️⃣ Pricing Service
**POST** `/api/v1/pricing/calculate`

### Purpose
Real-time price calculation based on user context, quantity breaks, and promotions.

### Request
```json
{
  "items": [
    {
      "productId": "uuid-here",
      "sku": "LX_RICE_001",          // Can use either productId or sku
      "quantity": 10                  // Quantity for pricing
    }
  ],
  "userContext": {
    "type": "restaurant",             // retail | restaurant | wholesale
    "tier": "gold",                   // Customer tier
    "location": {
      "zipCode": "10001",
      "zone": "manhattan"             // Delivery zone
    }
  },
  "promoCodes": ["SAVE10", "NEWUSER"],
  "includeShipping": true,
  "includeBreakdown": true            // Show detailed price breakdown
}
```

### Response
```json
{
  "status": "success",
  "data": {
    "pricing": {
      "items": [
        {
          "productId": "uuid-here",
          "sku": "LX_RICE_001",
          "quantity": 10,
          "basePrice": 35.00,         // Original wholesale price
          "adjustments": [
            {
              "type": "tier_discount",
              "description": "Gold tier discount",
              "amount": -3.50,
              "percentage": 10
            },
            {
              "type": "quantity_break",
              "description": "10+ units discount",
              "amount": -5.25,
              "percentage": 15
            }
          ],
          "unitPrice": 26.25,         // After adjustments
          "subtotal": 262.50          // quantity * unitPrice
        }
      ],
      
      "summary": {
        "subtotal": 262.50,
        "adjustments": [
          {
            "type": "promo_code",
            "code": "SAVE10",
            "amount": -26.25,
            "percentage": 10
          }
        ],
        "shipping": 15.00,
        "tax": 19.69,                 // Based on location
        "total": 271.19
      },
      
      // Quantity break information
      "quantityBreaks": [
        {"minQty": 1, "maxQty": 4, "discount": 0},
        {"minQty": 5, "maxQty": 9, "discount": 5},
        {"minQty": 10, "maxQty": null, "discount": 15}
      ],
      
      "validUntil": "2025-06-26T11:30:00Z"  // Price quote validity
    }
  },
  
  "meta": {
    "performance": {
      "totalMs": 25,
      "cached": true,
      "cacheKey": "price:restaurant:gold:10001"
    }
  }
}
```

---

## 5️⃣ Order Management
**POST** `/api/v1/orders`

### Purpose
Convert cart to order with delivery and payment information.

### Request
```json
{
  "sessionId": "user123_session456",
  "cartId": "cart_789",               // Optional if using session
  
  "delivery": {
    "address": {
      "street": "123 Main St",
      "city": "New York",
      "state": "NY",
      "zipCode": "10001",
      "instructions": "Leave at front desk"
    },
    "date": "2025-06-27",
    "timeSlot": "10:00-12:00",
    "type": "standard"                // standard | express | scheduled
  },
  
  "payment": {
    "method": "invoice",              // invoice | credit_card | terms
    "terms": "net30"                  // For invoice payments
  },
  
  "notes": "Please call before delivery"
}
```

### Response
```json
{
  "status": "success",
  "data": {
    "order": {
      "id": "order_12345",
      "number": "ORD-2025-12345",
      "status": "confirmed",
      "items": [...],                 // Same format as cart items
      
      "pricing": {
        "subtotal": 250.00,
        "shipping": 15.00,
        "tax": 21.25,
        "total": 286.25
      },
      
      "delivery": {
        "date": "2025-06-27",
        "timeSlot": "10:00-12:00",
        "trackingNumber": null,       // Added when shipped
        "estimatedDelivery": "2025-06-27T10:00:00Z"
      },
      
      "payment": {
        "method": "invoice",
        "status": "pending",
        "dueDate": "2025-07-27"
      },
      
      "createdAt": "2025-06-26T10:30:00Z",
      "updatedAt": "2025-06-26T10:30:00Z"
    }
  },
  
  "meta": {
    "performance": {
      "totalMs": 150
    },
    "notifications": [
      "Order confirmation sent to user@example.com",
      "Invoice will be sent within 24 hours"
    ]
  }
}
```

---

## 6️⃣ Recommendations Service
**GET** `/api/v1/recommendations`

### Purpose
Get personalized product recommendations without search.

### Request Query Parameters
```
sessionId=user123_session456         // Required
type=complementary                   // complementary | frequently_bought | trending
basedOn=cart                        // cart | history | category
limit=5                             // Max recommendations (default: 5)
```

### Response
```json
{
  "status": "success",
  "data": {
    "recommendations": [
      {
        "product": {...},             // Full product object
        "reason": "Frequently bought with items in your cart",
        "score": 0.92,               // Relevance score
        "matchedItems": ["LX_RICE_001", "LX_DAL_001"]
      }
    ],
    "type": "complementary",
    "basedOn": {
      "source": "cart",
      "items": 2,
      "categories": ["Rice & Grains", "Dal & Lentils"]
    }
  },
  
  "meta": {
    "performance": {
      "totalMs": 35,
      "cached": true
    },
    "algorithm": "collaborative_filtering_v2"
  }
}
```

---

## 🔄 Error Response Format (All Endpoints)

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",       // Standard error code
    "message": "Invalid quantity: must be positive integer",
    "field": "items[0].quantity",     // Specific field if applicable
    "details": {                      // Additional context
      "provided": -1,
      "required": "positive integer"
    }
  },
  "meta": {
    "requestId": "req_abc123",
    "timestamp": "2025-06-26T10:30:00Z",
    "documentation": "https://api.leafloaf.com/docs/errors#VALIDATION_ERROR"
  }
}
```

---

## 🚀 Latency Targets by Endpoint

| Endpoint | Target | Max | Cache TTL |
|----------|--------|-----|-----------|
| Product Search | 150ms | 300ms | 5 min |
| Cart Operations | 50ms | 100ms | No cache |
| Chat (Simple) | 300ms | 500ms | No cache |
| Chat (Complex) | 500ms | 800ms | No cache |
| Pricing | 25ms | 50ms | 1 hour |
| Orders | 150ms | 300ms | No cache |
| Recommendations | 35ms | 75ms | Per session |

---

## 📝 Implementation Notes

1. **Versioning**: All endpoints start with `/api/v1/`
2. **Authentication**: Bearer token in Authorization header
3. **Rate Limiting**: 1000 requests/min per API key
4. **Compression**: gzip for responses > 1KB
5. **CORS**: Configured for specific domains
6. **Monitoring**: X-Request-ID header for tracing

---

## 🔐 Security Considerations

1. **Input Validation**: 
   - Max query length: 100 chars
   - Max items per request: 50
   - Max page size: 50

2. **PII Protection**:
   - No PII in URLs
   - Session IDs are opaque
   - User context is minimal

3. **Rate Limiting by Endpoint**:
   - Search: 100/min
   - Cart: 200/min
   - Chat: 50/min
   - Pricing: 500/min