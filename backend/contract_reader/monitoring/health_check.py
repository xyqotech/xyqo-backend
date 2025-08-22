"""
Système de monitoring et health check pour la production
Surveillance des performances et de la santé du système
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from ..cache.redis_client import RedisClient
from ..config.performance_config import PerformanceConfig

logger = logging.getLogger(__name__)

class HealthCheckMonitor:
    """Moniteur de santé du système Contract Reader"""
    
    def __init__(self):
        self.redis_client = RedisClient()
        self.performance_config = PerformanceConfig()
        self.start_time = datetime.now()
        
    async def get_system_health(self) -> Dict[str, Any]:
        """Retourne l'état de santé complet du système"""
        try:
            health_data = {
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
                'components': await self._check_all_components(),
                'performance_metrics': await self._get_performance_metrics(),
                'configuration': self._get_config_status()
            }
            
            # Déterminer le statut global
            component_statuses = [comp['status'] for comp in health_data['components'].values()]
            if 'critical' in component_statuses:
                health_data['status'] = 'critical'
            elif 'warning' in component_statuses:
                health_data['status'] = 'warning'
            
            return health_data
            
        except Exception as e:
            logger.error(f"Erreur lors du health check: {e}")
            return {
                'status': 'critical',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    async def _check_all_components(self) -> Dict[str, Dict[str, Any]]:
        """Vérifie tous les composants du système"""
        components = {}
        
        # Redis
        components['redis'] = await self._check_redis()
        
        # OpenAI API
        components['openai'] = await self._check_openai()
        
        # Système de fichiers
        components['filesystem'] = await self._check_filesystem()
        
        # Mémoire et CPU
        components['system_resources'] = await self._check_system_resources()
        
        return components
    
    async def _check_redis(self) -> Dict[str, Any]:
        """Vérifie la connexion Redis"""
        try:
            await self.redis_client.ensure_connected()
            
            # Test de ping
            start_time = time.time()
            await self.redis_client.redis.ping()
            response_time = (time.time() - start_time) * 1000
            
            # Test d'écriture/lecture
            test_key = "health_check_test"
            test_value = str(datetime.now().timestamp())
            await self.redis_client.redis.set(test_key, test_value, ex=10)
            retrieved_value = await self.redis_client.redis.get(test_key)
            
            if retrieved_value.decode() != test_value:
                raise Exception("Test d'écriture/lecture Redis échoué")
            
            await self.redis_client.redis.delete(test_key)
            
            status = 'healthy'
            if response_time > 100:
                status = 'warning'
            if response_time > 500:
                status = 'critical'
            
            return {
                'status': status,
                'response_time_ms': round(response_time, 2),
                'connected': True,
                'message': f"Redis opérationnel (réponse: {response_time:.1f}ms)"
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'connected': False,
                'error': str(e),
                'message': "Redis inaccessible"
            }
    
    async def _check_openai(self) -> Dict[str, Any]:
        """Vérifie la disponibilité de l'API OpenAI"""
        try:
            import openai
            import os
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return {
                    'status': 'critical',
                    'configured': False,
                    'message': "Clé API OpenAI manquante"
                }
            
            # Test simple avec un prompt minimal
            start_time = time.time()
            client = openai.OpenAI(api_key=api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5,
                timeout=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            status = 'healthy'
            if response_time > 5000:
                status = 'warning'
            if response_time > 10000:
                status = 'critical'
            
            return {
                'status': status,
                'configured': True,
                'response_time_ms': round(response_time, 2),
                'model': response.model,
                'message': f"OpenAI opérationnel (réponse: {response_time:.1f}ms)"
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'configured': True,
                'error': str(e),
                'message': "API OpenAI inaccessible"
            }
    
    async def _check_filesystem(self) -> Dict[str, Any]:
        """Vérifie l'espace disque et les permissions"""
        try:
            import shutil
            import tempfile
            import os
            
            # Vérifier l'espace disque
            total, used, free = shutil.disk_usage("/")
            free_gb = free // (1024**3)
            free_percent = (free / total) * 100
            
            # Test d'écriture dans le répertoire temporaire
            temp_dir = tempfile.gettempdir()
            test_file = os.path.join(temp_dir, f"health_check_{datetime.now().timestamp()}")
            
            with open(test_file, 'w') as f:
                f.write("test")
            
            os.remove(test_file)
            
            status = 'healthy'
            if free_percent < 20:
                status = 'warning'
            if free_percent < 10:
                status = 'critical'
            
            return {
                'status': status,
                'free_space_gb': free_gb,
                'free_space_percent': round(free_percent, 1),
                'writable': True,
                'message': f"Espace disque: {free_gb}GB libres ({free_percent:.1f}%)"
            }
            
        except Exception as e:
            return {
                'status': 'critical',
                'error': str(e),
                'message': "Problème système de fichiers"
            }
    
    async def _check_system_resources(self) -> Dict[str, Any]:
        """Vérifie les ressources système (mémoire, CPU)"""
        try:
            import psutil
            
            # Mémoire
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.1)  # Réduire l'intervalle
            
            # Processus Python actuel
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / 1024 / 1024
            
            status = 'healthy'
            if memory_percent > 80 or cpu_percent > 80:
                status = 'warning'
            if memory_percent > 90 or cpu_percent > 90:
                status = 'critical'
            
            return {
                'status': status,
                'memory_percent': round(memory_percent, 1),
                'cpu_percent': round(cpu_percent, 1),
                'process_memory_mb': round(process_memory_mb, 1),
                'message': f"Mémoire: {memory_percent:.1f}%, CPU: {cpu_percent:.1f}%"
            }
            
        except ImportError:
            # Fallback sans psutil
            import os
            
            return {
                'status': 'healthy',
                'memory_percent': 0,
                'cpu_percent': 0,
                'process_memory_mb': 0,
                'message': "Monitoring système basique (psutil non disponible)",
                'fallback': True
            }
        except Exception as e:
            return {
                'status': 'warning',
                'error': str(e),
                'message': "Erreur monitoring ressources système"
            }
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques de performance depuis Redis"""
        try:
            await self.redis_client.ensure_connected()
            
            # Métriques des dernières 24h
            metrics_key = "metrics:performance:24h"
            metrics_data = await self.redis_client.redis.hgetall(metrics_key)
            
            if not metrics_data:
                return {
                    'total_requests': 0,
                    'avg_processing_time_ms': 0,
                    'success_rate_percent': 100,
                    'cache_hit_rate_percent': 0
                }
            
            # Conversion des données Redis
            total_requests = int(metrics_data.get(b'total_requests', 0))
            total_processing_time = float(metrics_data.get(b'total_processing_time', 0))
            successful_requests = int(metrics_data.get(b'successful_requests', 0))
            cache_hits = int(metrics_data.get(b'cache_hits', 0))
            
            avg_processing_time = (total_processing_time / total_requests * 1000) if total_requests > 0 else 0
            success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 100
            cache_hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'total_requests': total_requests,
                'avg_processing_time_ms': round(avg_processing_time, 2),
                'success_rate_percent': round(success_rate, 2),
                'cache_hit_rate_percent': round(cache_hit_rate, 2)
            }
            
        except Exception as e:
            logger.warning(f"Erreur récupération métriques: {e}")
            return {
                'total_requests': 0,
                'avg_processing_time_ms': 0,
                'success_rate_percent': 100,
                'cache_hit_rate_percent': 0,
                'error': str(e)
            }
    
    def _get_config_status(self) -> Dict[str, Any]:
        """Vérifie la configuration pour la production"""
        config_settings = self.performance_config.get_performance_settings()
        is_production_ready = self.performance_config.is_production_ready()
        recommendations = self.performance_config.get_production_recommendations()
        
        return {
            'production_ready': is_production_ready,
            'recommendations': recommendations,
            'current_settings': config_settings
        }
    
    async def log_performance_metrics(self, processing_time: float, success: bool, from_cache: bool):
        """Enregistre les métriques de performance"""
        try:
            await self.redis_client.ensure_connected()
            
            metrics_key = "metrics:performance:24h"
            
            # Incrémenter les compteurs
            pipe = self.redis_client.redis.pipeline()
            pipe.hincrby(metrics_key, "total_requests", 1)
            pipe.hincrbyfloat(metrics_key, "total_processing_time", processing_time)
            
            if success:
                pipe.hincrby(metrics_key, "successful_requests", 1)
            
            if from_cache:
                pipe.hincrby(metrics_key, "cache_hits", 1)
            
            # TTL de 24h
            pipe.expire(metrics_key, 86400)
            
            await pipe.execute()
            
        except Exception as e:
            logger.warning(f"Erreur enregistrement métriques: {e}")

# Instance globale
health_monitor = HealthCheckMonitor()
