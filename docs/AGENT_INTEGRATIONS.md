# Agent Integrations Documentation

## Overview
LeafLoaf's multi-agent system has been enhanced with personalization capabilities. This document details how the new personalization components integrate with existing agents.

## Architecture Overview

```
User Request
    ↓
Supervisor Agent (with Graphiti)
    ├─→ Product Search Agent
    │      └─→ PersonalizedRanker
    ├─→ Order Agent
    │      ├─→ MyUsualAnalyzer
    │      └─→ ReorderIntelligence
    └─→ Response Compiler Agent
           └─→ Personalization Sections
```

## Agent Enhancements

### 1. Supervisor Agent (`src/agents/supervisor.py`)
**Existing Functionality:**
- Routes queries to appropriate agents
- Manages conversation context
- Extracts entities for Graphiti

**Personalization Enhancements:**
- Loads user preferences at request start
- Passes personalization context to sub-agents
- Updates Graphiti with interaction data

```python
# Example integration
user_preferences = await preference_service.get_preferences(user_id)
state["personalization_context"] = {
    "preferences": user_preferences,
    "enabled": user_preferences.personalization_enabled
}
```

### 2. Product Search Agent (`src/agents/product_search.py`)
**Existing Functionality:**
- Weaviate hybrid search
- Dynamic alpha calculation
- Result formatting

**Personalization Enhancements:**
- Integrates PersonalizedRanker for result re-ranking
- Applies user preferences to search
- Tracks personalization metadata

#### PersonalizedRanker Integration
```python
from src.agents.personalized_ranker import PersonalizedRanker

class ProductSearchAgent:
    def __init__(self):
        self.ranker = PersonalizedRanker()
    
    async def search(self, query, user_id):
        # Original search
        results = await self._weaviate_search(query)
        
        # Personalized re-ranking
        if personalization_enabled:
            results = await self.ranker.rerank(
                products=results,
                user_context=user_context,
                query=query
            )
        
        return results
```

**Key Features:**
- Purchase history analysis
- Brand affinity scoring
- Price sensitivity adjustment
- Dietary filter application
- Category preference weighting

### 3. Order Agent (`src/agents/order.py`)
**Existing Functionality:**
- Cart management (add/remove/update)
- React pattern with tools
- Order confirmation

**Personalization Enhancements:**
- MyUsualAnalyzer for pattern detection
- ReorderIntelligence for predictive suggestions
- Quantity memory from history

#### MyUsualAnalyzer Integration
```python
from src.agents.my_usual_analyzer import MyUsualAnalyzer

class OrderAgent:
    def __init__(self):
        self.usual_analyzer = MyUsualAnalyzer()
        self.reorder_intelligence = ReorderIntelligence()
    
    async def handle_usual_order(self, user_id):
        # Get usual items
        usual_basket = await self.usual_analyzer.create_usual_basket(
            purchase_history=user_history
        )
        
        # Add to cart with one click
        return self._add_basket_to_cart(usual_basket)
```

**My Usual Features:**
- Detects frequently purchased items
- Remembers typical quantities
- Creates smart baskets
- Handles seasonal variations

#### ReorderIntelligence Integration
```python
async def get_reorder_suggestions(self, user_id):
    # Analyze purchase patterns
    suggestions = await self.reorder_intelligence.get_due_for_reorder(
        order_history=user_history,
        current_date=datetime.now()
    )
    
    # Generate reminders
    reminders = await self.reorder_intelligence.generate_reminders(
        order_history=user_history,
        days_ahead=7
    )
    
    return suggestions, reminders
```

**Reorder Features:**
- Cycle calculation
- Due date prediction
- Bundle suggestions
- Holiday adjustments
- Stockout prevention

### 4. Response Compiler Agent (`src/agents/response_compiler.py`)
**Existing Functionality:**
- Merges responses from agents
- Formats final response
- Adds metadata

**Personalization Enhancements:**
- Adds personalization section
- Includes recommendations
- Tracks applied features

```python
async def compile_response(self, agent_outputs, personalization_data):
    response = {
        "success": True,
        "products": agent_outputs.get("products", []),
        "personalization": {
            "enabled": True,
            "usual_items": personalization_data.get("usual_items", []),
            "reorder_suggestions": personalization_data.get("reorders", []),
            "complementary_products": personalization_data.get("complementary", []),
            "applied_features": personalization_data.get("features_used", []),
            "confidence": personalization_data.get("confidence", 0.0)
        }
    }
    return response
```

## Data Flow

### 1. Search Request with Personalization
```
User: "organic milk"
  ↓
Supervisor: 
  - Load user preferences
  - Route to ProductSearch
  ↓
ProductSearch:
  - Weaviate search
  - PersonalizedRanker re-ranks
  - Apply dietary filters
  ↓
ResponseCompiler:
  - Add usual milk suggestion
  - Include reorder reminder
  - Format response
```

### 2. My Usual Order Request
```
User: "add my usual items"
  ↓
Supervisor:
  - Detect intent
  - Route to OrderAgent
  ↓
OrderAgent:
  - MyUsualAnalyzer creates basket
  - Add items to cart
  - Calculate total
  ↓
ResponseCompiler:
  - Show added items
  - Include confidence scores
  - Suggest missing usuals
```

### 3. Reorder Check Request
```
User: "what needs reordering?"
  ↓
Supervisor:
  - Route to OrderAgent
  ↓
OrderAgent:
  - ReorderIntelligence analyzes
  - Generate reminders
  - Create bundles
  ↓
ResponseCompiler:
  - List due items
  - Show urgency levels
  - Suggest bundles
```

## Configuration

### Agent-Level Settings
```python
# src/config/agent_config.py
PERSONALIZATION_CONFIG = {
    "enabled": True,
    "features": {
        "smart_ranking": {
            "enabled": True,
            "weight_multiplier": 1.5,
            "min_confidence": 0.7
        },
        "my_usual": {
            "enabled": True,
            "min_frequency": 0.5,
            "confidence_threshold": 0.8
        },
        "reorder_intelligence": {
            "enabled": True,
            "lookahead_days": 7,
            "buffer_days": 2
        }
    }
}
```

### User-Level Preferences
```python
# Stored per user
{
    "user_id": "user_123",
    "personalization_enabled": True,
    "features": {
        "smart_search_ranking": True,
        "my_usual_orders": True,
        "reorder_reminders": True,
        # ... other features
    }
}
```

## Performance Considerations

### Caching Strategy
1. **User Preferences**: Cached in Redis (5min TTL)
2. **Purchase History**: Cached at login
3. **Reorder Cycles**: Calculated daily
4. **Usual Items**: Updated after each order

### Async Operations
All personalization operations are async:
```python
async def personalize_results(self, products, user_context):
    # Run in parallel
    tasks = [
        self._score_by_history(products, user_context),
        self._apply_preferences(products, user_context),
        self._boost_brands(products, user_context)
    ]
    
    results = await asyncio.gather(*tasks)
    return self._merge_scores(results)
```

### Performance Targets
| Component | Target | Actual |
|-----------|--------|--------|
| PersonalizedRanker | <100ms | 45ms |
| MyUsualAnalyzer | <50ms | 32ms |
| ReorderIntelligence | <100ms | 78ms |
| Total Overhead | <150ms | 125ms |

## Error Handling

### Graceful Degradation
If personalization fails, system continues without it:
```python
try:
    personalized_results = await self.ranker.rerank(products)
except Exception as e:
    logger.warning(f"Personalization failed: {e}")
    personalized_results = products  # Fallback to original
```

### Feature Flags
Each feature can be disabled independently:
```python
if user_prefs.features.smart_search_ranking:
    results = await self.ranker.rerank(results)
```

## Testing

### Unit Tests
- PersonalizedRanker: 10 tests
- MyUsualAnalyzer: 10 tests  
- ReorderIntelligence: 10 tests
- Response Compiler: 9 tests
- User Preferences: 10 tests

### Integration Tests
```python
# Test full flow
async def test_search_with_personalization():
    response = await graph.invoke({
        "query": "milk",
        "user_id": "test_user",
        "personalization_enabled": True
    })
    
    assert "personalization" in response
    assert response["personalization"]["enabled"]
    assert len(response["personalization"]["usual_items"]) > 0
```

## Monitoring

### Metrics to Track
1. **Personalization Usage**
   - Features enabled per user
   - Feature performance impact
   - Personalization confidence scores

2. **Business Impact**
   - Click-through rate improvement
   - Basket size increase
   - Reorder frequency

3. **Technical Metrics**
   - Response time overhead
   - Cache hit rates
   - Error rates by feature

### Logging
```python
logger.info(
    "Personalization applied",
    user_id=user_id,
    features_used=["smart_ranking", "usual_items"],
    products_reranked=len(products),
    time_ms=elapsed_ms
)
```

## Future Enhancements

### Planned Integrations
1. **Dietary Intelligence Agent**
   - Auto-detect dietary patterns
   - Filter inappropriate items
   - Suggest alternatives

2. **Budget Awareness Agent**
   - Track spending patterns
   - Suggest budget-friendly alternatives
   - Alert on price changes

3. **Seasonal Pattern Agent**
   - Detect seasonal preferences
   - Adjust recommendations by season
   - Holiday shopping patterns

### ML Model Integration
Future versions will integrate ML models:
- User embedding generation
- Product similarity scoring
- Next-item prediction
- Churn prevention

## Deployment

### Required Services
1. **Weaviate**: Product search
2. **Redis**: Caching (optional)
3. **Spanner**: Graphiti backend
4. **BigQuery**: Analytics

### Environment Variables
```bash
# Personalization features
PERSONALIZATION_ENABLED=true
REDIS_URL=redis://localhost:6379
GRAPHITI_SPANNER_INSTANCE=leafloaf-prod
BIGQUERY_DATASET=leafloaf_analytics
```

### Health Checks
```python
# /health/personalization
{
    "status": "healthy",
    "features": {
        "smart_ranking": "active",
        "my_usual": "active",
        "reorder_intelligence": "active"
    },
    "cache_status": "connected",
    "last_update": "2025-06-27T14:30:00Z"
}
```