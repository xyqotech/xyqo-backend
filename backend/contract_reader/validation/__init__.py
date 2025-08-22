"""
Module de validation croisée pour Contract Reader
Vérification exactitude + citations précises avec positions XY
"""

from .cross_validator import CrossValidator
from .citation_engine import CitationEngine
from .fact_checker import FactChecker

__all__ = ["CrossValidator", "CitationEngine", "FactChecker"]
