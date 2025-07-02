#!/usr/bin/env python3
"""
Start the LeafLoaf server
"""
import os
import sys
import subprocess

print("🚀 Starting LeafLoaf Server...")
print("=" * 60)

# Check port availability
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 8000))
sock.close()

if result == 0:
    print("⚠️  Port 8000 is in use. Killing existing processes...")
    # Kill any process using port 8000
    try:
        subprocess.run("lsof -ti:8000 | xargs kill -9", shell=True, capture_output=True)
        print("✅ Killed existing processes")
    except:
        pass

print("\n📦 Environment:")
print(f"Python: {sys.executable}")
print(f"Working Directory: {os.getcwd()}")

# Set environment for better logging
os.environ['PYTHONUNBUFFERED'] = '1'

print("\n🔧 Starting server...")
print("-" * 60)

# Start the server directly with uvicorn
subprocess.run([
    sys.executable, 
    "-m", 
    "uvicorn",
    "src.api.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload",
    "--log-level", "info"
])