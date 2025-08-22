"""
Minimal FastAPI app for Railway deployment
Only essential endpoints for health checks
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

# Environment variables with defaults
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
PORT = int(os.getenv("PORT", 8000))

# FastAPI app
app = FastAPI(
    title="XYQO Backend API",
    description="Minimal API for Railway deployment",
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

@app.get("/")
async def root():
    """Root endpoint - Railway health check"""
    return {
        "service": "XYQO Backend API",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "demo_mode": DEMO_MODE,
        "docs": "/docs"
    }

@app.get("/health")
async def health():
    """Simple health endpoint for Railway"""
    return {
        "status": "healthy",
        "service": "xyqo-backend",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "demo_mode": DEMO_MODE,
        "version": "1.0.0"
    }

@app.get("/api/v1/ready")
async def readiness_check():
    """Readiness check"""
    return {
        "ready": True,
        "checks": {
            "api": "healthy",
            "demo_mode": DEMO_MODE
        },
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "minimal_app:app",
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
