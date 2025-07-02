#!/usr/bin/env python3
from src.config.settings import settings

print("Weaviate settings:")
print(f"URL: {settings.weaviate_url}")
print(f"API Key (first 20 chars): {settings.weaviate_api_key[:20] if settings.weaviate_api_key else 'None'}...")
print(f"Class name: {settings.weaviate_class_name}")
print(f"HuggingFace API Key: {settings.huggingface_api_key[:20] if settings.huggingface_api_key else 'None'}...")