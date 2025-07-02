# Demo Improvements for Tomorrow

## Issues Found
1. **Search results not updating** - Products shown are static, not from actual Weaviate search
2. **No personalization reasoning** - Need to show WHY products are ranked differently
3. **Missing real-time updates** - After milk purchase, bread search should show personalized results

## Tomorrow's Tasks

### 1. Fix Search Integration
- Connect demo to actual Weaviate search results
- Show real products from database
- Update results dynamically based on query

### 2. Add Personalization Reasoning
For each product, show:
- **Score breakdown**: keyword match (0.3) + semantic match (0.7) + personalization boost (0.5)
- **Why recommended**: 
  - "You bought milk → bread is a complementary item"
  - "You prefer organic → showing organic bread first"
  - "Morning shopper → fresh bakery items prioritized"

### 3. Real-time Personalization Flow
After user buys milk:
```
Search: "bread"
→ Graphiti knows: user bought organic milk
→ Personalization applied:
  1. Organic Whole Wheat Bread (boost: bought organic)
  2. Artisan Sourdough (boost: premium like organic)
  3. Regular White Bread (no boost)
```

### 4. Show Complete Reasoning Chain
```
Query: "bread"
↓
Gemma: Intent=product_search, Alpha=0.4
↓
Weaviate: Found 15 bread products
↓
Graphiti: User prefers organic, bought milk
↓
Reranking:
- Organic bread: base_score(0.8) + organic_boost(0.3) = 1.1
- Regular bread: base_score(0.9) + no_boost(0.0) = 0.9
↓
Final order: Organic first despite lower base score
```

### 5. Visual Improvements
- Show score bars for each product
- Highlight personalization factors
- Add "Why this order?" explanation box
- Show before/after comparison side-by-side

### 6. Backend Fixes Needed
- `demo_api.py`: Return actual search results, not mock data
- Add personalization scoring logic
- Include reasoning in API response
- Store and retrieve user preferences properly

## Quick Fix for Tonight
To see real search results now:
1. Stop the demo: `kill $(lsof -t -i:8080)`
2. The search API needs to return actual Weaviate results
3. The personalization needs to actually rerank based on history

## For Tomorrow Morning
1. Review the personalization ranking algorithm
2. Implement reasoning explanations
3. Test the complete flow: search → purchase → search again
4. Ensure Spanner is storing relationships correctly
5. Show BigQuery ML features influencing ranking

---
**Note**: The core pipeline is working (Weaviate vector search is functional), but the demo UI needs to properly integrate with it to show the personalization in action.