"""
API endpoint simple pour Contract Reader - Version test sans GDPR
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form
import time
import hashlib

# Router simple sans dépendances complexes
router = APIRouter(tags=["Contract Reader Simple"])

def get_client_ip(request: Request) -> str:
    """Extrait l'IP du client"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

@router.post("/test")
async def test_contract_analysis(
    request: Request,
    file: UploadFile = File(...),
    summary_mode: str = Form(default="standard")
):
    """
    Endpoint de test simple pour analyse de contrat - Pas de GDPR
    """
    start_time = time.time()
    
    try:
        # Validation fichier basique
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")
        
        if file.size and file.size > 10 * 1024 * 1024:  # 10MB max
            raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10MB)")
        
        # Lecture contenu (pour validation)
        pdf_content = await file.read()
        
        # Génération user_id simple
        user_ip = get_client_ip(request)
        user_id = hashlib.sha256(user_ip.encode()).hexdigest()[:16]
        
        processing_time = time.time() - start_time
        
        # Résultat simulé pour test
        mock_summary = {
            "title": f"Résumé de {file.filename}",
            "tldr": "Contrat de prestation de services entre deux parties avec obligations mutuelles et conditions de paiement définies.",
            "parties": [
                {"nom": "Entreprise A", "role": "Prestataire"},
                {"nom": "Entreprise B", "role": "Client"}
            ],
            "dates": [
                {"type": "signature", "date": "2024-01-15"},
                {"type": "début", "date": "2024-02-01"},
                {"type": "fin", "date": "2024-12-31"}
            ],
            "montants": [
                {"type": "total", "montant": 50000, "devise": "EUR"}
            ],
            "confidence_score": 0.95,
            "key_terms": ["prestation", "paiement", "résiliation"],
            "summary_sections": {
                "objet": "Prestation de services informatiques",
                "obligations": "Livraison selon cahier des charges",
                "paiement": "Mensuel, 30 jours fin de mois"
            }
        }
        
        # Retour JSON simple
        return {
            "success": True,
            "summary": mock_summary,
            "processing_time": processing_time,
            "from_cache": False,
            "cost_euros": 0.02,
            "processing_id": f"test_{user_id[:8]}",
            "validation_report": None,
            "citations": None,
            "dod_compliance": None,
            "pdf_download_info": None,
            "file_size": len(pdf_content),
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")
