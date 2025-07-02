# Typeahead Search Design

## 🎯 Overview

Fast, responsive typeahead search for direct product name entry. This bypasses all LLM processing for sub-100ms response times.

---

## 📊 Typeahead Response Structure

```json
{
  "status": "success",
  "data": {
    "query": "ric",  // What user typed
    "suggestions": [
      {
        // Minimal product data for speed
        "product_id": "uuid-123",
        "sku": "LX_RICE_001",
        "display_name": "Laxmi Basmati Rice Premium",
        "highlight": "Laxmi Basmati <mark>Ric</mark>e Premium",  // HTML highlighting
        
        // Category for grouping
        "category": "Rice & Grains",
        "subcategory": "Basmati Rice",
        
        // Key info for display
        "brand": "Laxmi",
        "size": "10 LB",
        "price": 35.00,
        
        // Visual elements
        "thumbnail": "https://cdn.leafloaf.com/products/LX_RICE_001_50x50.jpg",
        "badges": ["Premium", "Non-GMO"],
        
        // Search metadata
        "match_type": "prefix",  // prefix | fuzzy | exact
        "match_field": "product_name",  // which field matched
        "score": 0.95
      },
      {
        "product_id": "uuid-456",
        "sku": "VS_RICE_002",
        "display_name": "Vistar Jasmine Rice",
        "highlight": "Vistar Jasmine <mark>Ric</mark>e",
        "category": "Rice & Grains",
        "subcategory": "Jasmine Rice",
        "brand": "Vistar",
        "size": "25 LB",
        "price": 42.50,
        "thumbnail": "https://cdn.leafloaf.com/products/VS_RICE_002_50x50.jpg",
        "badges": ["Bulk Size"],
        "match_type": "prefix",
        "match_field": "product_name",
        "score": 0.94
      },
      {
        "product_id": "uuid-789",
        "sku": "LX_RICE_FLOUR_001",
        "display_name": "Laxmi Rice Flour",
        "highlight": "Laxmi <mark>Ric</mark>e Flour",
        "category": "Flours & Mixes",
        "subcategory": "Rice Flour",
        "brand": "Laxmi",
        "size": "2 LB",
        "price": 8.99,
        "thumbnail": "https://cdn.leafloaf.com/products/LX_RICE_FLOUR_001_50x50.jpg",
        "badges": ["Gluten-Free"],
        "match_type": "prefix",
        "match_field": "product_name",
        "score": 0.90
      }
    ],
    
    // Categories for filtering
    "suggestion_groups": [
      {
        "category": "Rice & Grains",
        "count": 8,
        "top_suggestion": "LX_RICE_001"
      },
      {
        "category": "Flours & Mixes", 
        "count": 2,
        "top_suggestion": "LX_RICE_FLOUR_001"
      }
    ],
    
    // Quick actions
    "actions": {
      "view_all": {
        "text": "View all rice products",
        "query": "rice",
        "estimated_results": 45
      }
    }
  },
  
  "meta": {
    "performance": {
      "total_ms": 35,
      "cached": true,
      "index": "typeahead_products"
    },
    "suggestion_count": 10,
    "total_matches": 45,
    "query_normalized": "ric",
    "spell_corrected": false
  }
}
```

---

## 🚀 Implementation Strategy

### 1. **Dedicated Typeahead Index**

```python
# Elasticsearch/Redis Search configuration
typeahead_index = {
  "settings": {
    "analysis": {
      "analyzer": {
        "typeahead_analyzer": {
          "tokenizer": "edge_ngram_tokenizer",
          "filter": ["lowercase", "asciifolding"]
        }
      },
      "tokenizer": {
        "edge_ngram_tokenizer": {
          "type": "edge_ngram",
          "min_gram": 2,
          "max_gram": 20,
          "token_chars": ["letter", "digit"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "product_name": {
        "type": "text",
        "analyzer": "typeahead_analyzer",
        "search_analyzer": "standard"
      },
      "search_keywords": {
        "type": "text",
        "analyzer": "typeahead_analyzer"
      },
      "sku": {"type": "keyword"},
      "brand": {"type": "keyword"},
      "category": {"type": "keyword"},
      "price": {"type": "float"},
      "popularity_score": {"type": "float"}
    }
  }
}
```

### 2. **Endpoint Implementation**

```python
@router.get("/api/v1/products/typeahead")
async def typeahead_search(
    q: str = Query(..., min_length=2, max_length=50),
    limit: int = Query(10, ge=1, le=20),
    user_id: Optional[str] = None
):
    """
    Ultra-fast typeahead search
    Target: <100ms, ideally <50ms
    """
    
    # Normalize query
    query = q.lower().strip()
    
    # Check cache first
    cache_key = f"typeahead:{query}:{limit}:{user_id or 'anon'}"
    if cached := await redis.get(cache_key):
        return json.loads(cached)
    
    # Search strategy
    results = await search_client.search({
        "query": {
            "bool": {
                "should": [
                    # Prefix match on product name (highest weight)
                    {
                        "prefix": {
                            "product_name": {
                                "value": query,
                                "boost": 3.0
                            }
                        }
                    },
                    # Match on search keywords
                    {
                        "match": {
                            "search_keywords": {
                                "query": query,
                                "boost": 2.0
                            }
                        }
                    },
                    # Fuzzy match for typos
                    {
                        "fuzzy": {
                            "product_name": {
                                "value": query,
                                "fuzziness": "AUTO",
                                "boost": 1.0
                            }
                        }
                    },
                    # SKU match
                    {
                        "prefix": {
                            "sku": {
                                "value": query.upper(),
                                "boost": 2.5
                            }
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        },
        
        # Boosting
        "functions": [
            {
                "field_value_factor": {
                    "field": "popularity_score",
                    "modifier": "log1p",
                    "factor": 0.5
                }
            }
        ],
        
        # User personalization (if user_id provided)
        "user_preferences": user_id,
        
        # Return only needed fields
        "_source": [
            "product_id", "sku", "product_name", "brand",
            "category", "subcategory", "size", "price",
            "thumbnail", "badges"
        ],
        
        "size": limit,
        "highlight": {
            "fields": {
                "product_name": {
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                }
            }
        }
    })
    
    # Format response
    response = format_typeahead_response(query, results)
    
    # Cache for 5 minutes
    await redis.setex(cache_key, 300, json.dumps(response))
    
    return response
```

### 3. **Optimization Techniques**

```python
class TypeaheadOptimizer:
    def __init__(self):
        # Pre-compute popular searches
        self.popular_prefixes = self._load_popular_prefixes()
        
        # Memory cache for ultra-fast access
        self.memory_cache = LRUCache(maxsize=1000)
        
        # Pre-warm cache
        asyncio.create_task(self._warm_cache())
    
    async def _warm_cache(self):
        """Pre-warm cache with popular searches"""
        popular_queries = [
            "ric", "rice", "dal", "oi", "oil", "mil", "milk",
            "bre", "bread", "spi", "spice", "mas", "masala"
        ]
        
        for query in popular_queries:
            await self._cache_query(query)
    
    def _should_use_memory_cache(self, query: str) -> bool:
        """Determine if query is popular enough for memory cache"""
        return (
            len(query) <= 4 or
            query in self.popular_prefixes or
            self.memory_cache.get(query) is not None
        )
```

### 4. **Frontend Integration**

```javascript
// Debounced typeahead implementation
class TypeaheadSearch {
  constructor(inputElement, resultContainer) {
    this.input = inputElement;
    this.results = resultContainer;
    this.cache = new Map();
    this.currentRequest = null;
    
    // Debounce to avoid too many requests
    this.search = debounce(this._search.bind(this), 150);
    
    this.input.addEventListener('input', this.handleInput.bind(this));
  }
  
  handleInput(event) {
    const query = event.target.value.trim();
    
    // Minimum 2 characters
    if (query.length < 2) {
      this.clearResults();
      return;
    }
    
    // Check local cache first
    if (this.cache.has(query)) {
      this.displayResults(this.cache.get(query));
      return;
    }
    
    // Trigger search
    this.search(query);
  }
  
  async _search(query) {
    // Cancel previous request
    if (this.currentRequest) {
      this.currentRequest.abort();
    }
    
    const controller = new AbortController();
    this.currentRequest = controller;
    
    try {
      const response = await fetch(`/api/v1/products/typeahead?q=${query}`, {
        signal: controller.signal,
        headers: {
          'X-User-ID': getUserId() // For personalization
        }
      });
      
      const data = await response.json();
      
      // Cache result
      this.cache.set(query, data);
      
      // Display
      this.displayResults(data);
      
    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Typeahead error:', error);
      }
    }
  }
  
  displayResults(data) {
    const html = data.data.suggestions.map(suggestion => `
      <div class="typeahead-item" data-sku="${suggestion.sku}">
        <img src="${suggestion.thumbnail}" alt="">
        <div class="item-details">
          <div class="item-name">${suggestion.highlight}</div>
          <div class="item-meta">
            ${suggestion.brand} • ${suggestion.size} • $${suggestion.price}
          </div>
        </div>
        <div class="item-badges">
          ${suggestion.badges.map(b => `<span class="badge">${b}</span>`).join('')}
        </div>
      </div>
    `).join('');
    
    this.results.innerHTML = html;
  }
}
```

---

## 🎯 Performance Targets

### Response Time Breakdown:
- Network latency: ~20ms
- Redis cache hit: ~5ms
- Search execution: ~15-30ms
- Response formatting: ~5ms
- **Total target: <50ms (cached), <100ms (uncached)**

### Optimization Strategies:
1. **Edge caching** for popular queries
2. **Memory cache** for ultra-popular prefixes
3. **Connection pooling** for Redis/ES
4. **Minimal payload** (only display fields)
5. **CDN for thumbnails** with aggressive caching

### Scaling Considerations:
- Separate typeahead service/cluster
- Read replicas for search
- Geographic distribution
- Request coalescing for identical queries

---

## 🔄 Difference from Natural Language Search

| Aspect | Typeahead | Natural Language |
|--------|-----------|------------------|
| Input | Partial product names | Photos, notes, descriptions |
| Processing | Direct search, no LLM | LLM extraction + analysis |
| Response Time | <100ms | <500ms |
| Response Size | Minimal (10 items) | Rich (full context) |
| Use Case | Search bar | Complex queries |
| Caching | Aggressive (5 min) | Minimal |
| Personalization | Basic (popularity) | Deep (history, context) |