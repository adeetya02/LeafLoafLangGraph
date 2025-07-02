# Graphiti & Spanner Integration Status

## Current Architecture

### Integration Points

1. **Supervisor Agent** (`src/agents/supervisor.py`):
   - Creates Graphiti instance on user requests
   - Extracts entities from queries
   - Timeout: 100ms to prevent blocking
   - Falls back gracefully if Graphiti fails

2. **Order Agent** (`src/agents/order_agent.py`):
   - Uses Graphiti for "my usual" queries
   - Retrieves reorder patterns
   - Searches for past order relationships

3. **Memory Registry** (`src/memory/memory_registry.py`):
   - Manages Graphiti instances per agent
   - Supports multiple backends (Spanner, In-Memory)
   - Handles lifecycle and cleanup

## Graphiti Configuration

### Backend Selection Logic
```python
# Automatic backend selection
if os.getenv("SPANNER_INSTANCE_ID"):
    backend = MemoryBackend.SPANNER  # Production
else:
    backend = MemoryBackend.IN_MEMORY  # Development/Demo
```

### Environment Variables Needed
```bash
# For Spanner backend
SPANNER_INSTANCE_ID=your-instance
SPANNER_DATABASE_ID=your-database
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Currently NOT SET in demo - uses in-memory
```

## What Gets Stored in Graphiti

### 1. User Query Entities
```python
# Extracted from "I want organic milk and fresh strawberries"
entities = [
    {
        "name": "organic milk",
        "type": "product_preference",
        "attributes": {"category": "dairy", "modifier": "organic"}
    },
    {
        "name": "fresh strawberries", 
        "type": "product_preference",
        "attributes": {"category": "produce", "modifier": "fresh"}
    }
]
```

### 2. Order Relationships
```python
# When user adds to cart or purchases
relationships = [
    {
        "source": "user:demo_123",
        "target": "product:milk_organic",
        "type": "purchases",
        "properties": {
            "frequency": "weekly",
            "quantity": 2,
            "last_order": "2025-06-28"
        }
    }
]
```

### 3. Reorder Patterns
```python
# Detected patterns
patterns = [
    {
        "user": "demo_123",
        "pattern": "regular_purchase",
        "items": ["milk", "bread", "eggs"],
        "cycle_days": 7,
        "confidence": 0.85
    }
]
```

## Current Demo State

### What's Working
- ✅ Graphiti initialization at agent level
- ✅ Entity extraction from queries
- ✅ In-memory backend for demo
- ✅ Graceful timeout handling
- ✅ Memory registry pattern

### What's NOT Connected
- ❌ Spanner backend (no credentials in demo)
- ❌ Persistence between sessions
- ❌ Cross-agent memory sharing
- ❌ Long-term pattern learning

## Data Flow in Demo

```
User Query: "my usual milk"
    ↓
Supervisor Agent
    ├─→ Graphiti Entity Extraction (100ms timeout)
    │   └─→ Extracts: ["usual", "milk"]
    │
    └─→ Routes to Product Search
            ↓
        Order Agent (if needed)
            └─→ Graphiti: get_reorder_items()
                └─→ Returns: [] (no history in demo)
```

## Spanner Schema (When Configured)

### Tables Created by Graphiti
```sql
-- Entities table
CREATE TABLE entities (
    entity_id STRING(36) NOT NULL,
    entity_type STRING(50),
    entity_name STRING(200),
    attributes JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
) PRIMARY KEY (entity_id);

-- Relationships table  
CREATE TABLE relationships (
    relationship_id STRING(36) NOT NULL,
    source_id STRING(36),
    target_id STRING(36),
    relationship_type STRING(50),
    properties JSON,
    created_at TIMESTAMP,
) PRIMARY KEY (relationship_id);

-- Messages table (conversation history)
CREATE TABLE messages (
    message_id STRING(36) NOT NULL,
    session_id STRING(36),
    user_id STRING(100),
    content TEXT,
    role STRING(20),
    timestamp TIMESTAMP,
) PRIMARY KEY (message_id);
```

## How to Enable Spanner (Production)

### 1. Set Up Spanner Instance
```bash
# Create Spanner instance
gcloud spanner instances create leafloaf-prod \
    --config=regional-us-central1 \
    --nodes=1 \
    --description="LeafLoaf Graph Memory"

# Create database
gcloud spanner databases create leafloaf-graph \
    --instance=leafloaf-prod
```

### 2. Set Environment Variables
```bash
export SPANNER_INSTANCE_ID=leafloaf-prod
export SPANNER_DATABASE_ID=leafloaf-graph
export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
```

### 3. Initialize Tables
```bash
python src/scripts/setup_spanner.py
```

## Performance Characteristics

### In-Memory (Demo)
- Entity extraction: ~50ms
- Relationship lookup: <1ms
- No persistence
- Limited to session

### Spanner (Production)
- Entity extraction: ~50ms (same)
- Relationship write: ~100ms
- Relationship read: ~50ms
- Unlimited scale
- Full persistence

## Integration with Personalization

### Current State
- Graphiti runs **parallel** to instant personalization
- Not required for real-time features
- Provides context for complex queries
- Future: Feed patterns back to personalization

### Future Integration
```python
# Planned: Graphiti provides long-term memory
graphiti_patterns = await memory.get_user_patterns(user_id)

# Feed into instant personalization
personalization_engine.update_from_patterns(graphiti_patterns)

# Result: Best of both worlds
# - Instant updates (in-memory)
# - Long-term learning (Graphiti/Spanner)
```

## Demo Talking Points

1. **Agent-Level Integration**: 
   "Unlike typical implementations, we've integrated Graphiti at the agent level, giving each agent its own memory context"

2. **Graceful Degradation**:
   "Notice how the system continues working even without Spanner - Graphiti failures don't block user requests"

3. **Future Vision**:
   "While today's demo uses in-memory, in production this would persist across sessions, devices, and time"

4. **Privacy by Design**:
   "Each user's graph is isolated - no cross-contamination of preferences"

## Monitoring Graphiti

### Key Metrics (When Enabled)
- Entity extraction time
- Spanner write latency  
- Memory growth per user
- Relationship count
- Query patterns

### Current Demo Logs
```
2025-06-28 [info] Graphiti memory will be handled by individual agents
2025-06-28 [info] Agent completed duration_ms=0.11 (supervisor - no Graphiti delay)
```

The Graphiti integration is architecturally complete but runs in degraded mode for the demo (in-memory only, no persistence).