"""
Module IA pour résumés de contrats optimisés
Pipeline 2 étages : extraction factuelle + réécriture claire
"""

from .ai_summarizer import AISummarizer
from .prompt_templates import PromptTemplates
from .cost_optimizer import CostOptimizer

__all__ = ["AISummarizer", "PromptTemplates", "CostOptimizer"]
