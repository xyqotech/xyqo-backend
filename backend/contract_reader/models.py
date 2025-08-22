"""
Modèles Pydantic pour Contract Reader
Structures de données pour résumés, requêtes et réponses
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum

class SummaryMode(str, Enum):
    """Modes de résumé disponibles"""
    STANDARD = "standard"
    CLAUSES = "clauses"
    RED_FLAGS = "redflags"

class ContractSummaryRequest(BaseModel):
    """Requête de résumé de contrat"""
    mode: SummaryMode = SummaryMode.STANDARD
    language: str = Field(default="fr", pattern="^(fr|en)$")
    include_citations: bool = True
    max_pages: int = Field(default=2, ge=1, le=5)

class ContractMeta(BaseModel):
    """Métadonnées du contrat"""
    contract_type: Optional[str] = None
    date_signed: Optional[str] = None
    parties: List[str] = Field(default_factory=list)
    duration: Optional[str] = None
    amount: Optional[str] = None

class ContractClause(BaseModel):
    """Clause de contrat avec explication"""
    name: str
    text: str
    importance: str = Field(default="medium")  # low, medium, high, critical
    page_reference: Optional[str] = None

class GlossaryTerm(BaseModel):
    """Terme de glossaire juridique"""
    term: str
    simple_explanation: str
    legal_definition: Optional[str] = None

class ContractSummary(BaseModel):
    """Résumé structuré d'un contrat"""
    title: str
    meta: ContractMeta
    tldr: List[str] = Field(description="Points clés en langage simple")
    clauses: List[ContractClause] = Field(description="Clauses importantes expliquées")
    red_flags: List[str] = Field(description="Points d'attention et risques")
    glossary: List[GlossaryTerm] = Field(description="Termes juridiques expliqués")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Score de confiance de l'analyse")
    processing_notes: List[str] = Field(default_factory=list, description="Notes de traitement")
    disclaimer: str = "Ce résumé est généré automatiquement et ne remplace pas un avis juridique professionnel."

class ValidationResult(BaseModel):
    """Résultat de validation croisée"""
    is_valid: bool
    confidence_score: float
    missing_facts: List[str] = Field(default_factory=list)
    citations_verified: int = 0
    total_citations: int = 0
    validation_notes: List[str] = Field(default_factory=list)

class ProcessingMetrics(BaseModel):
    """Métriques de traitement"""
    extraction_time_ms: int
    ai_processing_time_ms: int
    validation_time_ms: int
    total_time_ms: int
    cost_cents: float
    cache_hit: bool = False
    tokens_used: int = 0

class PDFInfo(BaseModel):
    """Informations sur le PDF"""
    pass

class ContractSummaryResponse(BaseModel):
    """Réponse complète du résumé de contrat"""
    summary: ContractSummary
    validation: ValidationResult
    pdf_info: Optional[PDFInfo] = None
    processing_time_ms: int
    cache_hit: bool = False
    cost_cents: float = 0.0
    doc_hash: str
    created_at: datetime
    expires_at: datetime
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    quota_info: Optional[Dict[str, Any]] = None

class SystemHealth(BaseModel):
    """État de santé du système"""
    status: str
    timestamp: str
    components: Dict[str, Any]
    version: str = "1.0.0"

class BudgetStatus(BaseModel):
    """Statut budgétaire et quotas"""
    within_budget: bool
    estimated_cost_cents: float
    quota_remaining: Dict[str, int]
    message: str

class HealthCheck(BaseModel):
    """Santé du système Contract Reader"""
    status: str  # healthy, warning, critical
    health_score: int  # 0-100
    cache_hit_rate: float
    avg_processing_time_ms: float
    errors_last_24h: int
    active_summaries: int
    timestamp: datetime
