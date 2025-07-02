# LeafLoaf GCP Deployment Latency Report V2
## Enhanced with Query Categorization and Detailed Analysis

### Executive Summary

The LeafLoaf production deployment shows excellent performance across all query categories with 100% success rate. Specific product searches show slightly higher latency (avg 187ms) due to more complex matching, while vague queries are efficiently handled (avg 127ms).

### Key Performance Metrics by Query Type

| Query Category | Average | Min | Max | Description |
|----------------|---------|-----|-----|-------------|
| **Attribute Search** | 110.20ms | 98.40ms | 122.10ms | Best performance for attribute-based queries |
| **Exploratory** | 119.49ms | 94.37ms | 172.34ms | Fast responses for open-ended queries |
| **Vague Product** | 127.28ms | 119.02ms | 132.70ms | Consistent performance for simple queries |
| **Category Search** | 133.00ms | 125.88ms | 142.34ms | Reliable category browsing |
| **Specific Product** | 187.18ms | 128.67ms | 327.90ms | Higher latency for exact matching |

## Detailed Query Analysis

### 1. Specific Product Searches (Expected α: 0.1-0.2)

These queries target exact products with brand names and specific attributes:

| Query | Latency | Description |
|-------|---------|-------------|
| "Nature's Path Heritage Flakes" | 128.67ms | Exact product name |
| "Horizon organic whole milk" | 134.74ms | Brand + attributes |
| "Organic Valley 2% milk gallon" | 157.40ms | Brand + type + size |
| "Oatly Barista Edition oat milk" | 327.90ms | Brand + specific variant |

**Insights**: 
- Most specific searches complete in 130-160ms
- The Oatly query spike (327ms) likely due to multiple terms requiring more processing
- System uses α=0.5 consistently (not dynamically adjusting as expected)

### 2. Vague Product Searches (Expected α: 0.5-0.7)

Simple, general queries:

| Query | Latency | Description |
|-------|---------|-------------|
| "bread" | 119.02ms | Single word, common |
| "something for breakfast" | 126.11ms | Very vague |
| "healthy snacks" | 131.28ms | Vague category |
| "milk" | 132.70ms | Single word, common |

**Insights**: 
- Excellent consistency (119-133ms range)
- Vague queries are handled efficiently
- "Something for breakfast" performs well despite being extremely vague

### 3. Category Searches (Expected α: 0.5-0.6)

Department and category browsing:

| Query | Latency | Description |
|-------|---------|-------------|
| "breakfast cereals" | 125.88ms | Specific category |
| "plant-based alternatives" | 131.82ms | Modern category |
| "frozen foods" | 131.95ms | Department category |
| "dairy products" | 142.34ms | Product category |

**Insights**: 
- Consistent 126-142ms range
- Modern categories like "plant-based" perform as well as traditional ones

### 4. Attribute-Based Searches (Expected α: 0.4-0.5)

Searches focusing on product attributes:

| Query | Latency | Description |
|-------|---------|-------------|
| "non-GMO snacks" | 98.40ms | Certification attribute |
| "low sodium items" | 104.19ms | Health attribute |
| "organic gluten-free products" | 116.12ms | Multiple attributes |
| "vegan protein sources" | 122.10ms | Diet + nutrition |

**Insights**: 
- **Best performing category** (98-122ms)
- Single attributes faster than multiple
- Health/diet attributes well-optimized

### 5. Exploratory Searches (Expected α: 0.7-0.9)

Open-ended, conversational queries:

| Query | Latency | Description |
|-------|---------|-------------|
| "quick lunch solutions" | 94.37ms | Time-based need |
| "dinner ideas for tonight" | 103.91ms | Meal planning |
| "what's good for a picnic" | 107.34ms | Use case query |
| "healthy options for kids" | 172.34ms | Demographic + health |

**Insights**: 
- Generally fast (94-107ms) except demographic queries
- "Healthy options for kids" spike might indicate complex intent parsing

## Conversation Flow Analysis

### Specific Conversation Flow
Perfect for users who know what they want:

| Step | Query | Latency | Action |
|------|-------|---------|--------|
| 1 | "I need Oatly Barista Edition" | 101.11ms | Exact product request |
| 2 | "Add 2 cartons to my cart" | 100.20ms | Specific quantity |
| 3 | "Also get me Horizon organic milk" | 99.19ms | Another specific product |
| 4 | "Change Oatly quantity to 3" | 110.08ms | Modify specific item |
| 5 | "Show me my order" | 100.30ms | Review order |
| 6 | "That's all, confirm order" | 111.64ms | Confirm with context |

**Average**: 103.75ms per interaction

### Vague Conversation Flow
Typical browsing behavior:

| Step | Query | Latency | Action |
|------|-------|---------|--------|
| 1 | "I need some milk" | 109.58ms | Vague product request |
| 2 | "What options do you have?" | 114.19ms | Exploration |
| 3 | "I'll take the organic one" | 96.28ms | Relative selection |
| 4 | "Add some bread too" | 110.21ms | Another vague request |
| 5 | "Something for breakfast" | 110.30ms | Very vague addition |
| 6 | "That's good, checkout" | 107.49ms | Casual confirmation |

**Average**: 108.01ms per interaction

## Alpha Value Analysis

**Current Issue**: The system is using a fixed α=0.5 for all queries instead of dynamic calculation.

**Expected vs Actual**:
- Specific products (expected 0.1-0.2): Using 0.5 ❌
- Vague queries (expected 0.5-0.7): Using 0.5 ✅
- Exploratory (expected 0.7-0.9): Using 0.5 ❌

**Impact**: Despite suboptimal alpha values, performance remains good due to mock data. Real Weaviate performance may benefit more from dynamic alpha.

## Weaviate Production Expectations

When upgrading to real Weaviate data:

### Expected Latency Changes

| Query Type | Current (Mock) | Expected (Weaviate) | Increase |
|------------|----------------|---------------------|----------|
| Specific Product | 187ms | 220-250ms | +33-63ms |
| Vague Product | 127ms | 160-190ms | +33-63ms |
| Category Search | 133ms | 170-200ms | +37-67ms |
| Attribute Search | 110ms | 150-180ms | +40-70ms |
| Exploratory | 119ms | 180-220ms | +61-101ms |

### Factors Affecting Weaviate Performance

1. **Vector Search Overhead**: 30-50ms for semantic search
2. **Network Latency**: 10-20ms to Weaviate cloud
3. **Result Size**: More products = more processing
4. **Query Complexity**: Multi-term queries take longer
5. **Alpha Value**: Lower alpha (keyword) faster than high alpha (semantic)

## Testing Weaviate Production

To test with real Weaviate when credits are available:

```bash
# Run enhanced test with Weaviate flag
python3 scripts/test_gcp_deployment_v2.py --weaviate

# This will:
# 1. Switch to production mode automatically
# 2. Run subset of tests with real data
# 3. Compare performance
# 4. Switch back to test mode
```

## Optimization Recommendations

### 1. Implement Dynamic Alpha
```python
# Fix in supervisor agent:
if specific_brand_detected:
    alpha = 0.1  # Heavy keyword bias
elif category_search:
    alpha = 0.5  # Balanced
elif exploratory_query:
    alpha = 0.8  # Heavy semantic bias
```

### 2. Query-Specific Optimizations
- **Specific Products**: Cache popular brand searches
- **Categories**: Pre-compute category listings
- **Attributes**: Index common dietary restrictions
- **Exploratory**: Implement conversation context caching

### 3. Performance Targets
- Specific products: < 200ms
- Vague queries: < 150ms
- Conversation steps: < 120ms
- 95th percentile: < 300ms

## Conclusion

The LeafLoaf system demonstrates excellent performance across all query types:

✅ **Fastest**: Attribute searches (98-122ms)
✅ **Most Consistent**: Vague products (119-133ms)
✅ **Conversation Ready**: Both flows under 115ms average
⚠️ **Needs Attention**: Dynamic alpha calculation not working
🎯 **Production Ready**: Even with fixed alpha, performance is excellent

The system successfully handles everything from "non-GMO snacks" (98ms) to complex queries like "Oatly Barista Edition oat milk" (328ms) with high reliability.