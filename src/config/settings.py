from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
  # API Configuration
  api_title: str = "LeafAndLoaf Intelligent Search API"
  api_version: str = "1.0.0"
  api_port: int = 8080
  
  # Weaviate Configuration
  weaviate_url: Optional[str] = None
  weaviate_api_key: Optional[str] = None
  weaviate_class_name: str = "Product"
  weaviate_bm25_only: bool = False  # Use hybrid search with Gemma-determined alpha
  
  # HuggingFace Configuration
  huggingface_api_key: Optional[str] = None
  
  # 11Labs Configuration
  elevenlabs_api_key: Optional[str] = None
  elevenlabs_voice_id: Optional[str] = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice default
  
  # Deepgram Configuration
  deepgram_api_key: Optional[str] = None
  
  # Groq Configuration
  groq_api_key: Optional[str] = None
  
  # LangSmith Configuration
  langchain_tracing_v2: bool = True
  langchain_endpoint: str = "https://api.smith.langchain.com"
  langchain_api_key: Optional[str] = None
  langchain_project: str = "leafandloaf-search"
  
  # Search Configuration 
  search_timeout_ms: int = 5000  # Override with SEARCH_TIMEOUT_MS env var
  default_search_limit: int = 10  # Override with SEARCH_DEFAULT_LIMIT env var
  
  # Redis Configuration
  redis_url: Optional[str] = None  # Override with REDIS_URL env var
  redis_ttl_seconds: int = 3600  # 1 hour default cache TTL
  redis_max_connections: int = 10
  
  # Environment
  environment: str = "development"
  
  model_config = {
      "env_file": ".env",
      "env_file_encoding": "utf-8"
  }

settings = Settings()