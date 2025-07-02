# 🚀 Spanner Graph Implementation Guide for LeafLoaf

## Executive Summary

**Instead of Neo4j + Graphiti ($275/month), use Spanner Graph ($100-150/month) with native Vertex AI integration.**

## Why Spanner Graph?

### ✅ Native GCP Integration
- **Built-in Vertex AI**: No external LLM API costs
- **IAM & VPC**: Native security integration
- **Cloud Monitoring**: Built-in observability
- **Auto-scaling**: No manual capacity planning

### 💰 Cost Comparison

| Component | Neo4j + Graphiti | Spanner Graph |
|-----------|-----------------|---------------|
| Database | $150/month (AuraDB) | $72/month (1 node) |
| LLM for Entity Extraction | $100/month (OpenAI) | $0 (Vertex AI included) |
| Infrastructure | $25/month | $0 (serverless) |
| **Total** | **$275/month** | **~$100/month** |

### 🎯 Key Features

1. **GraphRAG with LangChain**: Native integration announced in 2024
2. **GQL + SQL**: Query with both languages in same database
3. **Vertex AI Models**: Direct access to Gemini, PaLM, embeddings
4. **Enterprise Scale**: Google's Spanner reliability

## Implementation Steps

### 1. Enable Spanner API

```bash
# Enable required APIs
gcloud services enable spanner.googleapis.com
gcloud services enable aiplatform.googleapis.com

# Create Spanner instance
gcloud spanner instances create leafloaf-graph \
  --config=regional-us-central1 \
  --description="LeafLoaf GraphRAG" \
  --nodes=1
```

### 2. Update Dependencies

```python
# requirements.txt
google-cloud-spanner==3.40.0
langchain-google-spanner==0.2.0
langchain-google-vertexai==1.0.0
google-cloud-aiplatform==1.60.0
```

### 3. Initialize Spanner Graph

```python
from src.integrations.spanner_graph_client import SpannerGraphClient

# Initialize client
graph_client = SpannerGraphClient({
    "project_id": "leafloafai",
    "instance_id": "leafloaf-graph",
    "database_id": "leafloaf-graphrag"
})

await graph_client.initialize()
```

### 4. Create Graph Schema

The schema combines:
- **Nodes**: Users, Products, Orders
- **Edges**: OrderItems, ProductRelationships
- **GraphRAG**: Episodes for context

```sql
-- Create property graph
CREATE OR REPLACE PROPERTY GRAPH UserShoppingGraph
NODE TABLES (
    Users KEY (user_id),
    Products KEY (sku),
    Orders KEY (order_id)
)
EDGE TABLES (
    OrderItems KEY (order_id, sku),
    ProductRelationships KEY (product1_sku, product2_sku)
)
```

### 5. Implement Use Cases

#### "My Usual Order"
```python
async def get_usual_order(user_id: str):
    patterns = await graph_client.get_reorder_patterns(user_id)
    
    # GraphRAG search for context
    result = await graph_client.graphrag_search(
        query="What are my regular monthly purchases?",
        user_id=user_id
    )
    
    return {
        "patterns": patterns,
        "ai_summary": result["answer"]
    }
```

#### "Like Last Time"
```python
async def repeat_last_order(user_id: str, product_hint: str):
    # Use GQL for graph query
    query = """
    GRAPH UserShoppingGraph
    MATCH (u:Users {user_id: @user_id})-[:PLACED]->(o:Orders)-[:CONTAINS]->(p:Products)
    WHERE p.name CONTAINS @product_hint
    RETURN p, o ORDER BY o.order_timestamp DESC LIMIT 1
    """
    
    # Execute with Vertex AI enhancement
    result = await graph_client.graphrag_search(
        query=f"I need {product_hint} like last time",
        user_id=user_id
    )
    
    return result
```

#### Event-Based Shopping
```python
async def get_event_suggestions(user_id: str, event_type: str):
    # GraphRAG understands context
    result = await graph_client.graphrag_search(
        query=f"What did I order for my last {event_type}?",
        user_id=user_id
    )
    
    return result
```

### 6. Update Memory Manager

```python
# src/memory/memory_manager_v2.py
class EnhancedMemoryManager:
    def __init__(self):
        self.session_memory = SessionMemory()
        self.graph_client = SpannerGraphClient()
    
    async def process_conversation(self, user_id: str, message: str):
        # Add to graph as episode
        episode_id = await self.graph_client.add_episode(
            user_id=user_id,
            content=message,
            episode_type="conversation"
        )
        
        # Get GraphRAG context
        context = await self.graph_client.graphrag_search(
            query=message,
            user_id=user_id
        )
        
        return context
```

### 7. Update Agents

```python
# In supervisor.py
if has_graphrag_keyword:
    # Use Spanner Graph instead of Graphiti
    context = await graph_client.graphrag_search(
        query=query,
        user_id=user_id
    )
    
    if "usual" in query_lower:
        intent = "usual_order"
        metadata = {"graph_context": context}
```

## Migration Path

### Phase 1: Parallel Testing (Week 1)
- Deploy Spanner instance
- Migrate subset of users
- Compare results with existing system

### Phase 2: Gradual Migration (Week 2-3)
- Route new users to Spanner
- Migrate historical data in batches
- Monitor performance

### Phase 3: Full Cutover (Week 4)
- Switch all traffic to Spanner
- Decommission Neo4j
- Optimize based on metrics

## Performance Optimization

### 1. Indexes
```sql
-- Optimize common queries
CREATE INDEX idx_orders_user_time 
ON Orders(user_id, order_timestamp DESC);

CREATE INDEX idx_products_embedding 
ON Products(embedding) 
WHERE embedding IS NOT NULL;
```

### 2. Partitioning
```sql
-- Partition orders by month
ALTER TABLE Orders 
SET OPTIONS (
  partition_retention_period = "365d"
);
```

### 3. Caching
```python
# Use Memorystore for hot data
from google.cloud import memcache

cache = memcache.Client()
cache.set(f"user_patterns:{user_id}", patterns, 3600)
```

## Monitoring

### 1. Built-in Metrics
- Query latency
- Transaction throughput
- Node CPU usage
- Storage growth

### 2. Custom Dashboards
```yaml
# monitoring/spanner-graph-dashboard.yaml
widgets:
  - query: |
      fetch spanner_instance
      | metric 'spanner.googleapis.com/instance/cpu/utilization'
      | filter resource.instance_id == 'leafloaf-graph'
```

### 3. Alerts
```yaml
# monitoring/alerts.yaml
- name: high-latency
  condition: |
    metric.type="spanner.googleapis.com/instance/api/request_latencies"
    AND metric.value > 100ms
```

## Security

### 1. IAM Roles
```bash
# Grant minimal permissions
gcloud spanner databases add-iam-policy-binding leafloaf-graphrag \
  --instance=leafloaf-graph \
  --member="serviceAccount:leafloaf-api@leafloafai.iam.gserviceaccount.com" \
  --role="roles/spanner.databaseUser"
```

### 2. VPC Service Controls
```yaml
# Restrict access to internal only
accessPolicies:
  - name: leafloaf-spanner-vpc
    serviceName: spanner.googleapis.com
    allowedSourceIPs: ["10.0.0.0/8"]
```

### 3. Encryption
- At-rest: Automatic with Google-managed keys
- In-transit: TLS 1.3 enforced
- Column-level: For sensitive data

## Cost Optimization

### 1. Node Configuration
```bash
# Start with 1 node, scale as needed
gcloud spanner instances update leafloaf-graph \
  --nodes=1

# Use autoscaling for production
gcloud spanner instances update leafloaf-graph \
  --autoscaling-min-nodes=1 \
  --autoscaling-max-nodes=3 \
  --autoscaling-cpu-target=65
```

### 2. Committed Use Discounts
```bash
# 1-year commitment saves 25%
gcloud compute commitments create leafloaf-spanner \
  --plan=TWELVE_MONTH \
  --resources=vcpu=4,memory=15GB
```

### 3. Storage Optimization
- Archive old orders to Cloud Storage
- Use TTL for episodes
- Compress large JSON fields

## Testing

### 1. Unit Tests
```python
# tests/test_spanner_graph.py
async def test_reorder_patterns():
    client = SpannerGraphClient()
    
    # Add test data
    await client.add_order({
        "order_id": "TEST001",
        "user_id": "test_user",
        "items": [{"sku": "RICE001", "name": "Basmati Rice"}]
    })
    
    # Test pattern detection
    patterns = await client.get_reorder_patterns("test_user")
    assert len(patterns) > 0
```

### 2. Integration Tests
```python
# tests/test_graphrag_integration.py
async def test_usual_order_flow():
    # Test complete flow
    result = await graph_client.graphrag_search(
        "I need my usual order",
        "test_user"
    )
    
    assert "Basmati Rice" in result["answer"]
```

### 3. Load Tests
```bash
# Use Locust for load testing
locust -f tests/load_test_spanner.py \
  --users 100 \
  --spawn-rate 10 \
  --host https://leafloaf-api.com
```

## Troubleshooting

### Common Issues

1. **Slow Queries**
   - Check query execution plan
   - Add appropriate indexes
   - Use query hints if needed

2. **Connection Errors**
   - Verify IAM permissions
   - Check VPC configuration
   - Ensure Spanner API is enabled

3. **High Costs**
   - Monitor node utilization
   - Enable autoscaling
   - Archive old data

## Next Steps

1. **Week 1**: Set up Spanner instance and schema
2. **Week 2**: Implement GraphRAG integration
3. **Week 3**: Migrate pilot users
4. **Week 4**: Full production rollout

## Resources

- [Spanner Graph Documentation](https://cloud.google.com/spanner/docs/graph)
- [LangChain Spanner Integration](https://python.langchain.com/docs/integrations/graphs/google_spanner)
- [Vertex AI with Spanner](https://cloud.google.com/spanner/docs/vertex-ai-integration)
- [GraphRAG Tutorial](https://github.com/GoogleCloudPlatform/spanner-graph-graphrag-langchain)

---

**Bottom Line**: Spanner Graph provides everything Neo4j + Graphiti offers, but at 50-60% lower cost with better GCP integration. The native Vertex AI integration eliminates external LLM costs while providing superior performance.