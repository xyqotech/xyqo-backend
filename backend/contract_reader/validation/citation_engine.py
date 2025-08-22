"""
Moteur de citations précises avec positions XY
Génère des références "p.X §Y (x:123, y:456)" pour chaque fait
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from ..extraction.pdf_extractor import ExtractedPage, TextElement
from ..models import ContractSummary

@dataclass
class Citation:
    """Citation précise avec position"""
    text: str
    page_number: int
    section_number: Optional[int] = None
    x_position: Optional[float] = None
    y_position: Optional[float] = None
    confidence: float = 1.0
    context: str = ""

@dataclass
class CitationResult:
    """Résultat de citation avec métriques"""
    citations: List[Citation]
    total_facts_checked: int
    citations_found: int
    citation_accuracy: float
    missing_citations: List[str]

class CitationEngine:
    """Moteur de citations avec positions XY précises"""
    
    def __init__(self):
        self.citation_stats = {
            "total_citations_generated": 0,
            "successful_citations": 0,
            "avg_accuracy": 0.0,
            "position_accuracy": 0.0
        }
    
    def generate_citations(self, summary: ContractSummary, pages: List[ExtractedPage]) -> CitationResult:
        """
        Génère des citations précises pour tous les faits du résumé
        """
        all_citations = []
        facts_to_check = []
        missing_citations = []
        
        # Collecter tous les faits à vérifier
        facts_to_check.extend(self._extract_facts_from_summary(summary))
        
        # Générer citations pour chaque fait
        for fact in facts_to_check:
            citation = self._find_citation_for_fact(fact, pages)
            if citation:
                all_citations.append(citation)
            else:
                missing_citations.append(fact)
        
        # Calculer métriques
        total_facts = len(facts_to_check)
        citations_found = len(all_citations)
        accuracy = (citations_found / max(total_facts, 1)) * 100
        
        # Mettre à jour statistiques
        self._update_citation_stats(total_facts, citations_found, accuracy)
        
        return CitationResult(
            citations=all_citations,
            total_facts_checked=total_facts,
            citations_found=citations_found,
            citation_accuracy=accuracy,
            missing_citations=missing_citations
        )
    
    def _extract_facts_from_summary(self, summary: ContractSummary) -> List[str]:
        """Extrait tous les faits vérifiables du résumé"""
        facts = []
        
        # Faits des métadonnées
        if hasattr(summary.meta, 'date_signed') and summary.meta.date_signed:
            facts.append(summary.meta.date_signed)
        
        if hasattr(summary.meta, 'amount') and summary.meta.amount:
            facts.append(summary.meta.amount)
        
        if hasattr(summary.meta, 'duration') and summary.meta.duration:
            facts.append(summary.meta.duration)
        
        if hasattr(summary.meta, 'parties') and summary.meta.parties:
            facts.extend(summary.meta.parties)
        
        # Faits des clauses importantes
        for clause in summary.clauses:
            if clause.importance in ["high", "critical"]:
                # Extraire les faits numériques/dates de la clause
                fact_patterns = [
                    r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b',  # Dates
                    r'\b\d{1,3}(?:\s?\d{3})*(?:[,\.]\d{2})?\s*(?:€|EUR|%)\b',  # Montants/pourcentages
                    r'\b\d+\s*(?:mois|ans?|jours?|semaines?)\b'  # Durées
                ]
                
                for pattern in fact_patterns:
                    matches = re.findall(pattern, clause.text, re.IGNORECASE)
                    facts.extend(matches)
        
        # Nettoyer et déduplication
        facts = [fact.strip() for fact in facts if fact.strip()]
        return list(set(facts))
    
    def _find_citation_for_fact(self, fact: str, pages: List[ExtractedPage]) -> Optional[Citation]:
        """Trouve la citation précise d'un fait dans les pages"""
        fact_lower = fact.lower().strip()
        
        # Stratégies de recherche par ordre de précision
        search_strategies = [
            self._exact_match_search,
            self._fuzzy_match_search,
            self._pattern_match_search
        ]
        
        for strategy in search_strategies:
            citation = strategy(fact, fact_lower, pages)
            if citation:
                return citation
        
        return None
    
    def _exact_match_search(self, fact: str, fact_lower: str, pages: List[ExtractedPage]) -> Optional[Citation]:
        """Recherche exacte dans les éléments avec position"""
        for page in pages:
            for element in page.elements:
                if fact_lower in element.text.lower():
                    section_num = self._detect_section_number(element, page)
                    context = self._get_context_around_element(element, page)
                    
                    return Citation(
                        text=fact,
                        page_number=page.page_number,
                        section_number=section_num,
                        x_position=element.x,
                        y_position=element.y,
                        confidence=1.0,
                        context=context
                    )
        
        return None
    
    def _fuzzy_match_search(self, fact: str, fact_lower: str, pages: List[ExtractedPage]) -> Optional[Citation]:
        """Recherche approximative pour dates/montants avec variations"""
        # Normaliser le fait pour la recherche floue
        normalized_fact = self._normalize_fact_for_search(fact)
        
        for page in pages:
            page_text_lower = page.text.lower()
            
            # Recherche dans le texte de page
            if normalized_fact in page_text_lower:
                # Trouver l'élément le plus proche
                best_element = self._find_closest_element(normalized_fact, page)
                if best_element:
                    section_num = self._detect_section_number(best_element, page)
                    context = self._get_context_around_element(best_element, page)
                    
                    return Citation(
                        text=fact,
                        page_number=page.page_number,
                        section_number=section_num,
                        x_position=best_element.x,
                        y_position=best_element.y,
                        confidence=0.8,
                        context=context
                    )
        
        return None
    
    def _pattern_match_search(self, fact: str, fact_lower: str, pages: List[ExtractedPage]) -> Optional[Citation]:
        """Recherche par pattern pour types spécifiques (dates, montants)"""
        # Déterminer le type de fait
        fact_type = self._classify_fact_type(fact)
        
        if fact_type == "date":
            return self._search_date_pattern(fact, pages)
        elif fact_type == "amount":
            return self._search_amount_pattern(fact, pages)
        elif fact_type == "duration":
            return self._search_duration_pattern(fact, pages)
        
        return None
    
    def _normalize_fact_for_search(self, fact: str) -> str:
        """Normalise un fait pour la recherche floue"""
        # Supprimer espaces multiples
        normalized = re.sub(r'\s+', ' ', fact.strip().lower())
        
        # Normaliser les dates (différents formats)
        date_patterns = [
            (r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', r'\1/\2/\3'),
            (r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})', r'\1 \2 \3')
        ]
        
        for pattern, replacement in date_patterns:
            normalized = re.sub(pattern, replacement, normalized)
        
        return normalized
    
    def _classify_fact_type(self, fact: str) -> str:
        """Classifie le type d'un fait"""
        if re.search(r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b', fact):
            return "date"
        elif re.search(r'\b\d{1,3}(?:\s?\d{3})*(?:[,\.]\d{2})?\s*(?:€|EUR|dollars?|\$)\b', fact):
            return "amount"
        elif re.search(r'\b\d+\s*(?:mois|ans?|jours?|semaines?)\b', fact):
            return "duration"
        elif len(fact.split()) <= 3 and any(char.isupper() for char in fact):
            return "entity"  # Nom propre/entité
        else:
            return "text"
    
    def _search_date_pattern(self, fact: str, pages: List[ExtractedPage]) -> Optional[Citation]:
        """Recherche spécialisée pour les dates"""
        # Extraire les composants de la date
        date_match = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{2,4})', fact)
        if not date_match:
            return None
        
        day, month, year = date_match.groups()
        
        # Rechercher des variations de cette date
        date_patterns = [
            f"{day}/{month}/{year}",
            f"{day}-{month}-{year}",
            f"{day}.{month}.{year}",
            f"{int(day)}/{int(month)}/{year}",  # Sans zéros de tête
        ]
        
        for page in pages:
            for pattern in date_patterns:
                for element in page.elements:
                    if pattern in element.text:
                        return Citation(
                            text=fact,
                            page_number=page.page_number,
                            x_position=element.x,
                            y_position=element.y,
                            confidence=0.9,
                            context=element.text
                        )
        
        return None
    
    def _search_amount_pattern(self, fact: str, pages: List[ExtractedPage]) -> Optional[Citation]:
        """Recherche spécialisée pour les montants"""
        # Extraire le montant numérique
        amount_match = re.search(r'(\d{1,3}(?:\s?\d{3})*(?:[,\.]\d{2})?)', fact)
        if not amount_match:
            return None
        
        amount_num = amount_match.group(1)
        
        for page in pages:
            for element in page.elements:
                if amount_num in element.text and any(currency in element.text for currency in ['€', 'EUR', '$']):
                    return Citation(
                        text=fact,
                        page_number=page.page_number,
                        x_position=element.x,
                        y_position=element.y,
                        confidence=0.9,
                        context=element.text
                    )
        
        return None
    
    def _search_duration_pattern(self, fact: str, pages: List[ExtractedPage]) -> Optional[Citation]:
        """Recherche spécialisée pour les durées"""
        duration_match = re.search(r'(\d+)\s*(mois|ans?|jours?|semaines?)', fact, re.IGNORECASE)
        if not duration_match:
            return None
        
        number, unit = duration_match.groups()
        
        for page in pages:
            for element in page.elements:
                if number in element.text and unit.lower() in element.text.lower():
                    return Citation(
                        text=fact,
                        page_number=page.page_number,
                        x_position=element.x,
                        y_position=element.y,
                        confidence=0.85,
                        context=element.text
                    )
        
        return None
    
    def _detect_section_number(self, element: TextElement, page: ExtractedPage) -> Optional[int]:
        """Détecte le numéro de section basé sur la position"""
        # Rechercher des patterns de section dans le contexte
        context_elements = [e for e in page.elements if abs(e.y - element.y) < 50]  # Même zone
        
        for ctx_element in context_elements:
            section_match = re.search(r'(?:article|section|§)\s*(\d+)', ctx_element.text, re.IGNORECASE)
            if section_match:
                return int(section_match.group(1))
        
        return None
    
    def _find_closest_element(self, text: str, page: ExtractedPage) -> Optional[TextElement]:
        """Trouve l'élément le plus proche contenant le texte"""
        candidates = [e for e in page.elements if text in e.text.lower()]
        
        if not candidates:
            return None
        
        # Retourner le premier (ou implémenter une logique de proximité plus sophistiquée)
        return candidates[0]
    
    def _get_context_around_element(self, element: TextElement, page: ExtractedPage, radius: int = 100) -> str:
        """Récupère le contexte autour d'un élément"""
        nearby_elements = [
            e for e in page.elements 
            if abs(e.x - element.x) < radius and abs(e.y - element.y) < 30
        ]
        
        # Trier par position pour reconstituer le texte
        nearby_elements.sort(key=lambda e: (e.y, e.x))
        
        context_texts = [e.text for e in nearby_elements]
        return " ".join(context_texts)[:200]  # Limiter à 200 caractères
    
    def format_citation_reference(self, citation: Citation) -> str:
        """Formate une référence de citation"""
        ref = f"p.{citation.page_number}"
        
        if citation.section_number:
            ref += f" §{citation.section_number}"
        
        if citation.x_position is not None and citation.y_position is not None:
            ref += f" (x:{int(citation.x_position)}, y:{int(citation.y_position)})"
        
        return ref
    
    def _update_citation_stats(self, total_facts: int, citations_found: int, accuracy: float):
        """Met à jour les statistiques de citation"""
        self.citation_stats["total_citations_generated"] += total_facts
        self.citation_stats["successful_citations"] += citations_found
        
        # Moyenne mobile de l'exactitude
        if self.citation_stats["total_citations_generated"] > 0:
            self.citation_stats["avg_accuracy"] = (
                self.citation_stats["successful_citations"] / 
                self.citation_stats["total_citations_generated"]
            ) * 100
    
    def get_citation_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de citation"""
        return self.citation_stats.copy()
