"""
Extension Contract Reader pour AUTOPILOT
Résumés intelligents de contrats avec IA et validation
"""

__version__ = "1.0.0"
__description__ = "Contract Reader - Résumés automatiques de contrats"

# Import du pipeline principal pour faciliter l'utilisation
from .main_pipeline import contract_reader_pipeline

__all__ = ["contract_reader_pipeline"]
