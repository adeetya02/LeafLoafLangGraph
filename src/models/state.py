from typing import TypedDict, Optional, List, Dict, Any, Annotated
from datetime import datetime
from enum import Enum
import operator

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

class Message(TypedDict):
    role: str  # "system", "human", "assistant", "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]]
    tool_call_id: Optional[str]

class SearchState(TypedDict):
    # Conversation messages for React pattern
    messages: Annotated[List[Message], operator.add]
    
    # Request Context
    query: str
    request_id: str
    timestamp: datetime
    
    # Search Configuration (for now static)
    alpha_value: float
    search_strategy: SearchStrategy
    
    # Agent decisions and reasoning
    intent: Optional[str]
    next_action: Optional[str]  # What the agent decides to do next
    confidence: float
    routing_decision: Optional[str]  # Add this!
    should_search: bool  # Add this!
    search_params: Dict[str, Any]  # Add this!
    reasoning: Annotated[List[str], operator.add]  # Agent reasoning steps
    
    # Product Search Results
    search_results: List[Dict[str, Any]]
    search_metadata: Dict[str, Any]
    
    # Tool call tracking
    pending_tool_calls: List[Dict[str, Any]]
    completed_tool_calls: List[Dict[str, Any]]
    
    # Execution Tracking
    agent_status: Dict[str, AgentStatus]
    agent_timings: Dict[str, float]
    total_execution_time: float
    
    # LangSmith Tracing
    trace_id: Optional[str]
    
    # Final Response
    final_response: Dict[str, Any]
    should_continue: bool  # For React loops
    error: Optional[str]