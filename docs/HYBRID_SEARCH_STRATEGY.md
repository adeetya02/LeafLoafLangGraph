# Hybrid Search Strategy for LeafLoaf

## Overview
Weaviate's hybrid search combines BM25 (keyword) and vector (semantic) search using an alpha parameter to control the balance.

## Alpha Parameter Guide

### Understanding Alpha
- **α = 0.0**: Pure keyword search (BM25 only)
- **α = 1.0**: Pure vector search (semantic only)
- **α = 0.5**: Equal weight to both
- **α = 0.75**: Our default (75% semantic, 25% keyword)

### Query-Based Alpha Strategy

#### 1. Brand/Product Specific (α = 0.1 - 0.3)
- "Oatly barista edition"
- "Kirkland paper towels"
- "Nature's Path cereal"
- **Why**: Exact matches matter most

#### 2. Product + Attributes (α = 0.3 - 0.5)
- "organic bananas"
- "gluten free bread"
- "2% milk"
- **Why**: Balance between exact product and semantic attributes

#### 3. Category Searches (α = 0.5 - 0.7)
- "dairy products"
- "fresh vegetables"
- "breakfast cereals"
- **Why**: Semantic understanding helps find related items

#### 4. Exploratory/Semantic (α = 0.7 - 0.9)
- "healthy breakfast ideas"
- "sustainable food options"
- "meal planning for diabetics"
- **Why**: Semantic understanding is crucial

## Implementation in Code

### Current Setup (search_tools.py)
```python
# Line 223-227
results = collection.query.hybrid(
    query=query,
    alpha=search_alpha,  # Currently 0.75 default
    limit=limit
)
```

### Enhanced Implementation (After Weaviate Upgrade)
```python
results = collection.query.hybrid(
    query=query,
    alpha=search_alpha,
    limit=limit,
    fusion_type="relativeScoreFusion",  # Better than rankedFusion
    properties=["name^2", "description", "category"],  # Weight name 2x
    return_metadata=["score", "explainScore"]  # For debugging
)
```

## Fusion Algorithms

### 1. Ranked Fusion (Original)
- Score = 1/(rank + 60)
- Simple ranking-based combination
- Less nuanced

### 2. Relative Score Fusion (Default v1.24+)
- Normalizes scores between 0 and 1
- Preserves relative score distributions
- More accurate result blending
- **Recommended for our use case**

## Performance Optimization

1. **Oversearch**: Weaviate automatically searches more results (100) then trims
2. **Property Weights**: Boost important fields (name^2)
3. **Limit Tuning**: Balance between coverage and speed

## Testing Different Alpha Values

```python
# Test scenarios after Weaviate upgrade
test_queries = [
    ("Oatly oat milk", 0.2),  # Brand specific
    ("organic milk", 0.5),     # Product + attribute
    ("breakfast items", 0.7),   # Category
    ("healthy meal ideas", 0.85)  # Exploratory
]
```

## Monitoring and Tuning

1. Use `explainScore` to understand result ranking
2. Track CTR (click-through rate) for different alpha values
3. A/B test alpha values for common query patterns
4. Log search performance metrics to BigQuery

## Next Steps After Weaviate Upgrade

1. Test hybrid search with vector capabilities restored
2. Implement dynamic alpha based on Gemma's analysis
3. Add property weighting for better relevance
4. Monitor search quality metrics
5. Fine-tune alpha ranges based on user behavior