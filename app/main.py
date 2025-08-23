#!/usr/bin/env python3
"""
XYQO Contract Reader - Backend Production
FastAPI backend with OpenAI GPT-4o-mini integration and professional PDF generation
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
from io import BytesIO

# Core dependencies
from fastapi import FastAPI, HTTPException, UploadFile, File, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import uvicorn

# PDF and AI dependencies
import PyPDF2
import openai
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# Environment setup
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="XYQO Contract Reader Backend",
    description="Professional contract analysis with OpenAI GPT-4o-mini and PDF generation",
    version="2.0.0"
)

# CORS configuration - CRITICAL: Only allow Vercel domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGINS", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI configuration - Allow startup without API key for healthcheck
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    openai.api_key = openai_api_key

# In-memory caches
pdf_cache: Dict[str, bytes] = {}
analysis_cache: Dict[str, Dict[str, Any]] = {}

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """Extract text content from PDF bytes"""
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise HTTPException(status_code=400, detail="Invalid PDF file")

def analyze_contract_with_openai(contract_text: str) -> Dict[str, Any]:
    """Analyze contract using OpenAI GPT-4o-mini - NO SIMULATION MODE"""
    
    # CRITICAL: Fail if no API key, don't simulate
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    
    system_prompt = """Tu es un expert juridique spécialisé dans l'analyse de contrats commerciaux français. 
Tu dois analyser le contrat fourni et produire UNIQUEMENT un JSON STRICT selon le schéma UniversalContractV3.

CONTRAINTES ABSOLUES :
- Réponse UNIQUEMENT en JSON valide, UTF-8
- Dates au format ISO 8601 (YYYY-MM-DD)
- Montants avec devise ISO 4217 (EUR, USD, etc.)
- Masquer IBAN/email/téléphone par "***MASQUÉ***"
- Ne JAMAIS inventer d'informations - utiliser null si incertain
- Résumé exécutif en 10-20 lignes compréhensible pour non-juristes

SCHÉMA JSON REQUIS :
{
  "executive_summary": "string (10-20 lignes)",
  "parties": [
    {
      "role": "CLIENT|PRESTATAIRE|AUTRE",
      "name": "string",
      "legal_form": "string|null",
      "siren_siret": "string|null", 
      "address": "string|null",
      "representative": "string|null"
    }
  ],
  "details": {
    "object": "string",
    "place": "string|null",
    "start_date": "YYYY-MM-DD|null",
    "end_date": "YYYY-MM-DD|null", 
    "minimum_duration": "string|null",
    "notice_period": "string|null"
  },
  "obligations": {
    "provider": ["string"],
    "client": ["string"]
  },
  "financials": {
    "pricing_model": "string|null",
    "payment_terms": "string|null",
    "amounts": [
      {
        "type": "string",
        "amount": "number|null",
        "currency": "string|null"
      }
    ]
  },
  "governance": {
    "applicable_law": "string|null",
    "jurisdiction": "string|null",
    "liability": "string|null",
    "confidentiality": "string|null"
  },
  "risks": ["string"],
  "missing_info": ["string"],
  "legal_warning": "Cette analyse est fournie à titre informatif uniquement et ne constitue pas un conseil juridique professionnel."
}"""

    user_prompt = f"Analyse ce contrat et réponds UNIQUEMENT avec le JSON selon le schéma :\n\n{contract_text[:8000]}"

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=3000,
            temperature=0.1
        )
        
        analysis_text = response.choices[0].message.content.strip()
        
        # Clean JSON markers
        if analysis_text.startswith("```json"):
            analysis_text = analysis_text[7:]
        if analysis_text.endswith("```"):
            analysis_text = analysis_text[:-3]
        
        analysis = json.loads(analysis_text)
        return analysis
        
    except Exception as e:
        logger.error(f"OpenAI analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

def generate_pdf_report(analysis: Dict[str, Any], processing_id: str) -> bytes:
    """Generate professional PDF report using ReportLab"""
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        textColor=HexColor('#2563eb'),
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        textColor=HexColor('#1f2937'),
        spaceBefore=16
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=8,
        alignment=TA_JUSTIFY
    )
    
    story = []
    
    # Title
    story.append(Paragraph("RAPPORT D'ANALYSE CONTRACTUELLE", title_style))
    story.append(Spacer(1, 20))
    
    # Executive Summary
    story.append(Paragraph("RÉSUMÉ EXÉCUTIF", heading_style))
    story.append(Paragraph(analysis.get('executive_summary', 'Non disponible'), body_style))
    story.append(Spacer(1, 12))
    
    # Parties
    story.append(Paragraph("PARTIES CONTRACTUELLES", heading_style))
    for party in analysis.get('parties', []):
        party_text = f"<b>{party.get('role', 'N/A')}</b>: {party.get('name', 'N/A')}"
        if party.get('legal_form'):
            party_text += f" ({party['legal_form']})"
        story.append(Paragraph(party_text, body_style))
    story.append(Spacer(1, 12))
    
    # Contract Details
    details = analysis.get('details', {})
    story.append(Paragraph("DÉTAILS DU CONTRAT", heading_style))
    story.append(Paragraph(f"<b>Objet:</b> {details.get('object', 'Non spécifié')}", body_style))
    if details.get('start_date'):
        story.append(Paragraph(f"<b>Date de début:</b> {details['start_date']}", body_style))
    if details.get('end_date'):
        story.append(Paragraph(f"<b>Date de fin:</b> {details['end_date']}", body_style))
    story.append(Spacer(1, 12))
    
    # Financials
    financials = analysis.get('financials', {})
    if financials.get('pricing_model') or financials.get('amounts'):
        story.append(Paragraph("ASPECTS FINANCIERS", heading_style))
        if financials.get('pricing_model'):
            story.append(Paragraph(f"<b>Modèle tarifaire:</b> {financials['pricing_model']}", body_style))
        for amount in financials.get('amounts', []):
            if amount.get('amount') and amount.get('currency'):
                story.append(Paragraph(f"<b>{amount.get('type', 'Montant')}:</b> {amount['amount']} {amount['currency']}", body_style))
        story.append(Spacer(1, 12))
    
    # Risks
    risks = analysis.get('risks', [])
    if risks:
        story.append(Paragraph("FACTEURS DE RISQUE", heading_style))
        for risk in risks:
            story.append(Paragraph(f"• {risk}", body_style))
        story.append(Spacer(1, 12))
    
    # Legal Warning
    story.append(Paragraph("AVERTISSEMENT JURIDIQUE", heading_style))
    story.append(Paragraph(analysis.get('legal_warning', 'Cette analyse est fournie à titre informatif uniquement.'), body_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

@app.get("/")
def root():
    """Root endpoint for Railway health checks"""
    return {"message": "XYQO Backend is running", "status": "ok"}

@app.get("/health")
def health():
    """Health check endpoint - CRITICAL: Must show FastAPI, not Node.js"""
    return {
        "status": "healthy",
        "service": "xyqo-backend",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "port": os.getenv("PORT", "8000"),
        "version": "2.0.0",
        "openai_configured": bool(openai_api_key)
    }

@app.post("/api/v1/contract/analyze")
async def analyze_contract(file: UploadFile = File(...)):
    """Contract analysis endpoint - CRITICAL: No simulation mode"""
    
    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read PDF content
        content = await file.read()
        
        # Extract text
        contract_text = extract_text_from_pdf(content)
        
        if len(contract_text) < 100:
            raise HTTPException(status_code=400, detail="PDF content too short or unreadable")
        
        # Analyze with OpenAI - CRITICAL: Will fail if no API key
        start_time = datetime.utcnow()
        analysis = analyze_contract_with_openai(contract_text)
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Generate processing ID
        processing_id = hashlib.sha256(content).hexdigest()[:16]
        
        # Generate PDF report
        pdf_bytes = generate_pdf_report(analysis, processing_id)
        
        # Cache both analysis and PDF
        analysis_cache[processing_id] = analysis
        pdf_cache[processing_id] = pdf_bytes
        
        # Return response - CRITICAL: Structure must match frontend expectations
        return JSONResponse({
            "success": True,
            "analysis": analysis,
            "metadata": {
                "processing_id": processing_id,
                "processing_time": round(processing_time, 2),
                "cost_euros": 0.01,
                "pdf_download_url": f"/api/v1/contract/download?id={processing_id}"
            }
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Contract analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/api/v1/contract/download")
def download_pdf(id: str):
    """PDF download endpoint - CRITICAL: Must serve real PDF bytes"""
    
    if id not in pdf_cache:
        raise HTTPException(status_code=404, detail="PDF not found or expired")
    
    pdf_bytes = pdf_cache[id]
    
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=rapport_contrat.pdf",
            "Content-Length": str(len(pdf_bytes))
        }
    )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)
