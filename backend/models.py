"""
AUTOPILOT - Modèles Pydantic
Structures de données pour l'API
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class ContractType(str, Enum):
    """Types de contrats supportés"""
    SERVICE = "service"
    PURCHASE = "purchase"
    EMPLOYMENT = "employment"
    LEASE = "lease"
    OTHER = "other"


class ContractExtraction(BaseModel):
    """Résultat d'extraction de contrat"""
    contract_type: ContractType
    parties: List[str] = Field(..., min_items=1, max_items=10)
    amount: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=3)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    key_terms: List[str] = Field(default_factory=list, max_items=20)
    summary: str = Field(..., min_length=10, max_length=1000)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('parties')
    def validate_parties(cls, v):
        """Validation des parties contractuelles"""
        if not v:
            raise ValueError("Au moins une partie doit être identifiée")
        # Filtrer les parties vides et s'assurer qu'il en reste au moins une
        filtered_parties = [party.strip() for party in v if party.strip()]
        if not filtered_parties:
            raise ValueError("Au moins une partie valide doit être identifiée")
        return filtered_parties
    
    @validator('currency')
    def validate_currency(cls, v):
        """Validation code devise"""
        if v and len(v) != 3:
            raise ValueError("Code devise doit faire 3 caractères (ex: EUR, USD)")
        return v.upper() if v else v


class JiraTicket(BaseModel):
    """Ticket Jira créé"""
    key: str
    url: str
    summary: str
    description: Union[str, Dict[str, Any]]
    project_key: str
    issue_type: str = "Task"
    priority: str = "Medium"
    created_at: datetime
    demo_mode: bool = False


class ExtractionResponse(BaseModel):
    """Réponse complète d'extraction"""
    session_id: str
    extraction: ContractExtraction
    jira_ticket: Optional[JiraTicket] = None
    processing_time_ms: int
    cached: bool = False
    demo_mode: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    """Réponse health check"""
    status: str = "healthy"
    timestamp: datetime
    demo_mode: bool = True
    version: str = "1.0.0"


class QualityMetrics(BaseModel):
    """Métriques qualité temps réel"""
    total_extractions: int
    success_rate: float = Field(..., ge=0.0, le=1.0)
    avg_confidence_score: float = Field(..., ge=0.0, le=1.0)
    avg_processing_time_ms: int
    cache_hit_rate: float = Field(..., ge=0.0, le=1.0)
    jira_success_rate: float = Field(..., ge=0.0, le=1.0)
    last_24h_extractions: int
    cost_per_extraction_eur: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DemoSession(BaseModel):
    """Session de démonstration"""
    session_id: str
    file_name: str
    file_size: int
    file_hash: str
    extraction_success: bool
    jira_ticket_created: bool = False
    jira_ticket_key: Optional[str] = None
    quality_score: Optional[float] = None
    latency_ms: int
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class FileValidationError(BaseModel):
    """Erreur de validation fichier"""
    error_type: str
    message: str
    file_name: str
    file_size: int
    allowed_types: List[str]
    max_size_mb: int
