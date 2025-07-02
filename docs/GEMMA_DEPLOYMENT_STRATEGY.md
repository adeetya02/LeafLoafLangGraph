# Gemma 2 9B Deployment Strategy

## Current Implementation: Vertex AI Generative API
**Location**: `/src/integrations/gemma_client.py`
```python
from vertexai.generative_models import GenerativeModel
self.vertex_model = GenerativeModel("gemma-2-9b-it")
```

### How it works:
- Uses Google's hosted Gemma endpoint
- No infrastructure management needed
- Pay-per-request pricing
- Shared infrastructure with other users
- Standard model (no customization)

### Pros:
- ✅ Zero setup required
- ✅ No GPU management
- ✅ Automatic scaling
- ✅ Lower initial cost

### Cons:
- ❌ No fine-tuning capability
- ❌ Higher per-request cost at scale
- ❌ Shared rate limits
- ❌ Can't customize for LeafLoaf data

## Future: Model Garden Deployment

### What is Model Garden?
- Deploy your own instance of Gemma 2 9B
- Dedicated endpoint just for LeafLoaf
- Can fine-tune on your supplier/product data
- Full control over the model

### Deployment Steps:
1. **Access Model Garden**
   ```
   Console > Vertex AI > Model Garden > Search "Gemma 2"
   ```

2. **Deploy Model**
   - Click "Deploy" on Gemma 2 9B
   - Choose machine type (e.g., n1-standard-8 with T4 GPU)
   - Set up endpoint name: `leafloaf-gemma-endpoint`

3. **Fine-tuning Process**
   ```python
   # Prepare training data
   training_data = [
       {"prompt": "organic milk", "response": "intent: reorder, confidence: 0.9"},
       {"prompt": "birthday cake ingredients", "response": "intent: meal_planning, confidence: 0.85"},
       {"prompt": "Oatly oat milk", "response": "intent: brand_specific, confidence: 0.95"}
   ]
   ```

4. **Update Code to Use Custom Endpoint**
   ```python
   # New implementation
   from google.cloud import aiplatform
   
   endpoint = aiplatform.Endpoint(
       endpoint_name="projects/leafloafai/locations/northamerica-northeast1/endpoints/leafloaf-gemma-endpoint"
   )
   
   response = endpoint.predict(instances=[{"prompt": query}])
   ```

## Cost Comparison

### Current (Vertex AI Generative API)
- ~$0.00025 per 1K characters input
- ~$0.0005 per 1K characters output
- No fixed costs
- Good for: Starting out, testing

### Model Garden Deployment
- Fixed: ~$200-500/month (GPU instance)
- Variable: Minimal (just compute)
- Break-even: ~2-4M requests/month
- Good for: Scale, customization

## Migration Strategy

### Phase 1: Current ✅
- Use Vertex AI Generative API
- Collect data on intents
- Monitor costs and usage

### Phase 2: Data Collection (Next)
- Track all queries and correct intents
- Build training dataset
- Format: JSONL with prompt/response pairs

### Phase 3: Model Garden Deployment
1. Deploy base Gemma 2 9B
2. Fine-tune with LeafLoaf data:
   - Product search patterns
   - Reorder behavior
   - Local supplier knowledge
3. A/B test against API version
4. Switch traffic gradually

### Phase 4: Optimization
- Quantize model for faster inference
- Implement caching for common queries
- Edge deployment for lowest latency

## Training Data Examples

```jsonl
{"prompt": "need milk", "response": "intent: reorder, products: ['dairy_milk', 'oat_milk'], confidence: 0.85"}
{"prompt": "organic vegetables for salad", "response": "intent: meal_planning, category: produce, dietary: organic, confidence: 0.9"}
{"prompt": "Kirkland paper towels", "response": "intent: brand_specific, brand: Kirkland, category: household, confidence: 0.95"}
{"prompt": "gluten free bread", "response": "intent: dietary_specific, dietary: gluten_free, category: bakery, confidence: 0.9"}
```

## Benefits of Custom Model

1. **LeafLoaf-Specific Understanding**
   - Knows your product catalog
   - Understands local brands
   - Trained on actual user queries

2. **Better Intent Classification**
   - Higher accuracy for your use cases
   - Faster inference (optimized)
   - Custom intents beyond generic

3. **Cost Efficiency at Scale**
   - Fixed monthly cost
   - Unlimited requests
   - Predictable budgeting

4. **Competitive Advantage**
   - Unique model trained on your data
   - Can't be replicated by competitors
   - Continuously improving with new data

## Implementation Timeline

- **Now**: Using Vertex AI API ✅
- **After BigQuery Streaming**: Start collecting training data
- **At 10K+ queries**: Deploy Model Garden instance
- **At 50K+ queries**: Fine-tune with real data
- **At 100K+ queries**: Full custom model in production

## Quota Limits Update
Since your quota limits are updated, you can:
1. Deploy Model Garden instance immediately if desired
2. Run parallel testing (API vs Model Garden)
3. Start fine-tuning experiments early

Would you like to proceed with Model Garden deployment now or continue with data collection first?