# LeafLoaf Architecture Visual Map

## System Overview Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        Voice[Voice Input]
        Web[Web Interface]
        API[API Clients]
    end
    
    subgraph "API Gateway"
        HTTP[HTTP Endpoints]
        WS[WebSocket Endpoints]
        Voice_EP[Voice Endpoints]
    end
    
    subgraph "Core Orchestration"
        LG[LangGraph Engine]
        State[State Management]
        Router[Agent Router]
    end
    
    subgraph "Agent Layer"
        Supervisor[Supervisor Agent]
        Search[Product Search Agent]
        Order[Order Agent]
        Compiler[Response Compiler]
        Promo[Promotion Agent]
    end
    
    subgraph "Memory Systems"
        Graphiti[Graphiti Memory]
        Session[Session Store]
        Redis[Redis Cache]
        Spanner[Spanner GraphDB]
    end
    
    subgraph "External Services"
        Weaviate[Weaviate Vector DB]
        Deepgram[Deepgram STT/TTS]
        Gemini[Gemini/Vertex AI]
        BigQuery[BigQuery Analytics]
    end
    
    Voice --> Voice_EP
    Web --> HTTP
    API --> HTTP
    Voice_EP --> WS
    
    HTTP --> LG
    WS --> LG
    
    LG --> State
    State --> Router
    Router --> Supervisor
    
    Supervisor --> Search
    Supervisor --> Order
    Supervisor --> Promo
    
    Search --> Weaviate
    Search --> Graphiti
    
    Order --> Redis
    Order --> Graphiti
    
    Search --> Compiler
    Order --> Compiler
    Promo --> Compiler
    
    Graphiti --> Spanner
    Session --> Redis
    
    Voice_EP --> Deepgram
    Supervisor --> Gemini
    
    LG --> BigQuery
```

## Agent Communication Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant LangGraph
    participant Supervisor
    participant Search
    participant Order
    participant Memory
    participant Compiler
    
    User->>API: Voice/Text Query
    API->>LangGraph: Process Request
    LangGraph->>Supervisor: Analyze Intent
    
    alt Product Search
        Supervisor->>Search: Route to Search
        Search->>Memory: Get User Context
        Memory-->>Search: Preferences/History
        Search->>Search: Execute Weaviate Query
        Search-->>LangGraph: Search Results
    else Order Management
        Supervisor->>Order: Route to Order
        Order->>Memory: Get Cart State
        Order->>Order: Execute Cart Tools
        Order-->>LangGraph: Order Updates
    end
    
    LangGraph->>Compiler: Compile Response
    Compiler->>Memory: Update Learning
    Compiler-->>API: Final Response
    API-->>User: Voice/JSON Response
```

## Voice Processing Pipeline

```mermaid
graph LR
    subgraph "Voice Input"
        Audio[Audio Stream]
        STT[Deepgram STT]
        Meta[Voice Metadata]
    end
    
    subgraph "Processing"
        Intent[Intent Analysis]
        Alpha[Alpha Calculation]
        Route[Routing Logic]
    end
    
    subgraph "Response"
        Gen[Response Generation]
        TTS[Deepgram TTS]
        Stream[Audio Stream]
    end
    
    Audio --> STT
    Audio --> Meta
    STT --> Intent
    Meta --> Alpha
    Intent --> Route
    Alpha --> Route
    Route --> Gen
    Gen --> TTS
    TTS --> Stream
```

## Memory Architecture

```mermaid
graph TB
    subgraph "Memory Layers"
        App[Application Layer]
        Registry[Memory Registry]
        Interface[Memory Interface]
        
        subgraph "Backends"
            InMem[In-Memory Store]
            Redis[Redis Cache]
            Graphiti[Graphiti Engine]
            Spanner[Spanner GraphDB]
        end
    end
    
    App --> Registry
    Registry --> Interface
    Interface --> InMem
    Interface --> Redis
    Interface --> Graphiti
    Graphiti --> Spanner
    
    subgraph "Data Types"
        Session[Session Data]
        User[User Preferences]
        Graph[Knowledge Graph]
        Cart[Cart State]
    end
    
    Session --> InMem
    Session --> Redis
    User --> Graphiti
    Graph --> Spanner
    Cart --> Redis
```

## Personalization Flow

```mermaid
graph LR
    subgraph "Input"
        Query[User Query]
        History[Purchase History]
        Context[Session Context]
    end
    
    subgraph "Learning"
        Extract[Entity Extraction]
        Pattern[Pattern Recognition]
        Graphiti[Graphiti Learning]
    end
    
    subgraph "Application"
        Rank[Re-ranking]
        Filter[Filtering]
        Suggest[Suggestions]
    end
    
    Query --> Extract
    History --> Pattern
    Context --> Extract
    
    Extract --> Graphiti
    Pattern --> Graphiti
    
    Graphiti --> Rank
    Graphiti --> Filter
    Graphiti --> Suggest
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "Google Cloud Platform"
        subgraph "Compute"
            CR[Cloud Run]
            VAI[Vertex AI]
        end
        
        subgraph "Storage"
            Spanner[Cloud Spanner]
            GCS[Cloud Storage]
            FS[Firestore]
        end
        
        subgraph "Analytics"
            BQ[BigQuery]
            Logging[Cloud Logging]
        end
    end
    
    subgraph "External Services"
        Weaviate[Weaviate Cloud]
        Deepgram[Deepgram API]
        Redis[Redis Cloud]
    end
    
    CR --> VAI
    CR --> Spanner
    CR --> BQ
    CR --> Weaviate
    CR --> Deepgram
    CR --> Redis
```

## Error Handling & Fallbacks

```mermaid
graph TD
    Request[Incoming Request]
    
    Request --> Primary{Primary Path}
    Primary -->|Success| Response[Return Response]
    Primary -->|Timeout| Fallback1[Fallback LLM]
    Primary -->|Error| Fallback2[Cache Response]
    
    Fallback1 -->|Success| Response
    Fallback1 -->|Fail| Fallback2
    
    Fallback2 -->|Hit| Response
    Fallback2 -->|Miss| Default[Default Response]
    
    Default --> Response
```

## Key Integration Points

### 1. **Voice Integration**
- Multiple Deepgram clients for different use cases
- Voice metadata influences search parameters
- Real-time STT/TTS with WebSocket support

### 2. **Memory Integration**
- All agents inherit from MemoryAwareAgent
- Graphiti provides self-learning capabilities
- Multiple backend support (Redis, Spanner, In-memory)

### 3. **Search Integration**
- Weaviate hybrid search with dynamic alpha
- Voice-driven search parameter adjustment
- Personalization through re-ranking

### 4. **Analytics Integration**
- Fire-and-forget BigQuery streaming
- Real-time event capture
- ML feature generation

### 5. **LLM Integration**
- Environment-aware model selection
- Automatic fallback mechanisms
- Multiple provider support (Gemini, Vertex AI, HuggingFace)

## Performance Optimization Points

1. **Caching Strategy**
   - Redis for session data
   - Search result caching
   - LLM response caching

2. **Parallel Execution**
   - Agent parallelization in graph_v2
   - Async operations throughout
   - Non-blocking analytics

3. **Connection Pooling**
   - Database connection reuse
   - API client pooling
   - WebSocket connection management

4. **Resource Management**
   - Per-request agent instances
   - Memory cleanup
   - Timeout management

This visual map provides a comprehensive overview of how all components in the LeafLoaf system interconnect and work together to provide a seamless, voice-native grocery shopping experience.