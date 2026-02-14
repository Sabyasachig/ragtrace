#!/usr/bin/env python3
"""
Simple HTTP server for the RAG Debugger Web UI.
Run this to serve the UI locally for testing.
"""

import http.server
import socketserver
import os
import sys

PORT = 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == "__main__":
    handler = MyHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"\n🚀 RAG Debugger UI Server")
        print(f"{'='*50}")
        print(f"📂 Serving: {DIRECTORY}")
        print(f"🌐 URL: http://localhost:{PORT}")
        print(f"{'='*50}")
        print(f"\n✓ Server started successfully!")
        print(f"✓ Open http://localhost:{PORT} in your browser")
        print(f"\n⚠️  Make sure the API server is running on port 8000")
        print(f"   Run: uvicorn api.main:app --reload --port 8000\n")
        print(f"Press Ctrl+C to stop the server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Server stopped")
            sys.exit(0)
