from typing import Dict, Any, List
from src.tools.search_tools import AVAILABLE_TOOLS
import json
import structlog

logger = structlog.get_logger()

class ToolExecutor:
    """Executes tool calls from agents"""
    
    def __init__(self):
        self.tools = AVAILABLE_TOOLS
        
    async def execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool call"""
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("args", {})
        tool_id = tool_call.get("id", "unknown")
        
        logger.info(f"Executing tool: {tool_name}", tool_id=tool_id, args=tool_args)
        
        if tool_name not in self.tools:
            return {
                "tool_call_id": tool_id,
                "error": f"Tool '{tool_name}' not found"
            }
        
        try:
            tool = self.tools[tool_name]
            result = await tool.run(**tool_args)
            
            return {
                "tool_call_id": tool_id,
                "name": tool_name,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", tool_name=tool_name)
            return {
                "tool_call_id": tool_id,
                "name": tool_name,
                "error": str(e)
            }
    
    async def execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple tool calls"""
        results = []
        for tool_call in tool_calls:
            result = await self.execute_tool_call(tool_call)
            results.append(result)
        return results
    
    def get_tool_descriptions(self) -> List[Dict[str, str]]:
        """Get descriptions of all available tools for agents"""
        return [
            {
                "name": name,
                "description": tool.description.strip()
            }
            for name, tool in self.tools.items()
        ]

# Global instance
tool_executor = ToolExecutor()