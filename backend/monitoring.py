"""
AUTOPILOT - Service de monitoring
OpenTelemetry, métriques, sessions démo
"""

import asyncio
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis.asyncio as redis
from openai import AsyncOpenAI
import httpx

from models import QualityMetrics, DemoSession
from config import settings


class MonitoringService:
    """Service de monitoring et métriques"""
    
    def __init__(self):
        self.redis_client = None
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def _get_redis(self):
        """Connexion Redis lazy"""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        return self.redis_client
    
    async def log_demo_session(
        self,
        db_session: Session,
        session_id: str,
        file_name: str,
        file_size: int,
        file_hash: str = "",
        extraction_success: bool = True,
        jira_ticket_created: bool = False,
        jira_ticket_key: Optional[str] = None,
        quality_score: Optional[float] = None,
        latency_ms: int = 0,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """Journaliser session démo"""
        try:
            # Insérer en base
            insert_query = text("""
                INSERT INTO demo_sessions (
                    session_id, file_name, file_size, file_hash,
                    extraction_success, jira_ticket_created, jira_ticket_key,
                    quality_score, latency_ms, error_message,
                    ip_address, user_agent, created_at
                ) VALUES (
                    :session_id, :file_name, :file_size, :file_hash,
                    :extraction_success, :jira_ticket_created, :jira_ticket_key,
                    :quality_score, :latency_ms, :error_message,
                    :ip_address, :user_agent, :created_at
                )
            """)
            
            db_session.execute(insert_query, {
                "session_id": session_id,
                "file_name": file_name,
                "file_size": file_size,
                "file_hash": file_hash,
                "extraction_success": extraction_success,
                "jira_ticket_created": jira_ticket_created,
                "jira_ticket_key": jira_ticket_key,
                "quality_score": quality_score,
                "latency_ms": latency_ms,
                "error_message": error_message,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "created_at": datetime.utcnow()
            })
            db_session.commit()
            
            # Métriques Redis
            redis_client = await self._get_redis()
            await redis_client.incr("autopilot:total_extractions")
            if extraction_success:
                await redis_client.incr("autopilot:successful_extractions")
            if jira_ticket_created:
                await redis_client.incr("autopilot:jira_tickets_created")
            
        except Exception as e:
            print(f"Monitoring error: {str(e)}")
            db_session.rollback()
    
    async def get_quality_metrics(self) -> QualityMetrics:
        """Métriques qualité temps réel"""
        try:
            # Métriques Redis
            redis_client = await self._get_redis()
            
            total_extractions = int(await redis_client.get("autopilot:total_extractions") or 0)
            successful_extractions = int(await redis_client.get("autopilot:successful_extractions") or 0)
            jira_tickets_created = int(await redis_client.get("autopilot:jira_tickets_created") or 0)
            
            # Calculs de base
            success_rate = successful_extractions / total_extractions if total_extractions > 0 else 0.0
            jira_success_rate = jira_tickets_created / successful_extractions if successful_extractions > 0 else 0.0
            
            # Métriques avancées (simulées pour démo)
            avg_confidence_score = 0.87  # À calculer depuis la DB en production
            avg_processing_time_ms = 6500  # À calculer depuis la DB
            cache_hit_rate = 0.42  # À calculer depuis Redis
            cost_per_extraction_eur = 0.08  # Basé sur usage OpenAI
            
            return QualityMetrics(
                total_extractions=total_extractions,
                success_rate=success_rate,
                avg_confidence_score=avg_confidence_score,
                avg_processing_time_ms=avg_processing_time_ms,
                cache_hit_rate=cache_hit_rate,
                jira_success_rate=jira_success_rate,
                last_24h_extractions=total_extractions,  # Simplification démo
                cost_per_extraction_eur=cost_per_extraction_eur
            )
            
        except Exception as e:
            print(f"Quality metrics error: {str(e)}")
            # Retour par défaut
            return QualityMetrics(
                total_extractions=0,
                success_rate=0.0,
                avg_confidence_score=0.0,
                avg_processing_time_ms=0,
                cache_hit_rate=0.0,
                jira_success_rate=0.0,
                last_24h_extractions=0,
                cost_per_extraction_eur=0.0
            )
    
    async def cleanup_demo_sessions(self, db_session: Session, keep_last: int = 10):
        """Nettoyer anciennes sessions démo"""
        try:
            cleanup_query = text("""
                DELETE FROM demo_sessions 
                WHERE id NOT IN (
                    SELECT id FROM demo_sessions 
                    ORDER BY created_at DESC 
                    LIMIT :keep_last
                )
            """)
            
            result = db_session.execute(cleanup_query, {"keep_last": keep_last})
            db_session.commit()
            
            return {"deleted_sessions": result.rowcount}
            
        except Exception as e:
            print(f"Cleanup error: {str(e)}")
            db_session.rollback()
            return {"deleted_sessions": 0}
    
    async def check_database(self) -> bool:
        """Health check base de données"""
        try:
            # Test connexion simple
            from database import engine
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.scalar() == 1
        except:
            return False
    
    async def check_redis(self) -> bool:
        """Health check Redis"""
        try:
            redis_client = await self._get_redis()
            await redis_client.ping()
            return True
        except:
            return False
    
    async def check_openai_api(self) -> bool:
        """Health check OpenAI API"""
        try:
            # Test simple avec timeout court
            response = await asyncio.wait_for(
                self.openai_client.models.list(),
                timeout=5.0
            )
            return len(response.data) > 0
        except:
            return False
    
    async def check_jira_api(self) -> bool:
        """Health check Jira API"""
        try:
            from base64 import b64encode
            
            auth_string = f"{settings.JIRA_EMAIL}:{settings.JIRA_API_TOKEN}"
            auth_bytes = auth_string.encode('ascii')
            auth_b64 = b64encode(auth_bytes).decode('ascii')
            
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{settings.JIRA_URL}/rest/api/3/myself",
                    headers=headers
                )
                return response.status_code == 200
        except:
            return False
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Métriques système"""
        import psutil
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "timestamp": datetime.utcnow().isoformat()
        }
