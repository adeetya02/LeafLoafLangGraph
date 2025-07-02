# 🚀 Spanner Graph Quick Start Guide

## Prerequisites

1. **Authenticate with GCP**:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   gcloud config set project leafloafai
   ```

2. **Install dependencies**:
   ```bash
   pip install google-cloud-spanner google-cloud-aiplatform vertexai
   ```

## Step 1: Create Spanner Instance

Run the setup script:
```bash
./setup_spanner_graph.sh
```

Or manually:
```bash
# Enable APIs
gcloud services enable spanner.googleapis.com aiplatform.googleapis.com

# Create instance (starts at ~$72/month)
gcloud spanner instances create leafloaf-graph \
  --config=regional-us-central1 \
  --description="LeafLoaf GraphRAG" \
  --nodes=1

# Create database
gcloud spanner databases create leafloaf-graphrag \
  --instance=leafloaf-graph
```

## Step 2: Create Schema

```bash
python create_spanner_schema.py
```

This creates:
- Users, Products, Orders tables
- Graph relationships (OrderItems, ProductRelationships)
- Episodes for GraphRAG context
- Optimized indexes

## Step 3: Run Tests

```bash
python test_spanner_graph_gcp.py
```

This tests:
- ✅ Connectivity
- ✅ Data insertion
- ✅ Graph queries
- ✅ Vertex AI integration
- ✅ GraphRAG use cases
- ✅ Performance (<100ms queries)

## Step 4: Monitor Costs

Check costs in Cloud Console:
- Spanner: ~$72/month (1 node)
- Storage: ~$0.30/GB/month
- Vertex AI: Included in API calls

## Step 5: Integration

Update your LeafLoaf code:

```python
from src.integrations.spanner_graph_client import SpannerGraphClient

# Initialize
graph_client = SpannerGraphClient()
await graph_client.initialize()

# Use GraphRAG
result = await graph_client.graphrag_search(
    "What are my usual groceries?",
    user_id="user123"
)
```

## 🎯 Quick Commands

```bash
# View instance details
gcloud spanner instances describe leafloaf-graph

# Connect with gcloud CLI
gcloud spanner databases execute-sql leafloaf-graphrag \
  --instance=leafloaf-graph \
  --sql="SELECT COUNT(*) FROM Users"

# Monitor performance
gcloud spanner instances operations list --instance=leafloaf-graph

# Scale up/down
gcloud spanner instances update leafloaf-graph --nodes=2  # Scale up
gcloud spanner instances update leafloaf-graph --nodes=1  # Scale down

# Delete (when done testing)
gcloud spanner databases delete leafloaf-graphrag --instance=leafloaf-graph
gcloud spanner instances delete leafloaf-graph
```

## 💰 Cost Management

1. **Start with 1 node** (~$72/month)
2. **Enable autoscaling** for production:
   ```bash
   gcloud spanner instances update leafloaf-graph \
     --autoscaling-min-nodes=1 \
     --autoscaling-max-nodes=3 \
     --autoscaling-cpu-target=65
   ```

3. **Use committed use discounts** (save 25%):
   ```bash
   # After testing, commit for savings
   gcloud compute commitments create spanner-commitment \
     --plan=TWELVE_MONTH \
     --resources=vcpu=2,memory=7.5GB
   ```

## 🔍 Verify Everything Works

1. **Check Spanner Console**: 
   https://console.cloud.google.com/spanner/instances/leafloaf-graph

2. **Run a test query**:
   ```sql
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = '';
   ```

3. **Test Vertex AI**:
   ```python
   import vertexai
   from vertexai.generative_models import GenerativeModel
   
   vertexai.init(project="leafloafai", location="us-central1")
   model = GenerativeModel("gemini-1.5-pro")
   response = model.generate_content("Test")
   print(response.text)
   ```

## ✅ Success Indicators

- Spanner instance shows "Running" status
- All 7 tables created
- Test script passes all 6 tests
- Queries return in <100ms
- Vertex AI responds correctly

## 🆘 Troubleshooting

**"Permission denied"**: 
```bash
gcloud projects add-iam-policy-binding leafloafai \
  --member="user:YOUR_EMAIL" \
  --role="roles/spanner.admin"
```

**"API not enabled"**:
```bash
gcloud services enable spanner.googleapis.com
```

**"Quota exceeded"**:
- Check quotas in Console
- Request increase if needed

## 🎉 Next Steps

1. **Integrate into LeafLoaf agents**
2. **Set up monitoring alerts**
3. **Implement caching layer**
4. **Add more graph relationships**
5. **Enable audit logging**

---

**Remember**: You're saving ~$175/month compared to Neo4j + Graphiti!