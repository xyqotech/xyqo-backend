#!/usr/bin/env python3
"""
XYQO Contract Analysis Backend with Claude AI Integration
Integrates Claude AI for advanced contract analysis using UniversalContractV3 schema
"""

import json
import os
import io
import PyPDF2
from datetime import datetime
from urllib.parse import parse_qs, urlparse
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import re
import uuid
import traceback

# OpenAI integration
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai package not available. Install with: pip install openai")

class XYQOHandler(BaseHTTPRequestHandler):
    
    # In-memory storage for analysis results
    analysis_storage = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/health':
            self._send_health_check()
        elif parsed_path.path.startswith('/download/'):
            self._send_pdf_download(parsed_path.path)
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/v1/contract/analyze':
            self._handle_contract_analysis()
        else:
            self.send_error(404, "Not Found")
    
    def _send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def _send_health_check(self):
        """Send health check response"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "openai_available": OPENAI_AVAILABLE and bool(os.getenv('OPENAI_API_KEY')),
            "version": "3.0"
        }
        
        self.wfile.write(json.dumps(health_data).encode('utf-8'))
    
    def _handle_contract_analysis(self):
        """Handle contract analysis request"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "No content provided")
                return
            
            # Read and parse multipart form data
            post_data = self.rfile.read(content_length)
            file_content, filename = self._parse_multipart_data(post_data)
            
            if not file_content:
                self.send_error(400, "No file content found")
                return
            
            # Analyze the document
            analysis = self._analyze_document_with_openai(file_content, filename)
            
            # Generate unique ID for this analysis
            analysis_id = str(uuid.uuid4())
            
            # Store analysis for PDF download
            self.analysis_storage[analysis_id] = {
                'analysis': analysis,
                'filename': filename,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Prepare response
            response_data = {
                "success": True,
                "analysis": analysis,
                "metadata": {
                    "filename": filename,
                    "analysis_id": analysis_id,
                    "download_url": f"/download/{analysis_id}.pdf",
                    "processed_at": datetime.now(timezone.utc).isoformat()
                }
            }
            
            self._send_json_response(response_data, 200)
            
        except Exception as e:
            print(f"Error in contract analysis: {e}")
            traceback.print_exc()
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def _parse_multipart_data(self, post_data):
        """Parse multipart form data to extract file content"""
        try:
            # Simple multipart parsing for file upload
            boundary_match = re.search(rb'boundary=([^;\r\n]+)', self.headers.get('Content-Type', '').encode())
            if not boundary_match:
                return None, None
            
            boundary = boundary_match.group(1)
            parts = post_data.split(b'--' + boundary)
            
            for part in parts:
                if b'Content-Disposition: form-data' in part and b'filename=' in part:
                    # Extract filename
                    filename_match = re.search(rb'filename="([^"]*)"', part)
                    filename = filename_match.group(1).decode('utf-8') if filename_match else "document.pdf"
                    
                    # Extract file content (after double CRLF)
                    content_start = part.find(b'\r\n\r\n')
                    if content_start != -1:
                        file_content = part[content_start + 4:]
                        # Remove trailing boundary markers
                        if file_content.endswith(b'\r\n'):
                            file_content = file_content[:-2]
                        return file_content, filename
            
            return None, None
            
        except Exception as e:
            print(f"Error parsing multipart data: {e}")
            return None, None
    
    def _analyze_document_with_openai(self, content, filename):
        """Analyze document using OpenAI GPT-4 mini or fallback to simulated analysis"""
        
        # Extract text from PDF
        extracted_text = self._extract_pdf_text(content)
        
        # Try OpenAI GPT-4 mini analysis first
        if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            try:
                openai_analysis = self._openai_contract_analysis(extracted_text)
                if openai_analysis:
                    return openai_analysis
            except Exception as e:
                print(f"OpenAI analysis failed: {e}")
                # Fall through to simulated analysis
        
        # Fallback to simulated analysis
        return self._simulate_contract_analysis(extracted_text, filename)
    
    def _extract_pdf_text(self, content):
        """Extract text from PDF content"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            extracted_text = ""
            
            for page in pdf_reader.pages:
                extracted_text += page.extract_text() + "\n"
            
            return extracted_text.strip()
            
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def _openai_contract_analysis(self, text):
        """Perform contract analysis using OpenAI GPT-4 mini"""
        
        system_prompt = """Tu es un assistant juridique expert spécialisé dans l'analyse de contrats français. Ton rôle est d'extraire et structurer les informations contractuelles selon le schéma JSON UniversalContractV3.

RÈGLES CRITIQUES:
    
    def _validate_universal_contract_v3(self, data):
        """Basic validation of UniversalContractV3 structure"""
        required_fields = ['meta', 'parties', 'contract', 'financials', 'governance', 
                          'summary_plain', 'risks_red_flags', 'missing_info', 'operational_actions']
        
        return all(field in data for field in required_fields)
    
    def _simulate_contract_analysis(self, text, filename):
        """Fallback simulated analysis conforming to UniversalContractV3"""
        
        # Basic keyword analysis
        parties_found = []
        if "société" in text.lower() or "sarl" in text.lower():
            parties_found.append({"name": "Société identifiée", "role": "Partie contractante"})
        
        contract_object = "Contrat non analysé - analyse automatique indisponible"
        if "prestation" in text.lower():
            contract_object = "Contrat de prestation de services"
        elif "vente" in text.lower():
            contract_object = "Contrat de vente"
        elif "location" in text.lower():
            contract_object = "Contrat de location"
        
        return {
            "meta": {
                "generator": "ContractSummarizer",
                "version": "3.0",
                "language": "fr",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "locale_guess": "France",
                "source_doc_info": {
                    "title": filename,
                    "doc_type": "PDF",
                    "signing_method": None,
                    "signatures_present": False,
                    "version_label": None,
                    "effective_date": None
                }
            },
            "parties": {
                "list": parties_found if parties_found else [
                    {"name": None, "role": None, "legal_form": None, "siren_siret": None, 
                     "address": None, "representative": None, "contact_masked": None}
                ],
                "third_parties": []
            },
            "contract": {
                "object": contract_object,
                "scope": {"deliverables": [], "exclusions": []},
                "location_or_site": None,
                "dates": {
                    "start_date": None,
                    "end_date": None,
                    "minimum_term_months": None,
                    "renewal": None,
                    "notice_period_days": None,
                    "milestones": []
                },
                "obligations": {
                    "by_provider": [],
                    "by_customer": [],
                    "by_other": []
                },
                "service_levels": {
                    "kpi_list": [],
                    "sla": None,
                    "penalties": None
                },
                "ip_rights": {
                    "ownership": None,
                    "license_terms": None
                },
                "data_privacy": {
                    "rgpd": None,
                    "processing_roles": None,
                    "subprocessors": [],
                    "data_locations": [],
                    "security_measures": []
                }
            },
            "financials": {
                "price_model": "inconnu",
                "items": [],
                "currency": None,
                "payment_terms": None,
                "late_fees": None,
                "indexation": None,
                "security_deposit": {
                    "amount": None,
                    "currency": None,
                    "refund_terms": None
                },
                "credit_details": {
                    "principal_amount": None,
                    "currency": None,
                    "taeg_percent": None,
                    "interest_rate_percent": None,
                    "repayment_schedule": [],
                    "withdrawal_rights": {
                        "days": None,
                        "instructions": None
                    }
                }
            },
            "governance": {
                "termination": {
                    "by_provider": None,
                    "by_customer": None,
                    "effects": None
                },
                "liability": None,
                "warranties": None,
                "compliance": None,
                "law": None,
                "jurisdiction": None,
                "insurance": None,
                "confidentiality": None,
                "force_majeure": None,
                "non_compete": {
                    "exists": None,
                    "duration_months": None,
                    "scope": None,
                    "consideration_amount": None,
                    "currency": None
                }
            },
            "assurances": {
                "policies": []
            },
            "conditions_suspensives": [],
            "employment_details": {
                "contract_type": None,
                "position_title": None,
                "qualification": None,
                "collective_agreement": None,
                "probation_period": {"months": None},
                "working_time": {
                    "type": None,
                    "hours_per_week": None,
                    "days_per_year": None
                },
                "remuneration": {
                    "base_amount": None,
                    "currency": None,
                    "periodicity": None,
                    "variable": None,
                    "minimum_guarantee": None
                },
                "paid_leave_days_per_year": None,
                "notice_period": None,
                "mobility_clause": None
            },
            "immobilier_specifics": {
                "property_type": None,
                "address": None,
                "surface_sqm": None,
                "rooms": None,
                "lot_description": None,
                "diagnostics": [],
                "charges_breakdown": None,
                "works_done": None,
                "retraction_rights": {"days": None},
                "delivery": {
                    "deadline_date": None,
                    "penalties": None
                }
            },
            "litiges_modes_alternatifs": {
                "mediation": None,
                "arbitration": None,
                "amicable_settlement_steps": None
            },
            "summary_plain": f"Analyse automatique du document {filename}. L'assistant OpenAI n'est pas disponible, analyse de base effectuée. Veuillez configurer la clé API OpenAI pour une analyse complète.",
            "risks_red_flags": ["Analyse automatique limitée - Configuration OpenAI requise"],
            "missing_info": ["Informations détaillées du contrat", "Analyse juridique approfondie"],
            "operational_actions": {
                "jira_summary": None,
                "key_dates": [],
                "renewal_window_days": None
            }
        }
    
    def _send_pdf_download(self, path):
        """Send PDF download response"""
        try:
            # Extract analysis ID from path
            analysis_id = path.split('/')[-1].replace('.pdf', '')
            
            if analysis_id not in self.analysis_storage:
                self.send_error(404, "Analysis not found")
                return
            
            stored_data = self.analysis_storage[analysis_id]
            analysis = stored_data['analysis']
            
            # Generate PDF content
            pdf_content = self._generate_pdf_content(analysis, stored_data['filename'])
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition', f'attachment; filename="contract_summary_{analysis_id}.pdf"')
            self._send_cors_headers()
            self.end_headers()
            
            self.wfile.write(pdf_content)
            
        except Exception as e:
            print(f"Error sending PDF download: {e}")
            self.send_error(500, "Error generating PDF")
    
    def _generate_pdf_content(self, analysis, filename):
        """Generate PDF content from analysis"""
        
        # Create a simple text-based PDF content
        summary = analysis.get('summary_plain', 'Aucun résumé disponible')
        parties = analysis.get('parties', {}).get('list', [])
        contract_object = analysis.get('contract', {}).get('object', 'Non spécifié')
        
        parties_text = ""
        for party in parties:
            if party.get('name'):
                parties_text += f"- {party['name']} ({party.get('role', 'Rôle non spécifié')})\n"
        
        if not parties_text:
            parties_text = "Aucune partie identifiée\n"
        
        risks = analysis.get('risks_red_flags', [])
        risks_text = "\n".join([f"- {risk}" for risk in risks]) if risks else "Aucun risque identifié"
        
        # Simple PDF-like content (text format for now)
        content = f"""RÉSUMÉ DE CONTRAT XYQO
========================================

Document: {filename}
Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}

OBJET DU CONTRAT:
{contract_object}

PARTIES:
{parties_text}

RÉSUMÉ:
{summary}

RISQUES ET ALERTES:
{risks_text}

========================================
Généré par XYQO Contract Analyzer v3.0
"""
        
        # For now, return as text. In production, use a proper PDF library
        return content.encode('utf-8')
    
    def _send_json_response(self, data, status_code):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._send_cors_headers()
        self.end_headers()
        
        json_data = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(json_data.encode('utf-8'))

def main():
    """Start the XYQO backend server"""
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("WARNING: OPENAI_API_KEY not set. OpenAI analysis will not be available.")
        print("Set your API key with: export OPENAI_API_KEY='your-key-here'")
    
    # Check if openai package is available
    if not OPENAI_AVAILABLE:
        print("WARNING: openai package not installed. Install with: pip install openai")
    
    port = 8002
    server = HTTPServer(('localhost', port), XYQOHandler)
    
    print(f"🚀 XYQO Contract Analysis Backend starting on http://localhost:{port}")
    print(f"📊 OpenAI Available: {OPENAI_AVAILABLE and bool(os.getenv('OPENAI_API_KEY'))}")
    print(f"🔗 Health Check: http://localhost:{port}/health")
    print(f"📄 Contract Analysis: POST http://localhost:{port}/api/v1/contract/analyze")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        server.shutdown()

if __name__ == '__main__':
    main()
