from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    api_title: str = "LeafAndLoaf Intelligent Search API"
    api_version: str = "1.0.0"
    api_port: int = 8000
    
    # Weaviate Configuration
    weaviate_url: str
    weaviate_api_key: str
    weaviate_class_name: str = "Product"
    huggingface_api_key: Optional[str] = None  # Add this line!
    
    # LangSmith Configuration
    langchain_tracing_v2: bool = True
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_api_key: Optional[str] = None
    langchain_project: str = "leafandloaf-search"
    
    # Search Configuration
    search_timeout_ms: int = 280
    default_search_limit: int = 10
    
    # Environment
    environment: str = "development"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()