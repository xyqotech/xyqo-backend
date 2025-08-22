"""
AUTOPILOT - Guardrails de sécurité
Validation fichiers, antivirus, PII redaction
"""

import os
import magic
import hashlib
import re
from typing import List, Dict, Any
from fastapi import UploadFile, HTTPException
import clamd

from config import settings


class SecurityGuards:
    """Guardrails de sécurité complets"""
    
    def __init__(self):
        self.max_size = settings.max_file_size_bytes
        self.allowed_extensions = settings.allowed_extensions_list
        self.clamav_client = None
        
        # Patterns PII pour redaction
        self.pii_patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone_fr': re.compile(r'(?:\+33|0)[1-9](?:[0-9]{8})'),
            'phone_intl': re.compile(r'\+\d{1,3}[\s.-]?\d{1,14}'),
            'iban': re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}[A-Z0-9]{1,16}\b'),
            'siret': re.compile(r'\b\d{14}\b'),
            'siren': re.compile(r'\b\d{9}\b')
        }
    
    async def validate_file(self, file: UploadFile) -> None:
        """Validation complète du fichier"""
        
        # 1. Validation taille
        file_content = await file.read()
        await file.seek(0)  # Reset pour lecture ultérieure
        
        if len(file_content) > self.max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.MAX_FILE_SIZE_MB}MB"
            )
        
        # 2. Validation extension
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename required")
        
        file_ext = '.' + file.filename.lower().split('.')[-1]
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type. Allowed: {', '.join(self.allowed_extensions)}"
            )
        
        # 3. Validation MIME type
        mime_type = magic.from_buffer(file_content, mime=True)
        allowed_mimes = {
            '.pdf': 'application/pdf',
            '.txt': 'text/plain',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        
        expected_mime = allowed_mimes.get(file_ext)
        if expected_mime and mime_type != expected_mime:
            # Tolérance pour text/plain
            if not (file_ext == '.txt' and mime_type.startswith('text/')):
                raise HTTPException(
                    status_code=415,
                    detail=f"MIME type mismatch. Expected: {expected_mime}, got: {mime_type}"
                )
        
        # 4. Scan antivirus (si disponible)
        if settings.ENVIRONMENT == "production":
            await self._scan_malware(file_content, file.filename)
        
        # 5. Validation contenu basique
        self._validate_content_safety(file_content)
    
    async def _scan_malware(self, file_content: bytes, filename: str) -> None:
        """Scan antivirus avec ClamAV"""
        try:
            if not self.clamav_client:
                self.clamav_client = clamd.ClamdNetworkSocket(
                    host=settings.CLAMAV_HOST,
                    port=settings.CLAMAV_PORT
                )
            
            # Test connexion
            if not self.clamav_client.ping():
                print("Warning: ClamAV not available, skipping malware scan")
                return
            
            # Scan du contenu
            scan_result = self.clamav_client.instream(file_content)
            
            if scan_result['stream'][0] == 'FOUND':
                raise HTTPException(
                    status_code=400,
                    detail=f"Malware detected: {scan_result['stream'][1]}"
                )
                
        except Exception as e:
            if "malware" in str(e).lower():
                raise  # Re-raise malware errors
            print(f"ClamAV scan error: {str(e)}")
            # Continue sans scan en dev/demo
    
    def _validate_content_safety(self, file_content: bytes) -> None:
        """Validation sécurité du contenu"""
        try:
            text_content = file_content.decode('utf-8', errors='ignore')
            
            # Vérifier contenu suspect
            suspicious_patterns = [
                r'<script[^>]*>',  # JavaScript
                r'javascript:',    # JavaScript URLs
                r'data:.*base64',  # Data URLs base64
                r'\\x[0-9a-fA-F]{2}',  # Hex encoding
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, text_content, re.IGNORECASE):
                    raise HTTPException(
                        status_code=400,
                        detail="Suspicious content detected in file"
                    )
            
            # Vérifier taille raisonnable après décodage
            if len(text_content) > 500000:  # 500KB de texte
                raise HTTPException(
                    status_code=413,
                    detail="Text content too large after processing"
                )
                
        except UnicodeDecodeError:
            # Fichiers binaires OK (PDF, DOCX)
            pass
    
    def redact_pii(self, text: str) -> str:
        """Redaction PII pour logs"""
        redacted = text
        
        for pii_type, pattern in self.pii_patterns.items():
            if pii_type == 'email':
                redacted = pattern.sub('[EMAIL_REDACTED]', redacted)
            elif pii_type.startswith('phone'):
                redacted = pattern.sub('[PHONE_REDACTED]', redacted)
            elif pii_type == 'iban':
                redacted = pattern.sub('[IBAN_REDACTED]', redacted)
            elif pii_type in ['siret', 'siren']:
                redacted = pattern.sub('[ID_REDACTED]', redacted)
        
        return redacted
    
    def generate_file_hash(self, file_content: bytes) -> str:
        """Hash sécurisé du fichier"""
        return hashlib.sha256(file_content).hexdigest()
    
    def validate_session_id(self, session_id: str) -> bool:
        """Validation session ID"""
        if not session_id or len(session_id) != 16:
            return False
        return all(c in '0123456789abcdef' for c in session_id.lower())
    
    async def check_rate_limit(self, ip_address: str) -> bool:
        """Vérification rate limiting (implémentation basique)"""
        # TODO: Implémenter avec Redis pour production
        return True
    
    def get_security_headers(self) -> Dict[str, str]:
        """Headers de sécurité recommandés"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", 
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
