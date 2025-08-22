"""
AUTOPILOT - Backend API FastAPI
Point d'entrée principal avec endpoints sécurisés
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import time
import hashlib
from datetime import datetime
from typing import Dict, Any

from models import ContractExtraction, ExtractionResponse, HealthResponse
from extraction import ExtractionService
from jira_client import JiraClient
from security import SecurityGuards
from monitoring import MonitoringService
from contract_reader.api import router as contract_reader_router
try:
    from database import get_db_session
except ImportError:
    # Fallback si pas de DB
    def get_db_session():
        return None

# Configuration
from config import settings
DEMO_MODE = settings.DEMO_MODE
CORS_ORIGINS = settings.CORS_ORIGINS.split(",")

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# FastAPI app
app = FastAPI(
    title="AUTOPILOT API",
    description="IA d'automatisation de processus métier",
    version="1.0.0",
    docs_url="/docs" if DEMO_MODE else None,
    redoc_url="/redoc" if DEMO_MODE else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permettre toutes les origines en mode démo
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiting error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Services
extraction_service = ExtractionService()
jira_client = JiraClient()
monitoring = MonitoringService()
security = SecurityGuards()

# Inclusion du router Contract Reader
app.include_router(contract_reader_router, prefix="/api/v1/contract")

# Inclusion du router Contract Reader Simple pour test
from contract_reader.api_simple import router as simple_router
app.include_router(simple_router, prefix="/api/v1/contract")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Ajouter les headers de sécurité"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-API-Version"] = "1.0.0"
    return response


@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "service": "AUTOPILOT API",
        "version": "1.0.0",
        "status": "operational",
        "demo_mode": str(DEMO_MODE),
        "docs": "/docs" if DEMO_MODE else "disabled"
    }


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Health check basique"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        demo_mode=DEMO_MODE
    )


@app.get("/api/v1/ready")
async def readiness_check():
    """Readiness check avec dépendances"""
    checks = {
        "database": await monitoring.check_database(),
        "redis": await monitoring.check_redis(),
        "openai": await monitoring.check_openai_api(),
        "jira": await monitoring.check_jira_api() if not DEMO_MODE else True,
    }
    
    all_ready = all(checks.values())
    status_code = 200 if all_ready else 503
    
    return JSONResponse(
        content={
            "ready": all_ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        },
        status_code=status_code
    )


@app.get("/api/v1/metrics")
async def prometheus_metrics():
    """Métriques Prometheus"""
    from prometheus_client import generate_latest, REGISTRY
    return Response(
        generate_latest(REGISTRY),
        media_type="text/plain"
    )


@app.post("/api/v1/extract", response_model=ExtractionResponse)
@limiter.limit("5/minute")
async def extract_document(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Extraction de document avec IA
    - Validation sécurité
    - Cache intelligent
    - Création ticket Jira
    - Journalisation complète
    """
    start_time = time.time()
    session_id = hashlib.sha256(f"{request.client.host}{time.time()}".encode()).hexdigest()[:16]
    
    try:
        # 1. Validation sécurité du fichier
        await security.validate_file(file)
        
        # 2. Lecture et hash du contenu
        file_content = await file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # 3. Extraction avec cache
        extraction_result = await extraction_service.extract_with_cache(
            file_content=file_content,
            filename=file.filename,
            file_hash=file_hash
        )
        
        # 4. Création ticket Jira
        jira_ticket = None
        if extraction_result.confidence_score >= 0.8:  # Seuil de confiance
            jira_ticket = await jira_client.create_ticket(
                extraction_result=extraction_result,
                filename=file.filename,
                demo_mode=DEMO_MODE
            )
        
        # 5. Journalisation session (optionnelle si DB disponible)
        try:
            db_session = get_db_session()
            if db_session:
                await monitoring.log_demo_session(
                    db_session=next(db_session),
                    session_id=session_id,
                    file_name=file.filename,
                    file_size=len(file_content),
                    file_hash=file_hash,
                    extraction_success=True,
                    jira_ticket_created=jira_ticket is not None,
                    jira_ticket_key=jira_ticket.key if jira_ticket else None,
                    quality_score=extraction_result.confidence_score,
                    latency_ms=int((time.time() - start_time) * 1000)
                )
        except Exception as e:
            print(f"Warning: Could not log session to database: {str(e)}")
        
        # 6. Réponse
        return ExtractionResponse(
            session_id=session_id,
            extraction=extraction_result,
            jira_ticket=jira_ticket,
            processing_time_ms=int((time.time() - start_time) * 1000),
            cached=extraction_service.was_cached(file_hash),
            demo_mode=DEMO_MODE
        )
        
    except Exception as e:
        print(f"Extraction error: {str(e)}")
        
        # Gestion d'erreur appropriée
        if "File too large" in str(e):
            raise HTTPException(status_code=413, detail=str(e))
        elif "Unsupported file type" in str(e):
            raise HTTPException(status_code=415, detail=str(e))
        elif "malware" in str(e).lower():
            raise HTTPException(status_code=400, detail="File security check failed")
        else:
            raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/api/v1/quality/dashboard")
async def quality_dashboard():
    """Dashboard qualité temps réel"""
    return await monitoring.get_quality_metrics()


@app.post("/api/v1/demo/reset")
async def reset_demo():
    """Reset environnement démo (idempotent)"""
    if not DEMO_MODE:
        raise HTTPException(status_code=403, detail="Reset only available in demo mode")
    
    try:
        # Vider cache avec gestionnaire intelligent
        from cache_manager import CacheManager
        cache_manager = CacheManager()
        deleted_count = await cache_manager.clear_all_cache()
        
        return JSONResponse({
            "status": "success",
            "message": f"Demo environment reset completed - {deleted_count} cache entries cleared",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Reset failed: {str(e)}"}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True if DEMO_MODE else False,
        log_level="info"
    )
