# Budget Deployment Plan - $50/month

## Philosophy: Build Everything First, Optimize Later

### Current Priorities
1. ✅ Core search working
2. ✅ Order management 
3. ✅ Fast local testing
4. ⏳ Redis session memory
5. ⏳ ML recommendations
6. ⏳ Personalization
7. ⏳ 11Labs voice
8. THEN scale up

## 🎯 Budget Architecture ($50/month)

### 1. GCP Cloud Run (Free Tier)
```yaml
# Cloud Run Configuration
service: leafloaf
memory: 512Mi          # Free tier
cpu: 1                 # Free tier
min-instances: 0       # Scale to zero
max-instances: 2       # Stay in free tier
concurrency: 10        # Lower concurrency

# Free tier limits:
# - 2 million requests/month
# - 360,000 GB-seconds/month
# - 180,000 vCPU-seconds/month
```

### 2. Gemma via Batch/Queue (~$30/month)
```python
# Instead of real-time Vertex AI, use batch processing
class BudgetGemmaClient:
    async def analyze_query(self, query: str):
        # 1. Check cache first
        if cached := await redis.get(f"intent:{query}"):
            return cached
            
        # 2. Use pattern matching (instant)
        intent = self._instant_analysis(query)
        
        # 3. Queue for batch Gemma enhancement (async)
        await queue.put({
            "query": query,
            "timestamp": now(),
            "session_id": session_id
        })
        
        # 4. Return instant result
        return intent

# Run batch job every 5 minutes
async def batch_gemma_processor():
    queries = await queue.get_batch(max=100)
    results = await vertex_ai.batch_predict(queries)
    await update_cache(results)
```

### 3. Weaviate Free Tier (Expires 6/28)
```python
# Maximize free tier usage
WEAVIATE_CONFIG = {
    "max_objects": 10000,      # Stay under free limit
    "rate_limit": 30/min,      # Self-imposed
    "cache_popular": True,     # Cache top 100 products
}

# After 6/28, options:
# A. Self-host Weaviate on Cloud Run ($0)
# B. Use PostgreSQL + pgvector ($0)
# C. Simple Elasticsearch ($0 with free tier)
```

### 4. Redis Alternative - Firestore ($0)
```python
# Use Firestore for session memory (free tier: 50K reads/day)
class FirestoreSessionMemory:
    def __init__(self):
        self.db = firestore.Client()
        self.sessions = self.db.collection('sessions')
    
    async def get_conversation(self, session_id: str):
        doc = self.sessions.document(session_id).get()
        return doc.to_dict() if doc.exists else {}
    
    async def add_message(self, session_id: str, message: dict):
        self.sessions.document(session_id).update({
            'messages': firestore.ArrayUnion([message]),
            'updated_at': firestore.SERVER_TIMESTAMP
        })

# Or use in-memory with Cloud Run persistence
class InMemoryWithBackup:
    def __init__(self):
        self.cache = {}  # In-memory
        self.backup_interval = 300  # 5 minutes
        
    async def persist_to_gcs(self):
        # Backup to Cloud Storage (free 5GB)
        blob = bucket.blob(f'sessions/{date}.json')
        blob.upload_from_string(json.dumps(self.cache))
```

### 5. ML & Personalization (~$20/month)

#### A. Recommendation Engine (Simple Collaborative Filtering)
```python
class BudgetRecommendationEngine:
    def __init__(self):
        # Use simple matrix factorization
        self.user_item_matrix = {}
        self.item_similarity = {}
    
    async def get_recommendations(self, user_id: str, n=5):
        # 1. Get user's purchase history (from Firestore)
        history = await self.get_user_history(user_id)
        
        # 2. Find similar users (cosine similarity)
        similar_users = self.find_similar_users(user_id)
        
        # 3. Get their top products
        recommendations = self.aggregate_preferences(similar_users)
        
        return recommendations[:n]
    
    # Update similarities in batch (nightly)
    async def update_similarities_batch(self):
        # Run as Cloud Scheduler job (free tier: 3 jobs)
        all_users = await self.get_all_users()
        self.compute_similarities(all_users)
        await self.save_to_gcs()
```

#### B. Personalization Layer
```python
class BudgetPersonalization:
    def __init__(self):
        self.user_profiles = {}  # Cache in memory
        
    async def personalize_search(self, query: str, user_id: str):
        # 1. Get user preferences (dietary, brands, etc)
        profile = await self.get_user_profile(user_id)
        
        # 2. Boost preferred attributes
        if profile.dietary_preferences:
            query = f"{query} {' '.join(profile.dietary_preferences)}"
            
        # 3. Adjust alpha based on user behavior
        if profile.prefers_specific_brands:
            alpha = 0.2  # More keyword focused
        else:
            alpha = 0.5  # Balanced
            
        return query, alpha
    
    # Learn preferences from orders
    async def update_profile(self, user_id: str, order: dict):
        products = order['items']
        
        # Extract patterns
        dietary = self.extract_dietary_preferences(products)
        brands = self.extract_brand_preferences(products)
        categories = self.extract_category_preferences(products)
        
        # Update profile
        await self.save_profile(user_id, {
            'dietary': dietary,
            'brands': brands,
            'categories': categories,
            'updated': now()
        })
```

### 6. Implementation Timeline

#### Week 1: Core Infrastructure
- [ ] Deploy to Cloud Run (free tier)
- [ ] Set up Firestore for sessions
- [ ] Implement in-memory caching
- [ ] Add batch Gemma queue

#### Week 2: ML Foundation
- [ ] User-item matrix in Firestore
- [ ] Simple collaborative filtering
- [ ] Nightly batch jobs for similarity
- [ ] Basic personalization rules

#### Week 3: Features
- [ ] User preference learning
- [ ] Search personalization
- [ ] Recommendation API
- [ ] A/B testing framework

#### Week 4: Polish
- [ ] 11Labs integration
- [ ] Analytics dashboard
- [ ] Performance monitoring
- [ ] Documentation

### 7. When to Scale Up

Monitor these metrics:
```python
SCALING_TRIGGERS = {
    "daily_users": 1000,        # Need more capacity
    "avg_latency": 1000,        # Need faster inference  
    "cache_hit_rate": 0.3,      # Need Redis
    "ml_accuracy": 0.6,         # Need better models
    "revenue": 5000,            # Can afford premium
}
```

### 8. Cost Breakdown

```
Current Budget Tier:
- Cloud Run: $0 (free tier)
- Gemma Batch: $30/month
- Weaviate: $0 (free until 6/28)
- Firestore: $0 (free tier)
- Cloud Storage: $0 (5GB free)
- Cloud Scheduler: $0 (3 jobs free)
- Monitoring: $0 (free tier)
TOTAL: ~$30-50/month

Future Scaling:
- Add Redis: +$50/month
- Vertex AI realtime: +$200/month  
- Dedicated Weaviate: +$100/month
- Scale as needed!
```

## 🎯 Key Principle: Feature Complete > Fast

1. Build all features on budget
2. Validate product-market fit
3. Collect real user data
4. Then optimize based on actual usage
5. Scale up only what's needed

This approach lets you build the complete system for <$50/month while learning what actually needs optimization!