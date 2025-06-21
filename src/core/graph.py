from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable
from src.models.state import SearchState
from src.agents.supervisor import SupervisorReactAgent
from src.agents.product_search import ProductSearchReactAgent
from src.agents.response_compiler import ResponseCompilerAgent
from src.core.config_manager import config_manager
import structlog

logger = structlog.get_logger()

# Initialize agents
supervisor = SupervisorReactAgent()
product_search = ProductSearchReactAgent()
response_compiler = ResponseCompilerAgent()

@traceable(name="supervisor_node")
async def supervisor_node(state: SearchState) -> SearchState:
    """Supervisor node - analyzes and routes"""
    return await supervisor.execute(state)

@traceable(name="product_search_node") 
async def product_search_node(state: SearchState) -> SearchState:
    """Product search node - autonomous search with tools"""
    return await product_search.execute(state)

@traceable(name="response_compiler_node")
async def response_compiler_node(state: SearchState) -> SearchState:
    """Response compiler node - formats final response"""
    return await response_compiler.execute(state)

def should_search(state: SearchState) -> str:
    """Conditional edge - decide if we should search"""
    routing = state.get("routing_decision", "")
    
    if routing == "product_search":
        return "product_search"
    elif routing == "help":
        return "response_compiler"  # Skip search, go straight to response
    elif routing == "clarify":
        return "response_compiler"  # Skip search, ask for clarification
    else:
        return "product_search"  # Default to search

def should_continue_search(state: SearchState) -> str:
    """Conditional edge - decide if search needs more iterations"""
    # For now, always go to response compiler
    # In future, could loop back to product_search if needed
    return "response_compiler"

def create_search_graph():
    """Create the autonomous agent LangGraph workflow"""
    
    # Create the graph with SearchState
    workflow = StateGraph(SearchState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("product_search", product_search_node)
    workflow.add_node("response_compiler", response_compiler_node)
    
    # Add edges with conditions
    workflow.set_entry_point("supervisor")
    
    # Supervisor decides where to go
    workflow.add_conditional_edges(
        "supervisor",
        should_search,
        {
            "product_search": "product_search",
            "response_compiler": "response_compiler"
        }
    )
    
    # Product search always goes to response compiler (for now)
    workflow.add_edge("product_search", "response_compiler")
    
    # Response compiler ends the flow
    workflow.add_edge("response_compiler", END)
    
    # Compile the graph WITHOUT checkpointer for now
    app = workflow.compile()
    
    logger.info("Autonomous agent LangGraph workflow created successfully")
    
    return app

# Create the global graph instance
search_graph = create_search_graph()