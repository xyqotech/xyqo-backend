"""
Client Redis pour Contract Reader avec fallback mock
Cache intelligent avec déduplication SHA256 et TTL
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    # Fallback pour environnements sans Redis
    REDIS_AVAILABLE = False
    
    class MockRedis:
        def __init__(self, *args, **kwargs):
            self._data = {}
            
        async def get(self, key): 
            return self._data.get(key)
            
        async def set(self, key, value, ex=None): 
            self._data[key] = value
            return True
            
        async def setex(self, key, ttl, value):
            self._data[key] = value
            return True
            
        async def close(self):
            pass
            
        async def delete(self, *keys): 
            for key in keys:
                self._data.pop(key, None)
            return len(keys)
            
        async def exists(self, key): 
            return key in self._data
            
        async def ping(self): 
            return True
            
        async def keys(self, pattern): 
            return list(self._data.keys())
            
        async def lrange(self, key, start, end): 
            return []
            
        async def lpush(self, key, *values): 
            return len(values)
            
        async def ltrim(self, key, start, end): 
            return True
            
        async def incr(self, key): 
            current = self._data.get(key, 0)
            if isinstance(current, bytes):
                current = int(current.decode())
            self._data[key] = str(current + 1).encode()
            return current + 1
    
    Redis = MockRedis

logger = logging.getLogger(__name__)

class RedisClient:
    """Client Redis avec cache intelligent et fallback mock"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis = None
        self._connected = False
        
    async def connect(self):
        """Connexion au Redis avec fallback"""
        try:
            if REDIS_AVAILABLE:
                self.redis = Redis.from_url(self.redis_url, decode_responses=False)
                await self.redis.ping()
                self._connected = True
                logger.info("Redis connecté avec succès")
            else:
                self.redis = MockRedis()
                self._connected = True
                logger.warning("Redis non disponible - utilisation du mock")
        except Exception as e:
            logger.warning(f"Connexion Redis échouée: {e} - utilisation du mock")
            self.redis = MockRedis()
            self._connected = True
    
    async def ensure_connected(self):
        """S'assure que la connexion est établie"""
        if not self._connected:
            await self.connect()
    
    async def setex(self, key: str, ttl: int, value: str):
        """Définit une clé avec TTL"""
        await self.ensure_connected()
        return await self.redis.setex(key, ttl, value)
    
    async def get_cached_summary(self, document_hash: str) -> Optional[Dict[str, Any]]:
        """
        Récupère un résumé du cache par hash SHA256
        
        Args:
            document_hash: Hash SHA256 du document
            
        Returns:
            Dict du résumé ou None si pas trouvé
        """
        await self.ensure_connected()
        
        try:
            cache_key = f"contract_summary:{document_hash}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode()
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur récupération cache: {e}")
            return None
    
    async def cache_summary(self, document_hash: str, summary_data: Dict[str, Any], ttl: int = 86400):
        """
        Met en cache un résumé avec TTL
        
        Args:
            document_hash: Hash SHA256 du document
            summary_data: Données du résumé
            ttl: Time to live en secondes (défaut: 24h)
        """
        await self.ensure_connected()
        
        try:
            cache_key = f"contract_summary:{document_hash}"
            
            # Ajout métadonnées cache
            cache_entry = {
                "summary": summary_data,
                "cached_at": datetime.now().isoformat(),
                "document_hash": document_hash,
                "ttl": ttl
            }
            
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(cache_entry)
            )
            
            logger.info(f"Résumé mis en cache: {document_hash[:12]}... (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"Erreur mise en cache: {e}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        await self.ensure_connected()
        
        try:
            # Comptage des clés par type
            summary_keys = await self.redis.keys("contract_summary:*")
            budget_keys = await self.redis.keys("budget:*")
            quota_keys = await self.redis.keys("quota:*")
            
            return {
                "total_summaries": len(summary_keys),
                "total_budget_entries": len(budget_keys),
                "total_quota_entries": len(quota_keys),
                "redis_connected": self._connected,
                "redis_available": REDIS_AVAILABLE
            }
            
        except Exception as e:
            logger.error(f"Erreur stats cache: {e}")
            return {
                "total_summaries": 0,
                "total_budget_entries": 0,
                "total_quota_entries": 0,
                "redis_connected": False,
                "redis_available": REDIS_AVAILABLE,
                "error": str(e)
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Vérification santé Redis"""
        await self.ensure_connected()
        
        try:
            await self.redis.ping()
            
            return {
                "status": "healthy",
                "redis_available": REDIS_AVAILABLE,
                "connected": self._connected,
                "url": self.redis_url if REDIS_AVAILABLE else "mock"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "redis_available": REDIS_AVAILABLE,
                "connected": False,
                "error": str(e)
            }
    
    async def cleanup_expired(self):
        """Nettoyage des entrées expirées (pour le mock)"""
        if not REDIS_AVAILABLE and hasattr(self.redis, '_data'):
            # Le vrai Redis gère automatiquement les TTL
            # Ici on simule pour le mock
            logger.info("Nettoyage mock Redis simulé")
    
    async def clear_cache(self, pattern: str = "contract_summary:*") -> int:
        """Vide le cache selon un pattern"""
        await self.ensure_connected()
        
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Cache vidé: {deleted} entrées supprimées")
                return deleted
            return 0
            
        except Exception as e:
            logger.error(f"Erreur vidage cache: {e}")
            return 0
