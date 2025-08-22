#!/usr/bin/env python3
"""
Test the simple server locally
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import threading
import time
import urllib.request

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
                    "timestamp": time.time()
                }
                self.wfile.write(json.dumps(response).encode())
                print(f"✅ Served {path}")
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Not found"}).encode())
        except Exception as e:
            print(f"❌ Error handling request: {e}")
            self.send_response(500)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def test_server():
    """Test the server endpoints"""
    time.sleep(1)  # Wait for server to start
    
    try:
        # Test root endpoint
        with urllib.request.urlopen('http://localhost:8000/') as response:
            data = json.loads(response.read().decode())
            print(f"✅ Root endpoint: {data['status']}")
        
        # Test health endpoint
        with urllib.request.urlopen('http://localhost:8000/health') as response:
            data = json.loads(response.read().decode())
            print(f"✅ Health endpoint: {data['status']}")
        
        print("🎉 All tests passed! Server is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")

def main():
    port = 8000
    print(f"🚀 Starting test server on port {port}")
    
    server = HTTPServer(('localhost', port), HealthHandler)
    
    # Start server in background thread
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    print(f"✅ Server started on http://localhost:{port}")
    
    # Run tests
    test_server()
    
    # Keep server running for a bit
    print("⏳ Server will run for 5 seconds...")
    time.sleep(5)
    
    server.shutdown()
    print("🛑 Server stopped")

if __name__ == "__main__":
    main()
