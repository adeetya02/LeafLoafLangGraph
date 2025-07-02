# Graphiti Personalization Implementation Plan

## Executive Summary
Implement personalization as a feature suite behind the existing `/api/v1/search` endpoint with user-level controls and privacy-first design.

## Current State Analysis

### Existing Components
1. **Working**:
   - Multi-agent architecture (Supervisor → Search/Order → Response Compiler)
   - Weaviate product search
   - Basic Graphiti integration in supervisor
   - Session-based cart management
   - Spanner Graph infrastructure

2. **Needs Enhancement**:
   - Supervisor needs full Graphiti context loading
   - Product search needs personalization logic
   - Order agent needs "my usual" understanding
   - Response compiler needs to merge personalization data

3. **Technical Debt**:
   - Gemma intent recognition (update_order not working)
   - Complex codebase needs feature-based refactoring
   - Inconsistent error handling

## Implementation Roadmap

### Day 1-2: Foundation
**Goal**: Set up user preferences and feature flag system

1. **Create User Preference Schema**
   ```python
   # src/models/user_preferences.py
   class UserPreferences(BaseModel):
       user_id: str
       personalization_enabled: bool = True
       features: Dict[str, bool]
       privacy_settings: Dict[str, Any]
       created_at: datetime
       updated_at: datetime
   ```

2. **Implement Feature Flag Service**
   ```python
   # src/services/feature_flags.py
   class PersonalizationFeatures:
       SMART_RANKING = "smart_ranking"
       USUAL_ORDERS = "usual_orders"
       REORDER_REMINDERS = "reorder_reminders"
       # ... etc
   ```

3. **Update API Models (OpenAPI)**
   - Enhance SearchRequest with personalization options
   - Enhance SearchResponse with personalization results
   - Maintain backward compatibility

### Day 3-4: Graphiti Enhancement
**Goal**: Full context extraction and learning

1. **Enhance Supervisor Agent**
   ```python
   # src/agents/supervisor.py
   - Load user preferences
   - Extract full Graphiti context
   - Pass personalization flags to other agents
   ```

2. **Implement Pattern Extractors**
   ```python
   # src/memory/pattern_extractors.py
   - Purchase frequency analyzer
   - Dietary preference detector
   - Household composition inferrer
   ```

3. **Create Learning Pipeline**
   ```python
   # src/services/learning_pipeline.py
   - Real-time pattern updates
   - Async processing
   - Error resilience
   ```

### Day 5-6: Smart Search
**Goal**: Personalized product search

1. **Enhance Product Search Agent**
   ```python
   # src/agents/product_search.py
   - Receive personalization context
   - Apply user preferences to search
   - Re-rank based on purchase history
   ```

2. **Implement Ranking Algorithm**
   ```python
   # src/services/personalized_ranker.py
   - Combine Weaviate scores with user affinity
   - Boost frequently purchased
   - Apply dietary filters
   ```

3. **Add Complementary Products**
   ```python
   # src/services/complementary_products.py
   - Query Spanner for relationships
   - Filter by user patterns
   - Rank by relevance
   ```

### Day 7-8: "My Usual" Feature
**Goal**: Implement usual order detection and compilation

1. **Enhance Order Agent**
   ```python
   # src/agents/order_agent.py
   - Detect "usual" intent variations
   - Build personalized order
   - Learn from modifications
   ```

2. **Create Usual Order Service**
   ```python
   # src/services/usual_order.py
   - Aggregate frequent purchases
   - Calculate typical quantities
   - Handle variations
   ```

3. **Implement Reorder Detection**
   ```python
   # src/services/reorder_analyzer.py
   - Calculate purchase cycles
   - Generate timely suggestions
   - Respect user preferences
   ```

### Day 9-10: Response Integration
**Goal**: Unified response with all personalization data

1. **Enhance Response Compiler**
   ```python
   # src/agents/response_compiler.py
   - Merge search results with personalization
   - Add usual items section
   - Include reorder suggestions
   ```

2. **Implement Response Formatter**
   ```python
   # src/services/response_formatter.py
   - Clean, consistent format
   - Respect feature flags
   - Maintain OpenAPI compliance
   ```

3. **Add Performance Monitoring**
   ```python
   # src/services/performance_monitor.py
   - Track personalization impact
   - Monitor latency
   - Alert on degradation
   ```

## Testing Strategy

### Unit Tests (Continuous)
```python
# tests/personalization/
- test_feature_flags.py
- test_pattern_extraction.py
- test_ranking_algorithm.py
- test_usual_orders.py
```

### Integration Tests (Daily)
```python
# tests/integration/
- test_personalized_search_flow.py
- test_my_usual_flow.py
- test_reorder_suggestions.py
- test_privacy_controls.py
```

### Load Tests (Weekly)
```python
# tests/performance/
- test_response_time_with_personalization.py
- test_concurrent_users.py
- test_spanner_query_performance.py
```

## Rollout Strategy

### Week 1: Internal Alpha
- Enable for team members only
- Full feature testing
- Performance baseline

### Week 2: Limited Beta (5% users)
- Gradual rollout
- A/B testing setup
- Monitoring dashboard

### Week 3: Extended Beta (25% users)
- Feature refinement based on feedback
- Load testing at scale
- Documentation updates

### Week 4: General Availability
- Full rollout with feature flags
- Marketing communications
- Success metrics tracking

## Risk Mitigation

### Technical Risks
1. **Performance degradation**
   - Mitigation: Feature flags for instant rollback
   - Monitoring: Real-time latency tracking

2. **Data consistency**
   - Mitigation: Transactional updates
   - Validation: Regular consistency checks

3. **Privacy concerns**
   - Mitigation: Granular user controls
   - Compliance: GDPR/CCPA adherence

### Operational Risks
1. **Increased complexity**
   - Mitigation: Comprehensive documentation
   - Training: Team knowledge sharing

2. **Support burden**
   - Mitigation: Self-service controls
   - Tools: Admin dashboard

## Success Criteria

### Week 1
- [ ] All unit tests passing
- [ ] Basic personalization working
- [ ] Response time <300ms maintained

### Week 2
- [ ] "My usual" feature functional
- [ ] 90% accuracy on reorder predictions
- [ ] Positive beta user feedback

### Month 1
- [ ] 15% increase in basket size
- [ ] 20% increase in user engagement
- [ ] <1% increase in error rate

## Next Steps

1. **Today**: Review and approve plan
2. **Tomorrow**: Start foundation implementation
3. **This Week**: Complete Phase 1 (Foundation + Graphiti)
4. **Next Week**: Complete Phase 2 (Search + Orders)
5. **Following Week**: Testing and rollout preparation

---

**Note**: This plan prioritizes implementing personalization first, with refactoring to follow after features are stable and working. This approach allows us to deliver value quickly while maintaining system stability.