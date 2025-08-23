#!/usr/bin/env python3
"""
Test Python server to compare with Node.js behavior
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

class TestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"🐍 {datetime.now().isoformat()} - {format % args}")

    def do_OPTIONS(self):
        print("✈️ Python: Handling OPTIONS preflight")
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        print("✅ Python: OPTIONS response sent")

    def do_GET(self):
        print(f"📥 Python: GET {self.path}")
        
        if self.path in ['/health', '/']:
            health_data = {
                'status': 'healthy',
                'service': 'python-test-server',
                'timestamp': datetime.now().isoformat(),
                'port': 8000,
                'uptime': time.time(),
                'test': 'python_working'
            }
            
            response_json = json.dumps(health_data, indent=2)
            print(f"📤 Python: Sending response: {response_json[:100]}...")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response_json)))
            self.end_headers()
            
            self.wfile.write(response_json.encode('utf-8'))
            print("✅ Python: Health response sent")
            
        else:
            error_response = json.dumps({'error': 'Not found', 'url': self.path})
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(error_response.encode('utf-8'))
            print("✅ Python: 404 response sent")

    def do_POST(self):
        print(f"📥 Python: POST {self.path}")
        
        if self.path == '/api/v1/contract/analyze':
            response_data = {
                'success': True,
                'message': 'Python server working',
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'title': 'Python Test Contract Analysis',
                    'parties': ['Python Party A', 'Python Party B'],
                    'contract_type': 'Python Test Agreement'
                }
            }
            
            response_json = json.dumps(response_data, indent=2)
            print(f"📤 Python: Sending analysis response: {response_json[:100]}...")
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response_json)))
            self.end_headers()
            
            self.wfile.write(response_json.encode('utf-8'))
            print("✅ Python: Analysis response sent")

if __name__ == '__main__':
    server_address = ('127.0.0.1', 8000)
    httpd = HTTPServer(server_address, TestHandler)
    
    print("🐍 Python Test Server started")
    print(f"📡 URL: http://127.0.0.1:8000")
    print(f"🏥 Health: http://127.0.0.1:8000/health")
    print(f"⏰ Started: {datetime.now().isoformat()}")
    print("🔍 Ready for testing...")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Python server...")
        httpd.shutdown()
        print("✅ Python server closed")
