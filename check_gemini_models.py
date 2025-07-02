#!/usr/bin/env python3
"""
Check available Gemini models
"""
import google.generativeai as genai
import os

api_key = "AIzaSyAGLGwNEXgoksFCawjU_x3pWMC-RFTlhPA"
genai.configure(api_key=api_key)

print("🔍 Available Gemini models:")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✅ {model.name}")
        
# Test the working models
print("\n🧪 Testing models...")
test_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro', 'gemini-1.0-pro']

for model_name in test_models:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say yes")
        print(f"✅ {model_name} works!")
        break
    except Exception as e:
        print(f"❌ {model_name}: {str(e)[:50]}...")