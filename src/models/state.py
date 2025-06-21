from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class AgentStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class SearchStrategy(Enum):
    KEYWORD = "keyword"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"

class SearchState(TypedDict):
    # Request Context
    query: str
    request_id: str
    timestamp: datetime
    
    # Alpha Calculation
    alpha_value: float
    search_strategy: SearchStrategy
    alpha_reasoning: List[str]
    
    # Supervisor Decisions
    intent: str
    confidence: float
    routing_decision: str
    
    # Product Search Results
    search_results: List[Dict[str, Any]]
    search_metadata: Dict[str, Any]
    
    # Execution Tracking
    agent_status: Dict[str, AgentStatus]
    agent_timings: Dict[str, float]
    total_execution_time: float
    
    # LangSmith Tracing
    trace_id: Optional[str]
    span_ids: Dict[str, str]
    
    # Final Response
    final_response: Dict[str, Any]
    error: Optional[str]