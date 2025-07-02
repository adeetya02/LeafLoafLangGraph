# LeafLoaf OpenAPI v2 Specification

## Overview

This document presents the recommended OpenAPI specification for LeafLoaf v2, implementing a nested feature architecture that supports extensibility while maintaining backward compatibility.

---

## OpenAPI 3.1.0 Specification

```yaml
openapi: 3.1.0
info:
  title: LeafLoaf Grocery API
  version: 2.0.0
  description: |
    AI-powered grocery shopping with personalization.
    
    ## Features
    - 🔍 Intelligent product search
    - 🛒 Cart management
    - 🧠 Personalization (Graphiti-powered)
    - 🤖 ML recommendations (coming soon)
    - 🎙️ Voice interface
    - 🏷️ Promotions
    
    ## API Design
    This API uses a nested feature architecture where core functionality
    is always available and additional features are conditionally included
    based on user preferences and system capabilities.

servers:
  - url: https://api.leafloaf.com/v2
    description: Production
  - url: https://staging-api.leafloaf.com/v2
    description: Staging

paths:
  /chat:
    post:
      summary: Unified chat interface
      description: |
        Main endpoint for all interactions. Handles search, orders,
        questions, and conversational flows.
      operationId: chat
      tags:
        - Core
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ChatRequest'
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ChatResponse'
        '400':
          $ref: '#/components/responses/BadRequest'
        '500':
          $ref: '#/components/responses/ServerError'

  /health:
    get:
      summary: Health check
      tags:
        - System
      responses:
        '200':
          description: System health status
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/HealthResponse'

components:
  schemas:
    # Request Schemas
    ChatRequest:
      type: object
      required: [message]
      properties:
        message:
          type: string
          description: User's natural language input
          example: "I need organic milk and eggs"
        context:
          $ref: '#/components/schemas/RequestContext'
        options:
          $ref: '#/components/schemas/RequestOptions'

    RequestContext:
      type: object
      description: Request context for personalization
      properties:
        user_id:
          type: string
          description: User identifier
          example: "user_123"
        session_id:
          type: string
          description: Session identifier for conversation continuity
          example: "session_abc123"
        location:
          type: object
          properties:
            store_id:
              type: string
            coordinates:
              type: object
              properties:
                lat:
                  type: number
                lng:
                  type: number

    RequestOptions:
      type: object
      description: Request processing options
      properties:
        limit:
          type: integer
          minimum: 1
          maximum: 50
          default: 10
        filters:
          type: object
          properties:
            dietary:
              type: array
              items:
                type: string
                enum: [organic, vegan, gluten_free, kosher, halal]
            price_range:
              type: object
              properties:
                min:
                  type: number
                max:
                  type: number
            brands:
              type: array
              items:
                type: string
        feature_flags:
          type: object
          description: Override feature enablement
          additionalProperties:
            type: boolean

    # Response Schemas
    ChatResponse:
      type: object
      required: [success, request_id, timestamp, core]
      properties:
        success:
          type: boolean
          description: Whether the request was processed successfully
        request_id:
          type: string
          description: Unique request identifier
          example: "req_abc123"
        timestamp:
          type: string
          format: date-time
          description: Response timestamp
        core:
          $ref: '#/components/schemas/CoreResponse'
        features:
          $ref: '#/components/schemas/Features'
        extensions:
          $ref: '#/components/schemas/Extensions'
        _metadata:
          $ref: '#/components/schemas/ResponseMetadata'

    CoreResponse:
      type: object
      required: [intent, message]
      description: Core response data always included
      properties:
        intent:
          type: string
          enum: [search, order, help, greeting, unknown]
          description: Detected user intent
        confidence:
          type: number
          minimum: 0
          maximum: 1
          description: Intent confidence score
        message:
          type: string
          description: Natural language response
          example: "I found 5 organic milk options for you"
        products:
          type: array
          description: Product search results (when intent=search)
          items:
            $ref: '#/components/schemas/Product'
        order:
          description: Order information (when intent=order)
          $ref: '#/components/schemas/OrderInfo'
        suggestions:
          type: array
          description: Alternative query suggestions
          items:
            type: string

    Features:
      type: object
      description: Optional features based on user preferences and system capabilities
      properties:
        personalization:
          $ref: '#/components/schemas/PersonalizationFeature'
        ml_recommendations:
          $ref: '#/components/schemas/MLRecommendationsFeature'
        voice:
          $ref: '#/components/schemas/VoiceFeature'
        promotions:
          $ref: '#/components/schemas/PromotionsFeature'

    PersonalizationFeature:
      type: object
      properties:
        enabled:
          type: boolean
          description: Whether personalization is active
        version:
          type: string
          description: Feature version
          example: "1.0"
        confidence:
          type: number
          minimum: 0
          maximum: 1
          description: Overall personalization confidence
        graphiti:
          type: object
          description: Graphiti-powered memory features
          properties:
            usual_items:
              type: array
              description: Frequently purchased items
              items:
                type: object
                required: [product_id, name, frequency]
                properties:
                  product_id:
                    type: string
                  name:
                    type: string
                  usual_quantity:
                    type: integer
                  frequency:
                    type: string
                    enum: [weekly, biweekly, monthly]
                  confidence:
                    type: number
                  last_purchased:
                    type: string
                    format: date
            reorder_suggestions:
              type: array
              description: Items due for reorder
              items:
                type: object
                required: [product_id, name, urgency]
                properties:
                  product_id:
                    type: string
                  name:
                    type: string
                  days_since_last_order:
                    type: integer
                  usual_cycle_days:
                    type: integer
                  urgency:
                    type: string
                    enum: [due_now, due_soon, upcoming]
                  message:
                    type: string
            detected_preferences:
              type: array
              description: Learned user preferences
              items:
                type: object
                properties:
                  type:
                    type: string
                    enum: [dietary, brand, price, category]
                  value:
                    type: string
                  confidence:
                    type: number
        applied_features:
          type: array
          description: Which personalization features were applied
          items:
            type: string
            enum: [
              smart_ranking,
              usual_orders,
              reorder_reminders,
              dietary_filters,
              budget_awareness,
              quantity_memory,
              seasonal_patterns
            ]
        impact_metrics:
          type: object
          description: How personalization affected results
          properties:
            products_reranked:
              type: integer
            filters_applied:
              type: integer
            time_saved_estimate:
              type: string

    MLRecommendationsFeature:
      type: object
      properties:
        enabled:
          type: boolean
        version:
          type: string
        recommendations:
          type: array
          items:
            type: object
            properties:
              type:
                type: string
                enum: [complementary, trending, seasonal, personalized]
              products:
                type: array
                items:
                  $ref: '#/components/schemas/Product'
              reason:
                type: string
              confidence:
                type: number

    VoiceFeature:
      type: object
      properties:
        enabled:
          type: boolean
        session_active:
          type: boolean
        voice_response:
          type: object
          properties:
            text:
              type: string
              description: Text to be spoken
            audio_url:
              type: string
              description: Pre-generated audio URL
            ssml:
              type: string
              description: SSML markup for advanced speech
        voice_settings:
          type: object
          properties:
            voice_id:
              type: string
            speed:
              type: number
            emotion:
              type: string

    PromotionsFeature:
      type: object
      properties:
        enabled:
          type: boolean
        applicable_promotions:
          type: array
          items:
            type: object
            properties:
              id:
                type: string
              type:
                type: string
                enum: [percentage, fixed, bogo, bundle]
              description:
                type: string
              products:
                type: array
                items:
                  type: string
              discount_amount:
                type: number
              requirements:
                type: object
        cart_savings:
          type: object
          properties:
            total_savings:
              type: number
            savings_percentage:
              type: number
            applied_promotions:
              type: array
              items:
                type: string

    Extensions:
      type: object
      description: Third-party or experimental features
      additionalProperties: true

    ResponseMetadata:
      type: object
      description: Response metadata and debugging info
      properties:
        version:
          type: string
          description: API version
        performance:
          type: object
          properties:
            total_ms:
              type: number
              description: Total response time
            breakdown:
              type: object
              description: Component timing breakdown
              additionalProperties:
                type: number
        agents_used:
          type: array
          description: Which agents processed this request
          items:
            type: string
        debug:
          type: object
          properties:
            trace_id:
              type: string
            langsmith_url:
              type: string
            reasoning_steps:
              type: array
              items:
                type: string

    # Data Models
    Product:
      type: object
      required: [id, name, price]
      properties:
        id:
          type: string
          description: Product identifier
        sku:
          type: string
          description: Stock keeping unit
        name:
          type: string
          description: Product name
        description:
          type: string
        price:
          type: number
          description: Current price
        unit:
          type: string
          description: Pricing unit
          example: "per lb"
        category:
          type: object
          properties:
            id:
              type: string
            name:
              type: string
            path:
              type: array
              items:
                type: string
        brand:
          type: object
          properties:
            id:
              type: string
            name:
              type: string
        attributes:
          type: object
          properties:
            dietary:
              type: array
              items:
                type: string
            organic:
              type: boolean
            local:
              type: boolean
            seasonal:
              type: boolean
        availability:
          type: object
          properties:
            in_stock:
              type: boolean
            quantity:
              type: integer
            locations:
              type: array
              items:
                type: string
        images:
          type: array
          items:
            type: object
            properties:
              url:
                type: string
              size:
                type: string
                enum: [thumb, small, medium, large]
        metadata:
          type: object
          properties:
            relevance_score:
              type: number
            personalization_boost:
              type: number
            ranking_factors:
              type: array
              items:
                type: string

    OrderInfo:
      type: object
      properties:
        order_id:
          type: string
        status:
          type: string
          enum: [draft, confirmed, processing, ready, delivered]
        items:
          type: array
          items:
            type: object
            properties:
              product_id:
                type: string
              name:
                type: string
              quantity:
                type: number
              unit:
                type: string
              price:
                type: number
              subtotal:
                type: number
        totals:
          type: object
          properties:
            subtotal:
              type: number
            tax:
              type: number
            delivery:
              type: number
            discounts:
              type: number
            total:
              type: number
        delivery:
          type: object
          properties:
            method:
              type: string
              enum: [pickup, delivery]
            scheduled_time:
              type: string
              format: date-time
            address:
              type: object

    HealthResponse:
      type: object
      required: [status, timestamp]
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy]
        timestamp:
          type: string
          format: date-time
        version:
          type: string
        services:
          type: object
          properties:
            weaviate:
              $ref: '#/components/schemas/ServiceHealth'
            redis:
              $ref: '#/components/schemas/ServiceHealth'
            graphiti:
              $ref: '#/components/schemas/ServiceHealth'
            ml_service:
              $ref: '#/components/schemas/ServiceHealth'

    ServiceHealth:
      type: object
      properties:
        status:
          type: string
          enum: [healthy, degraded, unhealthy, disabled]
        latency_ms:
          type: number
        error:
          type: string

  responses:
    BadRequest:
      description: Invalid request
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
              details:
                type: object

    ServerError:
      description: Server error
      content:
        application/json:
          schema:
            type: object
            properties:
              error:
                type: string
              request_id:
                type: string

  securitySchemes:
    ApiKey:
      type: apiKey
      in: header
      name: X-API-Key
    OAuth2:
      type: oauth2
      flows:
        authorizationCode:
          authorizationUrl: https://auth.leafloaf.com/oauth/authorize
          tokenUrl: https://auth.leafloaf.com/oauth/token
          scopes:
            read: Read access
            write: Write access
            admin: Admin access

security:
  - ApiKey: []
  - OAuth2: [read, write]
```

---

## Key Design Decisions

### 1. Single Unified Endpoint
- `/chat` handles all interactions
- Reduces complexity
- Better for conversational AI

### 2. Nested Feature Structure
- Core functionality always present
- Features conditionally included
- Clear separation of concerns

### 3. Extensibility
- `extensions` object for future features
- Feature versioning
- No breaking changes

### 4. Rich Metadata
- Performance tracking
- Debug information
- Feature impact metrics

### 5. Type Safety
- Comprehensive schemas
- Enum constraints
- Required vs optional clarity

---

## Migration Path

### Phase 1: Parallel APIs
```
/api/v1/search (existing)
/api/v2/chat   (new)
```

### Phase 2: Feature Parity
- Implement all v1 features in v2
- Add new nested features
- Client SDK updates

### Phase 3: Deprecation
- Mark v1 as deprecated
- 6-month migration window
- Sunset v1

---

## Client SDK Example

```typescript
// TypeScript SDK generated from OpenAPI
import { LeafLoafClient } from '@leafloaf/sdk';

const client = new LeafLoafClient({
  apiKey: 'your-api-key',
  version: 'v2'
});

// Type-safe request
const response = await client.chat({
  message: "I need organic milk",
  context: {
    user_id: "user_123",
    session_id: "session_abc"
  },
  options: {
    filters: {
      dietary: ["organic"]
    }
  }
});

// Type-safe feature access
if (response.features?.personalization?.enabled) {
  const usualItems = response.features.personalization.graphiti.usual_items;
  // TypeScript knows the structure
}
```

---

## Benefits

1. **Developer Experience**
   - Clear API structure
   - Excellent documentation
   - Type-safe SDKs

2. **Extensibility**
   - Easy to add features
   - No breaking changes
   - Plugin architecture

3. **Performance**
   - Conditional loading
   - Smaller payloads
   - Better caching

4. **Testing**
   - Clear contracts
   - Mockable features
   - BDD friendly

---

*This OpenAPI specification provides a modern, extensible API design for LeafLoaf v2.*