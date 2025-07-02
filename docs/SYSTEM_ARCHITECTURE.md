# LeafLoaf System Architecture

## Overview
LeafLoaf is a production-grade grocery shopping system built with a multi-agent architecture, competing with major industry players through advanced AI and personalization.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
├─────────────────┬────────────────┬──────────────────────────────┤
│   Web App       │  Mobile App    │    Voice (11Labs)            │
└────────┬────────┴───────┬────────┴────────┬─────────────────────┘
         │                │                 │
         └────────────────┴─────────────────┘
                          │
                    ┌─────▼─────┐
                    │  FastAPI  │
                    │   /graph   │
                    └─────┬─────┘
                          │
         ┌────────────────▼────────────────┐
         │      LangGraph Supervisor       │
         │    (with Graphiti Memory)       │
         └────┬──────────┬──────────┬──────┘
              │          │          │
     ┌────────▼───┐ ┌───▼─────┐ ┌──▼──────────┐
     │  Product   │ │  Order  │ │  Response   │
     │  Search    │ │  Agent  │ │  Compiler   │
     └──────┬─────┘ └────┬────┘ └──────┬──────┘
            │            │              │
     ┌──────▼─────────┐  │              │
     │ Personalized   │  │              │
     │    Ranker      │  │              │
     └────────────────┘  │              │
                         │              │
                ┌────────▼────────┐     │
                │ MyUsualAnalyzer │     │
                ├─────────────────┤     │
                │    Reorder      │     │
                │  Intelligence   │     │
                └─────────────────┘     │
                                       │
┌──────────────────────────────────────▼───────────────────────────┐
│                        Data Layer                                 │
├──────────┬──────────┬──────────┬──────────┬────────────────────┤
│ Weaviate │  Redis   │ Spanner │ BigQuery │ Cloud Storage      │
│(Products)│ (Cache)  │(Graphiti)│(Analytics)│  (Backup)         │
└──────────┴──────────┴──────────┴──────────┴────────────────────┘
```

## Component Details

### 1. API Layer (FastAPI)
- **Location**: `src/api/main.py`
- **Endpoints**:
  - `POST /graph/invoke` - Main interaction endpoint
  - `POST /webhooks/elevenlabs` - Voice integration
  - `GET /health` - System health check
- **Features**:
  - Request validation
  - Authentication
  - Rate limiting
  - Response formatting

### 2. Orchestration Layer (LangGraph)
- **Location**: `src/core/graph.py`
- **Components**:
  - **Supervisor Agent**: Routes queries, manages state
  - **Product Search Agent**: Handles product queries
  - **Order Agent**: Manages cart operations
  - **Response Compiler**: Formats final responses

### 3. Personalization Components

#### PersonalizedRanker
- **Location**: `src/agents/personalized_ranker.py`
- **Functionality**:
  - Re-ranks search results based on user history
  - Applies brand preferences
  - Considers price sensitivity
  - Respects dietary restrictions
- **Performance**: <100ms for 100 products

#### MyUsualAnalyzer
- **Location**: `src/agents/my_usual_analyzer.py`
- **Functionality**:
  - Detects frequently purchased items
  - Remembers typical quantities
  - Creates one-click baskets
  - Tracks seasonal variations
- **Performance**: <50ms for analysis

#### ReorderIntelligence
- **Location**: `src/agents/reorder_intelligence.py`
- **Functionality**:
  - Calculates reorder cycles
  - Predicts due dates
  - Suggests bundles
  - Adjusts for holidays
- **Performance**: <100ms for 200 orders

### 4. Data Storage

#### Weaviate (Vector Database)
- **Purpose**: Product catalog and semantic search
- **Schema**:
  ```json
  {
    "class": "GroceryProduct",
    "properties": [
      {"name": "name", "dataType": ["text"]},
      {"name": "description", "dataType": ["text"]},
      {"name": "price", "dataType": ["number"]},
      {"name": "category", "dataType": ["text"]},
      {"name": "dietary_tags", "dataType": ["text[]"]}
    ]
  }
  ```

#### Redis (Cache)
- **Purpose**: Session management and preference caching
- **TTL Strategy**:
  - User preferences: 5 minutes
  - Session data: 30 minutes
  - Search results: 2 minutes

#### Spanner (Graphiti Backend)
- **Purpose**: Graph-based memory storage
- **Tables**:
  - `entities`: User and product entities
  - `relationships`: Purchase patterns
  - `memories`: Interaction history

#### BigQuery (Analytics)
- **Purpose**: Event tracking and ML features
- **Datasets**:
  - `raw_events`: All user interactions
  - `user_behavior`: Aggregated patterns
  - `ml_features`: Recommendation data

## Data Flow Examples

### 1. Personalized Search Flow
```
1. User: "organic milk"
   ↓
2. API validates request, adds user context
   ↓
3. Supervisor loads user preferences from Redis/Memory
   ↓
4. Product Search queries Weaviate
   ↓
5. PersonalizedRanker re-ranks results:
   - Checks purchase history
   - Applies brand preferences
   - Considers price range
   ↓
6. Response Compiler adds personalization data:
   - Usual milk suggestion
   - Reorder reminder
   - Complementary products
   ↓
7. Response sent to user
   ↓
8. Event logged to BigQuery
```

### 2. My Usual Order Flow
```
1. User: "add my usual items"
   ↓
2. Supervisor detects intent
   ↓
3. Order Agent invokes MyUsualAnalyzer
   ↓
4. Analyzer queries purchase history:
   - Calculates frequency
   - Determines quantities
   - Checks confidence
   ↓
5. Creates smart basket
   ↓
6. Adds items to cart
   ↓
7. Updates reorder cycles
```

## Performance Architecture

### Caching Strategy
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │     │    Redis    │     │   Memory    │
│   Cache     │────▶│    Cache    │────▶│   Cache     │
└─────────────┘     └─────────────┘     └─────────────┘
                            │
                            ▼
                    ┌─────────────┐
                    │  Database   │
                    └─────────────┘
```

### Async Processing
- All personalization operations are async
- Parallel processing for multiple features
- Non-blocking I/O throughout

### Performance Budgets
| Component | Budget | Actual |
|-----------|--------|--------|
| API Gateway | 20ms | 15ms |
| Supervisor | 30ms | 25ms |
| Search + Personalization | 150ms | 125ms |
| Response Compilation | 50ms | 40ms |
| **Total** | **250ms** | **205ms** |

## Security Architecture

### Authentication Flow
```
Client → API Key → JWT Token → Request Context
                        ↓
                  Rate Limiter
                        ↓
                  Authorization
                        ↓
                   Processing
```

### Data Privacy
- User preferences stored separately
- PII encryption at rest
- Audit logging for access
- GDPR compliance built-in

## Deployment Architecture

### Google Cloud Platform
```
┌─────────────────────────────────────────┐
│           Cloud Load Balancer           │
└────────────────┬───────────────────────┘
                 │
     ┌───────────▼───────────┐
     │    Cloud Run          │
     │  (Auto-scaling)       │
     └───────────┬───────────┘
                 │
┌────────────────┼────────────────────────┐
│                │                        │
│  ┌─────────────▼──────────┐  ┌────────▼────────┐
│  │    Weaviate Cluster    │  │  Redis Cluster  │
│  └────────────────────────┘  └─────────────────┘
│                                                  │
│  ┌────────────────────────┐  ┌─────────────────┐
│  │   Spanner Instance     │  │    BigQuery     │
│  └────────────────────────┘  └─────────────────┘
└─────────────────────────────────────────────────┘
```

### Scaling Strategy
- **Horizontal Scaling**: Cloud Run auto-scales based on load
- **Database Scaling**: 
  - Weaviate: Clustered deployment
  - Redis: Master-replica setup
  - Spanner: Regional configuration
- **Caching**: Multi-tier to reduce database load

## Monitoring & Observability

### Metrics Collection
```
Application → OpenTelemetry → Cloud Monitoring
                   ↓
            Prometheus Metrics
                   ↓
             Grafana Dashboards
```

### Key Metrics
1. **Business Metrics**
   - Personalization adoption rate
   - Reorder frequency increase
   - Basket size improvement

2. **Technical Metrics**
   - Response time percentiles
   - Cache hit rates
   - Error rates by component

3. **Personalization Metrics**
   - Feature usage by user
   - Confidence score distribution
   - Ranking improvement metrics

## Development Workflow

### Local Development
```bash
# Start dependencies
docker-compose up -d

# Run application
python run.py

# Run tests
python run_all_personalization_tests.py
```

### CI/CD Pipeline
```
GitHub Push → Cloud Build → Run Tests → Deploy to Staging → Integration Tests → Deploy to Production
```

## Future Architecture Enhancements

### 1. ML Model Service
```
┌─────────────────┐
│  Vertex AI      │
│  Endpoints      │
├─────────────────┤
│ • Embeddings    │
│ • Ranking       │
│ • Next-item     │
└─────────────────┘
```

### 2. Event Streaming
```
API → Pub/Sub → Dataflow → BigQuery
         ↓
    Real-time ML
```

### 3. Edge Caching
```
CloudFlare Workers → Regional Cache → Origin
```

## Disaster Recovery

### Backup Strategy
- **Weaviate**: Daily snapshots to Cloud Storage
- **Redis**: AOF persistence + snapshots
- **Spanner**: Automated backups with PITR
- **BigQuery**: Dataset snapshots

### Failover Plan
1. **Primary Region Down**: Automatic failover to secondary
2. **Database Failure**: Read from replicas
3. **Cache Failure**: Direct database access
4. **Complete Outage**: Static maintenance page

## Cost Optimization

### Resource Allocation
- **Compute**: Cloud Run scales to zero
- **Storage**: Lifecycle policies for old data
- **Caching**: Reduces database queries by 70%
- **Batch Processing**: Off-peak for analytics

### Monitoring Costs
- Budget alerts at 50%, 80%, 100%
- Cost attribution by feature
- Regular optimization reviews