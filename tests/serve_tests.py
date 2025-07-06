#!/usr/bin/env python3
"""
Simple HTTP server for serving test HTML files
"""
import http.server
import socketserver
import os
import sys

PORT = 8888
DIRECTORY = "tests/implementation"


class TestHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        # Add CORS headers for testing
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    with socketserver.TCPServer(("", PORT), TestHTTPRequestHandler) as httpd:
        print(f"🧪 Test server running at http://localhost:{PORT}/")
        print(f"📁 Serving directory: {DIRECTORY}")
        print("\nAvailable tests:")
        print("- http://localhost:8888/deepgram/test_deepgram_streaming.html")
        print("\nPress Ctrl+C to stop")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n✋ Test server stopped")
            sys.exit(0)


if __name__ == "__main__":
    main()