# Graphiti Personalization Feature Documentation

## Overview
Graphiti Personalization transforms LeafLoaf from a generic grocery search into an intelligent, personalized shopping assistant. Each user gets a unique experience based on their preferences, patterns, and cultural context.

## Feature Architecture

### Core Components
1. **Graphiti Memory**: Real-time pattern learning and context understanding
2. **Spanner Graph**: Persistent relationship storage and pattern mining
3. **Personalization Service**: Orchestrates between memory systems
4. **Feature Flags**: User-level control over personalization features

### Single Endpoint Architecture
All personalization happens behind the existing `/api/v1/search` endpoint:
- Maintains backwards compatibility
- No client changes required
- OpenAPI 3.0 compliant
- Response compiler merges all data seamlessly

## Personalization Features

### 1. Smart Search Results
**What it does**: Re-ranks search results based on user preferences
- **Example**: Search "milk" → Shows user's preferred brand (Oatly) first
- **Toggle**: `personalization.smart_ranking`
- **Privacy**: Only uses purchase history, no PII

### 2. "My Usual" Orders
**What it does**: Understands user's regular purchases
- **Example**: "Add my usual" → Adds regular milk, bread, eggs with typical quantities
- **Toggle**: `personalization.usual_orders`
- **Learning**: Updates with each order

### 3. Reorder Reminders
**What it does**: Proactive suggestions based on purchase cycles
- **Example**: "Time to restock milk?" (knows user buys every 3 days)
- **Toggle**: `personalization.reorder_reminders`
- **Timing**: Configurable per product

### 4. Dietary Intelligence
**What it does**: Auto-filters based on dietary preferences
- **Example**: Vegan user sees only vegan products by default
- **Toggle**: `personalization.dietary_filters`
- **Detection**: Implicit from purchase patterns

### 5. Cultural Understanding
**What it does**: Understands cultural cooking patterns
- **Example**: "Sambar ingredients" → Complete ingredient list for South Indian cooking
- **Toggle**: `personalization.cultural_awareness`
- **Clusters**: Predefined + learned patterns

### 6. Smart Complementary Products
**What it does**: Suggests items frequently bought together
- **Example**: Coffee → Suggests user's usual creamer brand
- **Toggle**: `personalization.complementary_items`
- **Personalized**: Based on user's patterns, not global

### 7. Quantity Memory
**What it does**: Pre-fills typical quantities
- **Example**: Always buys 2 gallons of milk → Auto-suggests quantity: 2
- **Toggle**: `personalization.quantity_memory`
- **Editable**: User can always change

### 8. Budget Awareness
**What it does**: Respects user's price preferences by category
- **Example**: Premium coffee, budget paper products
- **Toggle**: `personalization.budget_awareness`
- **Learning**: From purchase patterns

### 9. Household Intelligence
**What it does**: Infers household composition for better suggestions
- **Example**: Baby food purchases → Suggests family-friendly items
- **Toggle**: `personalization.household_inference`
- **Privacy**: No personal data, only patterns

### 10. Seasonal Patterns
**What it does**: Anticipates seasonal needs
- **Example**: Summer → BBQ items, Winter → Soup ingredients
- **Toggle**: `personalization.seasonal_suggestions`
- **Proactive**: Suggests before user asks

## User Control Structure

```json
{
  "user_id": "user_123",
  "personalization_settings": {
    "enabled": true,  // Master toggle
    "features": {
      "smart_ranking": true,
      "usual_orders": true,
      "reorder_reminders": true,
      "dietary_filters": true,
      "cultural_awareness": true,
      "complementary_items": true,
      "quantity_memory": true,
      "budget_awareness": false,  // User opted out
      "household_inference": false,  // User opted out
      "seasonal_suggestions": true
    },
    "privacy": {
      "data_retention_days": 365,
      "allow_pattern_learning": true,
      "share_patterns_for_improvement": false
    }
  }
}
```

## API Integration

### Request Structure (OpenAPI 3.0)
```yaml
SearchRequest:
  type: object
  properties:
    query:
      type: string
      description: Search query
    user_id:
      type: string
      description: User identifier
    session_id:
      type: string
      description: Session identifier
    personalization:
      type: object
      properties:
        enabled:
          type: boolean
          default: true
        features:
          type: array
          items:
            type: string
          description: Specific features to enable for this request
```

### Response Structure
```yaml
SearchResponse:
  type: object
  properties:
    success:
      type: boolean
    products:
      type: array
      items:
        $ref: '#/components/schemas/ProductInfo'
    personalization_applied:
      type: object
      properties:
        features_used:
          type: array
          items:
            type: string
        confidence_scores:
          type: object
        usual_items:
          type: array
          items:
            $ref: '#/components/schemas/ProductInfo'
        reorder_suggestions:
          type: array
          items:
            $ref: '#/components/schemas/ReorderSuggestion'
        complementary_products:
          type: array
          items:
            $ref: '#/components/schemas/ProductInfo'
```

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] User settings schema
- [ ] Feature flag system
- [ ] Basic Graphiti integration
- [ ] Preference extraction

### Phase 2: Core Features (Week 2)
- [ ] Smart ranking
- [ ] "My usual" orders
- [ ] Reorder reminders
- [ ] Dietary filters

### Phase 3: Advanced Features (Week 3)
- [ ] Cultural understanding
- [ ] Complementary products
- [ ] Quantity memory
- [ ] Budget awareness

### Phase 4: Intelligence (Week 4)
- [ ] Household inference
- [ ] Seasonal patterns
- [ ] Predictive suggestions
- [ ] Learning optimization

## Privacy & Compliance

### Data Handling
- All personalization data encrypted at rest
- User can export their data anytime
- User can delete their data anytime
- No sharing without explicit consent

### GDPR Compliance
- Clear consent for each feature
- Granular control over data usage
- Right to be forgotten implemented
- Data portability supported

### Security
- Personalization data isolated per user
- No cross-user pattern sharing
- Audit logs for all data access
- Regular security reviews

## Performance Requirements

### Latency
- Personalization adds <50ms to response time
- Total response time remains <300ms
- Graceful degradation if systems slow

### Scalability
- Supports millions of users
- Spanner handles relationship scale
- Graphiti memory efficiently managed
- Async processing where possible

## Testing Strategy

### Unit Tests
- Each personalization feature isolated
- Toggle on/off behavior
- Privacy compliance checks

### Integration Tests
- End-to-end user journeys
- Multi-feature interactions
- Performance benchmarks

### User Acceptance Tests
- A/B testing framework
- Conversion tracking
- Satisfaction metrics

## Success Metrics

### Technical Metrics
- Response time <300ms: 99.9%
- Personalization accuracy >85%
- Feature adoption rate >60%
- System uptime >99.95%

### Business Metrics
- Basket size increase: +15%
- User retention: +20%
- Reorder rate: +25%
- Customer satisfaction: +30%

## Rollout Plan

### Week 1: Internal Testing
- Enable for employee accounts
- Monitor performance
- Gather feedback

### Week 2: Beta Users (5%)
- Gradual rollout
- A/B testing
- Performance monitoring

### Week 3: Extended Beta (25%)
- Feature refinement
- Load testing
- User feedback incorporation

### Week 4: General Availability
- Full rollout
- Marketing launch
- Success metrics tracking

## Support Documentation

### For Users
- How to enable/disable features
- Privacy controls
- Data export/deletion
- Troubleshooting guide

### For Developers
- Integration guide
- API documentation
- Performance optimization
- Debugging tools

### For Support Team
- Common issues
- Feature explanations
- Escalation procedures
- Admin tools

---

Last Updated: 2025-06-27
Version: 1.0
Status: Ready for Implementation