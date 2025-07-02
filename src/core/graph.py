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
  import time
  start = time.time()
  result = await supervisor.execute(state)
  elapsed = (time.time() - start) * 1000
  if 'agent_timings' not in result:
    result['agent_timings'] = {}
  result['agent_timings']['supervisor'] = elapsed
  return result

@traceable(name="product_search_node") 
async def product_search_node(state: SearchState) -> SearchState:
  """Product search node - autonomous search with tools"""
  import time
  start = time.time()
  result = await product_search.execute(state)
  elapsed = (time.time() - start) * 1000
  if 'agent_timings' not in result:
    result['agent_timings'] = {}
  result['agent_timings']['product_search'] = elapsed
  return result

@traceable(name="order_agent_node")
async def order_agent_node(state: SearchState) -> SearchState:
  """Order agent node - manages conversational ordering"""
  import time
  start = time.time()
  result = await order_agent.execute(state)
  elapsed = (time.time() - start) * 1000
  if 'agent_timings' not in result:
    result['agent_timings'] = {}
  result['agent_timings']['order_agent'] = elapsed
  return result

@traceable(name="promotion_agent_node")
async def promotion_agent_node(state: SearchState) -> SearchState:
  """Promotion agent node - handles promotion queries"""
  import time
  start = time.time()
  result = await promotion_agent.execute(state)
  elapsed = (time.time() - start) * 1000
  if 'agent_timings' not in result:
    result['agent_timings'] = {}
  result['agent_timings']['promotion_agent'] = elapsed
  return result

@traceable(name="response_compiler_node")
async def response_compiler_node(state: SearchState) -> SearchState:
  """Response compiler node - formats final response"""
  import time
  start = time.time()
  result = await response_compiler.execute(state)
  elapsed = (time.time() - start) * 1000
  if 'agent_timings' not in result:
    result['agent_timings'] = {}
  result['agent_timings']['response_compiler'] = elapsed
  return result

def should_search(state: SearchState) -> str:
  """Conditional edge - decide if we should search"""
  routing = state.get("routing_decision", "")
  
  if routing == "product_search":
      return "product_search"
  elif routing == "order_agent":
      return "order_agent"
  elif routing == "promotion_agent":
      return "promotion_agent"
  elif routing == "help":
      return "response_compiler"
  elif routing == "clarify":
      return "response_compiler"
  elif routing == "general_chat":
      return "response_compiler"
  else:
      return "product_search"  # Default to search

def after_order_agent(state: SearchState) -> str:
  """Decide what to do after order agent"""
  # If order agent needs to search for products
  if state.get("next_action") == "search_products":
      return "product_search"
  else:
      return "response_compiler"

def create_search_graph():
  """Create the autonomous agent LangGraph workflow"""
  
  # Create the graph with SearchState
  workflow = StateGraph(SearchState)
  
  # Add nodes
  workflow.add_node("supervisor", supervisor_node)
  workflow.add_node("product_search", product_search_node)
  workflow.add_node("order_agent", order_agent_node)
  workflow.add_node("promotion_agent", promotion_agent_node)
  workflow.add_node("response_compiler", response_compiler_node)
  
  # Add edges with conditions
  workflow.set_entry_point("supervisor")
  
  # Supervisor decides where to go
  workflow.add_conditional_edges(
      "supervisor",
      should_search,
      {
          "product_search": "product_search",
          "order_agent": "order_agent",
          "promotion_agent": "promotion_agent",
          "response_compiler": "response_compiler"
      }
  )
  
  # Product search always goes to response compiler
  workflow.add_edge("product_search", "response_compiler")
  
  # Promotion agent always goes to response compiler
  workflow.add_edge("promotion_agent", "response_compiler")
  
  # Order agent can go to product search or response compiler
  workflow.add_conditional_edges(
      "order_agent",
      after_order_agent,
      {
          "product_search": "product_search",
          "response_compiler": "response_compiler"
      }
  )
  
  # Response compiler ends the flow
  workflow.add_edge("response_compiler", END)
  
  # Compile the graph WITHOUT checkpointer for now
  app = workflow.compile()
  
  logger.info("Autonomous agent LangGraph workflow created with Order Agent")
  
  return app

# Create the global graph instance
search_graph = create_search_graph()