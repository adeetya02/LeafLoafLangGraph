"""
Simple HTTP server to test connectivity
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import sys

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Simple Test Server</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px;
                }
                .success {
                    color: green;
                    font-size: 24px;
                    margin: 20px;
                }
            </style>
        </head>
        <body>
            <h1>Simple Test Server</h1>
            <p class="success">✅ Server is working on port 7777!</p>
            <p>If you can see this, the basic HTTP server works.</p>
        </body>
        </html>
        """)

if __name__ == "__main__":
    port = 7777
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"\n✅ Simple HTTP server running on http://localhost:{port}")
    print("Press Ctrl+C to stop\n")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        sys.exit(0)