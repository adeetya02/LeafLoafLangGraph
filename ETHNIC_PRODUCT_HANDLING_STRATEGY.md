# Ethnic Product Handling Strategy

## Overview
This document outlines how LeafLoaf handles ethnic and international products through voice search.

## Current Implementation

### 1. Deepgram Nova-3 Keywords
The system uses Deepgram Nova-3's custom vocabulary feature to boost recognition of ethnic product names:

```python
ETHNIC_KEYWORDS = [
    # South Asian
    "paneer:15", "ghee:15", "dal:12", "masala:10",
    "basmati:10", "atta:12", "jaggery:15",
    
    # East Asian  
    "gochujang:15", "kimchi:12", "miso:12", "dashi:15",
    "tofu:10", "wakame:15", "nori:12",
    
    # Middle Eastern
    "harissa:15", "zaatar:15", "tahini:12", "sumac:12",
    "labneh:15", "halloumi:12", "falafel:10",
    
    # Latin American
    "plantains:10", "yuca:15", "mole:15",
    "achiote:15", "epazote:18",
    
    # African
    "injera:15", "berbere:15", "fufu:15", "jollof:12"
]
```

The numbers represent boost values (higher = more likely to be recognized).

### 2. Dynamic Intent Classification
The supervisor uses fully dynamic intent classification:
- No hardcoded ethnic product categories
- Learns from actual usage patterns
- Creates intents like "ethnic_product_request" organically

### 3. Product Search in Weaviate
All products come from Weaviate vector database:
- Ethnic products are stored with proper metadata
- Vector embeddings capture semantic meaning
- Hybrid search (keyword + semantic) finds related items

## Voice Flow for Ethnic Products

1. **User speaks**: "I need paneer and ghee"

2. **Deepgram STT**: 
   - Boosted recognition for "paneer" and "ghee"
   - Higher accuracy due to custom vocabulary

3. **Dynamic Supervisor**:
   - Classifies intent (e.g., "product_search")
   - Extracts entities: ["paneer", "ghee"]
   - No hardcoded ethnic categories

4. **Weaviate Search**:
   - Hybrid search with voice-driven alpha
   - Finds products in vector database
   - Returns only local inventory

5. **Response**:
   - Products with proper names and descriptions
   - Cultural context preserved

## Benefits

### 1. Accuracy
- Boosted recognition reduces transcription errors
- Common mispronunciations handled better
- Cultural product names preserved

### 2. Discoverability
- Semantic search finds related products
- "Indian cheese" might find "paneer"
- "Korean cabbage" might find "kimchi"

### 3. Scalability
- Easy to add new ethnic products
- No code changes needed
- Just update Weaviate database

### 4. Personalization
- System learns user's ethnic preferences
- Frequently bought ethnic products prioritized
- Cultural dietary patterns recognized

## Future Enhancements

### 1. Pronunciation Variants
```python
# Add common pronunciation variants
"paneer:15", "puneer:10", "paner:10",
"ghee:15", "ghi:12", "ghey:10"
```

### 2. Cultural Context
- Add recipe associations
- Suggest complementary ethnic products
- Recognize cultural meal patterns

### 3. Multi-language Support
- Accept queries in native languages
- Transliterate product names
- Support code-switching

### 4. Dietary Restrictions
- Halal/Kosher certification info
- Vegetarian/Vegan ethnic options
- Allergen information

## Testing Ethnic Products

### Voice Test Queries
1. "I need ingredients for palak paneer"
2. "Get me Korean BBQ essentials"
3. "Show me Middle Eastern spices"
4. "I want to make Thai curry"
5. "Find African cooking ingredients"

### Expected Behavior
- Accurate transcription of ethnic terms
- Relevant product results
- No external API calls
- Cultural context preserved

## Data Requirements

### Weaviate Product Schema
```json
{
  "name": "Amul Paneer",
  "description": "Fresh Indian cottage cheese",
  "category": "Dairy",
  "subcategory": "Ethnic Dairy",
  "cuisine": ["Indian", "South Asian"],
  "dietary": ["Vegetarian", "Gluten-Free"],
  "keywords": ["paneer", "cottage cheese", "Indian cheese"],
  "common_uses": ["palak paneer", "paneer tikka", "matar paneer"]
}
```

### Vector Embeddings
- Capture semantic meaning
- Include cultural context
- Support cross-lingual search

## Monitoring

### Metrics to Track
1. **Recognition Accuracy**: Success rate for ethnic terms
2. **Search Relevance**: Click-through on ethnic products
3. **User Satisfaction**: Reorder rates for ethnic items
4. **Coverage**: Percentage of ethnic queries handled

### Feedback Loop
1. Log unrecognized ethnic terms
2. Add to custom vocabulary
3. Update Weaviate with new products
4. Monitor improvement

## Conclusion

The ethnic product handling strategy focuses on:
- **Accuracy**: Better recognition through boosting
- **Flexibility**: Dynamic intent learning
- **Locality**: All products from Weaviate
- **Scalability**: Easy to add new products
- **Personalization**: Learn user preferences

This approach ensures ethnic products are handled with the same quality and care as mainstream products, making the grocery shopping experience inclusive and accessible for all users.