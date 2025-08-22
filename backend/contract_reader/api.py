"""
API endpoints pour Contract Reader
Intégration avec FastAPI pour résumés de contrats
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict
import time
from datetime import datetime, timedelta
import hashlib
import logging
from .cache import RedisClient, BudgetControl, MetricsCollector
from .models import (
    ContractSummaryResponse, 
    SystemHealth, BudgetStatus
)
from .main_pipeline import contract_reader_pipeline
from .gdpr.consent_manager import ConsentType
from .rendering.universal_pdf_generator import UniversalPDFGenerator
from .monitoring.health_check import health_monitor
from .config.performance_config import PerformanceConfig
import json

logger = logging.getLogger(__name__)

# Router pour les endpoints Contract Reader
router = APIRouter(tags=["Contract Reader"])

# Instances globales (à initialiser dans main.py)
cache = RedisClient()
budget_controller = BudgetControl(cache)
quota_manager = MetricsCollector(cache)
metrics = MetricsCollector(cache)
pdf_generator = UniversalPDFGenerator()

def get_client_ip(request: Request) -> str:
    """Extrait l'IP du client"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host

@router.post("/analyze")
async def analyze_contract(
    request: Request,
    file: UploadFile = File(...),
    summary_mode: str = Form(default="standard")
):
    """
    Endpoint simplifié pour analyse de contrat - Version test sans GDPR
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
        
        # Génération processing_id unique basé sur le contenu
        processing_id = hashlib.sha256(pdf_content).hexdigest()[:16]
        
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
            'processing_id': processing_id,
            'user_id': user_id,
            'summary': summary_result.get('summary', {}),
            'processing_time': summary_result.get('processing_time', 0),
            'cost_euros': summary_result.get('cost_euros', 0),
            'from_cache': False
        }
        
        # Retour JSON simple sans modèle Pydantic
        # Génération du PDF de résumé après traitement réussi
        pdf_download_url = None
        try:
            if result.get('success') and result.get('summary'):
                # Génération du PDF professionnel
                pdf_bytes = pdf_generator.generate_contract_summary_pdf(
                    summary_data=result.get('summary', {}),
                    filename=f"resume_contrat_{processing_id}.pdf"
                )
                
                # Stockage en cache Redis avec TTL de 7 jours
                await cache.ensure_connected()
                pdf_cache_key = f"pdf_summary:{processing_id}"
                await cache.redis.setex(
                    pdf_cache_key,
                    7 * 24 * 3600,  # 7 jours
                    pdf_bytes
                )
                
                # URL de téléchargement
                pdf_download_url = f"/api/v1/contract/download/summary_{processing_id}"
                
                logger.info(f"PDF résumé généré et mis en cache: {processing_id} ({len(pdf_bytes)} bytes)")
                
        except Exception as pdf_error:
            logger.warning(f"Erreur génération PDF résumé: {pdf_error}")

        return JSONResponse({
            "success": True,
            "summary": result.get('summary', {}),
            "processing_time": result.get('processing_time', 0),
            "from_cache": result.get('from_cache', False),
            "cost_euros": result.get('cost_euros', 0),
            "file_size": len(pdf_content),
            "user_id": result.get('user_id', user_id),
            "processing_id": result.get('processing_id', 'unknown'),
            "validation_report": result.get('validation_report'),
            "citations": result.get('citations'),
            "dod_compliance": result.get('dod_compliance'),
            "pdf_download_url": pdf_download_url
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur traitement contrat: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    request: Request,
    user_id: str = None
):
    """
    Télécharge un fichier PDF généré ou génère un PDF de résumé
    """
    try:
        user_ip = get_client_ip(request)
        
        # Si le file_id commence par "summary_", récupérer le PDF de résumé depuis le cache
        if file_id.startswith("summary_"):
            processing_id = file_id.replace("summary_", "")
            
            # Vérifier d'abord si le PDF est déjà en cache
            await cache.ensure_connected()
            pdf_cache_key = f"pdf_summary:{processing_id}"
            pdf_data = await cache.redis.get(pdf_cache_key)
            
            if pdf_data:
                # PDF trouvé en cache
                if isinstance(pdf_data, str):
                    pdf_data = pdf_data.encode()
                
                # Enregistrement des métriques de téléchargement
                await metrics.record_pdf_download(
                    processing_id=processing_id,
                    user_id=user_id or "anonymous",
                    user_ip=user_ip,
                    pdf_size=len(pdf_data)
                )
                
                from fastapi.responses import Response
                
                return Response(
                    content=pdf_data,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"attachment; filename=resume_contrat_{processing_id}.pdf",
                        "Content-Length": str(len(pdf_data)),
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0"
                    }
                )
            
            # Si pas de PDF en cache, générer à la volée
            cache_key = f"contract_summary:{processing_id}"
            cached_data = await cache.redis.get(cache_key)
            
            if cached_data:
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode()
                cached_result = json.loads(cached_data)
            else:
                cached_result = None
            
            if not cached_result:
                raise HTTPException(
                    status_code=404,
                    detail="Résumé introuvable ou expiré"
                )
            
            # Extraction des données de résumé (sans métadonnées techniques)
            summary_data = cached_result.get('summary', {})
            
            if not summary_data:
                raise HTTPException(
                    status_code=400,
                    detail="Données de résumé invalides"
                )
            
            # Génération du PDF professionnel
            pdf_bytes = pdf_generator.generate_contract_summary_pdf(
                summary_data=summary_data,
                filename=f"resume_contrat_{processing_id}.pdf"
            )
            
            # Mise en cache du PDF généré pour 7 jours
            await cache.redis.setex(
                pdf_cache_key,
                7 * 24 * 3600,  # 7 jours
                pdf_bytes
            )
            
            # Enregistrement des métriques de téléchargement
            await metrics.record_pdf_download(
                processing_id=processing_id,
                user_id=user_id or "anonymous",
                user_ip=user_ip,
                pdf_size=len(pdf_bytes)
            )
            
            from fastapi.responses import Response
            
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=resume_contrat_{processing_id}.pdf",
                    "Content-Length": str(len(pdf_bytes)),
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        
        # Logique originale pour les autres fichiers
        file_result = await contract_reader_pipeline.get_cached_file(
            file_id=file_id,
            user_id=user_id,
            user_ip=user_ip
        )
        
        if not file_result:
            raise HTTPException(
                status_code=404,
                detail="Fichier introuvable ou URL expirée"
            )
        
        file_content, filename = file_result
        
        from fastapi.responses import Response
        
        return Response(
            content=file_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_content))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur téléchargement PDF: {e}")
        raise HTTPException(status_code=500, detail="Erreur téléchargement")

@router.get("/pdf/{processing_id}")
async def download_contract_pdf(
    processing_id: str,
    request: Request,
    user_id: str = None
):
    """
    Télécharge le PDF du résumé de contrat
    Endpoint simple et direct pour téléchargement PDF
    """
    try:
        user_ip = get_client_ip(request)
        
        # Vérifier d'abord si le PDF est déjà en cache
        await cache.ensure_connected()
        pdf_cache_key = f"pdf_summary:{processing_id}"
        pdf_data = await cache.redis.get(pdf_cache_key)
        
        if pdf_data:
            # PDF trouvé en cache
            if isinstance(pdf_data, str):
                pdf_data = pdf_data.encode()
            
            # Enregistrement des métriques de téléchargement
            await metrics.record_pdf_download(
                processing_id=processing_id,
                user_id=user_id or "anonymous",
                user_ip=user_ip,
                pdf_size=len(pdf_data)
            )
            
            from fastapi.responses import Response
            
            return Response(
                content=pdf_data,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename=resume_contrat_{processing_id}.pdf",
                    "Content-Length": str(len(pdf_data)),
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        
        # Si pas de PDF en cache, récupérer le résumé et générer le PDF
        cache_key = f"contract_summary:{processing_id}"
        cached_data = await cache.redis.get(cache_key)
        
        if cached_data:
            if isinstance(cached_data, bytes):
                cached_data = cached_data.decode()
            cached_result = json.loads(cached_data)
        else:
            cached_result = None
        
        if not cached_result:
            raise HTTPException(
                status_code=404,
                detail="Résumé introuvable ou expiré"
            )
        
        # Extraction des données de résumé (sans métadonnées techniques)
        summary_data = cached_result.get('summary', {})
        
        if not summary_data:
            raise HTTPException(
                status_code=400,
                detail="Données de résumé invalides"
            )
        
        # Génération du PDF professionnel
        pdf_bytes = pdf_generator.generate_contract_summary_pdf(
            summary_data=summary_data,
            filename=f"resume_contrat_{processing_id}.pdf"
        )
        
        # Mise en cache du PDF généré pour 7 jours
        await cache.redis.setex(
            pdf_cache_key,
            7 * 24 * 3600,  # 7 jours
            pdf_bytes
        )
        
        # Enregistrement des métriques de téléchargement
        await metrics.record_pdf_download(
            processing_id=processing_id,
            user_id=user_id or "anonymous",
            user_ip=user_ip,
            pdf_size=len(pdf_bytes)
        )
        
        from fastapi.responses import Response
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=resume_contrat_{processing_id}.pdf",
                "Content-Length": str(len(pdf_bytes)),
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur génération PDF: {e}")
        raise HTTPException(status_code=500, detail="Erreur génération PDF")

@router.post("/consent")
async def record_user_consent(
    consents: Dict[str, bool],
    user_ip: str = Depends(get_client_ip)
):
    """
    Enregistre le consentement GDPR de l'utilisateur
    """
    try:
        # Génération user_id
        user_id = hashlib.sha256(user_ip.encode()).hexdigest()[:16]
        
        # Conversion vers types ConsentType
        consent_mapping = {
            'processing': ConsentType.PROCESSING,
            'download': ConsentType.DOWNLOAD,
            'analytics': ConsentType.ANALYTICS,
            'marketing': ConsentType.MARKETING
        }
        
        typed_consents = {}
        for consent_key, given in consents.items():
            if consent_key in consent_mapping:
                typed_consents[consent_mapping[consent_key]] = given
        
        # Enregistrement consentement
        result = await contract_reader_pipeline.consent_manager.record_consent(
            user_id=user_id,
            consents=typed_consents,
            user_ip=user_ip
        )
        
        if not result['success']:
            raise HTTPException(
                status_code=400,
                detail=f"Erreur consentement: {result.get('error')}"
            )
        
        return {
            "success": True,
            "consent_id": result['consent_id'],
            "expires_at": result['expires_at'],
            "granted_consents": [ct.value for ct in result['granted_consents']]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur enregistrement consentement: {e}")
        raise HTTPException(status_code=500, detail="Erreur consentement")

@router.delete("/gdpr/erase")
async def request_data_erasure(
    user_ip: str = Depends(get_client_ip)
):
    """
    Demande d'effacement GDPR (droit à l'oubli)
    """
    try:
        # Génération user_id
        user_id = hashlib.sha256(user_ip.encode()).hexdigest()[:16]
        
        # Demande effacement
        result = await contract_reader_pipeline.request_data_erasure(user_id)
        
        if not result['success']:
            if result.get('error') == 'no_data_found':
                raise HTTPException(
                    status_code=404,
                    detail="Aucune donnée trouvée pour cet utilisateur"
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur effacement: {result.get('error')}"
                )
        
        return {
            "success": True,
            "message": "Demande d'effacement enregistrée",
            "purge_details": result.get('purge_details', {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur demande effacement: {e}")
        raise HTTPException(status_code=500, detail="Erreur effacement")

@router.get("/health")
async def health_check():
    """Vérification de l'état du service"""
    try:
        # Health check complet via pipeline
        health_data = await contract_reader_pipeline.get_system_health()
        
        return SystemHealth(
            status=health_data.get('overall_status', 'error'),
            timestamp=datetime.now(),
            components=health_data.get('components', {}),
            gdpr_compliance=health_data.get('gdpr_compliance', {}),
            dod_compliance=health_data.get('dod_compliance', {})
        )
        
    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        return SystemHealth(
            status="error",
            timestamp=datetime.now(),
            components={"error": str(e)},
            gdpr_compliance={},
            dod_compliance={}
        )

@router.get("/stats")
async def get_stats():
    """Statistiques détaillées du système"""
    try:
        stats_data = await contract_reader_pipeline.get_detailed_stats()
        return stats_data
        
    except Exception as e:
        logger.error(f"Erreur stats: {e}")
        return {"error": str(e), "timestamp": time.time()}

@router.get("/budget")
async def get_budget_status(user_ip: str = Depends(get_client_ip)):
    """Statut du budget utilisateur"""
    try:
        user_id = hashlib.sha256(user_ip.encode()).hexdigest()[:16]
        budget_status = await budget_controller.get_user_budget_status(user_id)
        
        return BudgetStatus(
            user_id=user_id,
            daily_spent=budget_status.get('daily_spent', 0.0),
            daily_limit=budget_status.get('daily_limit', 1.0),
            remaining_budget=budget_status.get('remaining_budget', 1.0),
            requests_today=budget_status.get('requests_today', 0),
            last_reset=budget_status.get('last_reset')
        )
        
    except Exception as e:
        logger.error(f"Erreur budget: {e}")
        raise HTTPException(status_code=500, detail="Erreur budget")

@router.get("/health", response_model=Dict)
async def health_check():
    """
    Endpoint de health check pour monitoring de production
    """
    try:
        health_data = await health_monitor.get_system_health()
        
        # Déterminer le code de statut HTTP
        status_code = 200
        if health_data['status'] == 'warning':
            status_code = 200  # Warning mais service disponible
        elif health_data['status'] == 'critical':
            status_code = 503  # Service indisponible
        
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
        
    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        return JSONResponse(
            status_code=503,
            content={
                'status': 'critical',
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'message': 'Health check failed'
            }
        )

@router.get("/performance", response_model=Dict)
async def performance_status():
    """
    Endpoint pour les métriques de performance
    """
    try:
        config_settings = PerformanceConfig.get_performance_settings()
        is_production_ready = PerformanceConfig.is_production_ready()
        recommendations = PerformanceConfig.get_production_recommendations()
        
        return {
            'production_ready': is_production_ready,
            'configuration': config_settings,
            'recommendations': recommendations,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur performance status: {e}")
        raise HTTPException(status_code=500, detail="Erreur performance status")
