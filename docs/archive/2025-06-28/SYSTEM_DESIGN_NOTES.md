# LeafLoaf System Design Notes

## 🎯 Current Status (2025-06-25)

### ✅ Completed
1. **Multi-Agent System**: Working with LangGraph orchestration
2. **Laxmi Catalog Processing**: 259 products with full pricing extracted
3. **Cloud Storage Structure**: Organized supplier data pipeline
4. **Basic Search**: Weaviate with hybrid search (keyword + semantic)

### 🚧 Components to Design

## 1. Search Terms Architecture

### Current Issues
- Over-indexing: Too many redundant terms
- Inaccurate associations: "lentil, pulse, protein" for ALL dal products
- Missing cultural context: Hindi/regional names not included

### Proposed Search Term Categories

#### A. Product Attributes (not in description)
```python
{
    "storage": ["frozen", "fresh", "dried", "canned"],
    "dietary": ["organic", "non-gmo", "gluten-free", "vegan", "halal", "kosher"],
    "preparation": ["instant", "ready-to-eat", "pre-cooked", "raw"],
    "flavor": ["spicy", "mild", "sweet", "tangy", "savory"],
    "texture": ["crispy", "soft", "crunchy", "smooth"],
    "usage": ["breakfast", "snack", "dinner", "dessert"]
}
```

#### B. Cultural/Regional Terms
```python
{
    "indian": {
        "dal": ["daal", "dhal", "lentils"],  # Multiple spellings
        "ghee": ["clarified butter", "desi ghee"],
        "atta": ["wheat flour", "chapati flour"],
        "besan": ["gram flour", "chickpea flour"]
    },
    "korean": {
        "kimchi": ["kimchee", "fermented cabbage"],
        "gochugaru": ["korean chili flakes", "red pepper flakes"],
        "doenjang": ["soybean paste", "fermented bean paste"]
    }
}
```

#### C. Supplier-Specific Parsing Rules
- **Laxmi**: Extract pack size patterns (8X908 GM), NON-GMO indicators
- **Baldor**: Seasonality, farm location, harvest date
- **Asian suppliers**: Romanization variations, English translations

### Search Term Guidelines
1. **Maximum 10-15 terms per product** (not 50!)
2. **Only attributes NOT in description**
3. **Include cultural synonyms/spellings**
4. **Avoid generic terms** ("food", "item", "product")

---

## 2. Pricing Agent Design

### Requirements
- **<50ms latency** for price calculation
- **No pre-calculated markups** in data layer
- **Dynamic pricing** based on user segment, quantity, location

### Architecture
```
Request → Redis Cache → Pricing Agent → Response
                ↓ (miss)
           Calculate Price
                ↓
           Update Cache
```

### Pricing Factors
1. **Base wholesale price** (from catalog)
2. **User segment** (retail, restaurant, distributor)
3. **Quantity breaks** (case qty discounts)
4. **Location** (delivery zones, tax)
5. **Promotions** (active discounts)
6. **Seasonality** (produce pricing)

### Redis Cache Strategy
```python
# Cache key structure
price_key = f"price:{sku}:{user_segment}:{quantity}:{zip_code}"
# TTL: 1 hour for regular items, 15 min for produce

# Cache warming at login
user_frequent_items = get_frequent_purchases(user_id)
warm_price_cache(user_frequent_items, user_segment, location)
```

---

## 3. ML Recommendations System

### Design Principles
- **Rule-based, NO LLM** for recommendations
- **Pre-compute at login** for zero latency
- **5 products always** with smart rotation

### Recommendation Types
1. **Frequently Bought** (user history)
2. **Buy Again** (reorder reminders)
3. **Complementary** (rice → dal, pasta → sauce)
4. **Trending** (popular in user segment)
5. **Seasonal** (weather/holiday based)

### Redis Cache Structure
```python
# User recommendation cache
rec_key = f"recs:{user_id}:{session_id}"
{
    "frequently_bought": ["SKU1", "SKU2", ...],
    "buy_again": ["SKU3", "SKU4", ...],
    "complementary": {"SKU5": ["SKU6", "SKU7"]},
    "viewed_skus": set(),  # Track for diversity
    "last_refresh": timestamp
}
```

### ML Pipeline
```
Login → Fetch User History → Generate Recs → Cache in Redis
                                    ↓
                        BigQuery Analytics → Update Models
```

---

## 4. Analytics Engine

### Event Tracking
```python
# Comprehensive event schema
{
    "event_type": "search|view|cart|purchase|recommendation",
    "session_id": "uuid",
    "user_id": "user123",
    "timestamp": "2025-06-25T10:30:00Z",
    "intent": {  # From Gemma
        "raw_query": "show me organic rice",
        "classified_intent": "product_search",
        "extracted_attributes": ["organic", "rice"],
        "confidence": 0.95
    },
    "search": {
        "query": "organic rice",
        "alpha": 0.75,
        "results_count": 15,
        "clicked_position": 3,
        "latency_ms": 234
    },
    "product": {
        "sku": "LX_RICE_001",
        "category": "Rice & Grains",
        "cuisine": "Indian",
        "price_shown": 24.99,
        "position": 3
    },
    "ml_attribution": {
        "recommendation_type": "complementary",
        "algorithm": "association_rules",
        "score": 0.87
    }
}
```

### BigQuery Tables Design
```sql
-- Intent Analysis
CREATE TABLE analytics.intent_analysis (
    session_id STRING,
    query STRING,
    intent STRING,
    attributes ARRAY<STRING>,
    confidence FLOAT64,
    timestamp TIMESTAMP
)

-- Search Performance  
CREATE TABLE analytics.search_events (
    session_id STRING,
    query STRING,
    alpha FLOAT64,
    strategy STRING,  -- keyword/semantic/hybrid
    results_count INT64,
    clicked_position INT64,
    latency_ms INT64,
    timestamp TIMESTAMP
)

-- ML Recommendations
CREATE TABLE analytics.ml_recommendations (
    user_id STRING,
    session_id STRING,
    recommendation_type STRING,
    skus_shown ARRAY<STRING>,
    skus_clicked ARRAY<STRING>,
    algorithm STRING,
    timestamp TIMESTAMP
)
```

---

## 5. System Integration Points

### A. Search Flow
```
User Query → Gemma (Intent) → Search Agent → Weaviate
                ↓                   ↓
           Analytics            Redis Cache
                              (search results)
```

### B. Pricing Flow
```
Product Results → Pricing Agent → Redis Check → Calculate
                                      ↓
                                 Return Prices
```

### C. ML Flow
```
Login → ML Service → Redis Cache → Serve Recs
            ↓
       BigQuery (async update)
```

### D. Complete User Journey
```
1. User: "show me rice for biryani"
2. Gemma: {intent: "product_search", attributes: ["rice", "biryani"]}
3. Search: Hybrid search with α=0.6
4. Results: 15 products (Basmati rice prioritized)
5. Pricing: Calculate based on user segment
6. ML: Add complementary (dal, spices for biryani)
7. Analytics: Track entire flow with attribution
```

---

## 6. Performance Targets

### Latency Budget (300ms total)
- Gemma Intent: 50ms
- Search: 100ms  
- Pricing: 50ms
- ML Recs: 20ms
- Response Compile: 30ms
- Network/Other: 50ms

### Caching Strategy
1. **Search Results**: 5 min TTL
2. **Prices**: 1 hour (15 min for produce)
3. **ML Recs**: Per session
4. **User Preferences**: 24 hours

---

## 7. Next Implementation Steps

### Phase 1: Search Terms Refinement
- [ ] Audit current search terms
- [ ] Create supplier-specific parsers
- [ ] Implement cultural synonyms
- [ ] Test search accuracy

### Phase 2: Pricing Agent
- [ ] Design cache schema
- [ ] Implement pricing rules
- [ ] Add quantity breaks
- [ ] Test <50ms latency

### Phase 3: ML Recommendations  
- [ ] BigQuery table creation
- [ ] Rule engine implementation
- [ ] Redis caching layer
- [ ] A/B testing framework

### Phase 4: Analytics Engine
- [ ] Event streaming to BigQuery
- [ ] Real-time dashboards
- [ ] ML model training pipeline
- [ ] Performance monitoring

---

## 8. Key Decisions

1. **No LLM for ML recommendations** - Pure rules for speed
2. **Redis for all hot data** - Search, prices, recs
3. **BigQuery for analytics** - Not real-time queries
4. **Supplier-specific parsers** - Better data quality
5. **Comprehensive event tracking** - Full attribution

---

## 9. Open Questions

1. How to handle multi-language search? (Hindi, Korean, etc.)
2. Price refresh strategy for volatile items (produce)?
3. ML recommendation diversity vs relevance balance?
4. Search result caching invalidation strategy?
5. How to track and optimize for cart abandonment?

---

## 10. Testing Strategy

### Search Quality
- Precision/Recall metrics
- A/B test different alpha values
- User satisfaction surveys

### Performance
- Load testing (1000 concurrent users)
- Cache hit rates
- P95 latency monitoring

### ML Effectiveness
- Click-through rates
- Conversion lift
- Revenue per session

---

This document should be updated as we make design decisions and implementation progress.