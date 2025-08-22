"""
AUTOPILOT - Gestionnaire de Cache Intelligent
Évite la mise en cache d'erreurs et gère la qualité des résultats
"""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from models import ContractExtraction
from config import settings


class CacheManager:
    """Gestionnaire de cache intelligent pour éviter les erreurs persistantes"""
    
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.min_confidence_for_cache = 0.5
        self.cache_ttl_days = 7
        
    async def _get_redis(self):
        """Connexion Redis async"""
        return redis.from_url(self.redis_url, decode_responses=True)
    
    async def get_cached_extraction(self, file_hash: str) -> Optional[ContractExtraction]:
        """Récupérer extraction en cache avec validation qualité"""
        redis_client = await self._get_redis()
        cache_key = f"extraction:{file_hash}"
        
        try:
            cached_result = await redis_client.get(cache_key)
            if not cached_result:
                return None
                
            # Parser le résultat
            cached_extraction = ContractExtraction.parse_raw(cached_result)
            
            # Vérifier la qualité
            if cached_extraction.confidence_score >= self.min_confidence_for_cache:
                return cached_extraction
            else:
                # Supprimer cache de mauvaise qualité
                await redis_client.delete(cache_key)
                print(f"Cache de faible qualité supprimé (confidence: {cached_extraction.confidence_score})")
                return None
                
        except Exception as e:
            # Supprimer cache corrompu
            await redis_client.delete(cache_key)
            print(f"Cache corrompu supprimé: {str(e)}")
            return None
    
    async def cache_extraction(self, file_hash: str, extraction: ContractExtraction) -> bool:
        """Mettre en cache seulement si qualité suffisante"""
        
        # Ne cacher que les extractions de bonne qualité
        if extraction.confidence_score < self.min_confidence_for_cache:
            print(f"Extraction non mise en cache (confidence: {extraction.confidence_score} < {self.min_confidence_for_cache})")
            return False
        
        # Ne pas cacher les erreurs
        if "llm_error" in extraction.key_terms or "validation_error" in extraction.key_terms:
            print("Extraction d'erreur non mise en cache")
            return False
        
        try:
            redis_client = await self._get_redis()
            cache_key = f"extraction:{file_hash}"
            
            await redis_client.setex(
                cache_key,
                int(timedelta(days=self.cache_ttl_days).total_seconds()),
                extraction.json()
            )
            
            print(f"Extraction mise en cache avec succès (confidence: {extraction.confidence_score})")
            return True
            
        except Exception as e:
            print(f"Erreur mise en cache: {str(e)}")
            return False
    
    async def invalidate_cache(self, file_hash: str) -> bool:
        """Invalider le cache pour un fichier spécifique"""
        try:
            redis_client = await self._get_redis()
            cache_key = f"extraction:{file_hash}"
            result = await redis_client.delete(cache_key)
            return result > 0
        except Exception as e:
            print(f"Erreur invalidation cache: {str(e)}")
            return False
    
    async def clear_all_cache(self) -> int:
        """Vider tout le cache d'extraction"""
        try:
            redis_client = await self._get_redis()
            keys = await redis_client.keys("extraction:*")
            if keys:
                deleted = await redis_client.delete(*keys)
                print(f"{deleted} entrées de cache supprimées")
                return deleted
            return 0
        except Exception as e:
            print(f"Erreur vidage cache: {str(e)}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        try:
            redis_client = await self._get_redis()
            keys = await redis_client.keys("extraction:*")
            
            # Analyser la qualité des entrées en cache
            high_quality = 0
            low_quality = 0
            
            for key in keys[:50]:  # Limiter l'analyse
                try:
                    cached_data = await redis_client.get(key)
                    if cached_data:
                        extraction = ContractExtraction.parse_raw(cached_data)
                        if extraction.confidence_score >= self.min_confidence_for_cache:
                            high_quality += 1
                        else:
                            low_quality += 1
                except:
                    low_quality += 1
            
            return {
                "total_entries": len(keys),
                "high_quality": high_quality,
                "low_quality": low_quality,
                "min_confidence_threshold": self.min_confidence_for_cache,
                "cache_ttl_days": self.cache_ttl_days
            }
            
        except Exception as e:
            return {"error": str(e)}
