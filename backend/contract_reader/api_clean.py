"""
API endpoints pour Contract Reader - Version simplifiée
Intégration avec FastAPI pour résumés de contrats
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form
from typing import Dict
import time
import hashlib
import logging

logger = logging.getLogger(__name__)

# Router pour les endpoints Contract Reader
router = APIRouter(tags=["Contract Reader"])

# Fonction utilitaire pour obtenir l'IP client
def get_client_ip(request: Request) -> str:
    """Extrait l'IP du client depuis les headers"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

@router.post("/analyze")
async def analyze_contract(
    request: Request,
    file: UploadFile = File(...),
    summary_mode: str = Form(default="standard")
):
    """
    Endpoint pour analyse de contrat avec OpenAI GPT-4o-mini
    """
    start_time = time.time()
    
    try:
        # Validation fichier
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")
        
        if file.size and file.size > 10 * 1024 * 1024:  # 10MB max
            raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10MB)")
        
        # Lecture contenu
        pdf_content = await file.read()
        
        # Génération user_id (hash IP pour anonymisation)
        user_ip = get_client_ip(request)
        user_id = hashlib.sha256(user_ip.encode()).hexdigest()[:16]
        
        # Mode REAL FORCÉ: vraie extraction et analyse IA
        from .ai.ai_summarizer import AISummarizer
        from .extraction.extraction_pipeline import ExtractionPipeline
        
        logger.info(f"REAL MODE: Traitement du PDF {file.filename} ({len(pdf_content)} bytes)")
        
        # Extraction du texte du PDF
        extractor = ExtractionPipeline()
        extraction_result = await extractor.extract_contract_data(pdf_content, file.filename)
        
        if not extraction_result.get('success'):
            logger.error(f"Erreur extraction: {extraction_result.get('error')}")
            raise HTTPException(status_code=400, detail="Erreur extraction PDF")
        
        logger.info(f"Extraction réussie: {len(extraction_result['extracted_text'])} caractères")
        
        # Analyse IA avec OpenAI
        ai_summarizer = AISummarizer()
        summary_result = await ai_summarizer.generate_summary(
            extracted_text=extraction_result['extracted_text'],
            filename=file.filename,
            summary_mode=summary_mode
        )
        
        if not summary_result.get('success'):
            logger.error(f"Erreur IA: {summary_result.get('error')}")
            raise HTTPException(status_code=500, detail=f"Erreur analyse IA: {summary_result.get('error')}")
        
        logger.info(f"Analyse IA réussie: coût {summary_result.get('cost_euros', 0):.3f}€")
        
        # Construction du résultat
        result = {
            'success': True,
            'result': {
                'summary': summary_result['summary'],
                'processing_metrics': {
                    'total_cost_euros': summary_result.get('cost_euros', 0.0),
                    'ai_time': summary_result.get('processing_time', 0.0)
                }
            }
        }
        
        # Retour JSON simple sans modèle Pydantic
        return {
            "success": True,
            "summary": result['result']['summary'],
            "processing_time": time.time() - start_time,
            "from_cache": False,
            "cost_euros": result['result']['processing_metrics'].get('total_cost_euros', 0.0),
            "file_size": len(pdf_content),
            "user_id": user_id,
            "processing_id": f"real_{user_id[:8]}",
            "validation_report": None,
            "citations": None,
            "dod_compliance": None,
            "pdf_download_info": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur traitement contrat: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/health")
async def health_check():
    """Vérification de l'état du service"""
    return {
        "status": "healthy",
        "service": "contract_reader",
        "timestamp": time.time()
    }
