"""
AUTOPILOT - Configuration centralisée
Variables d'environnement et paramètres
"""

import os
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configuration de l'application"""
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # Database
    DATABASE_URL: str = "postgresql://autopilot:autopilot@localhost:5432/autopilot_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Jira
    JIRA_URL: str
    JIRA_EMAIL: str
    JIRA_API_TOKEN: str
    JIRA_PROJECT_KEY: str = "DEMO"
    
    # Application
    SECRET_KEY: str = "demo-secret-key"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Security
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:57342,https://xyqo.ai"
    RATE_LIMIT_PER_MINUTE: int = 5
    
    # Demo
    DEMO_MODE: bool = True
    SANDBOX_PROJECT_KEY: str = "SANDBOX"
    
    # Monitoring
    JAEGER_ENDPOINT: str = "http://localhost:14268/api/traces"
    PROMETHEUS_PORT: int = 9090
    
    # File Security
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt"
    
    # Antivirus
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    
    # Analytics
    GOOGLE_ANALYTICS_ID: str = ""
    MIXPANEL_TOKEN: str = ""
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Liste des extensions autorisées"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Liste des origines CORS autorisées"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        """Taille max fichier en bytes"""
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
    
    class Config:
        env_file = "../.env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env


# Instance globale
settings = Settings()
