#!/usr/bin/env python3
"""
XYQO Contract Analysis Backend - Production Version
FastAPI-based backend with production-ready features
"""

import json
import os
import io
import PyPDF2
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
from pydantic import BaseModel

# OpenAI integration
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai package not available. Install with: pip install openai")

# Initialize FastAPI app
app = FastAPI(
    title="XYQO Contract Analysis API",
    description="Production-ready contract analysis with OpenAI integration",
    version="3.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") == "development" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") == "development" else None
)

# Production middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "https://xyqo.ai,https://www.xyqo.ai").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Trust proxy headers in production
if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["xyqo.ai", "www.xyqo.ai", "api.xyqo.ai"]
    )

# In-memory storage (TODO: Replace with database in production)
analysis_storage: Dict[str, Dict[str, Any]] = {}

# Response models
class HealthResponse(BaseModel):
    status: str
    timestamp: str
    openai_available: bool
    version: str

class AnalysisResponse(BaseModel):
    success: bool
    analysis: Dict[str, Any]
    metadata: Dict[str, Any]

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        openai_available=OPENAI_AVAILABLE and bool(os.getenv('OPENAI_API_KEY')),
        version="3.0.0"
    )

@app.post("/api/v1/contract/analyze", response_model=AnalysisResponse)
async def analyze_contract(file: UploadFile = File(...)):
    """Analyze contract PDF with OpenAI"""
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Validate file size (max 10MB)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
    
    try:
        # Read PDF content
        pdf_content = await file.read()
        extracted_text = extract_pdf_text(pdf_content)
        
        if not extracted_text or len(extracted_text) < 100:
            raise HTTPException(status_code=400, detail="Could not extract sufficient text from PDF")
        
        # Analyze with OpenAI or fallback
        analysis = await analyze_contract_content(extracted_text, file.filename)
        
        # Generate unique ID and store analysis
        analysis_id = str(uuid.uuid4())
        analysis_storage[analysis_id] = {
            'analysis': analysis,
            'filename': file.filename,
            'timestamp': datetime.now().isoformat()
        }
        
        return AnalysisResponse(
            success=True,
            analysis=analysis,
            metadata={
                "filename": file.filename,
                "analysis_id": analysis_id,
                "download_url": f"/download/{analysis_id}.pdf",
                "processed_at": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        print(f"Error analyzing contract: {e}")
        raise HTTPException(status_code=500, detail="Error analyzing contract")

@app.get("/download/{analysis_id}.pdf")
async def download_pdf(analysis_id: str):
    """Download generated PDF report"""
    
    if analysis_id not in analysis_storage:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        stored_data = analysis_storage[analysis_id]
        analysis = stored_data['analysis']
        filename = stored_data['filename']
        
        # Generate PDF content
        pdf_content = generate_pdf_content(analysis, filename)
        
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=resume_contrat_{analysis_id}.pdf"
            }
        )
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        raise HTTPException(status_code=500, detail="Error generating PDF")

def extract_pdf_text(pdf_content: bytes) -> str:
    """Extract text from PDF content"""
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

async def analyze_contract_content(text: str, filename: str) -> Dict[str, Any]:
    """Analyze contract text with OpenAI or fallback"""
    
    # Try OpenAI analysis first
    if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
        try:
            return await analyze_with_openai(text, filename)
        except Exception as e:
            print(f"OpenAI analysis error: {e}")
    
    # Fallback analysis
    return create_empty_analysis(filename)

async def analyze_with_openai(text: str, filename: str) -> Dict[str, Any]:
    """Analyze contract using OpenAI GPT-4o-mini"""
    
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    prompt = f"""Analyse intégralement le contrat fourni et produis un JSON selon le schéma ci-dessous, en remplissant chaque clé avec les informations du contrat.

SCHÉMA JSON REQUIS:
{{
    "executive_summary": "Résumé exécutif détaillé du contrat en français",
    "parties": [
        {{
            "name": "Nom de la partie",
            "role": "CLIENT ou PRESTATAIRE ou FOURNISSEUR",
            "legal_form": "Forme juridique (SAS, SARL, etc.)",
            "siren_siret": "Numéro SIREN/SIRET",
            "address": "Adresse complète",
            "representative": "Nom du représentant"
        }}
    ],
    "details": {{
        "object": "Objet principal du contrat",
        "location": "Lieu d'exécution",
        "start_date": "Date de début",
        "end_date": "Date de fin",
        "minimum_duration": "Durée minimale",
        "notice_period": "Préavis de résiliation en jours"
    }},
    "obligations": {{
        "provider": ["Liste des obligations du prestataire"],
        "client": ["Liste des obligations du client"]
    }},
    "financials": {{
        "pricing_model": "Modèle de tarification",
        "payment_terms": "Conditions de paiement",
        "amounts": [
            {{"description": "Description", "amount": "Montant", "currency": "EUR"}}
        ]
    }},
    "governance": {{
        "applicable_law": "Droit applicable",
        "jurisdiction": "Juridiction compétente",
        "liability": "Clauses de responsabilité",
        "confidentiality": true/false
    }},
    "risks": ["Liste des risques identifiés"],
    "missing_info": ["Informations manquantes importantes"],
    "legal_warning": "Ce résumé ne constitue pas un conseil juridique et peut comporter des erreurs."
}}

CONTRAT À ANALYSER:
{text[:15000]}

Réponds UNIQUEMENT avec le JSON valide, sans texte additionnel."""

    response = await client.chat.completions.acreate(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.3
    )
    
    # Parse JSON response
    json_text = response.choices[0].message.content.strip()
    if json_text.startswith('```json'):
        json_text = json_text[7:-3]
    elif json_text.startswith('```'):
        json_text = json_text[3:-3]
    
    return json.loads(json_text)

def create_empty_analysis(filename: str) -> Dict[str, Any]:
    """Create fallback analysis when OpenAI is not available"""
    return {
        "executive_summary": "Analyse automatique basique - OpenAI non disponible",
        "parties": [{
            "name": "Partie non identifiée",
            "role": "CLIENT",
            "legal_form": None,
            "siren_siret": None,
            "address": None,
            "representative": None
        }],
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

def generate_pdf_content(analysis: Dict[str, Any], filename: str) -> bytes:
    """Generate PDF content from analysis using reportlab"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
        content = f"""RÉSUMÉ DE CONTRAT XYQO
========================================

Document: {filename}
Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}

OBJET DU CONTRAT:
{analysis.get('details', {}).get('object', 'Non spécifié')}

RÉSUMÉ EXÉCUTIF:
{analysis.get('executive_summary', 'Aucun résumé disponible')}

RISQUES ET ALERTES:
{chr(10).join([f"- {risk}" for risk in analysis.get('risks', [])]) if analysis.get('risks') else "Aucun risque identifié"}

========================================
Généré par XYQO Contract Analyzer v3.0
"""
        return content.encode('utf-8')

if __name__ == "__main__":
    # Production configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 XYQO Contract Analysis Backend starting on {host}:{port}")
    print(f"📊 OpenAI Available: {OPENAI_AVAILABLE and bool(os.getenv('OPENAI_API_KEY'))}")
    print(f"🌍 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    uvicorn.run(
        "xyqo_backend_production:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development"
    )
