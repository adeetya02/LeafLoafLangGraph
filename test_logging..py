print("=== Testing Console Output ===")

import structlog
logger = structlog.get_logger()

print("1. Regular print works")
logger.info("2. Structlog info message")

try:
    from src.config.settings import settings
    print(f"3. Settings loaded: {settings.api_title}")
except Exception as e:
    print(f"3. Error loading settings: {e}")

print("=== End Test ===")