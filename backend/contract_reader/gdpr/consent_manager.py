"""
Gestionnaire de consentement RGPD granulaire
Consentement séparé pour traitement et téléchargement
"""

import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
import logging
from pydantic import BaseModel
from ..cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

class ConsentType(Enum):
    """Types de consentement granulaire"""
    PROCESSING = "processing"  # Traitement du document
    DOWNLOAD = "download"      # Téléchargement du résumé
    ANALYTICS = "analytics"    # Métriques anonymisées
    MARKETING = "marketing"    # Communications marketing

class ConsentStatus(Enum):
    """Statuts de consentement"""
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"

class ConsentRecord(BaseModel):
    """Enregistrement de consentement"""
    consent_id: str
    user_id: str
    ip_address: str  # Hashé
    timestamp: datetime
    expires_at: datetime
    consents: Dict[str, bool]
    status: str = "active"

class ConsentManager:
    """Gestionnaire de consentement RGPD"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        
        # Configuration RGPD
        self.consent_ttl_days = 365  # Durée validité consentement
        self.required_consents = [ConsentType.PROCESSING]  # Obligatoires
        self.optional_consents = [ConsentType.DOWNLOAD, ConsentType.ANALYTICS]
    
    async def record_consent(self, 
                           user_id: str,
                           consents: Dict[ConsentType, bool],
                           user_ip: str = None,
                           user_agent: str = None) -> Dict[str, Any]:
        """
        Enregistre le consentement utilisateur
        
        Args:
            user_id: Identifiant utilisateur (IP hashée ou session)
            consents: Dict des consentements par type
            user_ip: IP utilisateur (pour audit)
            user_agent: User agent (pour audit)
            
        Returns:
            Dict avec statut et détails du consentement
        """
        try:
            timestamp = datetime.now()
            consent_id = self._generate_consent_id(user_id, timestamp)
            
            # Validation consentements obligatoires
            missing_required = []
            for required_consent in self.required_consents:
                if not consents.get(required_consent, False):
                    missing_required.append(required_consent.value)
            
            if missing_required:
                return {
                    'success': False,
                    'error': 'missing_required_consents',
                    'missing_consents': missing_required
                }
            
            # Structure consentement
            consent_record = {
                'consent_id': consent_id,
                'user_id': user_id,
                'timestamp': timestamp.isoformat(),
                'expires_at': (timestamp + timedelta(days=self.consent_ttl_days)).isoformat(),
                'consents': {consent_type.value: given for consent_type, given in consents.items()},
                'ip_hash': hashlib.sha256(user_ip.encode()).hexdigest()[:16] if user_ip else None,
                'user_agent_hash': hashlib.sha256(user_agent.encode()).hexdigest()[:16] if user_agent else None,
                'status': ConsentStatus.GIVEN.value
            }
            
            # Stockage Redis avec TTL
            await self.redis_client.redis.setex(
                f"consent:{user_id}",
                self.consent_ttl_days * 24 * 3600,
                json.dumps(consent_record)
            )
            
            # Index par consent_id pour audit
            await self.redis_client.redis.setex(
                f"consent_audit:{consent_id}",
                self.consent_ttl_days * 24 * 3600,
                json.dumps(consent_record)
            )
            
            # Log audit
            await self._log_consent_event(
                user_id=user_id,
                action="consent_given",
                consents=consents,
                ip_hash=consent_record['ip_hash']
            )
            
            logger.info(f"Consentement enregistré: {consent_id}")
            
            return {
                'success': True,
                'consent_id': consent_id,
                'expires_at': consent_record['expires_at'],
                'granted_consents': [k for k, v in consents.items() if v]
            }
            
        except Exception as e:
            logger.error(f"Erreur enregistrement consentement: {e}")
            return {
                'success': False,
                'error': 'internal_error'
            }
    
    async def check_consent(self, 
                          user_id: str, 
                          required_consent: ConsentType) -> Dict[str, Any]:
        """
        Vérifie le consentement pour une action spécifique
        
        Args:
            user_id: Identifiant utilisateur
            required_consent: Type de consentement requis
            
        Returns:
            Dict avec statut de vérification
        """
        try:
            # Vérification connexion Redis
            if not self.redis_client or not hasattr(self.redis_client, 'redis') or not self.redis_client.redis:
                # Redis non disponible - consentement requis
                return {
                    'valid': False,
                    'reason': 'redis_unavailable',
                    'consent_id': 'test_consent_123',
                    'granted_at': datetime.now().isoformat(),
                    'expires_at': (datetime.now() + timedelta(days=365)).isoformat()
                }
            
            # Récupération consentement
            consent_data = await self.redis_client.redis.get(f"consent:{user_id}")
            
            if not consent_data:
                return {
                    'valid': False,
                    'reason': 'no_consent_found',
                    'required_consent': required_consent.value
                }
            
            consent_record = json.loads(consent_data.decode())
            
            # Vérification expiration
            expires_at = datetime.fromisoformat(consent_record['expires_at'])
            if datetime.now() > expires_at:
                # Marquage comme expiré
                consent_record['status'] = ConsentStatus.EXPIRED.value
                await self.redis_client.redis.setex(
                    f"consent:{user_id}",
                    86400,  # Garde 24h pour audit
                    json.dumps(consent_record)
                )
                
                return {
                    'valid': False,
                    'reason': 'consent_expired',
                    'expired_at': consent_record['expires_at']
                }
            
            # Vérification consentement spécifique
            consents = consent_record.get('consents', {})
            consent_given = consents.get(required_consent.value, False)
            
            if not consent_given:
                return {
                    'valid': False,
                    'reason': 'consent_not_granted',
                    'required_consent': required_consent.value
                }
            
            # Vérification statut
            if consent_record.get('status') == ConsentStatus.WITHDRAWN.value:
                return {
                    'valid': False,
                    'reason': 'consent_withdrawn'
                }
            
            return {
                'valid': True,
                'consent_id': consent_record['consent_id'],
                'granted_at': consent_record['timestamp'],
                'expires_at': consent_record['expires_at']
            }
            
        except Exception as e:
            logger.error(f"Erreur vérification consentement: {e}")
            return {
                'valid': False,
                'reason': 'verification_error'
            }
    
    async def withdraw_consent(self, 
                             user_id: str,
                             consent_types: List[ConsentType] = None) -> Dict[str, Any]:
        """
        Retire le consentement (partiellement ou totalement)
        
        Args:
            user_id: Identifiant utilisateur
            consent_types: Types spécifiques à retirer (None = tous)
            
        Returns:
            Dict avec résultat du retrait
        """
        try:
            # Récupération consentement actuel
            consent_data = await self.redis_client.redis.get(f"consent:{user_id}")
            
            if not consent_data:
                return {
                    'success': False,
                    'error': 'no_consent_found'
                }
            
            consent_record = json.loads(consent_data.decode())
            
            # Retrait spécifique ou total
            if consent_types is None:
                # Retrait total
                consent_record['status'] = ConsentStatus.WITHDRAWN.value
                consent_record['withdrawn_at'] = datetime.now().isoformat()
                consent_record['consents'] = {k: False for k in consent_record['consents']}
                withdrawn_types = list(consent_record['consents'].keys())
            else:
                # Retrait partiel
                withdrawn_types = []
                for consent_type in consent_types:
                    if consent_type.value in consent_record['consents']:
                        consent_record['consents'][consent_type.value] = False
                        withdrawn_types.append(consent_type.value)
                
                # Si tous les consentements obligatoires sont retirés
                required_still_given = any(
                    consent_record['consents'].get(req.value, False) 
                    for req in self.required_consents
                )
                
                if not required_still_given:
                    consent_record['status'] = ConsentStatus.WITHDRAWN.value
                    consent_record['withdrawn_at'] = datetime.now().isoformat()
            
            # Mise à jour Redis
            await self.redis_client.redis.setex(
                f"consent:{user_id}",
                86400 * 7,  # Garde 7 jours pour audit
                json.dumps(consent_record)
            )
            
            # Log audit
            await self._log_consent_event(
                user_id=user_id,
                action="consent_withdrawn",
                consents={ct: False for ct in withdrawn_types},
                ip_hash=consent_record.get('ip_hash')
            )
            
            logger.info(f"Consentement retiré: {user_id}, types: {withdrawn_types}")
            
            return {
                'success': True,
                'withdrawn_types': withdrawn_types,
                'withdrawn_at': consent_record.get('withdrawn_at'),
                'status': consent_record['status']
            }
            
        except Exception as e:
            logger.error(f"Erreur retrait consentement: {e}")
            return {
                'success': False,
                'error': 'withdrawal_error'
            }
    
    async def record_consent(self, user_id: str, ip_address: str, consent_data: Dict[str, bool]) -> ConsentRecord:
        """Enregistrement de consentement"""
        try:
            # Ensure Redis connection
            await self.redis_client.ensure_connected()
            
            # Create consent record
            consent_record = ConsentRecord(
                consent_id=self._generate_consent_id(user_id, datetime.now()),
                user_id=user_id,
                ip_address=hashlib.sha256(ip_address.encode()).hexdigest()[:16],
                timestamp=datetime.now(),
                expires_at=datetime.now() + timedelta(days=365),
                consents=consent_data
            )
            
            # Store in Redis
            consent_key = f"consent:{user_id}"
            # Convert to dict with JSON-serializable dates
            consent_dict = consent_record.dict()
            consent_dict['timestamp'] = consent_record.timestamp.isoformat()
            consent_dict['expires_at'] = consent_record.expires_at.isoformat()
            
            await self.redis_client.redis.setex(
                consent_key,
                365 * 24 * 60 * 60,  # 1 year
                json.dumps(consent_dict)
            )
            
            return consent_record
            
        except Exception as e:
            logger.error(f"Erreur enregistrement consentement: {e}")
            raise Exception(f"consent_error: {e}")
    
    def _generate_consent_id(self, user_id: str, timestamp: datetime) -> str:
        """Génère un ID unique pour le consentement"""
        data = f"{user_id}:{timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def _log_consent_event(self, 
                                user_id: str,
                                action: str,
                                consents: Dict,
                                ip_hash: str = None):
        """Log d'audit pour événements de consentement"""
        try:
            audit_entry = {
                'timestamp': datetime.now().isoformat(),
                'user_id': user_id,
                'action': action,
                'consents': consents,
                'ip_hash': ip_hash
            }
            
            # Log d'audit (liste limitée)
            await self.redis_client.redis.lpush(
                "contract_reader:consent_audit",
                json.dumps(audit_entry)
            )
            
            # Limite à 50000 entrées
            await self.redis_client.redis.ltrim(
                "contract_reader:consent_audit",
                0, 49999
            )
            
        except Exception as e:
            logger.warning(f"Erreur log audit consentement: {e}")
    
    async def get_consent_stats(self) -> Dict[str, Any]:
        """Statistiques de consentement"""
        try:
            # Comptage consentements actifs
            consent_keys = await self.redis_client.redis.keys("consent:*")
            active_consents = len([k for k in consent_keys if not k.decode().startswith("consent_audit:")])
            
            # Analyse des logs d'audit récents
            audit_logs = await self.redis_client.redis.lrange(
                "contract_reader:consent_audit", 0, 999
            )
            
            consent_given_count = 0
            consent_withdrawn_count = 0
            
            for log_entry in audit_logs:
                try:
                    entry = json.loads(log_entry.decode())
                    if entry['action'] == 'consent_given':
                        consent_given_count += 1
                    elif entry['action'] == 'consent_withdrawn':
                        consent_withdrawn_count += 1
                except:
                    continue
            
            return {
                'active_consents': active_consents,
                'recent_consents_given': consent_given_count,
                'recent_consents_withdrawn': consent_withdrawn_count,
                'consent_ttl_days': self.consent_ttl_days,
                'required_consent_types': [ct.value for ct in self.required_consents],
                'optional_consent_types': [ct.value for ct in self.optional_consents]
            }
            
        except Exception as e:
            logger.error(f"Erreur stats consentement: {e}")
            return {
                'active_consents': 0,
                'recent_consents_given': 0,
                'recent_consents_withdrawn': 0,
                'consent_ttl_days': self.consent_ttl_days
            }
