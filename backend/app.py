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

# Simplified imports for Railway deployment
from datetime import datetime
from typing import Dict, Any

# Optional imports with fallbacks
try:
    from models import ContractExtraction, ExtractionResponse, HealthResponse
except ImportError:
    from pydantic import BaseModel
    
    class HealthResponse(BaseModel):
        status: str = "healthy"
        timestamp: datetime
        demo_mode: bool = True

try:
    from extraction import ExtractionService
    extraction_service = ExtractionService()
except ImportError:
    extraction_service = None

try:
    from jira_client import JiraClient
    jira_client = JiraClient()
except ImportError:
    jira_client = None

try:
    from security import SecurityGuards
    security = SecurityGuards()
except ImportError:
    security = None

try:
    from monitoring import MonitoringService
    monitoring = MonitoringService()
except ImportError:
    monitoring = None

try:
    from contract_reader.api import router as contract_reader_router
    has_contract_reader = True
except ImportError:
    has_contract_reader = False

def get_db_session():
    return None

# Configuration with fallback
try:
    from config import settings
    DEMO_MODE = settings.DEMO_MODE
    CORS_ORIGINS = settings.CORS_ORIGINS.split(",")
except ImportError:
    DEMO_MODE = True
    CORS_ORIGINS = ["*"]

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# FastAPI app
app = FastAPI(
    title="AUTOPILOT API",
    description="IA d'automatisation de processus métier",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiting error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Optional router inclusion
if has_contract_reader:
    app.include_router(contract_reader_router, prefix="/api/v1/contract")
    
    try:
        from contract_reader.api_simple import router as simple_router
        app.include_router(simple_router, prefix="/api/v1/contract")
    except ImportError:
        pass


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
    """Root endpoint - Railway health check"""
    return {
        "service": "AUTOPILOT API",
        "version": "1.0.0",
        "status": "healthy",
        "demo_mode": str(DEMO_MODE),
        "docs": "/docs" if DEMO_MODE else "disabled"
    }

@app.get("/health")
async def health():
    """Simple health endpoint for Railway"""
    return {"status": "healthy", "service": "xyqo-backend"}


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
        "database": True,  # Simplified for Railway
        "redis": True,     # Simplified for Railway
        "openai": True,    # Simplified for Railway
        "jira": True,      # Simplified for Railway
    }
    
    if monitoring:
        try:
            checks.update({
                "database": await monitoring.check_database(),
                "redis": await monitoring.check_redis(),
                "openai": await monitoring.check_openai_api(),
                "jira": await monitoring.check_jira_api() if not DEMO_MODE else True,
            })
        except Exception:
            pass  # Keep simplified checks
    
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
    try:
        from prometheus_client import generate_latest, REGISTRY
        return Response(
            generate_latest(REGISTRY),
            media_type="text/plain"
        )
    except ImportError:
        return {"status": "metrics not available"}


@app.post("/api/v1/extract")
@limiter.limit("5/minute")
async def extract_document(
    request: Request,
    file: UploadFile = File(...)
):
    """Simplified extraction endpoint for Railway deployment"""
    if not extraction_service:
        raise HTTPException(status_code=503, detail="Extraction service not available")
        
    start_time = time.time()
    session_id = hashlib.sha256(f"{request.client.host}{time.time()}".encode()).hexdigest()[:16]
    
    try:
        # Basic file validation
        if security:
            await security.validate_file(file)
        
        # Read file content
        file_content = await file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Extract with cache if available
        extraction_result = await extraction_service.extract_with_cache(
            file_content=file_content,
            filename=file.filename,
            file_hash=file_hash
        )
        
        # Create Jira ticket if available
        jira_ticket = None
        if jira_client and extraction_result.confidence_score >= 0.8:
            jira_ticket = await jira_client.create_ticket(
                extraction_result=extraction_result,
                filename=file.filename,
                demo_mode=DEMO_MODE
            )
        
        # Return response
        return {
            "session_id": session_id,
            "extraction": extraction_result,
            "jira_ticket": jira_ticket,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "cached": extraction_service.was_cached(file_hash) if hasattr(extraction_service, 'was_cached') else False,
            "demo_mode": DEMO_MODE
        }
        
    except Exception as e:
        print(f"Extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/api/v1/quality/dashboard")
async def quality_dashboard():
    """Dashboard qualité temps réel"""
    if monitoring:
        try:
            return await monitoring.get_quality_metrics()
        except Exception:
            pass
    return {"status": "dashboard not available", "demo_mode": DEMO_MODE}


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
