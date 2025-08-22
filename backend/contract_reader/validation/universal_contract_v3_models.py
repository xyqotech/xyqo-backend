"""
Modèles Pydantic pour UniversalContractV3
Validation stricte du schéma JSON de sortie
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
from pydantic import BaseModel, Field, validator
from enum import Enum

class PriceModel(str, Enum):
    """Modèles de prix disponibles"""
    FORFAIT = "forfait"
    ABONNEMENT = "abonnement"
    A_L_ACTE = "à_l_acte"
    MIXTE = "mixte"
    INCONNU = "inconnu"

class Period(str, Enum):
    """Périodicités disponibles"""
    UNIQUE = "unique"
    MENSUEL = "mensuel"
    TRIMESTRIEL = "trimestriel"
    ANNUEL = "annuel"
    INCONNU = "inconnu"

class ContractType(str, Enum):
    """Types de contrat de travail"""
    CDI = "CDI"
    CDD = "CDD"
    PORTAGE = "Portage"
    INTERIM = "Interim"
    AUTRE = "Autre"

class WorkingTimeType(str, Enum):
    """Types de temps de travail"""
    HEURES = "heures"
    FORFAIT_JOURS = "forfait_jours"

class Periodicity(str, Enum):
    """Périodicité de rémunération"""
    HORAIRE = "horaire"
    JOURNALIER = "journalier"
    MENSUEL = "mensuel"
    ANNUEL = "annuel"

class PropertyType(str, Enum):
    """Types de propriété immobilière"""
    HABITATION = "habitation"
    COMMERCIAL = "commercial"
    TERRAIN = "terrain"
    VEFA = "vefa"
    AUTRE = "autre"

class InsuranceType(str, Enum):
    """Types d'assurance"""
    RC_PRO = "rc_pro"
    DOMMAGES_OUVRAGE = "dommages_ouvrage"
    DECENNALE = "decennale"
    ASSURANCE_EMPRUNTEUR = "assurance_emprunteur"
    AUTRE = "autre"

# Modèles de base
class Party(BaseModel):
    """Partie contractuelle"""
    name: str
    role: str
    legal_form: Optional[str] = None
    siren_siret: Optional[str] = None
    address: Optional[str] = None
    representative: Optional[str] = None
    contact_masked: Optional[str] = None

class Parties(BaseModel):
    """Parties contractuelles"""
    list: List[Party]
    third_parties: List[Party] = Field(default_factory=list)

class Meta(BaseModel):
    """Métadonnées du document"""
    generator: str = "ContractSummarizer"
    version: str = "2.0"
    language: str = "fr"
    generated_at: str
    locale_guess: str = "fr"
    source_doc_info: Dict[str, Any]

class Deliverable(BaseModel):
    """Livrable ou exclusion"""
    pass

class Scope(BaseModel):
    """Périmètre du contrat"""
    deliverables: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)

class Milestone(BaseModel):
    """Étape importante"""
    label: str
    date: Optional[date] = None

class Dates(BaseModel):
    """Dates du contrat"""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    minimum_term_months: Optional[int] = None
    renewal: Optional[str] = None
    notice_period_days: Optional[int] = None
    milestones: List[Milestone] = Field(default_factory=list)

class Obligations(BaseModel):
    """Obligations contractuelles"""
    by_provider: List[str] = Field(default_factory=list)
    by_customer: List[str] = Field(default_factory=list)
    by_other: List[str] = Field(default_factory=list)

class ServiceLevels(BaseModel):
    """Niveaux de service"""
    kpi_list: List[str] = Field(default_factory=list)
    sla: Optional[str] = None
    penalties: Optional[str] = None

class IPRights(BaseModel):
    """Droits de propriété intellectuelle"""
    ownership: Optional[str] = None
    license_terms: Optional[str] = None

class DataPrivacy(BaseModel):
    """Protection des données"""
    rgpd: Optional[bool] = None
    processing_roles: Optional[str] = None
    subprocessors: List[str] = Field(default_factory=list)
    data_locations: List[str] = Field(default_factory=list)
    security_measures: List[str] = Field(default_factory=list)

class Contract(BaseModel):
    """Détails du contrat"""
    object: str
    scope: Scope
    location_or_site: Optional[str] = None
    dates: Dates
    obligations: Obligations
    service_levels: ServiceLevels
    ip_rights: IPRights
    data_privacy: DataPrivacy

# Modèles financiers
class FinancialItem(BaseModel):
    """Élément financier"""
    label: str
    amount: Optional[float] = None
    currency: Optional[str] = None
    period: Optional[Period] = None

class SecurityDeposit(BaseModel):
    """Dépôt de garantie"""
    amount: Optional[float] = None
    currency: Optional[str] = None
    refund_terms: Optional[str] = None

class RepaymentScheduleItem(BaseModel):
    """Élément d'échéancier de remboursement"""
    amount: Optional[float] = None
    currency: Optional[str] = None
    due_date: Optional[date] = None

class WithdrawalRights(BaseModel):
    """Droits de rétractation"""
    days: Optional[int] = None
    instructions: Optional[str] = None

class CreditDetails(BaseModel):
    """Détails de crédit"""
    principal_amount: Optional[float] = None
    currency: Optional[str] = None
    taeg_percent: Optional[float] = None
    interest_rate_percent: Optional[float] = None
    repayment_schedule: List[RepaymentScheduleItem] = Field(default_factory=list)
    withdrawal_rights: Optional[WithdrawalRights] = None

class Financials(BaseModel):
    """Informations financières"""
    price_model: Optional[PriceModel] = None
    items: List[FinancialItem] = Field(default_factory=list)
    currency: Optional[str] = None
    payment_terms: Optional[str] = None
    late_fees: Optional[str] = None
    indexation: Optional[str] = None
    security_deposit: Optional[SecurityDeposit] = None
    credit_details: Optional[CreditDetails] = None

# Modèles de gouvernance
class Termination(BaseModel):
    """Conditions de résiliation"""
    by_provider: Optional[str] = None
    by_customer: Optional[str] = None
    effects: Optional[str] = None

class NonCompete(BaseModel):
    """Clause de non-concurrence"""
    exists: Optional[bool] = None
    duration_months: Optional[int] = None
    scope: Optional[str] = None
    consideration_amount: Optional[float] = None
    currency: Optional[str] = None

class Governance(BaseModel):
    """Gouvernance du contrat"""
    termination: Optional[Termination] = None
    liability: Optional[str] = None
    warranties: Optional[str] = None
    compliance: Optional[str] = None
    law: Optional[str] = None
    jurisdiction: Optional[str] = None
    insurance: Optional[str] = None
    confidentiality: Optional[bool] = None
    force_majeure: Optional[bool] = None
    non_compete: Optional[NonCompete] = None

# Modèles spécialisés
class InsurancePolicy(BaseModel):
    """Police d'assurance"""
    type: Optional[InsuranceType] = None
    provider: Optional[str] = None
    policy_number: Optional[str] = None
    coverage: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class Assurances(BaseModel):
    """Assurances"""
    policies: List[InsurancePolicy] = Field(default_factory=list)

class ConditionSuspensive(BaseModel):
    """Condition suspensive"""
    label: str
    description: Optional[str] = None
    deadline_date: Optional[date] = None
    satisfied: Optional[bool] = None

class ProbationPeriod(BaseModel):
    """Période d'essai"""
    months: Optional[int] = None

class WorkingTime(BaseModel):
    """Temps de travail"""
    type: Optional[WorkingTimeType] = None
    hours_per_week: Optional[float] = None
    days_per_year: Optional[int] = None

class Remuneration(BaseModel):
    """Rémunération"""
    base_amount: Optional[float] = None
    currency: Optional[str] = None
    periodicity: Optional[Periodicity] = None
    variable: Optional[str] = None
    minimum_guarantee: Optional[float] = None

class EmploymentDetails(BaseModel):
    """Détails d'emploi"""
    contract_type: Optional[ContractType] = None
    position_title: Optional[str] = None
    qualification: Optional[str] = None
    collective_agreement: Optional[str] = None
    probation_period: Optional[ProbationPeriod] = None
    working_time: Optional[WorkingTime] = None
    remuneration: Optional[Remuneration] = None
    paid_leave_days_per_year: Optional[float] = None
    notice_period: Optional[str] = None
    mobility_clause: Optional[bool] = None

class RetractionRights(BaseModel):
    """Droits de rétractation"""
    days: Optional[int] = None

class Delivery(BaseModel):
    """Livraison"""
    deadline_date: Optional[date] = None
    penalties: Optional[str] = None

class ImmobilierSpecifics(BaseModel):
    """Spécificités immobilières"""
    property_type: Optional[PropertyType] = None
    address: Optional[str] = None
    surface_sqm: Optional[float] = None
    rooms: Optional[int] = None
    lot_description: Optional[str] = None
    diagnostics: List[str] = Field(default_factory=list)
    charges_breakdown: Optional[str] = None
    works_done: Optional[str] = None
    retraction_rights: Optional[RetractionRights] = None
    delivery: Optional[Delivery] = None

class LitigesModesAlternatifs(BaseModel):
    """Modes alternatifs de résolution des litiges"""
    mediation: Optional[str] = None
    arbitration: Optional[str] = None
    amicable_settlement_steps: Optional[str] = None

class OperationalActions(BaseModel):
    """Actions opérationnelles"""
    jira_summary: Optional[str] = None
    key_dates: List[date] = Field(default_factory=list)
    renewal_window_days: Optional[int] = None

# Modèle principal
class UniversalContractV3(BaseModel):
    """Schéma UniversalContractV3 complet"""
    meta: Meta
    parties: Parties
    contract: Contract
    financials: Financials
    governance: Governance
    assurances: Optional[Assurances] = None
    conditions_suspensives: List[ConditionSuspensive] = Field(default_factory=list)
    employment_details: Optional[EmploymentDetails] = None
    immobilier_specifics: Optional[ImmobilierSpecifics] = None
    litiges_modes_alternatifs: Optional[LitigesModesAlternatifs] = None
    summary_plain: str
    risks_red_flags: List[str] = Field(default_factory=list)
    missing_info: List[str] = Field(default_factory=list)
    operational_actions: OperationalActions

    class Config:
        """Configuration Pydantic"""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # Interdit les champs supplémentaires

    @validator('summary_plain')
    def validate_summary_length(cls, v):
        """Valide la longueur du résumé"""
        if not v or len(v.strip()) < 50:
            raise ValueError("Le résumé doit contenir au moins 50 caractères")
        return v.strip()

    @validator('meta')
    def validate_meta(cls, v):
        """Valide les métadonnées"""
        if not v.generated_at:
            raise ValueError("La date de génération est requise")
        return v
