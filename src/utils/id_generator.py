import uuid
from datetime import datetime

def generate_request_id() -> str:
  """Generate unique request ID"""
  return f"req_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

def generate_trace_id() -> str:
  """Generate LangSmith trace ID"""
  return str(uuid.uuid4())

def generate_order_id() -> str:
  """Generate unique order ID"""
  return f"ord_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"