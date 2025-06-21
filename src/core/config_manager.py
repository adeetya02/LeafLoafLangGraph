import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

class AgentConfigManager:
    """Manages agent configuration from YAML file"""
    
    def __init__(self, config_path: str = "config/agent_priorities.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Fallback configuration if file loading fails"""
        return {
            "search_strategy": {
                "default_strategy": "hybrid",
                "default_alpha": 0.7
            },
            "agents": {
                "supervisor": {"timeout_ms": 50, "enabled": True},
                "product_search": {"timeout_ms": 150, "enabled": True},
                "response_compiler": {"timeout_ms": 30, "enabled": True}
            }
        }
    
    def get_default_search_config(self) -> Dict[str, Any]:
        """Get default search configuration (static for now)"""
        search_config = self.config.get("search_strategy", {})
        return {
            "strategy": search_config.get("default_strategy", "hybrid"),
            "alpha": search_config.get("default_alpha", 0.7)
        }
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """Get configuration for specific agent"""
        return self.config.get("agents", {}).get(agent_name, {})
    
    def is_agent_enabled(self, agent_name: str) -> bool:
        """Check if agent is enabled"""
        agent_config = self.get_agent_config(agent_name)
        return agent_config.get("enabled", True)

# Global instance
config_manager = AgentConfigManager()