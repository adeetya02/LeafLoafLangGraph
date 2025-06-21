import uvicorn
from src.config.settings import settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
if __name__ == "__main__":
    print(f"🚀 Starting {settings.api_title} on port {settings.api_port}")
    print(f"📊 Weaviate URL: {settings.weaviate_url}")
    print(f"🔍 LangSmith Tracing: {'Enabled' if settings.langchain_tracing_v2 else 'Disabled'}")
    print(f"\n✨ API will be available at: http://localhost:{settings.api_port}/docs\n")
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=False  # Auto-reload on code changes
        log_level="info"
    )