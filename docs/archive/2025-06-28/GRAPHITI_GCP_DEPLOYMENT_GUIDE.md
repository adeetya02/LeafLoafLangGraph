# 🚀 Graphiti + Neo4j GCP Deployment Guide for LeafLoaf

## Overview

Based on research, **Graphiti requires Neo4j 5.26+** as its graph database backend. This guide covers deploying a production-ready Graphiti + Neo4j setup on Google Cloud Platform.

## 📊 Graph Database Decision

### Why Neo4j for Graphiti?
- **Required**: Graphiti is built specifically for Neo4j (5.26+)
- **Temporal Support**: Bi-temporal model tracking (when events occurred vs ingested)
- **Mature Ecosystem**: Best tooling and support
- **GCP Integration**: Available via AuraDB or self-managed

### Alternative Considerations
While other graph databases exist (FalkorDB, TigerGraph, Amazon Neptune), Graphiti specifically requires Neo4j, making this the clear choice.

## 🏗️ Deployment Options on GCP

### Option 1: Neo4j AuraDB (Recommended for Production)
**Fully managed, auto-scaling, zero-maintenance**

#### Pros:
- No infrastructure management
- Automatic backups and updates
- Built-in monitoring
- Pay-as-you-go pricing
- GCP Marketplace integration

#### Setup Steps:
```bash
# 1. Go to GCP Marketplace
# Search for "Neo4j AuraDB"

# 2. Create AuraDB instance
# - Select region (us-central1 for LeafLoaf)
# - Choose tier (Professional for production)
# - Enable GCP billing integration

# 3. Get connection details
# - Bolt URL: neo4j+s://xxxxx.databases.neo4j.io
# - Username: neo4j
# - Password: (generated)
```

### Option 2: Self-Managed Neo4j on GCE
**More control, requires maintenance**

#### Deployment via Terraform:
```hcl
# terraform/neo4j-gce.tf
resource "google_compute_instance" "neo4j" {
  name         = "leafloaf-neo4j"
  machine_type = "n2-standard-4"  # 4 vCPU, 16GB RAM
  zone         = "us-central1-a"

  boot_disk {
    initialize_params {
      image = "neo4j-public/neo4j-enterprise-5-26"
      size  = 100  # GB
      type  = "pd-ssd"
    }
  }

  network_interface {
    network = "default"
    access_config {
      // Ephemeral IP
    }
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    # Configure Neo4j
    echo "dbms.default_listen_address=0.0.0.0" >> /etc/neo4j/neo4j.conf
    echo "dbms.security.auth_enabled=true" >> /etc/neo4j/neo4j.conf
    echo "dbms.memory.heap.initial_size=4G" >> /etc/neo4j/neo4j.conf
    echo "dbms.memory.heap.max_size=8G" >> /etc/neo4j/neo4j.conf
    
    # Set initial password
    neo4j-admin dbms set-initial-password "${var.neo4j_password}"
    
    # Start Neo4j
    systemctl enable neo4j
    systemctl start neo4j
  EOF

  tags = ["neo4j", "graphiti"]
}

# Firewall rules
resource "google_compute_firewall" "neo4j" {
  name    = "allow-neo4j"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["7474", "7687"]  # HTTP and Bolt
  }

  source_ranges = ["10.0.0.0/8"]  # Internal only
  target_tags   = ["neo4j"]
}
```

### Option 3: Neo4j in GKE (Kubernetes)
**Best for microservices architecture**

```yaml
# k8s/neo4j-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: neo4j
spec:
  serviceName: neo4j
  replicas: 3  # For cluster
  selector:
    matchLabels:
      app: neo4j
  template:
    metadata:
      labels:
        app: neo4j
    spec:
      containers:
      - name: neo4j
        image: neo4j:5.26-enterprise
        ports:
        - containerPort: 7474
          name: http
        - containerPort: 7687
          name: bolt
        - containerPort: 6000
          name: tx
        - containerPort: 7000
          name: raft
        env:
        - name: NEO4J_AUTH
          valueFrom:
            secretKeyRef:
              name: neo4j-auth
              key: password
        - name: NEO4J_ACCEPT_LICENSE_AGREEMENT
          value: "yes"
        - name: NEO4J_server_memory_heap_max__size
          value: "4G"
        volumeMounts:
        - name: data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "pd-ssd"
      resources:
        requests:
          storage: 100Gi
```

## 🔧 Graphiti Configuration

### 1. Install Graphiti
```bash
pip install graphiti-core
```

### 2. Environment Configuration
```yaml
# .env.production.yaml
# Neo4j Configuration
NEO4J_URI: "neo4j+s://xxxxx.databases.neo4j.io"  # For AuraDB
# NEO4J_URI: "bolt://10.x.x.x:7687"  # For self-managed
NEO4J_USERNAME: "neo4j"
NEO4J_PASSWORD: "${SECRET_NEO4J_PASSWORD}"
NEO4J_DATABASE: "neo4j"

# Graphiti Configuration
GRAPHITI_LOG_LEVEL: "INFO"
GRAPHITI_BATCH_SIZE: 500
GRAPHITI_TEMPORAL_AWARE: "true"

# LLM Configuration (for entity extraction)
OPENAI_API_KEY: "${SECRET_OPENAI_API_KEY}"
AZURE_OPENAI_ENDPOINT: "https://leafloaf.openai.azure.com/"
AZURE_OPENAI_API_KEY: "${SECRET_AZURE_OPENAI_KEY}"
```

### 3. Update LeafLoaf Integration
```python
# src/integrations/graphiti_client.py
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
import os

class GraphitiClient:
    def __init__(self):
        self.graphiti = Graphiti(
            neo4j_uri=os.getenv("NEO4J_URI"),
            neo4j_user=os.getenv("NEO4J_USERNAME"),
            neo4j_password=os.getenv("NEO4J_PASSWORD"),
            llm_provider="azure_openai",  # or "openai"
            embedding_provider="azure_openai"
        )
    
    async def initialize(self):
        """Initialize Graphiti and create indexes"""
        await self.graphiti.build_indices()
    
    async def add_episode(self, user_id: str, content: str, episode_type: EpisodeType):
        """Add an episode (conversation/order/event) to the graph"""
        await self.graphiti.add_episode(
            name=f"user_{user_id}",
            episode_body=content,
            source_description=f"LeafLoaf {episode_type.value}",
            reference_time=datetime.utcnow(),
            episode_type=episode_type
        )
    
    async def search(self, query: str, user_id: str):
        """Search the knowledge graph"""
        return await self.graphiti.search(
            query=query,
            namespace=f"user_{user_id}",
            num_results=10
        )
    
    async def get_context(self, user_id: str):
        """Get full context for a user"""
        return await self.graphiti.retrieve_episodes(
            namespace=f"user_{user_id}",
            reference_time=datetime.utcnow()
        )
```

## 📈 Performance Optimization

### 1. Neo4j Tuning for Graphiti
```conf
# neo4j.conf optimizations
dbms.memory.heap.initial_size=8G
dbms.memory.heap.max_size=16G
dbms.memory.pagecache.size=8G

# Query cache
dbms.query_cache_size=20

# Indexes for Graphiti patterns
CREATE INDEX node_name_index FOR (n:Node) ON (n.name);
CREATE INDEX edge_valid_time FOR ()-[r:RELATES_TO]-() ON (r.valid_from, r.valid_to);
CREATE INDEX episode_type FOR (e:Episode) ON (e.type);
CREATE FULLTEXT INDEX entity_search FOR (n:Entity) ON EACH [n.name, n.description];
```

### 2. Connection Pooling
```python
# Use connection pooling for high throughput
from neo4j import AsyncGraphDatabase

driver = AsyncGraphDatabase.driver(
    uri,
    auth=(username, password),
    max_connection_pool_size=100,
    connection_acquisition_timeout=60,
    max_transaction_retry_time=30
)
```

## 🚦 Monitoring & Observability

### 1. Neo4j Metrics to Monitor
- Query execution time
- Memory usage (heap & page cache)
- Transaction throughput
- Connection pool utilization

### 2. GCP Monitoring Setup
```yaml
# monitoring/neo4j-dashboard.yaml
apiVersion: monitoring.dashboard/v1
kind: Dashboard
metadata:
  name: neo4j-graphiti-metrics
spec:
  tiles:
    - query: |
        fetch gce_instance
        | metric 'compute.googleapis.com/instance/cpu/utilization'
        | filter resource.instance_name =~ 'neo4j.*'
    - query: |
        fetch gce_instance
        | metric 'compute.googleapis.com/instance/memory/utilization'
        | filter resource.instance_name =~ 'neo4j.*'
```

## 💰 Cost Estimation

### AuraDB Professional (Managed)
- **Base**: ~$65/month (0.5 GB RAM, 2 GB storage)
- **Production**: ~$300-500/month (8 GB RAM, 100 GB storage)
- **Scaling**: Automatic, pay per use

### Self-Managed on GCE
- **VM**: n2-standard-4 ~$140/month
- **Storage**: 100GB SSD ~$17/month
- **Backup**: Cloud Storage ~$5/month
- **Total**: ~$162/month + management overhead

## 🔐 Security Best Practices

1. **Network Security**
   - Use Private Service Connect for AuraDB
   - VPC peering for self-managed
   - Firewall rules limiting access

2. **Authentication**
   - Use service accounts for GCP resources
   - Rotate Neo4j passwords regularly
   - Enable SSL/TLS for all connections

3. **Data Protection**
   - Enable encryption at rest
   - Regular automated backups
   - Point-in-time recovery

## 🚀 Production Checklist

- [ ] Choose deployment option (AuraDB recommended)
- [ ] Set up Neo4j instance with proper sizing
- [ ] Configure Graphiti with Neo4j connection
- [ ] Create necessary indexes
- [ ] Set up monitoring and alerts
- [ ] Configure automated backups
- [ ] Test failover scenarios
- [ ] Document connection strings
- [ ] Set up CI/CD for schema migrations
- [ ] Performance test with expected load

## 📚 Next Steps

1. **Test Locally First**
   ```bash
   docker run -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/testpassword \
     neo4j:5.26
   ```

2. **Deploy to GCP Staging**
   - Start with smallest AuraDB instance
   - Test Graphiti integration
   - Monitor performance

3. **Production Deployment**
   - Size based on load tests
   - Enable all security features
   - Set up alerting

## 🆘 Troubleshooting

### Common Issues:
1. **Connection timeouts**: Check firewall rules and network connectivity
2. **Memory errors**: Increase heap/page cache sizes
3. **Slow queries**: Add indexes, check query plans
4. **Version mismatch**: Ensure Neo4j 5.26+ for Graphiti

### Support Resources:
- Neo4j Community: https://community.neo4j.com/
- Graphiti GitHub: https://github.com/getzep/graphiti
- GCP Support: Via console for marketplace deployments

---

**Remember**: Graphiti requires Neo4j 5.26+. Don't use Community Edition for production as it lacks certain features Graphiti needs.