# LeafLoaf LangGraph Architecture Diagram

## System Overview

```mermaid
graph TB
    %% External Systems
    subgraph External["External Systems"]
        11Labs["11Labs TTS API"]
        Deepgram["Deepgram STT API"]
        Gemma["Gemma 2 9B<br/>(Vertex AI)"]
        Weaviate["Weaviate<br/>Vector DB"]
        Spanner["Google Spanner<br/>Graph DB"]
        BigQuery["BigQuery<br/>Analytics"]
        Redis["Redis Cache<br/>(Optional)"]
    end

    %% Client Layer
    subgraph Client["Client Layer"]
        Voice["Voice Interface<br/>(11Labs/Deepgram)"]
        Web["Web Interface<br/>(chatbot.html)"]
        API["REST API<br/>(FastAPI)"]
    end

    %% Core System
    subgraph Core["LangGraph Core"]
        Supervisor["Supervisor Agent<br/>(Router)"]
        ProductSearch["Product Search Agent<br/>(Hybrid Search)"]
        OrderAgent["Order Agent<br/>(React Pattern)"]
        ResponseCompiler["Response Compiler<br/>(ML-Enhanced)"]
    end

    %% Memory Layer
    subgraph Memory["Memory Management"]
        MemoryManager["Improved Memory Manager<br/>(Thread-Safe Singleton)"]
        SessionMemory["Session Memory<br/>(In-Memory/Redis)"]
        GraphMemory["Graph Memory<br/>(Graphiti)"]
        SpannerAdapter["Spanner Graph Adapter"]
    end

    %% Data Flow
    Voice -->|STT| API
    Web --> API
    API --> Supervisor

    Supervisor -->|Intent Analysis| Gemma
    Supervisor -->|Route| ProductSearch
    Supervisor -->|Route| OrderAgent
    
    ProductSearch -->|Query| Weaviate
    ProductSearch -->|Extract Entities| GraphMemory
    
    OrderAgent -->|Cart Ops| SessionMemory
    OrderAgent -->|Context| GraphMemory
    
    GraphMemory --> SpannerAdapter
    SpannerAdapter --> Spanner
    
    SessionMemory --> Redis
    SessionMemory --> MemoryManager
    GraphMemory --> MemoryManager
    
    ProductSearch --> ResponseCompiler
    OrderAgent --> ResponseCompiler
    ResponseCompiler -->|TTS| 11Labs
    ResponseCompiler --> API
    
    %% Analytics Flow
    API -.->|Events| BigQuery
    OrderAgent -.->|Orders| BigQuery
    ResponseCompiler -.->|ML Data| BigQuery
```

## Component Details

### 1. Client Layer
- **Voice Interface**: 11Labs for TTS, Deepgram for STT
- **Web Interface**: Simple HTML/JS for testing
- **REST API**: FastAPI with async support

### 2. LangGraph Core (Multi-Agent System)
- **Supervisor**: LLM-powered router with parallel execution capability
- **Product Search**: Hybrid search (semantic + keyword) with dynamic alpha
- **Order Agent**: React pattern with tools (add/remove/update/confirm)
- **Response Compiler**: Merges results with ML recommendations

### 3. Memory Management
- **Improved Memory Manager**: Thread-safe singleton with dependency injection
- **Session Memory**: Conversation history and cart state
- **Graph Memory**: Entity extraction and relationship tracking
- **Spanner Adapter**: Bridge between Graphiti interface and Spanner

### 4. External Integrations
- **Gemma 2 9B**: Primary LLM (moving to Vertex AI)
- **Weaviate**: Vector search for products
- **Spanner**: Graph database for user patterns
- **BigQuery**: Real-time analytics and ML features
- **Redis**: Optional session cache

## Data Flow Patterns

### 1. Conversational Flow
```
User Voice → Deepgram STT → API → Supervisor → Agents → Memory → Response → 11Labs TTS → User
```

### 2. Search Flow
```
Query → Supervisor → Product Search → Weaviate (Hybrid) → Graphiti (Entities) → Response Compiler
```

### 3. Order Flow
```
Cart Operation → Order Agent → Session Memory → Spanner (Patterns) → BigQuery (Analytics)
```

### 4. Memory Flow
```
Message → Entity Extraction → Graph Memory → Spanner → Pattern Detection → Context Retrieval
```

## Key Design Decisions

1. **LangGraph over LangChain**: Better agent orchestration
2. **Spanner over Neo4j**: Native GCP integration, better scaling
3. **Hybrid Search**: Balances semantic understanding with exact matches
4. **Thread-Safe Singleton**: Prevents memory leaks, enables testing
5. **Event Streaming**: Real-time BigQuery analytics without latency impact
6. **Rule-Based ML**: No LLM overhead for recommendations
7. **Voice-First**: Natural conversation patterns drive the design

## Performance Targets

- **Total Latency**: <300ms
- **Search**: <100ms (with Weaviate)
- **LLM**: <200ms (with cached auth)
- **Memory Ops**: <50ms
- **Voice**: <150ms round-trip

## Scaling Considerations

1. **Horizontal Scaling**: Stateless API, shared memory via Redis
2. **Graph Partitioning**: User-based sharding in Spanner
3. **Cache Strategy**: Redis for hot data, Spanner for cold
4. **Async Everything**: Non-blocking I/O throughout
5. **Connection Pooling**: Reuse expensive connections