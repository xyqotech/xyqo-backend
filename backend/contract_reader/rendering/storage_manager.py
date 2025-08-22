"""
Gestionnaire de stockage sécurisé pour PDFs
URLs signées temporaires + nettoyage automatique
"""

import os
import tempfile
import hashlib
import secrets
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import logging
import asyncio

from ..cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

class StorageManager:
    """Gestionnaire de stockage sécurisé avec URLs signées"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.storage_dir = Path(tempfile.gettempdir()) / "contract_reader_secure"
        self.storage_dir.mkdir(exist_ok=True, mode=0o700)  # Permissions restreintes
        
        # Configuration sécurité
        self.max_file_age_hours = 24
        self.max_downloads_per_file = 5
        self.signed_url_ttl = 3600  # 1h
        
        # Clé secrète pour signatures (en production: variable d'environnement)
        self.signing_key = os.getenv('PDF_SIGNING_KEY', secrets.token_hex(32))
    
    async def store_pdf_securely(self, 
                                pdf_bytes: bytes, 
                                filename: str,
                                user_ip: str = None) -> str:
        """
        Stocke un PDF de manière sécurisée avec URL signée
        
        Args:
            pdf_bytes: Contenu PDF
            filename: Nom du fichier
            user_ip: IP utilisateur pour audit
            
        Returns:
            str: Token d'accès sécurisé
        """
        try:
            # Génération identifiants sécurisés
            file_id = secrets.token_urlsafe(32)
            access_token = secrets.token_urlsafe(48)
            
            # Stockage fichier avec nom sécurisé
            secure_filename = f"{file_id}.pdf"
            file_path = self.storage_dir / secure_filename
            
            # Écriture sécurisée
            with open(file_path, 'wb') as f:
                f.write(pdf_bytes)
            
            # Permissions restrictives
            os.chmod(file_path, 0o600)
            
            # Métadonnées en Redis
            metadata = {
                'file_id': file_id,
                'original_filename': filename,
                'file_path': str(file_path),
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=self.max_file_age_hours)).isoformat(),
                'file_size': len(pdf_bytes),
                'downloads_count': 0,
                'max_downloads': self.max_downloads_per_file,
                'user_ip': user_ip,
                'access_token': access_token
            }
            
            # Stockage métadonnées (TTL 25h pour marge)
            await self.redis_client.redis.setex(
                f"secure_pdf:{file_id}",
                self.max_file_age_hours * 3600 + 3600,
                str(metadata)
            )
            
            # Index par token d'accès
            await self.redis_client.redis.setex(
                f"pdf_token:{access_token}",
                self.signed_url_ttl,
                file_id
            )
            
            logger.info(f"PDF stocké de manière sécurisée: {file_id}")
            return access_token
            
        except Exception as e:
            logger.error(f"Erreur stockage sécurisé PDF: {e}")
            raise
    
    async def get_signed_download_url(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Génère une URL signée temporaire pour téléchargement
        
        Args:
            access_token: Token d'accès
            
        Returns:
            Dict avec URL signée et métadonnées
        """
        try:
            # Vérification token
            file_id = await self.redis_client.redis.get(f"pdf_token:{access_token}")
            if not file_id:
                logger.warning(f"Token d'accès invalide ou expiré: {access_token[:12]}...")
                return None
            
            file_id = file_id.decode()
            
            # Récupération métadonnées
            metadata_raw = await self.redis_client.redis.get(f"secure_pdf:{file_id}")
            if not metadata_raw:
                logger.warning(f"Métadonnées PDF introuvables: {file_id}")
                return None
            
            metadata = eval(metadata_raw.decode())
            
            # Vérifications sécurité
            if not self._is_file_accessible(metadata):
                return None
            
            # Génération signature temporaire
            timestamp = int(datetime.now().timestamp())
            signature = self._generate_signature(file_id, timestamp)
            
            # URL signée
            signed_url = f"/api/contract-reader/download/{file_id}?t={timestamp}&s={signature}"
            
            return {
                'download_url': signed_url,
                'filename': metadata['original_filename'],
                'expires_in': self.signed_url_ttl,
                'file_size': metadata['file_size'],
                'downloads_remaining': metadata['max_downloads'] - metadata['downloads_count']
            }
            
        except Exception as e:
            logger.error(f"Erreur génération URL signée: {e}")
            return None
    
    async def serve_secure_file(self, 
                              file_id: str, 
                              timestamp: int, 
                              signature: str,
                              user_ip: str = None) -> Optional[Tuple[bytes, str]]:
        """
        Sert un fichier avec vérification de signature
        
        Args:
            file_id: ID du fichier
            timestamp: Timestamp de la signature
            signature: Signature à vérifier
            user_ip: IP utilisateur pour audit
            
        Returns:
            Tuple[bytes, str]: (contenu_fichier, nom_fichier) ou None
        """
        try:
            # Vérification signature
            if not self._verify_signature(file_id, timestamp, signature):
                logger.warning(f"Signature invalide pour fichier: {file_id}")
                return None
            
            # Vérification expiration signature
            if datetime.now().timestamp() - timestamp > self.signed_url_ttl:
                logger.warning(f"URL expirée pour fichier: {file_id}")
                return None
            
            # Récupération métadonnées
            metadata_raw = await self.redis_client.redis.get(f"secure_pdf:{file_id}")
            if not metadata_raw:
                logger.warning(f"Fichier introuvable: {file_id}")
                return None
            
            metadata = eval(metadata_raw.decode())
            
            # Vérifications sécurité
            if not self._is_file_accessible(metadata):
                return None
            
            # Vérification limite téléchargements
            if metadata['downloads_count'] >= metadata['max_downloads']:
                logger.warning(f"Limite téléchargements atteinte: {file_id}")
                return None
            
            # Lecture fichier
            file_path = Path(metadata['file_path'])
            if not file_path.exists():
                logger.error(f"Fichier physique introuvable: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Incrémentation compteur téléchargements
            metadata['downloads_count'] += 1
            metadata['last_download'] = datetime.now().isoformat()
            metadata['last_download_ip'] = user_ip
            
            # Mise à jour métadonnées
            await self.redis_client.redis.setex(
                f"secure_pdf:{file_id}",
                self.max_file_age_hours * 3600,
                str(metadata)
            )
            
            # Audit log
            await self._log_download(file_id, user_ip, metadata['original_filename'])
            
            logger.info(f"Fichier servi: {file_id}, téléchargement {metadata['downloads_count']}")
            return file_content, metadata['original_filename']
            
        except Exception as e:
            logger.error(f"Erreur service fichier sécurisé: {e}")
            return None
    
    def _is_file_accessible(self, metadata: Dict[str, Any]) -> bool:
        """Vérifie si un fichier est accessible"""
        try:
            # Vérification expiration
            expires_at = datetime.fromisoformat(metadata['expires_at'])
            if datetime.now() > expires_at:
                logger.warning(f"Fichier expiré: {metadata['file_id']}")
                return False
            
            # Vérification existence physique
            file_path = Path(metadata['file_path'])
            if not file_path.exists():
                logger.warning(f"Fichier physique manquant: {file_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur vérification accessibilité: {e}")
            return False
    
    def _generate_signature(self, file_id: str, timestamp: int) -> str:
        """Génère une signature HMAC pour URL"""
        message = f"{file_id}:{timestamp}"
        signature = hashlib.hmac.new(
            self.signing_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature[:16]  # Troncature pour URLs plus courtes
    
    def _verify_signature(self, file_id: str, timestamp: int, signature: str) -> bool:
        """Vérifie une signature HMAC"""
        expected_signature = self._generate_signature(file_id, timestamp)
        return secrets.compare_digest(signature, expected_signature)
    
    async def _log_download(self, file_id: str, user_ip: str, filename: str):
        """Log d'audit pour téléchargements"""
        try:
            audit_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'download',
                'file_id': file_id,
                'filename': filename,
                'user_ip': user_ip
            }
            
            # Log d'audit (liste limitée)
            await self.redis_client.redis.lpush(
                "contract_reader:download_audit",
                str(audit_entry)
            )
            
            # Limite à 10000 entrées
            await self.redis_client.redis.ltrim(
                "contract_reader:download_audit",
                0, 9999
            )
            
        except Exception as e:
            logger.warning(f"Erreur log audit: {e}")
    
    async def cleanup_expired_files(self):
        """Nettoyage automatique des fichiers expirés"""
        try:
            cleaned_count = 0
            
            # Scan des fichiers stockés
            for file_path in self.storage_dir.glob("*.pdf"):
                try:
                    # Extraction file_id du nom
                    file_id = file_path.stem
                    
                    # Vérification métadonnées
                    metadata_raw = await self.redis_client.redis.get(f"secure_pdf:{file_id}")
                    
                    if not metadata_raw:
                        # Métadonnées manquantes = fichier orphelin
                        file_path.unlink()
                        cleaned_count += 1
                        continue
                    
                    metadata = eval(metadata_raw.decode())
                    
                    # Vérification expiration
                    expires_at = datetime.fromisoformat(metadata['expires_at'])
                    if datetime.now() > expires_at:
                        # Suppression fichier et métadonnées
                        file_path.unlink()
                        await self.redis_client.redis.delete(f"secure_pdf:{file_id}")
                        cleaned_count += 1
                        
                except Exception as e:
                    logger.warning(f"Erreur nettoyage fichier {file_path}: {e}")
                    continue
            
            if cleaned_count > 0:
                logger.info(f"Nettoyage terminé: {cleaned_count} fichiers supprimés")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage automatique: {e}")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Statistiques de stockage"""
        try:
            # Comptage fichiers actifs
            active_files = 0
            total_size = 0
            
            for file_path in self.storage_dir.glob("*.pdf"):
                if file_path.exists():
                    active_files += 1
                    total_size += file_path.stat().st_size
            
            # Statistiques Redis
            pdf_keys = await self.redis_client.redis.keys("secure_pdf:*")
            active_metadata = len(pdf_keys)
            
            return {
                'active_files': active_files,
                'active_metadata': active_metadata,
                'total_storage_mb': round(total_size / (1024 * 1024), 2),
                'storage_directory': str(self.storage_dir),
                'max_file_age_hours': self.max_file_age_hours
            }
            
        except Exception as e:
            logger.error(f"Erreur stats stockage: {e}")
            return {
                'active_files': 0,
                'active_metadata': 0,
                'total_storage_mb': 0.0,
                'storage_directory': str(self.storage_dir),
                'max_file_age_hours': self.max_file_age_hours
            }
