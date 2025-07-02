# LeafLoaf API Design Specification

## 🎯 Architecture Overview

### API Flow
```
User Request → API Endpoint → Supervisor → Agent(s) → Response Compiler → Standardized Response
```

### Key Principles
1. **Separate Endpoints** for different operations (search, cart, order)
2. **Standardized Responses** across all endpoints
3. **Response Compiler** only for multi-agent coordination
4. **Direct responses** for single operations (cart add/remove)

## 📋 API Endpoints

### 1. Product Search
**POST** `/api/v1/search`

**Purpose**: Search products across all suppliers
**Flow**: User → Supervisor → Search Agent → Response Compiler → Response

```json
// Request
{
  "query": "organic rice",
  "filters": {
    "category": "Rice & Grains",
    "priceRange": {"min": 10, "max": 50},
    "dietary": ["organic", "gluten-free"],
    "suppliers": ["Laxmi", "Baldor"]
  },
  "sort": "price_asc",
  "limit": 20,
  "offset": 0,
  "session_id": "user123_session456"
}

// Response
{
  "status": "success",
  "data": {
    "products": [
      {
        "id": "uuid",
        "sku": "LX_RICE_001",
        "name": "Laxmi Organic Basmati Rice",
        "description": "Premium organic basmati rice",
        "category": "Rice & Grains",
        "supplier": "Laxmi",
        "brand": "Laxmi",
        "price": {
          "wholesale": 35.00,
          "retail": 35.00,  // No markup in data layer
          "currency": "USD",
          "unit": "case"
        },
        "pack_info": {
          "size": "10 LB",
          "units_per_case": 1,
          "case_weight": 10.0
        },
        "attributes": {
          "cuisine": "Indian",
          "isOrganic": true,
          "isGlutenFree": true,
          "isNonGMO": true,
          "isVegetarian": true
        },
        "availability": {
          "inStock": true,
          "quantity": 100
        },
        "score": 0.95  // Search relevance
      }
    ],
    "facets": {
      "categories": {"Rice & Grains": 45, "Dal & Lentils": 23},
      "suppliers": {"Laxmi": 68, "Vistar": 12},
      "priceRanges": {"0-25": 20, "25-50": 35, "50+": 13},
      "attributes": {"organic": 15, "gluten-free": 42}
    },
    "pagination": {
      "total": 68,
      "limit": 20,
      "offset": 0,
      "hasMore": true
    }
  },
  "meta": {
    "query": {
      "original": "organic rice",
      "enhanced": "organic rice gluten-free",
      "intent": "product_search",
      "confidence": 0.95
    },
    "performance": {
      "totalMs": 245,
      "breakdown": {
        "supervisor": 45,
        "searchAgent": 180,
        "responseCompiler": 20
      }
    },
    "session": {
      "id": "user123_session456",
      "context": ["previous_search: dal", "cart_items: 2"]
    }
  }
}
```

### 2. Cart Operations
**POST** `/api/v1/cart/{action}`

**Purpose**: Direct cart manipulations
**Flow**: User → Cart Service → Response (No supervisor needed)

**Actions**: `add`, `remove`, `update`, `clear`, `get`

```json
// Request - Add to Cart
POST /api/v1/cart/add
{
  "product_id": "uuid",
  "sku": "LX_RICE_001",
  "quantity": 2,
  "session_id": "user123_session456"
}

// Response
{
  "status": "success",
  "data": {
    "cart": {
      "id": "cart_789",
      "items": [
        {
          "product_id": "uuid",
          "sku": "LX_RICE_001",
          "name": "Laxmi Organic Basmati Rice",
          "quantity": 2,
          "price": 35.00,
          "subtotal": 70.00
        }
      ],
      "summary": {
        "itemCount": 2,
        "uniqueItems": 1,
        "subtotal": 70.00,
        "tax": 0.00,
        "shipping": 0.00,
        "total": 70.00
      }
    },
    "addedItem": {
      "sku": "LX_RICE_001",
      "quantity": 2
    }
  },
  "meta": {
    "performance": {
      "totalMs": 45
    }
  }
}

// Request - Update Quantity
POST /api/v1/cart/update
{
  "product_id": "uuid",
  "quantity": 5,
  "session_id": "user123_session456"
}

// Request - Get Cart
POST /api/v1/cart/get
{
  "session_id": "user123_session456"
}
```

### 3. Natural Language Processing
**POST** `/api/v1/chat`

**Purpose**: Handle complex natural language requests
**Flow**: User → Supervisor → Multiple Agents → Response Compiler → Response

```json
// Request
{
  "message": "I need rice and dal for 20 people, add to cart",
  "session_id": "user123_session456",
  "context": {
    "user_type": "restaurant",
    "location": "10001"
  }
}

// Response
{
  "status": "success",
  "data": {
    "interpretation": {
      "intent": "search_and_add_to_cart",
      "entities": {
        "products": ["rice", "dal"],
        "quantity_context": "for 20 people",
        "action": "add to cart"
      },
      "confidence": 0.92
    },
    "products": [
      // Product results from search
    ],
    "cart": {
      // Updated cart if items were added
    },
    "message": "I found 5 rice and 3 dal products suitable for serving 20 people. I've added Laxmi Basmati Rice (2 x 10lb bags) and Toor Dal (1 x 4lb bag) to your cart.",
    "suggestions": [
      "Would you like to see more options?",
      "Add some vegetables?",
      "View cooking instructions?"
    ]
  },
  "meta": {
    "agents_executed": ["supervisor", "search", "cart", "response_compiler"],
    "performance": {
      "totalMs": 380,
      "breakdown": {
        "supervisor": 50,
        "searchAgent": 200,
        "cartAgent": 80,
        "responseCompiler": 50
      }
    }
  }
}
```

### 4. Order Management
**POST** `/api/v1/order/{action}`

**Actions**: `create`, `get`, `update`, `cancel`

```json
// Request - Create Order
POST /api/v1/order/create
{
  "cart_id": "cart_789",
  "delivery": {
    "address": "123 Main St, New York, NY 10001",
    "date": "2025-06-27",
    "time_slot": "10:00-12:00"
  },
  "payment": {
    "method": "invoice",
    "terms": "net30"
  },
  "session_id": "user123_session456"
}

// Response
{
  "status": "success",
  "data": {
    "order": {
      "id": "order_12345",
      "status": "confirmed",
      "items": [...],
      "totals": {
        "subtotal": 250.00,
        "tax": 21.25,
        "delivery": 15.00,
        "total": 286.25
      },
      "delivery": {...},
      "estimatedDelivery": "2025-06-27T10:00:00Z"
    }
  }
}
```

### 5. Pricing Service
**POST** `/api/v1/pricing/calculate`

**Purpose**: Real-time price calculation with user context
**Flow**: Direct service call (No agents needed)

```json
// Request
{
  "items": [
    {"sku": "LX_RICE_001", "quantity": 2},
    {"sku": "LX_DAL_001", "quantity": 1}
  ],
  "user": {
    "type": "restaurant",
    "tier": "gold",
    "location": "10001"
  },
  "promo_codes": ["SAVE10"]
}

// Response
{
  "status": "success",
  "data": {
    "pricing": {
      "items": [
        {
          "sku": "LX_RICE_001",
          "quantity": 2,
          "basePrice": 35.00,
          "userPrice": 31.50,  // With tier discount
          "subtotal": 63.00
        }
      ],
      "summary": {
        "subtotal": 94.50,
        "discounts": [
          {"type": "tier", "amount": 9.45},
          {"type": "promo", "amount": 8.51}
        ],
        "total": 76.54
      }
    }
  },
  "meta": {
    "performance": {
      "totalMs": 25,
      "cacheHit": true
    }
  }
}
```

## 🔄 Response Compiler Role

### When Response Compiler is Used:
1. **Multi-agent coordination** - Search + Cart operations
2. **Natural language responses** - Converting agent outputs to human-friendly text
3. **Context synthesis** - Combining results from multiple sources
4. **ML recommendations** - Merging search results with recommendations

### When Response Compiler is NOT Used:
1. **Direct API calls** - Cart add/remove/update
2. **Simple lookups** - Get cart, get order
3. **Pricing calculations** - Direct service response
4. **Health checks** - System status

## 📊 Standardized Error Response

```json
{
  "status": "error",
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Product with SKU 'ABC123' not found",
    "details": {
      "sku": "ABC123",
      "suggestion": "Did you mean 'ABC124'?"
    }
  },
  "meta": {
    "timestamp": "2025-06-26T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

## 🎯 Implementation Guidelines

### 1. Endpoint Separation
```python
# routes.py
app.include_router(search_router, prefix="/api/v1/search")
app.include_router(cart_router, prefix="/api/v1/cart")
app.include_router(order_router, prefix="/api/v1/order")
app.include_router(chat_router, prefix="/api/v1/chat")
app.include_router(pricing_router, prefix="/api/v1/pricing")
```

### 2. Response Models (Pydantic)
```python
class StandardResponse(BaseModel):
    status: Literal["success", "error"]
    data: Optional[Dict[str, Any]]
    error: Optional[ErrorDetail]
    meta: MetaInfo

class MetaInfo(BaseModel):
    performance: PerformanceMetrics
    session: Optional[SessionInfo]
    query: Optional[QueryInfo]
```

### 3. Performance Tracking
```python
@track_performance
async def search_products(request: SearchRequest) -> StandardResponse:
    with timer("total"):
        with timer("supervisor"):
            intent = await analyze_intent(request.query)
        
        with timer("search"):
            results = await search_agent.execute(intent)
        
        with timer("response_compiler"):
            response = await compile_response(results)
    
    return StandardResponse(
        status="success",
        data=response,
        meta={"performance": get_timings()}
    )
```

## 🚀 Benefits of This Design

1. **Clear Separation** - Each endpoint has a specific purpose
2. **Predictable Responses** - Frontend knows exactly what to expect
3. **Performance Visibility** - Every response includes timing breakdown
4. **Flexible Integration** - Can use endpoints independently or combined
5. **Scalable** - Can optimize each endpoint separately
6. **Testable** - Clear contracts for testing

## 📝 Migration Path

1. **Phase 1**: Implement standardized responses for existing endpoints
2. **Phase 2**: Separate cart operations from chat endpoint
3. **Phase 3**: Add pricing service endpoint
4. **Phase 4**: Implement full OpenAPI spec with Swagger UI
5. **Phase 5**: Add response caching and optimization