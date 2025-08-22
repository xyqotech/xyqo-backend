"""
Gestionnaire de purge automatique des données RGPD
Suppression sécurisée et audit trail immutable
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import logging

from ..cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

class DataPurgeManager:
    """Gestionnaire de purge RGPD avec audit immutable"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        
        # Configuration purge
        self.auto_purge_after_hours = 24  # Purge auto après 24h
        self.audit_retention_days = 2555  # 7 ans pour audit (RGPD)
        self.batch_size = 100  # Traitement par lots
    
    async def schedule_data_purge(self, 
                                user_id: str,
                                data_types: List[str] = None,
                                delay_hours: int = 0) -> Dict[str, Any]:
        """
        Programme une purge de données utilisateur
        
        Args:
            user_id: Identifiant utilisateur
            data_types: Types de données à purger (None = tout)
            delay_hours: Délai avant purge (0 = immédiat)
            
        Returns:
            Dict avec détails de la programmation
        """
        try:
            purge_id = self._generate_purge_id(user_id)
            scheduled_at = datetime.now() + timedelta(hours=delay_hours)
            
            # Types de données par défaut
            if data_types is None:
                data_types = [
                    'contract_summaries',
                    'pdf_files',
                    'cache_entries',
                    'processing_logs',
                    'consent_records'
                ]
            
            # Enregistrement demande de purge
            purge_request = {
                'purge_id': purge_id,
                'user_id': user_id,
                'data_types': data_types,
                'requested_at': datetime.now().isoformat(),
                'scheduled_at': scheduled_at.isoformat(),
                'status': 'scheduled',
                'delay_hours': delay_hours
            }
            
            # Stockage avec TTL approprié
            ttl_seconds = (delay_hours + 48) * 3600  # +48h marge
            await self.redis_client.redis.setex(
                f"purge_request:{purge_id}",
                ttl_seconds,
                json.dumps(purge_request)
            )
            
            # Index par user_id
            await self.redis_client.redis.setex(
                f"user_purge:{user_id}",
                ttl_seconds,
                purge_id
            )
            
            # Audit immutable
            await self._log_purge_event(
                user_id=user_id,
                action="purge_scheduled",
                details={
                    'purge_id': purge_id,
                    'data_types': data_types,
                    'scheduled_at': scheduled_at.isoformat()
                }
            )
            
            logger.info(f"Purge programmée: {purge_id} pour {user_id}")
            
            return {
                'success': True,
                'purge_id': purge_id,
                'scheduled_at': scheduled_at.isoformat(),
                'data_types': data_types,
                'estimated_completion': (scheduled_at + timedelta(minutes=30)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur programmation purge: {e}")
            return {
                'success': False,
                'error': 'scheduling_error'
            }
    
    async def execute_immediate_purge(self, user_id: str) -> Dict[str, Any]:
        """
        Exécute une purge immédiate (droit à l'effacement RGPD)
        
        Args:
            user_id: Identifiant utilisateur
            
        Returns:
            Dict avec résultats de la purge
        """
        try:
            purge_id = self._generate_purge_id(user_id)
            start_time = datetime.now()
            
            # Résultats de purge
            purge_results = {
                'purge_id': purge_id,
                'user_id': user_id,
                'started_at': start_time.isoformat(),
                'data_types_processed': [],
                'items_deleted': {},
                'errors': []
            }
            
            # 1. Purge des résumés de contrats
            try:
                deleted_summaries = await self._purge_contract_summaries(user_id)
                purge_results['items_deleted']['contract_summaries'] = deleted_summaries
                purge_results['data_types_processed'].append('contract_summaries')
            except Exception as e:
                purge_results['errors'].append(f"contract_summaries: {str(e)}")
            
            # 2. Purge des fichiers PDF
            try:
                deleted_pdfs = await self._purge_pdf_files(user_id)
                purge_results['items_deleted']['pdf_files'] = deleted_pdfs
                purge_results['data_types_processed'].append('pdf_files')
            except Exception as e:
                purge_results['errors'].append(f"pdf_files: {str(e)}")
            
            # 3. Purge du cache
            try:
                deleted_cache = await self._purge_cache_entries(user_id)
                purge_results['items_deleted']['cache_entries'] = deleted_cache
                purge_results['data_types_processed'].append('cache_entries')
            except Exception as e:
                purge_results['errors'].append(f"cache_entries: {str(e)}")
            
            # 4. Purge des logs de traitement
            try:
                deleted_logs = await self._purge_processing_logs(user_id)
                purge_results['items_deleted']['processing_logs'] = deleted_logs
                purge_results['data_types_processed'].append('processing_logs')
            except Exception as e:
                purge_results['errors'].append(f"processing_logs: {str(e)}")
            
            # 5. Purge des consentements (en dernier)
            try:
                deleted_consents = await self._purge_consent_records(user_id)
                purge_results['items_deleted']['consent_records'] = deleted_consents
                purge_results['data_types_processed'].append('consent_records')
            except Exception as e:
                purge_results['errors'].append(f"consent_records: {str(e)}")
            
            # Finalisation
            end_time = datetime.now()
            purge_results['completed_at'] = end_time.isoformat()
            purge_results['duration_seconds'] = (end_time - start_time).total_seconds()
            purge_results['status'] = 'completed' if not purge_results['errors'] else 'completed_with_errors'
            
            # Audit immutable
            await self._log_purge_event(
                user_id=user_id,
                action="purge_executed",
                details=purge_results
            )
            
            logger.info(f"Purge exécutée: {purge_id}, durée: {purge_results['duration_seconds']:.2f}s")
            
            return {
                'success': True,
                'purge_results': purge_results
            }
            
        except Exception as e:
            logger.error(f"Erreur exécution purge: {e}")
            return {
                'success': False,
                'error': 'execution_error',
                'details': str(e)
            }
    
    async def _purge_contract_summaries(self, user_id: str) -> int:
        """Purge des résumés de contrats"""
        deleted_count = 0
        
        # Recherche par patterns Redis
        summary_keys = await self.redis_client.redis.keys(f"contract_summary:*:{user_id}")
        
        if summary_keys:
            # Suppression par lots
            for i in range(0, len(summary_keys), self.batch_size):
                batch = summary_keys[i:i + self.batch_size]
                deleted = await self.redis_client.redis.delete(*batch)
                deleted_count += deleted
        
        return deleted_count
    
    async def _purge_pdf_files(self, user_id: str) -> int:
        """Purge des fichiers PDF stockés"""
        deleted_count = 0
        
        # Recherche fichiers PDF par user_id
        pdf_keys = await self.redis_client.redis.keys(f"secure_pdf:*")
        
        for key in pdf_keys:
            try:
                metadata_raw = await self.redis_client.redis.get(key)
                if metadata_raw:
                    metadata = json.loads(metadata_raw.decode())
                    
                    # Vérification user_id dans métadonnées ou IP
                    if (metadata.get('user_id') == user_id or 
                        self._user_matches_ip_hash(user_id, metadata.get('user_ip'))):
                        
                        # Suppression fichier physique
                        file_path = Path(metadata.get('file_path', ''))
                        if file_path.exists():
                            file_path.unlink()
                        
                        # Suppression métadonnées
                        await self.redis_client.redis.delete(key)
                        deleted_count += 1
                        
            except Exception as e:
                logger.warning(f"Erreur purge PDF {key}: {e}")
                continue
        
        return deleted_count
    
    async def _purge_cache_entries(self, user_id: str) -> int:
        """Purge des entrées de cache"""
        deleted_count = 0
        
        # Patterns de cache liés à l'utilisateur
        cache_patterns = [
            f"*:{user_id}",
            f"*:{user_id}:*",
            f"user_cache:{user_id}:*"
        ]
        
        for pattern in cache_patterns:
            cache_keys = await self.redis_client.redis.keys(pattern)
            if cache_keys:
                deleted = await self.redis_client.redis.delete(*cache_keys)
                deleted_count += deleted
        
        return deleted_count
    
    async def _purge_processing_logs(self, user_id: str) -> int:
        """Purge des logs de traitement"""
        deleted_count = 0
        
        # Logs dans listes Redis
        log_lists = [
            "contract_reader:processing_logs",
            "contract_reader:pdf_metrics",
            "contract_reader:download_audit"
        ]
        
        for list_key in log_lists:
            try:
                # Récupération et filtrage
                logs = await self.redis_client.redis.lrange(list_key, 0, -1)
                filtered_logs = []
                
                for log_entry in logs:
                    try:
                        log_data = json.loads(log_entry.decode())
                        
                        # Vérification si log concerne l'utilisateur
                        if not self._log_concerns_user(log_data, user_id):
                            filtered_logs.append(log_entry)
                        else:
                            deleted_count += 1
                            
                    except:
                        # Garde les logs non parsables
                        filtered_logs.append(log_entry)
                
                # Remplacement de la liste
                if len(filtered_logs) != len(logs):
                    await self.redis_client.redis.delete(list_key)
                    if filtered_logs:
                        await self.redis_client.redis.lpush(list_key, *filtered_logs)
                        
            except Exception as e:
                logger.warning(f"Erreur purge logs {list_key}: {e}")
                continue
        
        return deleted_count
    
    async def _purge_consent_records(self, user_id: str) -> int:
        """Purge des enregistrements de consentement"""
        deleted_count = 0
        
        # Consentement principal
        consent_key = f"consent:{user_id}"
        if await self.redis_client.redis.exists(consent_key):
            await self.redis_client.redis.delete(consent_key)
            deleted_count += 1
        
        # Recherche consentements d'audit
        audit_keys = await self.redis_client.redis.keys(f"consent_audit:*")
        
        for key in audit_keys:
            try:
                consent_data = await self.redis_client.redis.get(key)
                if consent_data:
                    consent_record = json.loads(consent_data.decode())
                    if consent_record.get('user_id') == user_id:
                        await self.redis_client.redis.delete(key)
                        deleted_count += 1
            except:
                continue
        
        return deleted_count
    
    def _user_matches_ip_hash(self, user_id: str, user_ip: str) -> bool:
        """Vérifie si user_id correspond à un hash d'IP"""
        if not user_ip:
            return False
        
        # Si user_id est un hash d'IP
        if len(user_id) == 16 and all(c in '0123456789abcdef' for c in user_id.lower()):
            ip_hash = hashlib.sha256(user_ip.encode()).hexdigest()[:16]
            return user_id.lower() == ip_hash.lower()
        
        return False
    
    def _log_concerns_user(self, log_data: Dict[str, Any], user_id: str) -> bool:
        """Vérifie si un log concerne un utilisateur"""
        # Champs à vérifier
        user_fields = ['user_id', 'user_ip', 'ip_hash']
        
        for field in user_fields:
            if field in log_data:
                value = log_data[field]
                if value == user_id or self._user_matches_ip_hash(user_id, value):
                    return True
        
        return False
    
    def _generate_purge_id(self, user_id: str) -> str:
        """Génère un ID unique pour la purge"""
        data = f"{user_id}:{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def _log_purge_event(self, 
                              user_id: str,
                              action: str,
                              details: Dict[str, Any]):
        """Log d'audit immutable pour purges"""
        try:
            audit_entry = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'action': action,
                'details': details,
                'audit_hash': self._generate_audit_hash(user_id, action, details)
            }
            
            # Log immutable (S3 Object Lock en production)
            await self.redis_client.redis.lpush(
                "contract_reader:purge_audit_immutable",
                json.dumps(audit_entry)
            )
            
            # Pas de limite sur les logs d'audit (immutables)
            
        except Exception as e:
            logger.error(f"Erreur log audit purge: {e}")
    
    def _generate_audit_hash(self, user_id: str, action: str, details: Dict[str, Any]) -> str:
        """Génère un hash pour vérification intégrité audit"""
        data = f"{user_id}:{action}:{json.dumps(details, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    async def get_purge_status(self, user_id: str) -> Dict[str, Any]:
        """Statut des purges pour un utilisateur"""
        try:
            # Recherche demande de purge active
            purge_id = await self.redis_client.redis.get(f"user_purge:{user_id}")
            
            if not purge_id:
                return {
                    'has_pending_purge': False,
                    'can_request_purge': True
                }
            
            purge_id = purge_id.decode()
            
            # Détails de la demande
            purge_data = await self.redis_client.redis.get(f"purge_request:{purge_id}")
            
            if not purge_data:
                return {
                    'has_pending_purge': False,
                    'can_request_purge': True
                }
            
            purge_request = json.loads(purge_data.decode())
            
            return {
                'has_pending_purge': True,
                'purge_id': purge_id,
                'scheduled_at': purge_request['scheduled_at'],
                'status': purge_request['status'],
                'data_types': purge_request['data_types'],
                'can_request_purge': False
            }
            
        except Exception as e:
            logger.error(f"Erreur statut purge: {e}")
            return {
                'has_pending_purge': False,
                'can_request_purge': True,
                'error': 'status_error'
            }
    
    async def run_scheduled_purges(self):
        """Exécute les purges programmées (tâche cron)"""
        try:
            # Recherche demandes de purge
            purge_keys = await self.redis_client.redis.keys("purge_request:*")
            
            for key in purge_keys:
                try:
                    purge_data = await self.redis_client.redis.get(key)
                    if not purge_data:
                        continue
                    
                    purge_request = json.loads(purge_data.decode())
                    
                    # Vérification si c'est le moment
                    scheduled_at = datetime.fromisoformat(purge_request['scheduled_at'])
                    
                    if datetime.now() >= scheduled_at and purge_request['status'] == 'scheduled':
                        # Exécution purge
                        user_id = purge_request['user_id']
                        result = await self.execute_immediate_purge(user_id)
                        
                        # Mise à jour statut
                        purge_request['status'] = 'executed'
                        purge_request['executed_at'] = datetime.now().isoformat()
                        purge_request['result'] = result
                        
                        await self.redis_client.redis.setex(
                            key,
                            86400 * 7,  # Garde 7 jours pour audit
                            json.dumps(purge_request)
                        )
                        
                        logger.info(f"Purge programmée exécutée: {purge_request['purge_id']}")
                        
                except Exception as e:
                    logger.error(f"Erreur exécution purge programmée {key}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Erreur tâche purges programmées: {e}")
    
    async def get_purge_stats(self) -> Dict[str, Any]:
        """Statistiques de purge"""
        try:
            # Comptage demandes actives
            purge_keys = await self.redis_client.redis.keys("purge_request:*")
            active_requests = len(purge_keys)
            
            # Analyse logs d'audit
            audit_logs = await self.redis_client.redis.lrange(
                "contract_reader:purge_audit_immutable", 0, 999
            )
            
            scheduled_count = 0
            executed_count = 0
            
            for log_entry in audit_logs:
                try:
                    entry = json.loads(log_entry.decode())
                    if entry['action'] == 'purge_scheduled':
                        scheduled_count += 1
                    elif entry['action'] == 'purge_executed':
                        executed_count += 1
                except:
                    continue
            
            return {
                'active_purge_requests': active_requests,
                'total_purges_scheduled': scheduled_count,
                'total_purges_executed': executed_count,
                'auto_purge_after_hours': self.auto_purge_after_hours,
                'audit_retention_days': self.audit_retention_days
            }
            
        except Exception as e:
            logger.error(f"Erreur stats purge: {e}")
            return {
                'active_purge_requests': 0,
                'total_purges_scheduled': 0,
                'total_purges_executed': 0,
                'auto_purge_after_hours': self.auto_purge_after_hours,
                'audit_retention_days': self.audit_retention_days
            }
