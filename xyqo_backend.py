#!/usr/bin/env python3
"""
XYQO Contract Analysis Backend with OpenAI Integration
Integrates OpenAI GPT-4 mini for advanced contract analysis with new user prompt
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
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
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
            file_content = None
            filename = "document.pdf"
            
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                
                # Parse multipart form data
                try:
                    boundary = None
                    content_type = self.headers.get('Content-Type', '')
                    if 'boundary=' in content_type:
                        boundary = content_type.split('boundary=')[1]
                    
                    if boundary:
                        parts = post_data.split(f'--{boundary}'.encode())
                        for part in parts:
                            if b'Content-Disposition: form-data' in part and b'name="file"' in part:
                                # Extract filename
                                if b'filename=' in part:
                                    filename_match = re.search(rb'filename="([^"]*)"', part)
                                    if filename_match:
                                        filename = filename_match.group(1).decode('utf-8')
                                
                                # Extract file content
                                content_start = part.find(b'\r\n\r\n')
                                if content_start != -1:
                                    file_content = part[content_start + 4:]
                                    # Remove trailing boundary markers
                                    if file_content.endswith(b'\r\n'):
                                        file_content = file_content[:-2]
                                break
                    
                except Exception as e:
                    print(f"Error parsing multipart data: {e}")
                    self.send_error(400, "Invalid multipart data")
                    return
            
            if not file_content:
                self.send_error(400, "No file content found")
                return
            
            # Analyze the document
            analysis = self._analyze_document(file_content, filename)
            
            # Generate unique analysis ID
            analysis_id = str(uuid.uuid4())
            
            # Store analysis for PDF download
            self.analysis_storage[analysis_id] = {
                'analysis': analysis,
                'filename': filename,
                'timestamp': datetime.now().isoformat()
            }
            
            # Prepare response
            response_data = {
                "success": True,
                "analysis": analysis,
                "metadata": {
                    "filename": filename,
                    "analysis_id": analysis_id,
                    "download_url": f"/download/{analysis_id}.pdf",
                    "processed_at": datetime.now().isoformat()
                }
            }
            
            self._send_json_response(response_data, 200)
            
        except Exception as e:
            print(f"Error in contract analysis: {e}")
            traceback.print_exc()
            self.send_error(500, "Internal server error")
    
    def _analyze_document(self, content, filename):
        """Analyze document content"""
        # Extract text from PDF
        extracted_text = self._extract_pdf_text(content)
        
        if not extracted_text:
            return self._create_empty_analysis(filename)
        
        # Try OpenAI analysis first
        if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            openai_result = self._analyze_with_openai(extracted_text, filename)
            if openai_result:
                return openai_result
        
        # Fallback to basic analysis
        return self._basic_analysis(extracted_text, filename)
    
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
    
    def _analyze_with_openai(self, extracted_text, filename):
        """Analyze contract using OpenAI GPT-4 mini with new user prompt"""
        try:
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            prompt = f"""Analyse intégralement le contrat fourni et produis un JSON selon le schéma ci-dessous, en remplissant chaque clé avec les informations du contrat.

<format_json_attendu>
{{
  "executive_summary": "Résumé concis en français (10–20 lignes)",
  "parties": [
    {{
      "name": "Nom complet de la partie",
      "role": "CLIENT ou PRESTATAIRE ou autre",
      "legal_form": "Forme juridique",
      "siren_siret": "Numéro SIREN/SIRET ou null",
      "address": "Adresse complète ou null",
      "representative": "Nom du représentant légal ou null"
    }}
  ],
  "details": {{
    "object": "Objet du contrat (services, bail, etc.)",
    "location": "Lieu d'exécution ou du bien ou null",
    "start_date": "YYYY-MM-DD ou null",
    "end_date": "YYYY-MM-DD ou null",
    "minimum_duration": "Nombre de mois ou null",
    "notice_period": "Nombre de jours de préavis ou null"
  }},
  "obligations": {{
    "provider": ["Liste des obligations du prestataire"],
    "client": ["Liste des obligations du client"]
  }},
  "financials": {{
    "pricing_model": "Forfait, abonnement, à l'acte, mixte ou inconnu",
    "payment_terms": "Modalités de paiement ou null",
    "amounts": [
      {{"label": "Libellé", "amount": 0, "currency": "EUR"}}
    ]
  }},
  "governance": {{
    "applicable_law": "Droit applicable ou null",
    "jurisdiction": "Tribunal compétent ou null",
    "liability": "Clause de responsabilité ou null",
    "confidentiality": true/false/null
  }},
  "risks": ["Liste des points d'attention ou risques relevés"],
  "missing_info": ["Liste des informations absentes du contrat"],
  "legal_warning": "Texte standard rappelant que ce résumé ne constitue pas un conseil juridique et qu'il peut comporter des erreurs"
}}
</format_json_attendu>

<contract_text>
{extracted_text[:12000]}
</contract_text>

<instructions_sortie>
- Respecte exactement la structure JSON demandée.  
- Utilise null ou [] si un champ n'existe pas.  
- Le résumé doit refléter fidèlement le contrat sans reprendre mot pour mot les clauses.  
</instructions_sortie>

Réponds UNIQUEMENT avec le JSON valide, sans texte additionnel."""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Tu es un expert en analyse contractuelle. Réponds uniquement en JSON valide selon le format demandé."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=4000
            )
            
            # Parse the JSON response
            analysis_text = response.choices[0].message.content.strip()
            
            # Clean up the response (remove markdown code blocks if present)
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text[7:]
            if analysis_text.endswith('```'):
                analysis_text = analysis_text[:-3]
            
            analysis = json.loads(analysis_text)
            
            return analysis
            
        except Exception as e:
            print(f"OpenAI analysis error: {e}")
            return None
    
    def _basic_analysis(self, text, filename):
        """Basic fallback analysis"""
        return {
            "executive_summary": "Analyse automatique basique - OpenAI non disponible",
            "parties": [
                {
                    "name": "Partie non identifiée",
                    "role": "CLIENT",
                    "legal_form": None,
                    "siren_siret": None,
                    "address": None,
                    "representative": None
                }
            ],
            "details": {
                "object": "Objet du contrat non analysé",
                "location": None,
                "start_date": None,
                "end_date": None,
                "minimum_duration": None,
                "notice_period": None
            },
            "obligations": {
                "provider": ["Obligations non analysées"],
                "client": ["Obligations non analysées"]
            },
            "financials": {
                "pricing_model": "inconnu",
                "payment_terms": None,
                "amounts": []
            },
            "governance": {
                "applicable_law": None,
                "jurisdiction": None,
                "liability": None,
                "confidentiality": None
            },
            "risks": ["Analyse IA non disponible - vérification manuelle recommandée"],
            "missing_info": ["Toutes les informations - analyse automatique limitée"],
            "legal_warning": "Ce résumé automatique ne constitue pas un conseil juridique et peut comporter des erreurs. Une analyse par un professionnel du droit est recommandée."
        }
    
    def _create_empty_analysis(self, filename):
        """Create empty analysis when PDF extraction fails"""
        return {
            "executive_summary": "Impossible d'extraire le texte du document PDF",
            "parties": [],
            "details": {
                "object": "Document non lisible",
                "location": None,
                "start_date": None,
                "end_date": None,
                "minimum_duration": None,
                "notice_period": None
            },
            "obligations": {
                "provider": [],
                "client": []
            },
            "financials": {
                "pricing_model": "inconnu",
                "payment_terms": None,
                "amounts": []
            },
            "governance": {
                "applicable_law": None,
                "jurisdiction": None,
                "liability": None,
                "confidentiality": None
            },
            "risks": ["Document PDF non lisible ou corrompu"],
            "missing_info": ["Toutes les informations - extraction PDF échouée"],
            "legal_warning": "Ce document n'a pas pu être analysé. Veuillez vérifier le format du fichier PDF."
        }
    
    def _send_pdf_download(self, path):
        """Handle PDF download requests"""
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
            self.send_header('Content-Disposition', f'attachment; filename="resume_contrat_{analysis_id}.pdf"')
            self._send_cors_headers()
            self.end_headers()
            
            self.wfile.write(pdf_content)
            
        except Exception as e:
            print(f"Error sending PDF download: {e}")
            self.send_error(500, "Error generating PDF")
    
    def _generate_pdf_content(self, analysis, filename):
        """Generate actual PDF content from analysis using reportlab"""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            import io
            
            # Create PDF in memory
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
            
            # Get styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=18, spaceAfter=30, alignment=1)
            heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, spaceAfter=12, textColor=colors.darkblue)
            
            # Build story
            story = []
            
            # Title
            story.append(Paragraph("RÉSUMÉ DE CONTRAT XYQO", title_style))
            story.append(Spacer(1, 12))
            
            # Document info
            story.append(Paragraph(f"<b>Document:</b> {filename}", styles['Normal']))
            story.append(Paragraph(f"<b>Généré le:</b> {datetime.now().strftime('%d/%m/%Y à %H:%M')}", styles['Normal']))
            story.append(Spacer(1, 20))
            
            # Contract object
            contract_object = analysis.get('details', {}).get('object', 'Non spécifié')
            story.append(Paragraph("OBJET DU CONTRAT", heading_style))
            story.append(Paragraph(contract_object, styles['Normal']))
            story.append(Spacer(1, 15))
            
            # Parties
            story.append(Paragraph("PARTIES", heading_style))
            parties = analysis.get('parties', [])
            if parties:
                for party in parties:
                    if party.get('name'):
                        party_info = f"<b>{party['name']}</b> ({party.get('role', 'Rôle non spécifié')})"
                        if party.get('address'):
                            party_info += f"<br/>{party['address']}"
                        if party.get('siren_siret'):
                            party_info += f"<br/>SIREN/SIRET: {party['siren_siret']}"
                        story.append(Paragraph(party_info, styles['Normal']))
                        story.append(Spacer(1, 8))
            else:
                story.append(Paragraph("Aucune partie identifiée", styles['Normal']))
            story.append(Spacer(1, 15))
            
            # Executive summary
            story.append(Paragraph("RÉSUMÉ EXÉCUTIF", heading_style))
            summary = analysis.get('executive_summary', 'Aucun résumé disponible')
            story.append(Paragraph(summary, styles['Normal']))
            story.append(Spacer(1, 15))
            
            # Obligations
            obligations = analysis.get('obligations', {})
            if obligations.get('provider') or obligations.get('client'):
                story.append(Paragraph("OBLIGATIONS", heading_style))
                
                if obligations.get('provider'):
                    story.append(Paragraph("<b>Obligations du prestataire:</b>", styles['Normal']))
                    for obligation in obligations['provider']:
                        story.append(Paragraph(f"• {obligation}", styles['Normal']))
                    story.append(Spacer(1, 8))
                
                if obligations.get('client'):
                    story.append(Paragraph("<b>Obligations du client:</b>", styles['Normal']))
                    for obligation in obligations['client']:
                        story.append(Paragraph(f"• {obligation}", styles['Normal']))
                story.append(Spacer(1, 15))
            
            # Risks
            story.append(Paragraph("RISQUES ET ALERTES", heading_style))
            risks = analysis.get('risks', [])
            if risks:
                for risk in risks:
                    story.append(Paragraph(f"⚠️ {risk}", styles['Normal']))
                    story.append(Spacer(1, 4))
            else:
                story.append(Paragraph("Aucun risque identifié", styles['Normal']))
            
            story.append(Spacer(1, 30))
            story.append(Paragraph("Généré par XYQO Contract Analyzer v3.0", styles['Italic']))
            
            # Build PDF
            doc.build(story)
            
            # Get PDF data
            pdf_data = buffer.getvalue()
            buffer.close()
            
            return pdf_data
            
        except ImportError:
            # Fallback to text if reportlab not available
            summary = analysis.get('executive_summary', 'Aucun résumé disponible')
            parties = analysis.get('parties', [])
            contract_object = analysis.get('details', {}).get('object', 'Non spécifié')
            
            parties_text = ""
            for party in parties:
                if party.get('name'):
                    parties_text += f"- {party['name']} ({party.get('role', 'Rôle non spécifié')})\n"
            
            if not parties_text:
                parties_text = "Aucune partie identifiée\n"
            
            risks = analysis.get('risks', [])
            risks_text = "\n".join([f"- {risk}" for risk in risks]) if risks else "Aucun risque identifié"
            
            content = f"""RÉSUMÉ DE CONTRAT XYQO
========================================

Document: {filename}
Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}

OBJET DU CONTRAT:
{contract_object}

PARTIES:
{parties_text}

RÉSUMÉ EXÉCUTIF:
{summary}

RISQUES ET ALERTES:
{risks_text}

========================================
Généré par XYQO Contract Analyzer v3.0
"""
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
