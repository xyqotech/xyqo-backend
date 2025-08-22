"""
Optimiseur de coûts IA pour Contract Reader
Gestion intelligente des tokens et budgets
"""

import time
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from ..models import SummaryMode
from ..extraction.text_processor import ProcessedDocument

@dataclass
class CostMetrics:
    """Métriques de coût pour une requête"""
    input_tokens: int
    output_tokens: int
    cost_cents: float
    processing_time_ms: int
    optimization_applied: bool = False
    savings_cents: float = 0.0

class CostOptimizer:
    """Optimiseur de coûts pour requêtes IA"""
    
    def __init__(self):
        self.cost_history = []
        self.optimization_stats = {
            "total_requests": 0,
            "total_cost_cents": 0.0,
            "total_savings_cents": 0.0,
            "avg_cost_per_request": 0.0,
            "optimization_rate": 0.0
        }
        
        # Prix GPT-4o-mini (cents par 1K tokens)
        self.pricing = {
            "input_cost_per_1k": 0.015,  # $0.00015 = 0.015 cents
            "output_cost_per_1k": 0.06   # $0.0006 = 0.06 cents
        }
    
    def optimize_input_text(self, doc: ProcessedDocument, mode: SummaryMode) -> Tuple[str, Dict[str, Any]]:
        """
        Optimise le texte d'entrée pour réduire les tokens
        Pipeline 2 étages : faits structurés → résumé IA
        """
        original_length = len(doc.cleaned_text)
        
        # Étape 1: Créer un résumé factuel structuré (local, 0€)
        structured_facts = self._create_structured_facts(doc, mode)
        
        optimized_length = len(structured_facts)
        tokens_saved = (original_length - optimized_length) // 4  # Approximation
        cost_saved = (tokens_saved / 1000) * self.pricing["input_cost_per_1k"]
        
        optimization_info = {
            "original_length": original_length,
            "optimized_length": optimized_length,
            "reduction_percent": (1 - optimized_length / original_length) * 100,
            "tokens_saved": tokens_saved,
            "cost_saved_cents": round(cost_saved, 3),
            "method": "structured_facts_extraction"
        }
        
        return structured_facts, optimization_info
    
    def _create_structured_facts(self, doc: ProcessedDocument, mode: SummaryMode) -> str:
        """Crée un résumé factuel structuré pour l'IA"""
        
        # Sélectionner les sections pertinentes selon le mode
        relevant_sections = self._select_relevant_sections(doc.sections, mode)
        
        # Construire le texte optimisé
        structured_text = f"""CONTRAT - ANALYSE STRUCTURÉE

TYPE: {self._infer_contract_type(doc)}

PARTIES:
{chr(10).join(f"- {party}" for party in doc.facts.get('parties', [])[:3])}

DATES IMPORTANTES:
{chr(10).join(f"- {date}" for date in doc.facts.get('dates', [])[:5])}

MONTANTS:
{chr(10).join(f"- {amount}" for amount in doc.facts.get('amounts', [])[:3])}

DURÉES:
{chr(10).join(f"- {duration}" for duration in doc.facts.get('durations', [])[:3])}

SECTIONS CLÉS:
{chr(10).join(f"{k.upper()}: {v[:150]}..." for k, v in relevant_sections.items())}

CONTEXTE ADDITIONNEL:
{doc.cleaned_text[:500]}..."""

        return structured_text
    
    def _select_relevant_sections(self, sections: Dict[str, str], mode: SummaryMode) -> Dict[str, str]:
        """Sélectionne les sections pertinentes selon le mode"""
        
        if mode == SummaryMode.RED_FLAGS:
            # Focus sur les sections à risque
            priority_sections = ["resiliation", "responsabilite", "obligations", "prix"]
        elif mode == SummaryMode.CLAUSES:
            # Toutes les sections importantes
            priority_sections = ["objet", "duree", "prix", "obligations", "resiliation", "responsabilite"]
        else:  # STANDARD
            # Sections essentielles
            priority_sections = ["objet", "duree", "prix", "resiliation"]
        
        return {k: v for k, v in sections.items() if k in priority_sections}
    
    def _infer_contract_type(self, doc: ProcessedDocument) -> str:
        """Infère le type de contrat à partir du contenu"""
        text_lower = doc.cleaned_text.lower()
        
        contract_indicators = {
            "service": ["prestation", "service", "mission", "consultant"],
            "employment": ["emploi", "travail", "salaire", "employeur", "salarié"],
            "lease": ["bail", "location", "loyer", "locataire", "propriétaire"],
            "purchase": ["achat", "vente", "commande", "livraison", "fournisseur"],
            "partnership": ["partenariat", "collaboration", "associé", "société"]
        }
        
        scores = {}
        for contract_type, keywords in contract_indicators.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[contract_type] = score
        
        return max(scores, key=scores.get) if scores else "général"
    
    def estimate_cost(self, input_text: str, mode: SummaryMode) -> CostMetrics:
        """Estime le coût d'une requête"""
        
        # Estimation des tokens
        input_tokens = len(input_text) // 4  # Approximation
        
        # Tokens de sortie selon le mode
        output_tokens_by_mode = {
            SummaryMode.STANDARD: 400,
            SummaryMode.CLAUSES: 600,
            SummaryMode.RED_FLAGS: 300
        }
        output_tokens = output_tokens_by_mode.get(mode, 400)
        
        # Calcul du coût
        input_cost = (input_tokens / 1000) * self.pricing["input_cost_per_1k"]
        output_cost = (output_tokens / 1000) * self.pricing["output_cost_per_1k"]
        total_cost = input_cost + output_cost
        
        return CostMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_cents=round(total_cost, 3),
            processing_time_ms=0  # Sera mis à jour après traitement
        )
    
    def record_actual_cost(self, metrics: CostMetrics) -> None:
        """Enregistre le coût réel d'une requête"""
        self.cost_history.append(metrics)
        
        # Mettre à jour les statistiques
        self.optimization_stats["total_requests"] += 1
        self.optimization_stats["total_cost_cents"] += metrics.cost_cents
        self.optimization_stats["total_savings_cents"] += metrics.savings_cents
        
        if metrics.optimization_applied:
            self.optimization_stats["optimization_rate"] = (
                self.optimization_stats["optimization_rate"] * (self.optimization_stats["total_requests"] - 1) + 1
            ) / self.optimization_stats["total_requests"]
        
        self.optimization_stats["avg_cost_per_request"] = (
            self.optimization_stats["total_cost_cents"] / self.optimization_stats["total_requests"]
        )
        
        # Garder seulement les 100 dernières requêtes
        if len(self.cost_history) > 100:
            self.cost_history.pop(0)
    
    def get_budget_status(self, estimated_cost: float, daily_budget: float = 10.0) -> Dict[str, Any]:
        """Vérifie le statut budgétaire"""
        
        # Coût total aujourd'hui
        today_cost = sum(m.cost_cents for m in self.cost_history[-50:])  # Approximation journée
        
        return {
            "estimated_cost_cents": estimated_cost,
            "daily_spent_cents": today_cost,
            "daily_budget_cents": daily_budget,
            "within_budget": estimated_cost <= 5.0,  # Limite par requête
            "daily_budget_remaining": max(0, daily_budget - today_cost),
            "can_process": estimated_cost <= 5.0 and (today_cost + estimated_cost) <= daily_budget
        }
    
    def suggest_optimizations(self, doc: ProcessedDocument, estimated_cost: float) -> List[str]:
        """Suggère des optimisations si le coût est élevé"""
        suggestions = []
        
        if estimated_cost > 4.0:
            suggestions.append("Coût élevé détecté - considérer le mode RED_FLAGS")
        
        if len(doc.cleaned_text) > 8000:
            suggestions.append("Document très long - extraction factuelle recommandée")
        
        if len(doc.facts.get('dates', [])) == 0:
            suggestions.append("Peu de faits extraits - vérifier la qualité du PDF")
        
        if not doc.sections:
            suggestions.append("Aucune section identifiée - document peut être mal structuré")
        
        return suggestions
    
    def get_cost_report(self) -> Dict[str, Any]:
        """Rapport détaillé des coûts"""
        if not self.cost_history:
            return {"message": "Aucune donnée de coût disponible"}
        
        recent_costs = [m.cost_cents for m in self.cost_history[-20:]]
        
        return {
            "summary": self.optimization_stats.copy(),
            "recent_performance": {
                "avg_cost_last_20": sum(recent_costs) / len(recent_costs),
                "min_cost": min(recent_costs),
                "max_cost": max(recent_costs),
                "cost_trend": "stable"  # TODO: calculer la tendance
            },
            "budget_compliance": {
                "requests_over_budget": sum(1 for m in self.cost_history if m.cost_cents > 5.0),
                "avg_savings_per_optimization": (
                    self.optimization_stats["total_savings_cents"] / 
                    max(1, sum(1 for m in self.cost_history if m.optimization_applied))
                )
            }
        }
