"""
Configuration centralisée pour Contract Reader
Permet d'activer/désactiver OpenAI et GDPR via variables d'environnement
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class ContractReaderConfig(BaseSettings):
    """Configuration pour Contract Reader"""
    
    # Configuration OpenAI
    openai_enabled: bool = True
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.1
    
    # Configuration GDPR
    gdpr_enabled: bool = False
    gdpr_consent_required: bool = False
    
    # Mode simulation
    simulation_mode: bool = False
    
    # Mode de fonctionnement: "test" ou "real"
    mode: str = "real"
    
    # Limites de sécurité
    max_cost_cents: float = 10.0  # 0.10€ max par résumé
    max_file_size_mb: int = 10
    
    class Config:
        env_prefix = "CONTRACT_READER_"
        case_sensitive = False
        
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Récupération de la clé OpenAI depuis la variable globale si pas définie
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY")
            
        # Si pas de clé OpenAI, forcer le mode simulation
        if not self.openai_api_key and self.openai_enabled:
            self.simulation_mode = True
            
    @property
    def use_real_openai(self) -> bool:
        """Détermine si on utilise la vraie API OpenAI"""
        return (
            self.openai_enabled and 
            self.openai_api_key and 
            not self.simulation_mode and
            self.mode == "real"
        )
    
    @property
    def require_gdpr_consent(self) -> bool:
        """Détermine si le consentement GDPR est requis"""
        return self.gdpr_enabled and self.gdpr_consent_required
    
    @property
    def is_test_mode(self) -> bool:
        """Détermine si on est en mode test (données simulées)"""
        return self.mode == "test"
    
    @property
    def is_real_mode(self) -> bool:
        """Détermine si on est en mode réel (vraie analyse)"""
        return self.mode == "real"

# Instance globale de configuration
contract_reader_config = ContractReaderConfig()
