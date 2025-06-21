from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable
from src.models.state import SearchState
from src.agents.supervisor import SupervisorAgent
from src.agents.product_search import ProductSearchAgent
from src.agents.response_compiler import ResponseCompilerAgent
from src.core.config_manager import config_manager
import structlog

logger = structlog.get_logger()

# Initialize agents
supervisor = SupervisorAgent()
product_search = ProductSearchAgent()
response_compiler = ResponseCompilerAgent()

@traceable(name="supervisor_node")
async def supervisor_node(state: SearchState) -> SearchState:
    """Supervisor node in the graph"""
    return await supervisor.execute(state)

@traceable(name="product_search_node") 
async def product_search_node(state: SearchState) -> SearchState:
    """Product search node in the graph"""
    return await product_search.execute(state)

@traceable(name="response_compiler_node")
async def response_compiler_node(state: SearchState) -> SearchState:
    """Response compiler node in the graph"""
    return await response_compiler.execute(state)

def create_search_graph():
    """Create the LangGraph workflow"""
    
    # Create the graph with SearchState
    workflow = StateGraph(SearchState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("product_search", product_search_node)
    workflow.add_node("response_compiler", response_compiler_node)
    
    # Add edges (linear flow for now)
    workflow.add_edge("supervisor", "product_search")
    workflow.add_edge("product_search", "response_compiler")
    workflow.add_edge("response_compiler", END)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Add memory for conversation continuity
    memory = MemorySaver()
    
    # Compile the graph
    app = workflow.compile(checkpointer=memory)
    
    logger.info("LangGraph workflow created successfully")
    
    return app

# Create the global graph instance
search_graph = create_search_graph()