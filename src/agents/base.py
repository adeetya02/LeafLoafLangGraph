from abc import ABC, abstractmethod
from typing import Dict, Any
import time
import structlog
from src.models.state import SearchState, AgentStatus

logger = structlog.get_logger()

class BaseAgent(ABC):
  """Base class for all LangGraph agents"""
  
  def __init__(self, name: str):
      self.name = name
      self.logger = logger.bind(agent=name)
      
  async def execute(self, state: SearchState) -> SearchState:
      """Execute agent with timing and error handling"""
      start_time = time.perf_counter()
      
      # Ensure agent_status exists
      if "agent_status" not in state:
          state["agent_status"] = {}
      
      # Update status
      state["agent_status"][self.name] = AgentStatus.RUNNING
      
      try:
          # Execute agent logic
          result = await self._run(state)
          
          # Update status on success
          state["agent_status"][self.name] = AgentStatus.COMPLETED
          
          return result
          
      except Exception as e:
          # Log error
          self.logger.error(f"Agent failed: {str(e)}")
          
          # Update status on failure
          state["agent_status"][self.name] = AgentStatus.FAILED
          
          # Run fallback
          return await self._fallback(state, e)
          
      finally:
          # Ensure agent_timings exists
          if "agent_timings" not in state:
              state["agent_timings"] = {}
              
          # Record timing
          execution_time = (time.perf_counter() - start_time) * 1000
          state["agent_timings"][self.name] = execution_time
          
          self.logger.info(
              f"Agent completed",
              status=state["agent_status"][self.name].value,
              duration_ms=execution_time
          )
  
  @abstractmethod
  async def _run(self, state: SearchState) -> SearchState:
      """Agent-specific logic to implement"""
      pass
  
  async def _fallback(self, state: SearchState, error: Exception) -> SearchState:
      """Default fallback behavior"""
      if state.get("error") is None:
          state["error"] = f"{self.name} failed: {str(error)}"
      return state