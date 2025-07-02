# Gemma Model Garden Deployment Guide

## 🚀 Optimal Configuration for <100ms Latency

### 1. Model Selection
- **Model**: Gemma 2 9B-it (Instruction-tuned)
- **Alternative**: Gemma 2 2B-it (faster but less capable)

### 2. Hardware Configuration
```yaml
Machine Type: n1-standard-8  # 8 vCPUs, 30GB RAM
Accelerator: NVIDIA Tesla T4  # Critical for low latency
Accelerator Count: 1

# For even lower latency (if budget allows):
# Machine Type: n1-standard-16
# Accelerator: NVIDIA V100
```

### 3. Deployment Settings
```yaml
Min Replicas: 1  # Prevents cold starts
Max Replicas: 3  # Auto-scale for load
Region: us-central1  # Match your Cloud Run region!

# Enable these features:
- Enable request-response logging
- Enable automatic scaling
- Enable private endpoint (if possible)
```

### 4. Model Configuration
```python
# In the Model Garden deployment UI:
parameters = {
    "temperature": 0.1,      # Low for consistency
    "max_output_tokens": 100,  # Keep small for speed
    "top_k": 10,            # Limit sampling
    "top_p": 0.9
}
```

### 5. Network Optimization

#### Option A: Private Service Connect (Recommended)
```bash
# After deployment, enable private endpoint
gcloud ai endpoints update YOUR_NEW_ENDPOINT_ID \
  --region=us-central1 \
  --enable-private-service-connect

# This keeps traffic within Google's network
# Reduces latency by ~50-100ms
```

#### Option B: VPC Peering
- If your Cloud Run is in a VPC
- Configure VPC peering with AI Platform

### 6. Post-Deployment Optimization

```python
# Update your client code with new endpoint
class GemmaOptimizedClient:
    def __init__(self):
        self.endpoint_id = "YOUR_NEW_ENDPOINT_ID"  # Update this
        self.endpoint_domain = f"{self.endpoint_id}.us-central1-aiplatform.googleapis.com"
        
        # Enable HTTP/2 for better performance
        self.client = httpx.AsyncClient(
            timeout=5.0,  # Reduce timeout since latency should be low
            http2=True,   # Enable HTTP/2
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            )
        )
```

### 7. Expected Latencies

| Configuration | Expected Latency |
|--------------|------------------|
| Current (CPU, Public) | 700-900ms |
| GPU (T4) | 150-250ms |
| GPU + Private Connect | 100-150ms |
| GPU + Same Region + Private | 50-100ms |
| V100 + Optimizations | 30-50ms |

### 8. Monitoring & Alerts

```bash
# Set up latency monitoring
gcloud monitoring policies create \
  --notification-channels=YOUR_CHANNEL \
  --display-name="Gemma High Latency" \
  --condition-display-name="Response > 150ms" \
  --condition-expression='
    resource.type="aiplatform.googleapis.com/Endpoint"
    AND metric.type="aiplatform.googleapis.com/prediction/latencies"
    AND metric.value > 150'
```

### 9. Testing After Deployment

```python
# Run this test to verify performance
async def test_new_endpoint():
    client = GemmaOptimizedClient()  # With new endpoint
    
    # Warm up
    await client.analyze_query("test")
    
    # Test latency
    latencies = []
    for query in ["milk", "add rice", "show cart"]:
        start = time.time()
        await client.analyze_query(query)
        latencies.append((time.time() - start) * 1000)
    
    avg_latency = sum(latencies) / len(latencies)
    print(f"Average latency: {avg_latency:.0f}ms")
    
    if avg_latency < 150:
        print("✅ Deployment successful!")
    else:
        print("⚠️ Latency still high, check configuration")
```

### 10. Fallback Strategy

Keep current endpoint as fallback:
```python
async def analyze_with_fallback(query):
    try:
        # Try new fast endpoint first
        result = await new_client.analyze_query(query)
        if result.latency_ms < 150:
            return result
    except:
        pass
    
    # Fallback to current endpoint
    return await current_client.analyze_query(query)
```

## 📋 Deployment Checklist

- [ ] Select Gemma 2 9B-it in Model Garden
- [ ] Configure n1-standard-8 + Tesla T4
- [ ] Set min_replicas = 1
- [ ] Deploy in us-central1 (or your app's region)
- [ ] Note down new endpoint ID
- [ ] Enable Private Service Connect
- [ ] Update client code with new endpoint
- [ ] Test latency < 150ms
- [ ] Set up monitoring alerts
- [ ] Keep old endpoint as fallback

## 🎯 Target Metrics

- **P50 Latency**: < 80ms
- **P95 Latency**: < 150ms
- **P99 Latency**: < 200ms
- **Error Rate**: < 0.1%
- **Availability**: > 99.9%