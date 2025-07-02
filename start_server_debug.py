#!/usr/bin/env python3
"""
Start server with debug information
"""
import subprocess
import sys
import time
import os

print("🚀 Starting LeafLoaf Server with Debug Info\n")

# Check if port 8000 is available
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 8000))
sock.close()

if result == 0:
    print("❌ Port 8000 is already in use!")
    print("Please kill the existing process or use a different port")
    sys.exit(1)
else:
    print("✅ Port 8000 is available")

# Set environment variables for better logging
env = os.environ.copy()
env['PYTHONUNBUFFERED'] = '1'

print("\n📝 Starting server...")
print("=" * 60)

try:
    # Start the server
    process = subprocess.Popen(
        [sys.executable, 'run.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env
    )
    
    # Monitor output
    print("Server output:")
    print("-" * 60)
    
    start_time = time.time()
    server_started = False
    
    for line in process.stdout:
        print(line, end='')
        
        # Check if server started successfully
        if "Uvicorn running on" in line or "Application startup complete" in line:
            server_started = True
            print("\n" + "=" * 60)
            print("✅ Server started successfully!")
            print(f"🌐 Open: http://localhost:8000/static/voice_google_test.html")
            print("=" * 60)
        
        # Check for errors
        if "error" in line.lower() and "deprecation" not in line.lower():
            print(f"\n⚠️  Error detected: {line}")
        
        # Timeout after 30 seconds
        if not server_started and (time.time() - start_time) > 30:
            print("\n❌ Server failed to start within 30 seconds")
            process.terminate()
            sys.exit(1)
    
    # Keep the server running
    process.wait()
    
except KeyboardInterrupt:
    print("\n\n🛑 Shutting down server...")
    process.terminate()
    print("✅ Server stopped")
except Exception as e:
    print(f"\n❌ Error starting server: {e}")
    sys.exit(1)