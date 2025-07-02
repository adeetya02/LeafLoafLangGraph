"""
Check available Vertex AI models
"""
import vertexai
from vertexai.generative_models import GenerativeModel

# Initialize Vertex AI
vertexai.init(project="leafloafai", location="us-central1")

# List of models to try
models_to_test = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-001", 
    "gemini-1.5-pro",
    "gemini-1.5-pro-001",
    "gemini-1.0-pro",
    "gemini-1.0-pro-001",
    "gemini-pro",
    "gemini-ultra"
]

print("Testing Vertex AI models...")
print("="*40)

for model_name in models_to_test:
    try:
        model = GenerativeModel(model_name)
        response = model.generate_content("Say hello in one word")
        print(f"✅ {model_name}: {response.text.strip()}")
    except Exception as e:
        print(f"❌ {model_name}: {str(e)[:100]}...")