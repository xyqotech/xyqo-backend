"""
Templates de prompts optimisés pour résumés de contrats
Pipeline 2 étages pour réduire les tokens et coûts
"""

from typing import Dict, Any, List
from ..models import SummaryMode

class PromptTemplates:
    """Templates de prompts structurés et optimisés"""
    
    @staticmethod
    def get_factual_extraction_prompt(facts: Dict[str, List[str]], sections: Dict[str, str]) -> str:
        """
        Étape 1: Extraction factuelle locale (tokens réduits)
        Prépare les données structurées pour l'IA
        """
        return f"""EXTRACTION FACTUELLE - Contrat analysé

FAITS IDENTIFIÉS:
Dates: {', '.join(facts.get('dates', []))}
Montants: {', '.join(facts.get('amounts', []))}
Durées: {', '.join(facts.get('durations', []))}
Parties: {', '.join(facts.get('parties', []))}
Pourcentages: {', '.join(facts.get('percentages', []))}

SECTIONS CLÉS:
{chr(10).join(f"{k.upper()}: {v[:200]}..." for k, v in sections.items())}

STRUCTURE REQUISE:
- Type de contrat
- Parties contractantes  
- Durée et dates importantes
- Montants et conditions financières
- Obligations principales de chaque partie
- Conditions de résiliation
- Clauses particulières (confidentialité, non-concurrence, etc.)
- Points d'attention et risques"""

    @staticmethod
    def get_rewrite_prompt(structured_facts: str, mode: SummaryMode, language: str = "fr") -> str:
        """
        Étape 2: Réécriture claire par l'IA (tokens optimisés)
        """
        mode_instructions = {
            SummaryMode.STANDARD: "Fais un résumé équilibré et accessible pour un particulier.",
            SummaryMode.CLAUSES: "Détaille chaque clause importante avec explication simple.",
            SummaryMode.RED_FLAGS: "Concentre-toi uniquement sur les risques et points d'attention."
        }
        
        instruction = mode_instructions.get(mode, mode_instructions[SummaryMode.STANDARD])
        
        return f"""Tu es un expert juridique qui aide les particuliers à comprendre leurs contrats.

{instruction}

DONNÉES STRUCTURÉES DU CONTRAT:
{structured_facts}

Réponds UNIQUEMENT au format JSON suivant :
{{
    "title": "Synthèse de votre contrat",
    "meta": {{
        "contract_type": "Type détecté",
        "date_signed": "Date si trouvée",
        "parties": ["Partie 1", "Partie 2"],
        "duration": "Durée du contrat",
        "amount": "Montant principal"
    }},
    "tldr": [
        "Point clé 1 en langage simple",
        "Point clé 2",
        "Point clé 3",
        "Point clé 4",
        "Point clé 5"
    ],
    "clauses": [
        {{"name": "Nom clause", "text": "Explication claire", "importance": "high|medium|low"}},
        {{"name": "Autre clause", "text": "Explication", "importance": "medium"}}
    ],
    "red_flags": [
        "Point d'attention 1",
        "Risque identifié 2"
    ],
    "glossary": [
        {{"term": "Terme juridique", "simple_explanation": "Définition simple"}},
        {{"term": "Autre terme", "simple_explanation": "Explication claire"}}
    ]
}}

RÈGLES IMPORTANTES:
- Utilise un langage simple et accessible
- Évite le jargon juridique
- Sois précis sur les montants et dates
- Mentionne les risques réels
- Reste factuel, ne pas inventer d'informations"""

    @staticmethod
    def get_validation_prompt(original_text: str, summary_json: Dict[str, Any]) -> str:
        """
        Prompt de validation croisée pour vérifier l'exactitude
        """
        return f"""VALIDATION CROISÉE - Vérification exactitude

TEXTE ORIGINAL (extrait):
{original_text[:2000]}...

RÉSUMÉ GÉNÉRÉ:
{summary_json}

Vérifie que CHAQUE fait dans le résumé existe dans l'original:
- Dates mentionnées
- Montants exacts  
- Noms des parties
- Durées spécifiées
- Conditions de résiliation

Réponds au format JSON:
{{
    "validation_passed": true/false,
    "confidence_score": 0.0-1.0,
    "errors_found": ["erreur 1", "erreur 2"],
    "missing_facts": ["fait manquant 1"],
    "accuracy_notes": "Notes sur la précision"
}}"""

    @staticmethod
    def get_cost_estimation_prompt(text_length: int, mode: SummaryMode) -> Dict[str, Any]:
        """
        Estime le coût en tokens pour optimisation
        """
        # Estimation basée sur la longueur et le mode
        base_tokens = text_length // 4  # Approximation 1 token = 4 caractères
        
        mode_multipliers = {
            SummaryMode.STANDARD: 1.0,
            SummaryMode.CLAUSES: 1.3,  # Plus détaillé
            SummaryMode.RED_FLAGS: 0.8  # Plus ciblé
        }
        
        estimated_input_tokens = int(base_tokens * mode_multipliers.get(mode, 1.0))
        estimated_output_tokens = 500  # Sortie JSON structurée
        
        # Prix GPT-4o-mini (approximatif)
        input_cost = (estimated_input_tokens / 1000) * 0.00015  # $0.00015/1K tokens
        output_cost = (estimated_output_tokens / 1000) * 0.0006  # $0.0006/1K tokens
        total_cost_usd = input_cost + output_cost
        total_cost_cents = total_cost_usd * 100
        
        return {
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "estimated_cost_cents": round(total_cost_cents, 2),
            "within_budget": total_cost_cents <= 5.0,  # Budget 0.05€
            "optimization_suggestions": [
                "Réduire le texte d'entrée" if estimated_input_tokens > 2000 else None,
                "Utiliser mode RED_FLAGS" if mode == SummaryMode.CLAUSES and total_cost_cents > 4.0 else None
            ]
        }

    @staticmethod
    def get_system_prompts() -> Dict[str, str]:
        """Prompts système pour différents contextes"""
        return {
            "contract_expert": "Tu es un expert juridique spécialisé dans l'analyse de contrats. Tu expliques les termes complexes en langage simple pour aider les particuliers et PME à comprendre leurs engagements.",
            
            "fact_checker": "Tu es un vérificateur de faits rigoureux. Tu compares les informations extraites avec le document original pour détecter toute erreur ou hallucination.",
            
            "cost_optimizer": "Tu optimises les requêtes IA pour réduire les coûts tout en maintenant la qualité. Tu suggères des améliorations de prompts et de structure.",
            
            "gdpr_compliance": "Tu respectes strictement le RGPD. Tu ne stockes aucune donnée personnelle et tu anonymises les informations sensibles dans tes réponses."
        }
