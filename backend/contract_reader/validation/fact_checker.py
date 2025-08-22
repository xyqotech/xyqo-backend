"""
Vérificateur de faits rigoureux pour Contract Reader
Validation croisée entre résumé IA et document original
"""

import re
from typing import List, Dict, Any, Tuple, Set
from dataclasses import dataclass
from ..models import ContractSummary
from ..extraction.text_processor import ProcessedDocument
from .citation_engine import CitationEngine, Citation

@dataclass
class FactCheckResult:
    """Résultat de vérification d'un fait"""
    fact: str
    found_in_original: bool
    confidence: float
    citation: Citation = None
    error_type: str = None  # "missing", "modified", "hallucination"

@dataclass
class ValidationReport:
    """Rapport complet de validation"""
    total_facts_checked: int
    facts_verified: int
    facts_missing: int
    facts_modified: int
    hallucinations: int
    accuracy_percentage: float
    critical_errors: List[str]
    warnings: List[str]
    citation_accuracy: float

class FactChecker:
    """Vérificateur de faits avec validation croisée rigoureuse"""
    
    def __init__(self):
        self.citation_engine = CitationEngine()
        self.validation_stats = {
            "total_validations": 0,
            "avg_accuracy": 0.0,
            "critical_errors_detected": 0,
            "hallucinations_prevented": 0
        }
    
    def validate_summary_facts(self, summary: ContractSummary, doc: ProcessedDocument) -> ValidationReport:
        """
        Validation complète des faits du résumé contre le document original
        """
        fact_results = []
        critical_errors = []
        warnings = []
        
        # 1. Vérifier les métadonnées critiques
        meta_results = self._validate_metadata(summary.meta, doc)
        fact_results.extend(meta_results)
        
        # 2. Vérifier les points clés (TL;DR)
        tldr_results = self._validate_tldr_facts(summary.tldr, doc)
        fact_results.extend(tldr_results)
        
        # 3. Vérifier les clauses importantes
        clause_results = self._validate_clauses(summary.clauses, doc)
        fact_results.extend(clause_results)
        
        # 4. Vérifier les red flags
        redflags_results = self._validate_red_flags(summary.red_flags, doc)
        fact_results.extend(redflags_results)
        
        # 5. Générer citations pour les faits vérifiés
        citation_result = self.citation_engine.generate_citations(summary, doc.pages)
        
        # Analyser les résultats
        total_facts = len(fact_results)
        verified_facts = sum(1 for r in fact_results if r.found_in_original)
        missing_facts = sum(1 for r in fact_results if not r.found_in_original and r.error_type == "missing")
        modified_facts = sum(1 for r in fact_results if not r.found_in_original and r.error_type == "modified")
        hallucinations = sum(1 for r in fact_results if r.error_type == "hallucination")
        
        accuracy = (verified_facts / max(total_facts, 1)) * 100
        
        # Identifier erreurs critiques et avertissements
        for result in fact_results:
            if not result.found_in_original:
                if result.error_type == "hallucination":
                    critical_errors.append(f"Hallucination détectée: {result.fact}")
                elif result.error_type == "modified":
                    warnings.append(f"Fait modifié: {result.fact}")
                elif result.error_type == "missing":
                    warnings.append(f"Fait non trouvé: {result.fact}")
        
        # Mettre à jour statistiques
        self._update_validation_stats(accuracy, len(critical_errors), hallucinations)
        
        return ValidationReport(
            total_facts_checked=total_facts,
            facts_verified=verified_facts,
            facts_missing=missing_facts,
            facts_modified=modified_facts,
            hallucinations=hallucinations,
            accuracy_percentage=accuracy,
            critical_errors=critical_errors,
            warnings=warnings,
            citation_accuracy=citation_result.citation_accuracy
        )
    
    def _validate_metadata(self, meta, doc: ProcessedDocument) -> List[FactCheckResult]:
        """Valide les métadonnées du contrat"""
        results = []
        
        # Vérifier la date de signature
        if hasattr(meta, 'date_signed') and meta.date_signed:
            result = self._check_date_fact(meta.date_signed, doc)
            results.append(result)
        
        # Vérifier le montant principal
        if hasattr(meta, 'amount') and meta.amount:
            result = self._check_amount_fact(meta.amount, doc)
            results.append(result)
        
        # Vérifier la durée
        if hasattr(meta, 'duration') and meta.duration:
            result = self._check_duration_fact(meta.duration, doc)
            results.append(result)
        
        # Vérifier les parties
        if hasattr(meta, 'parties') and meta.parties:
            for party in meta.parties:
                result = self._check_party_fact(party, doc)
                results.append(result)
        
        return results
    
    def _validate_tldr_facts(self, tldr: List[str], doc: ProcessedDocument) -> List[FactCheckResult]:
        """Valide les faits dans le résumé TL;DR"""
        results = []
        
        for point in tldr:
            # Extraire les faits vérifiables du point
            facts = self._extract_verifiable_facts(point)
            
            for fact in facts:
                result = self._check_generic_fact(fact, doc)
                results.append(result)
        
        return results
    
    def _validate_clauses(self, clauses: List, doc: ProcessedDocument) -> List[FactCheckResult]:
        """Valide les clauses mentionnées"""
        results = []
        
        for clause in clauses:
            # Vérifier que la clause existe réellement
            clause_name = clause.name if hasattr(clause, 'name') else str(clause)
            clause_text = clause.text if hasattr(clause, 'text') else ""
            
            # Rechercher la clause dans le document
            result = self._check_clause_existence(clause_name, clause_text, doc)
            results.append(result)
            
            # Extraire et vérifier les faits spécifiques de la clause
            clause_facts = self._extract_verifiable_facts(clause_text)
            for fact in clause_facts:
                fact_result = self._check_generic_fact(fact, doc)
                results.append(fact_result)
        
        return results
    
    def _validate_red_flags(self, red_flags: List[str], doc: ProcessedDocument) -> List[FactCheckResult]:
        """Valide les points d'attention mentionnés"""
        results = []
        
        for flag in red_flags:
            # Les red flags sont souvent des interprétations
            # On vérifie si les éléments factuels sous-jacents existent
            facts = self._extract_verifiable_facts(flag)
            
            for fact in facts:
                result = self._check_generic_fact(fact, doc)
                # Les red flags ont une tolérance plus élevée car ils sont interprétatifs
                if result.confidence < 0.5:
                    result.confidence = 0.7  # Ajustement pour interprétation
                results.append(result)
        
        return results
    
    def _check_date_fact(self, date_str: str, doc: ProcessedDocument) -> FactCheckResult:
        """Vérifie une date spécifique"""
        # Normaliser la date pour la recherche
        normalized_date = self._normalize_date(date_str)
        
        # Rechercher dans les faits extraits
        doc_dates = doc.facts.get('dates', [])
        
        for doc_date in doc_dates:
            if self._dates_match(normalized_date, doc_date):
                return FactCheckResult(
                    fact=date_str,
                    found_in_original=True,
                    confidence=1.0
                )
        
        # Recherche floue dans le texte
        if self._fuzzy_search_date(date_str, doc.cleaned_text):
            return FactCheckResult(
                fact=date_str,
                found_in_original=True,
                confidence=0.8
            )
        
        return FactCheckResult(
            fact=date_str,
            found_in_original=False,
            confidence=0.0,
            error_type="missing"
        )
    
    def _check_amount_fact(self, amount_str: str, doc: ProcessedDocument) -> FactCheckResult:
        """Vérifie un montant spécifique"""
        # Extraire le montant numérique
        amount_match = re.search(r'(\d{1,3}(?:\s?\d{3})*(?:[,\.]\d{2})?)', amount_str)
        if not amount_match:
            return FactCheckResult(
                fact=amount_str,
                found_in_original=False,
                confidence=0.0,
                error_type="malformed"
            )
        
        amount_num = amount_match.group(1)
        
        # Rechercher dans les faits extraits
        doc_amounts = doc.facts.get('amounts', [])
        
        for doc_amount in doc_amounts:
            if amount_num in doc_amount:
                return FactCheckResult(
                    fact=amount_str,
                    found_in_original=True,
                    confidence=1.0
                )
        
        # Recherche dans le texte complet
        if amount_num in doc.cleaned_text:
            return FactCheckResult(
                fact=amount_str,
                found_in_original=True,
                confidence=0.9
            )
        
        return FactCheckResult(
            fact=amount_str,
            found_in_original=False,
            confidence=0.0,
            error_type="missing"
        )
    
    def _check_duration_fact(self, duration_str: str, doc: ProcessedDocument) -> FactCheckResult:
        """Vérifie une durée spécifique"""
        # Extraire la durée
        duration_match = re.search(r'(\d+)\s*(mois|ans?|années?|jours?|semaines?)', duration_str, re.IGNORECASE)
        if not duration_match:
            return FactCheckResult(
                fact=duration_str,
                found_in_original=False,
                confidence=0.0,
                error_type="malformed"
            )
        
        number, unit = duration_match.groups()
        
        # Rechercher dans les faits extraits
        doc_durations = doc.facts.get('durations', [])
        
        for doc_duration in doc_durations:
            if number in doc_duration and unit.lower() in doc_duration.lower():
                return FactCheckResult(
                    fact=duration_str,
                    found_in_original=True,
                    confidence=1.0
                )
        
        return FactCheckResult(
            fact=duration_str,
            found_in_original=False,
            confidence=0.0,
            error_type="missing"
        )
    
    def _check_party_fact(self, party_str: str, doc: ProcessedDocument) -> FactCheckResult:
        """Vérifie une partie contractante"""
        party_lower = party_str.lower().strip()
        
        # Rechercher dans les faits extraits
        doc_parties = doc.facts.get('parties', [])
        
        for doc_party in doc_parties:
            if party_lower in doc_party.lower() or doc_party.lower() in party_lower:
                return FactCheckResult(
                    fact=party_str,
                    found_in_original=True,
                    confidence=1.0
                )
        
        # Recherche floue dans le texte
        if party_lower in doc.cleaned_text.lower():
            return FactCheckResult(
                fact=party_str,
                found_in_original=True,
                confidence=0.8
            )
        
        return FactCheckResult(
            fact=party_str,
            found_in_original=False,
            confidence=0.0,
            error_type="missing"
        )
    
    def _check_clause_existence(self, clause_name: str, clause_text: str, doc: ProcessedDocument) -> FactCheckResult:
        """Vérifie l'existence d'une clause"""
        # Rechercher le nom de la clause
        clause_name_lower = clause_name.lower()
        
        # Rechercher dans les sections identifiées
        for section_name, section_text in doc.sections.items():
            if clause_name_lower in section_name.lower() or clause_name_lower in section_text.lower():
                return FactCheckResult(
                    fact=f"Clause: {clause_name}",
                    found_in_original=True,
                    confidence=0.9
                )
        
        # Recherche dans le texte complet
        if clause_name_lower in doc.cleaned_text.lower():
            return FactCheckResult(
                fact=f"Clause: {clause_name}",
                found_in_original=True,
                confidence=0.7
            )
        
        return FactCheckResult(
            fact=f"Clause: {clause_name}",
            found_in_original=False,
            confidence=0.0,
            error_type="missing"
        )
    
    def _check_generic_fact(self, fact: str, doc: ProcessedDocument) -> FactCheckResult:
        """Vérification générique d'un fait"""
        fact_lower = fact.lower().strip()
        
        # Recherche exacte
        if fact_lower in doc.cleaned_text.lower():
            return FactCheckResult(
                fact=fact,
                found_in_original=True,
                confidence=1.0
            )
        
        # Recherche par mots-clés (pour faits complexes)
        fact_words = set(word for word in fact_lower.split() if len(word) > 3)
        doc_words = set(word for word in doc.cleaned_text.lower().split() if len(word) > 3)
        
        if fact_words and len(fact_words.intersection(doc_words)) / len(fact_words) > 0.7:
            return FactCheckResult(
                fact=fact,
                found_in_original=True,
                confidence=0.8
            )
        
        return FactCheckResult(
            fact=fact,
            found_in_original=False,
            confidence=0.0,
            error_type="missing"
        )
    
    def _extract_verifiable_facts(self, text: str) -> List[str]:
        """Extrait les faits vérifiables d'un texte"""
        facts = []
        
        # Patterns pour faits vérifiables
        patterns = [
            r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b',  # Dates
            r'\b\d{1,3}(?:\s?\d{3})*(?:[,\.]\d{2})?\s*(?:€|EUR|%)\b',  # Montants/pourcentages
            r'\b\d+\s*(?:mois|ans?|jours?|semaines?)\b',  # Durées
            r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'  # Noms propres
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            facts.extend(matches)
        
        return [fact.strip() for fact in facts if fact.strip()]
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalise une date pour la comparaison"""
        # Supprimer espaces et normaliser séparateurs
        normalized = re.sub(r'[\s\-\.]', '/', date_str.strip())
        return normalized.lower()
    
    def _dates_match(self, date1: str, date2: str) -> bool:
        """Compare deux dates avec tolérance"""
        norm1 = self._normalize_date(date1)
        norm2 = self._normalize_date(date2)
        
        return norm1 == norm2 or norm1 in norm2 or norm2 in norm1
    
    def _fuzzy_search_date(self, date_str: str, text: str) -> bool:
        """Recherche floue d'une date dans le texte"""
        # Extraire composants de la date
        date_match = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', date_str)
        if not date_match:
            return False
        
        day, month, year = date_match.groups()
        
        # Rechercher variations
        variations = [
            f"{day}/{month}/{year}",
            f"{day}-{month}-{year}",
            f"{int(day)}/{int(month)}/{year}",
            f"{day} {month} {year}"
        ]
        
        text_lower = text.lower()
        return any(var.lower() in text_lower for var in variations)
    
    def _update_validation_stats(self, accuracy: float, critical_errors: int, hallucinations: int):
        """Met à jour les statistiques de validation"""
        self.validation_stats["total_validations"] += 1
        self.validation_stats["critical_errors_detected"] += critical_errors
        self.validation_stats["hallucinations_prevented"] += hallucinations
        
        # Moyenne mobile de l'exactitude
        total = self.validation_stats["total_validations"]
        self.validation_stats["avg_accuracy"] = (
            (self.validation_stats["avg_accuracy"] * (total - 1) + accuracy) / total
        )
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de validation"""
        return self.validation_stats.copy()
