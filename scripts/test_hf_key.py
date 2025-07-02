#!/usr/bin/env python3
import os
print(f"HF API Key set: {bool(os.getenv('HUGGINGFACE_API_KEY'))}")
print(f"Key value: {os.getenv('HUGGINGFACE_API_KEY', 'NOT SET')[:10]}...")