# LeafLoaf LangGraph Codebase Summary

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Client    │────▶│  API Layer   │────▶│  LangGraph Core │
│ (Single EP) │     │ (/api/v1/)   │     │  (Supervisor)   │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    │                              │                              │
              ┌─────▼──────┐             ┌────────▼────────┐           ┌─────────▼────────┐
              │Product     │             │  Order Agent    │           │Response Compiler │
              │Search Agent│             │ (React Pattern) │           │    (Merger)      │
              └─────┬──────┘             └────────┬────────┘           └──────────────────┘
                    │                              │
         ┌──────────┴───────────┐                 │
         │                      │                 │
    ┌────▼────┐  ┌─────────────▼──────┐   ┌─────▼──────┐
    │Weaviate │  │Graphiti Memory      │   │Order Tools │
    │(Search) │  │(Real-time Learning) │   │(Cart Mgmt) │
    └─────────┘  └─────────┬──────────┘   └────────────┘
                           │
                     ┌─────▼──────┐
                     │Spanner     │
                     │Graph Store │
                     └────────────┘
```

## Key Components

### 1. API Layer (`src/api/`)
- **main.py**: Single endpoint `/api/v1/search` handles ALL requests
- **voice_webhooks.py**: 11Labs voice integration
- **OpenAPI compliant**: Full schema validation

### 2. Core System (`src/core/`)
- **graph.py**: LangGraph orchestration
- **config_manager.py**: Configuration management
- **State management**: Tracks execution flow

### 3. Agents (`src/agents/`)
- **supervisor.py**: Routes queries based on intent
- **product_search.py**: Weaviate integration
- **order_agent.py**: Cart management (add/remove/update)
- **response_compiler.py**: Merges all agent outputs

### 4. Memory System (`src/memory/`)
- **graphiti_memory_spanner.py**: Real-time pattern learning
- **spanner_graph_client.py**: Persistent relationships
- **memory_registry.py**: Dependency injection pattern

### 5. Integrations (`src/integrations/`)
- **gemma_optimized_client.py**: LLM for intent/alpha
- **weaviate_client_optimized.py**: Product search
- **spanner_graph_client.py**: GraphRAG implementation

## Current State

### Working ✅
1. Multi-agent system with proper routing
2. Basic Graphiti integration at agent level
3. Weaviate search (BM25 fallback mode)
4. Session-based cart management
5. Response compilation
6. GCP deployment

### Issues 🔧
1. Gemma intent recognition (update_order failing)
2. Vertex AI endpoint configuration mismatch
3. Complex codebase needs refactoring
4. Performance optimization needed

### In Progress 🚧
1. Graphiti Personalization Feature
2. User preference management
3. Feature flag system
4. "My Usual" order implementation

## Data Flow

1. **Request arrives** at `/api/v1/search`
2. **Supervisor analyzes** intent using Gemma/fallback
3. **Routes to appropriate agent**:
   - Product Search → Weaviate
   - Order Operations → Order Agent
4. **Agents access**:
   - Graphiti for real-time context
   - Spanner for persistent patterns
5. **Response Compiler** merges all data
6. **Single response** returned to client

## Performance Targets

- Total response time: <300ms
- Personalization overhead: <50ms
- Weaviate search: <200ms
- LLM intent: <150ms

## Key Patterns

### 1. Agent Pattern
```python
class BaseAgent:
    async def _run(self, state: SearchState) -> SearchState:
        # Process state
        # Update state
        # Return enriched state
```

### 2. Memory Pattern
```python
# Per-user instance creation
memory = GraphitiMemorySpanner(user_id, session_id)
await memory.initialize()
context = await memory.get_context(query)
```

### 3. Response Pattern
```python
# All responses follow OpenAPI schema
response = SearchResponse(
    success=True,
    products=[...],
    personalization=PersonalizationInfo(...)
)
```

## Environment Configuration

### Required Services
- Google Cloud Project (Vertex AI, Spanner, Cloud Run)
- Weaviate instance
- Redis (optional, fallback to memory)
- 11Labs (voice features)

### Key Environment Variables
- `GCP_PROJECT_ID`: Google Cloud project
- `WEAVIATE_URL`: Weaviate endpoint
- `VERTEX_AI_ENDPOINT_ID`: Gemma endpoint
- `SPANNER_INSTANCE_ID`: Spanner instance

## Testing Strategy

### Unit Tests
- Agent logic isolation
- Memory system mocking
- API contract validation

### Integration Tests
- End-to-end flows
- Multi-agent coordination
- Performance benchmarks

### Load Tests
- Concurrent user simulation
- Latency under load
- Memory usage patterns

## Deployment

### Current
- Cloud Run (auto-scaling)
- Artifact Registry for images
- Environment variables via .env.yaml

### Planned
- GKE for better control
- GPU nodes for local Gemma
- Multi-region support

## Next Steps

1. **Immediate**: Fix Gemma intent recognition
2. **This Week**: Complete personalization MVP
3. **Next Week**: Performance optimization
4. **Future**: Refactor to feature-based modules

---

**Note**: This codebase is actively evolving. See CLAUDE.md for session-specific context and GRAPHITI_PERSONALIZATION.md for the current feature implementation.