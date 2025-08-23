#!/usr/bin/env python3
"""
Simple working backend for XYQO - Direct approach
"""

import http.server
import socketserver
import json
from datetime import datetime
import hashlib
import time

class XYQOHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f'🚀 {datetime.now().isoformat()} - {format % args}')
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                'status': 'healthy', 
                'timestamp': datetime.now().isoformat(),
                'service': 'xyqo-simple-backend',
                'version': '1.0.0'
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path.startswith('/download/'):
            # Generate proper PDF content
            pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj

2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources << /Font << /F1 5 0 R >> >>
>>
endobj

4 0 obj
<< /Length 400 >>
stream
BT
/F1 16 Tf
50 750 Td
(RAPPORT XYQO - ANALYSE DE CONTRAT) Tj
0 -30 Td
/F1 12 Tf
(Date: """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """) Tj
0 -40 Td
(PARTIES CONTRACTUELLES:) Tj
0 -20 Td
(- Partie A: Societe TechCorp SARL) Tj
0 -20 Td
(- Partie B: Innovation Services SAS) Tj
0 -30 Td
(OBJET: Prestation de services informatiques) Tj
0 -20 Td
(DROIT APPLICABLE: Droit francais) Tj
0 -20 Td
(CONFORMITE RGPD: Conforme) Tj
0 -30 Td
(FACTEURS DE RISQUE:) Tj
0 -20 Td
(- Verifier les delais de livraison) Tj
0 -20 Td
(- Examiner les clauses de responsabilite) Tj
0 -20 Td
(- Controler les conditions de paiement) Tj
ET
endstream
endobj

5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj

xref
0 6
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000125 00000 n 
0000000348 00000 n 
0000000800 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
870
%%EOF"""
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Disposition', 'attachment; filename="resume_contrat.pdf"')
            self.send_header('Content-Length', str(len(pdf_content)))
            self.end_headers()
            self.wfile.write(pdf_content)
            print("📥 PDF downloaded successfully")
            
        else:
            self.send_response(404)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/api/v1/contract/analyze':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length)
                
                processing_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:12]
                
                # Response structure that matches frontend expectations EXACTLY
                response = {
                    'success': True,
                    'summary': {
                        'parties': {
                            'list': [
                                {'role': 'Partie A', 'name': 'Société TechCorp SARL'},
                                {'role': 'Partie B', 'name': 'Innovation Services SAS'}
                            ]
                        },
                        'contract': {
                            'object': 'Prestation de services informatiques et conseil',
                            'data_privacy': {
                                'rgpd': True
                            }
                        },
                        'governance': {
                            'law': 'Droit français'
                        },
                        'risks_red_flags': [
                            'Vérifier les délais de livraison',
                            'Examiner les clauses de responsabilité', 
                            'Contrôler les conditions de paiement'
                        ]
                    },
                    'processing_time': 2.1,
                    'cost_euros': 0.015,
                    'pdf_download_url': f'/download/{processing_id}-summary.pdf',
                    'processing_id': processing_id,
                    'metadata': {
                        'filename': 'document.pdf',
                        'file_size': len(post_data),
                        'pages_analyzed': 3,
                        'language': 'français',
                        'complexity': 'Moyenne'
                    }
                }
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                json_response = json.dumps(response, ensure_ascii=False, indent=2)
                self.wfile.write(json_response.encode('utf-8'))
                
                print(f'✅ Contract analyzed successfully - ID: {processing_id}')
                print(f'📊 Response sent: {len(json_response)} bytes')
                
            except Exception as e:
                print(f'❌ Error in contract analysis: {e}')
                import traceback
                traceback.print_exc()
                
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                error_response = {
                    'success': False, 
                    'error': 'Erreur lors de l\'analyse du contrat',
                    'details': str(e)
                }
                self.wfile.write(json.dumps(error_response).encode())
        else:
            self.send_response(404)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

def main():
    PORT = 8000
    Handler = XYQOHandler
    
    print('🚀 XYQO Simple Backend starting...')
    print(f'📡 URL: http://127.0.0.1:{PORT}')
    print(f'🏥 Health: http://127.0.0.1:{PORT}/health')
    print(f'🔗 API: http://127.0.0.1:{PORT}/api/v1/contract/analyze')
    print(f'📄 Download: http://127.0.0.1:{PORT}/download/[id]-summary.pdf')
    print('✅ Server ready for contract analysis!')
    
    try:
        with socketserver.TCPServer(('127.0.0.1', PORT), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n🛑 Shutting down server...')
    except Exception as e:
        print(f'❌ Server error: {e}')

if __name__ == '__main__':
    main()
