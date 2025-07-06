"""
Diagnostic script to understand the server issue
"""
import socket
import sys

def check_port(port):
    """Check if a port is available"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', port))
        sock.close()
        return True, "Port is available"
    except OSError as e:
        return False, str(e)

def test_basic_http_server(port):
    """Test a basic HTTP server"""
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import threading
    
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"<h1>Basic HTTP Server Works!</h1>")
    
    try:
        server = HTTPServer(('127.0.0.1', port), Handler)
        print(f"✅ Basic HTTP server started on port {port}")
        print(f"   Visit http://127.0.0.1:{port}")
        
        # Run in thread so we can continue
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        return True
    except Exception as e:
        print(f"❌ Failed to start HTTP server: {e}")
        return False

def test_fastapi_server(port):
    """Test FastAPI without WebSocket"""
    try:
        from fastapi import FastAPI
        import uvicorn
        import threading
        
        app = FastAPI()
        
        @app.get("/")
        async def root():
            return {"message": "FastAPI works!"}
        
        def run_server():
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
        
        thread = threading.Thread(target=run_server)
        thread.daemon = True
        thread.start()
        
        print(f"✅ FastAPI server started on port {port}")
        print(f"   Visit http://127.0.0.1:{port}")
        return True
    except Exception as e:
        print(f"❌ Failed to start FastAPI: {e}")
        return False

def test_websocket_server(port):
    """Test FastAPI with WebSocket"""
    try:
        from fastapi import FastAPI, WebSocket
        import uvicorn
        import threading
        
        app = FastAPI()
        
        @app.get("/")
        async def root():
            return {"message": "FastAPI with WebSocket endpoint exists"}
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("Hello WebSocket")
            await websocket.close()
        
        def run_server():
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
        
        thread = threading.Thread(target=run_server)
        thread.daemon = True
        thread.start()
        
        print(f"✅ FastAPI + WebSocket server started on port {port}")
        print(f"   Visit http://127.0.0.1:{port}")
        return True
    except Exception as e:
        print(f"❌ Failed to start FastAPI + WebSocket: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Server Diagnostic Tool\n")
    
    # Test different ports
    test_ports = [7777, 8001, 8002, 8003]
    
    print("1. Checking port availability:")
    for port in test_ports:
        available, msg = check_port(port)
        print(f"   Port {port}: {'✅ Available' if available else f'❌ {msg}'}")
    
    print("\n2. Testing basic HTTP server:")
    if test_basic_http_server(7777):
        input("   Press Enter to continue...")
    
    print("\n3. Testing FastAPI without WebSocket:")
    if test_fastapi_server(8001):
        input("   Press Enter to continue...")
    
    print("\n4. Testing FastAPI with WebSocket:")
    if test_websocket_server(8002):
        input("   Press Enter to continue...")
    
    print("\n✅ All tests complete!")
    print("Check which servers you can access in your browser.")
    input("Press Enter to exit...")