"""
Enhanced graph with parallel agent execution
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable
from src.models.state import SearchState
from src.agents.supervisor_optimized import OptimizedSupervisorAgent as SupervisorReactAgent
from src.agents.product_search import ProductSearchReactAgent
from src.agents.response_compiler import ResponseCompilerAgent
from src.agents.order_agent import OrderReactAgent
from src.agents.promotion_agent import PromotionAgent
from src.core.config_manager import config_manager
import asyncio
import structlog

logger = structlog.get_logger()

# Initialize agents
supervisor = SupervisorReactAgent()
product_search = ProductSearchReactAgent()
response_compiler = ResponseCompilerAgent()
order_agent = OrderReactAgent()
promotion_agent = PromotionAgent()

@traceable(name="supervisor_node")
async def supervisor_node(state: SearchState) -> SearchState:
    """Supervisor node - analyzes and routes"""
    return await supervisor.execute(state)

@traceable(name="parallel_execution_node")
async def parallel_execution_node(state: SearchState) -> SearchState:
    """Execute multiple agents in parallel based on routing decision"""
    routing = state.get("routing_decision", "")
    
    # Determine which agents to run
    tasks = []
    agents_to_run = []
    
    # Always run promotion agent to check for applicable promotions
    tasks.append(promotion_agent.execute(state))
    agents_to_run.append("promotion_agent")
    
    # Add other agents based on routing
    if routing == "product_search":
        tasks.append(product_search.execute(state))
        agents_to_run.append("product_search")
    elif routing == "order_agent":
        tasks.append(order_agent.execute(state))
        agents_to_run.append("order_agent")
        # For order operations, also run product search if needed
        if state.get("search_results") is None or len(state.get("search_results", [])) == 0:
            tasks.append(product_search.execute(state))
            agents_to_run.append("product_search")
    
    logger.info(f"Running agents in parallel: {agents_to_run}")
    
    # Execute all tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Merge results back into state
    merged_state = state.copy()
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Agent {agents_to_run[i]} failed: {result}")
            continue
            
        # Merge the results from each agent
        if isinstance(result, dict):
            # Merge specific fields we care about
            if "search_results" in result and result["search_results"]:
                merged_state["search_results"] = result["search_results"]
                merged_state["search_metadata"] = result.get("search_metadata", {})
            
            if "order_response" in result:
                merged_state["order_response"] = result["order_response"]
                merged_state["order_success"] = result.get("order_success", False)
            
            if "promotion_response" in result:
                merged_state["promotion_response"] = result["promotion_response"]
                merged_state["cart_discount_info"] = result.get("cart_discount_info", {})
                merged_state["has_promotion_info"] = result.get("has_promotion_info", False)
            
            # Merge agent timings
            if "agent_timings" in result:
                if "agent_timings" not in merged_state:
                    merged_state["agent_timings"] = {}
                merged_state["agent_timings"].update(result["agent_timings"])
            
            # Update agent status
            if "agent_status" in result:
                if "agent_status" not in merged_state:
                    merged_state["agent_status"] = {}
                merged_state["agent_status"].update(result["agent_status"])
    
    return merged_state

@traceable(name="response_compiler_node")
async def response_compiler_node(state: SearchState) -> SearchState:
    """Response compiler node - formats final response with all agent outputs"""
    return await response_compiler.execute(state)

def create_enhanced_graph():
    """Create the enhanced agent graph with parallel execution"""
    
    # Create the graph with SearchState
    workflow = StateGraph(SearchState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("parallel_execution", parallel_execution_node)
    workflow.add_node("response_compiler", response_compiler_node)
    
    # Set entry point
    workflow.set_entry_point("supervisor")
    
    # Supervisor always goes to parallel execution
    workflow.add_edge("supervisor", "parallel_execution")
    
    # Parallel execution always goes to response compiler
    workflow.add_edge("parallel_execution", "response_compiler")
    
    # Response compiler ends
    workflow.add_edge("response_compiler", END)
    
    # Compile with memory
    memory = MemorySaver()
    
    # Get checkpointer from config
    checkpointer = config_manager.get_checkpointer()
    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
    else:
        app = workflow.compile(checkpointer=memory)
    
    return app

# Create the enhanced graph
enhanced_graph = create_enhanced_graph()