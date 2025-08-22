"""
Configuration des performances pour la production
Optimisations pour le déploiement en production
"""

import os
from typing import Dict, Any

class PerformanceConfig:
    """Configuration des performances pour la production"""
    
    # Limites de traitement
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '10'))
    MAX_PAGES_PER_CONTRACT = int(os.getenv('MAX_PAGES_PER_CONTRACT', '50'))
    MAX_TEXT_LENGTH = int(os.getenv('MAX_TEXT_LENGTH', '100000'))
    
    # Timeouts
    EXTRACTION_TIMEOUT_SECONDS = int(os.getenv('EXTRACTION_TIMEOUT_SECONDS', '30'))
    AI_PROCESSING_TIMEOUT_SECONDS = int(os.getenv('AI_PROCESSING_TIMEOUT_SECONDS', '60'))
    VALIDATION_TIMEOUT_SECONDS = int(os.getenv('VALIDATION_TIMEOUT_SECONDS', '15'))
    PDF_GENERATION_TIMEOUT_SECONDS = int(os.getenv('PDF_GENERATION_TIMEOUT_SECONDS', '30'))
    
    # Cache Redis
    REDIS_TTL_SUMMARY = int(os.getenv('REDIS_TTL_SUMMARY', '604800'))  # 7 jours
    REDIS_TTL_PDF = int(os.getenv('REDIS_TTL_PDF', '604800'))  # 7 jours
    REDIS_TTL_METRICS = int(os.getenv('REDIS_TTL_METRICS', '86400'))  # 1 jour
    
    # Optimisations IA
    OPENAI_MAX_TOKENS = int(os.getenv('OPENAI_MAX_TOKENS', '4000'))
    OPENAI_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.1'))
    OPENAI_REQUEST_TIMEOUT = int(os.getenv('OPENAI_REQUEST_TIMEOUT', '60'))
    
    # Limites de débit
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '10'))
    RATE_LIMIT_PER_HOUR = int(os.getenv('RATE_LIMIT_PER_HOUR', '100'))
    RATE_LIMIT_PER_DAY = int(os.getenv('RATE_LIMIT_PER_DAY', '1000'))
    
    # Monitoring
    METRICS_ENABLED = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'
    PERFORMANCE_LOGGING = os.getenv('PERFORMANCE_LOGGING', 'true').lower() == 'true'
    
    # Optimisations PDF
    PDF_COMPRESSION_LEVEL = int(os.getenv('PDF_COMPRESSION_LEVEL', '6'))
    PDF_IMAGE_QUALITY = int(os.getenv('PDF_IMAGE_QUALITY', '85'))
    
    @classmethod
    def get_performance_settings(cls) -> Dict[str, Any]:
        """Retourne toutes les configurations de performance"""
        return {
            'file_limits': {
                'max_file_size_mb': cls.MAX_FILE_SIZE_MB,
                'max_pages_per_contract': cls.MAX_PAGES_PER_CONTRACT,
                'max_text_length': cls.MAX_TEXT_LENGTH
            },
            'timeouts': {
                'extraction_seconds': cls.EXTRACTION_TIMEOUT_SECONDS,
                'ai_processing_seconds': cls.AI_PROCESSING_TIMEOUT_SECONDS,
                'validation_seconds': cls.VALIDATION_TIMEOUT_SECONDS,
                'pdf_generation_seconds': cls.PDF_GENERATION_TIMEOUT_SECONDS
            },
            'cache': {
                'summary_ttl': cls.REDIS_TTL_SUMMARY,
                'pdf_ttl': cls.REDIS_TTL_PDF,
                'metrics_ttl': cls.REDIS_TTL_METRICS
            },
            'ai_optimization': {
                'max_tokens': cls.OPENAI_MAX_TOKENS,
                'temperature': cls.OPENAI_TEMPERATURE,
                'request_timeout': cls.OPENAI_REQUEST_TIMEOUT
            },
            'rate_limits': {
                'per_minute': cls.RATE_LIMIT_PER_MINUTE,
                'per_hour': cls.RATE_LIMIT_PER_HOUR,
                'per_day': cls.RATE_LIMIT_PER_DAY
            },
            'monitoring': {
                'metrics_enabled': cls.METRICS_ENABLED,
                'performance_logging': cls.PERFORMANCE_LOGGING
            },
            'pdf_optimization': {
                'compression_level': cls.PDF_COMPRESSION_LEVEL,
                'image_quality': cls.PDF_IMAGE_QUALITY
            }
        }
    
    @classmethod
    def is_production_ready(cls) -> bool:
        """Vérifie si la configuration est prête pour la production"""
        checks = [
            cls.MAX_FILE_SIZE_MB <= 50,  # Limite raisonnable
            cls.EXTRACTION_TIMEOUT_SECONDS <= 60,  # Timeout raisonnable
            cls.AI_PROCESSING_TIMEOUT_SECONDS <= 120,  # Timeout raisonnable
            cls.REDIS_TTL_SUMMARY > 0,  # Cache activé
            cls.RATE_LIMIT_PER_MINUTE > 0,  # Rate limiting activé
        ]
        return all(checks)
    
    @classmethod
    def get_production_recommendations(cls) -> Dict[str, str]:
        """Retourne des recommandations pour la production"""
        recommendations = {}
        
        if cls.MAX_FILE_SIZE_MB > 50:
            recommendations['file_size'] = "Réduire MAX_FILE_SIZE_MB à 50MB maximum"
        
        if cls.EXTRACTION_TIMEOUT_SECONDS > 60:
            recommendations['extraction_timeout'] = "Réduire EXTRACTION_TIMEOUT_SECONDS à 60s maximum"
        
        if cls.AI_PROCESSING_TIMEOUT_SECONDS > 120:
            recommendations['ai_timeout'] = "Réduire AI_PROCESSING_TIMEOUT_SECONDS à 120s maximum"
        
        if not cls.METRICS_ENABLED:
            recommendations['metrics'] = "Activer METRICS_ENABLED pour le monitoring"
        
        if cls.RATE_LIMIT_PER_MINUTE == 0:
            recommendations['rate_limit'] = "Configurer RATE_LIMIT_PER_MINUTE pour éviter les abus"
        
        return recommendations
