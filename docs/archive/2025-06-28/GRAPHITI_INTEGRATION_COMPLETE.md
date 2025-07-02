# Graphiti Integration Complete Documentation

## Overview
This document captures the complete Graphiti integration journey, key decisions, and final implementation details for future reference and TDD-based development.

## Integration Timeline & Key Decisions

### Phase 1: Initial API-Level Integration (Failed Approach)
- **What we tried**: Graphiti processing at API level in `src/api/main.py:346-375`
- **Issues**: 
  - Timing problems - results not ready when agents needed them
  - All requests paid the Graphiti cost even if not needed
  - Poor separation of concerns

### Phase 2: Agent-Level Integration (Successful Approach)
- **Implementation**: Each agent manages its own Graphiti instance
- **Benefits**:
  - Agents control when/how to use Graphiti
  - Better error handling and graceful degradation
  - Targeted usage based on agent needs

## Current Architecture

### 1. Memory Infrastructure

#### Core Components:
- `src/memory/graphiti_memory.py` - Base Graphiti implementation (Neo4j)
- `src/memory/graphiti_memory_spanner.py` - Production Spanner implementation
- `src/memory/graphiti_wrapper.py` - Wrapper for managing user/session instances
- `src/memory/memory_registry.py` - Registry pattern for memory managers

#### Key Classes:
```python
# GraphitiMemorySpanner (Production)
- initialize() - Sets up Spanner connection
- process_message() - Extracts entities from messages
- get_context() - Returns context including reorder_patterns
- get_product_relationships() - Gets related products

# GraphitiMemoryWrapper 
- Manages instances per user/session
- Routes to Spanner or Neo4j based on backend
```

### 2. Agent Integration Points

#### Supervisor Agent (`src/agents/supervisor.py:48-100`)
```python
# Key integration at line 48-100
- Creates own MemoryRegistry instance
- Processes message with 200ms timeout
- Gets context with 100ms timeout  
- Adds graphiti_context and graphiti_entities to state
```

#### Order Agent (`src/agents/order_agent.py:334-425`)
```python
# _handle_graphiti_intent method at line 334
- Creates GraphitiMemorySpanner instance
- Uses get_context() for reorder patterns
- Handles usual_order, repeat_order, event_order intents
```

#### Product Search Agent (TODO)
- Should extract brand/product preferences
- Use entity recognition for better search

#### Response Compiler (TODO)
- Should use conversation history
- Personalize responses based on patterns

### 3. Spanner Schema

Created in `create_spanner_schema.py`:
```sql
-- Key Tables
Users - User profiles and preferences
Products - Product catalog with embeddings
Orders - Order history
OrderItems - Order line items (edge table)
Episodes - Graphiti memory episodes
ProductRelationships - Product associations
ReorderPatterns - Calculated reorder patterns
```

### 4. Configuration

#### Environment Variables:
```yaml
SPANNER_INSTANCE_ID: leafloaf-graph
SPANNER_DATABASE_ID: leafloaf-graphrag
GCP_PROJECT_ID: leafloafai
```

#### Dependencies (requirements.txt:81-85):
```
google-cloud-spanner==3.55.0
langchain-google-vertexai==2.0.26  # For embeddings
langchain-google-spanner==0.8.0    # For graph operations
```

## Codebase Complexity Assessment

### Current Complexity Level: **HIGH**

#### Why it's complex:
1. **Multi-Agent Architecture**: 4 specialized agents with different responsibilities
2. **Multiple Memory Systems**: Redis, In-memory, Spanner, Graphiti
3. **Async Patterns**: Extensive use of asyncio with timeouts and error handling
4. **Multiple Integrations**: Weaviate, Vertex AI, Spanner, Redis, 11Labs
5. **State Management**: Complex state passing between agents
6. **Dynamic Behavior**: LLM-driven routing and decision making

#### Complexity Metrics:
- **Files**: 50+ Python files across multiple packages
- **Lines of Code**: ~8,000+ lines
- **External Services**: 7+ (Weaviate, Spanner, Vertex AI, Redis, etc.)
- **Async Functions**: 100+ async methods
- **Agent Interactions**: 4 agents with 10+ interaction patterns

## TDD Approach Going Forward

### 1. Test Structure Needed

```
tests/
├── unit/
│   ├── agents/
│   │   ├── test_supervisor.py
│   │   ├── test_order_agent.py
│   │   └── test_product_search.py
│   ├── memory/
│   │   ├── test_graphiti_memory.py
│   │   └── test_memory_registry.py
│   └── integrations/
│       └── test_spanner_client.py
├── integration/
│   ├── test_agent_coordination.py
│   ├── test_graphiti_flow.py
│   └── test_memory_persistence.py
└── e2e/
    ├── test_search_to_order.py
    ├── test_conversational_flows.py
    └── test_performance.py
```

### 2. Key Test Scenarios

#### Unit Tests:
- Entity extraction accuracy
- Memory persistence
- Agent decision logic
- Timeout handling

#### Integration Tests:
- Agent handoffs
- Memory sharing between agents
- Spanner operations
- Cache behavior

#### E2E Tests:
- Complete user journeys
- Performance benchmarks
- Error recovery
- Conversation continuity

### 3. Testing Challenges

1. **Async Testing**: Need proper async test fixtures
2. **External Services**: Mock or use test instances
3. **LLM Behavior**: Non-deterministic outputs
4. **Performance**: Need baseline metrics

## Code Organization Recommendations

### 1. Reduce Complexity:
- Extract common patterns to base classes
- Centralize configuration
- Standardize error handling
- Create agent interfaces

### 2. Improve Testability:
- Dependency injection everywhere
- Mock-friendly interfaces
- Separate business logic from I/O
- Use factories for object creation

### 3. Documentation:
- Add docstrings to all public methods
- Create sequence diagrams for flows
- Document state schema
- Add inline comments for complex logic

## Key Code References

### Graphiti Integration:
- Supervisor integration: `src/agents/supervisor.py:48-100`
- Order agent Graphiti: `src/agents/order_agent.py:334-425`
- Memory wrapper: `src/memory/graphiti_wrapper.py:25-39`
- Spanner implementation: `src/memory/graphiti_memory_spanner.py:172-219`

### Configuration:
- Memory backends: `src/memory/memory_interfaces.py`
- Constants: `src/config/constants.py`
- Agent priorities: `config/agent_priorities.yaml`

### API Changes:
- Removed Graphiti: `src/api/main.py:346-348` (now just comments)
- State creation: `src/api/main.py:350-356`

## Future Improvements

1. **Refactor Spanner Client**: Remove LangChain dependencies
2. **Add Circuit Breakers**: For external service calls
3. **Implement Caching Layer**: For Graphiti results
4. **Add Metrics**: For monitoring and alerting
5. **Create Test Framework**: Base classes for common test patterns

## Deployment Notes

Current deployment status:
- Revision: leafloaf-00021-94f (pending new build)
- URL: https://leafloaf-v2srnrkkhq-uc.a.run.app
- Spanner: Instance and database created
- Schema: Tables created (views failed due to SQL SECURITY)

## Summary

The Graphiti integration is now at the agent level, providing better control and flexibility. The codebase has grown complex but is well-structured for a production system. Moving to TDD will help manage this complexity and ensure reliability as we continue development.