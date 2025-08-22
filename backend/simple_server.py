#!/usr/bin/env python3
"""
Absolute minimal HTTP server for Railway deployment
No external dependencies - uses only Python standard library
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            path = urlparse(self.path).path
            
            if path in ['/', '/health']:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {
                    "status": "healthy",
                    "service": "xyqo-backend",
                    "path": path,
                    "python_version": sys.version
                }
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Not found"}).encode())
        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_response(500)
            self.end_headers()
    
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

def main():
    try:
        port = int(os.environ.get("PORT", 8000))
        print(f"Python version: {sys.version}")
        print(f"Starting server on 0.0.0.0:{port}")
        
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        print(f"Server started successfully")
        print(f"Health check: http://0.0.0.0:{port}/health")
        
        server.serve_forever()
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
