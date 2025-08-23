#!/usr/bin/env python3
"""
XYQO Simple HTTP Server - Railway Compatible
Minimal HTTP server that bypasses FastAPI complexity
"""

import os
import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class XYQOHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        logger.info(f"GET {path}")
        
        if path == '/' or path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "service": "xyqo-backend-simple",
                "message": "XYQO Backend is running",
                "version": "3.0.0",
                "port": os.getenv("PORT", "8000")
            }
            
            self.wfile.write(json.dumps(response).encode())
            return
        
        # 404 for other paths
        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(format % args)

def main():
    """Start the HTTP server"""
    try:
        # Force port 8000 to match Railway networking
        port = 8000
        host = "0.0.0.0"
        
        logger.info(f"=== XYQO Simple Server Starting ===")
        logger.info(f"Host: {host}, Port: {port} (FORCED)")
        logger.info(f"Railway PORT env: {os.environ.get('PORT', 'NOT SET')}")
        
        server = HTTPServer((host, port), XYQOHandler)
        
        logger.info(f"Server running on http://{host}:{port}")
        logger.info("Ready to handle requests...")
        
        server.serve_forever()
        
    except Exception as e:
        logger.error(f"Server failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()
