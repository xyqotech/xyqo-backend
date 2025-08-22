"""
Processeur de texte pour normalisation et structuration
Nettoyage, segmentation et préparation pour l'IA
"""

import re
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from .pdf_extractor import ExtractedPage, TextElement

@dataclass
class ProcessedDocument:
    """Document traité et structuré"""
    raw_text: str
    cleaned_text: str
    sections: Dict[str, str]
    facts: Dict[str, List[str]]
    pages: List[ExtractedPage]
    processing_stats: Dict[str, Any]
    
    @property
    def full_text(self) -> str:
        """Texte complet du document"""
        return self.cleaned_text or self.raw_text
    
    @property
    def extraction_method(self) -> str:
        """Méthode d'extraction utilisée"""
        return self.processing_stats.get('extraction_method', 'text_processing')
    
    @property
    def confidence_score(self) -> float:
        """Score de confiance de l'extraction"""
        return self.processing_stats.get('confidence_score', 0.8)

class TextProcessor:
    """Processeur de texte pour normalisation et extraction de faits"""
    
    def __init__(self):
        self.processing_stats = {
            "documents_processed": 0,
            "avg_processing_time_ms": 0,
            "facts_extracted_total": 0
        }
        
        # Patterns regex pour extraction de faits
        self.fact_patterns = {
            "dates": [
                r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b',  # DD/MM/YYYY
                r'\b\d{1,2}\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b',
                r'\b(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{1,2},?\s+\d{4}\b'
            ],
            "amounts": [
                r'\b\d{1,3}(?:\s?\d{3})*(?:[,\.]\d{2})?\s*(?:€|EUR|euros?)\b',
                r'\b(?:€|EUR)\s*\d{1,3}(?:\s?\d{3})*(?:[,\.]\d{2})?\b',
                r'\b\d{1,3}(?:\s?\d{3})*(?:[,\.]\d{2})?\s*(?:dollars?|\$)\b'
            ],
            "percentages": [
                r'\b\d{1,3}(?:[,\.]\d{1,2})?\s*%\b'
            ],
            "durations": [
                r'\b\d+\s*(?:an|année|années|mois|semaine|semaines|jour|jours)s?\b',
                r'\b(?:un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)\s+(?:an|année|années|mois)\b'
            ],
            "parties": [
                r'\b(?:Monsieur|Madame|M\.|Mme)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b',
                r'\b[A-Z][A-Z\s&]{2,50}(?:S\.A\.S|SARL|SAS|SA|EURL|SCI)\b',
                r'\b(?:société|entreprise|compagnie)\s+[A-Z][a-zA-Z\s&]{2,50}\b'
            ]
        }
    
    def process_document(self, pages: List[ExtractedPage]) -> ProcessedDocument:
        """Traite un document complet"""
        start_time = time.time()
        
        # Combiner tout le texte
        raw_text = "\n\n".join(f"=== PAGE {p.page_number} ===\n{p.text}" for p in pages)
        
        # Nettoyer le texte
        cleaned_text = self._clean_text(raw_text)
        
        # Segmenter en sections
        sections = self._extract_sections(cleaned_text, pages)
        
        # Extraire les faits
        facts = self._extract_facts(cleaned_text)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Statistiques
        total_facts = sum(len(fact_list) for fact_list in facts.values())
        self.processing_stats["documents_processed"] += 1
        self.processing_stats["facts_extracted_total"] += total_facts
        self.processing_stats["avg_processing_time_ms"] = (
            (self.processing_stats["avg_processing_time_ms"] * (self.processing_stats["documents_processed"] - 1) + processing_time)
            / self.processing_stats["documents_processed"]
        )
        
        stats = {
            "processing_time_ms": processing_time,
            "text_length": len(cleaned_text),
            "sections_found": len(sections),
            "facts_extracted": total_facts,
            "pages_processed": len(pages)
        }
        
        return ProcessedDocument(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            sections=sections,
            facts=facts,
            pages=pages,
            processing_stats=stats
        )
    
    def _clean_text(self, text: str) -> str:
        """Nettoie et normalise le texte"""
        # Supprimer les caractères de contrôle
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normaliser les espaces
        text = re.sub(r'\s+', ' ', text)
        
        # Supprimer les lignes vides multiples
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        
        # Corriger les coupures de mots
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)
        
        # Normaliser la ponctuation
        text = re.sub(r'\s+([,.;:!?])', r'\1', text)
        text = re.sub(r'([,.;:!?])\s*([,.;:!?])', r'\1\2', text)
        
        return text.strip()
    
    def _extract_sections(self, text: str, pages: List[ExtractedPage]) -> Dict[str, str]:
        """Extrait les sections logiques du document"""
        sections = {}
        
        # Patterns pour identifier les sections
        section_patterns = {
            "preambule": r'(?:préambule|considérant|attendu que)',
            "objet": r'(?:objet|article 1|a pour objet)',
            "duree": r'(?:durée|article.*durée|terme)',
            "prix": r'(?:prix|tarif|montant|article.*prix|rémunération)',
            "obligations": r'(?:obligations|engagements|article.*obligations)',
            "resiliation": r'(?:résiliation|fin|terme|article.*résiliation)',
            "responsabilite": r'(?:responsabilité|garantie|article.*responsabilité)',
            "confidentialite": r'(?:confidentialité|secret|article.*confidentialité)',
            "propriete": r'(?:propriété intellectuelle|droits d\'auteur|article.*propriété)',
            "litiges": r'(?:litiges|différends|tribunal|juridiction)',
            "signatures": r'(?:signatures?|fait à|lu et approuvé)'
        }
        
        text_lower = text.lower()
        
        for section_name, pattern in section_patterns.items():
            matches = list(re.finditer(pattern, text_lower, re.IGNORECASE))
            if matches:
                # Prendre le premier match et extraire le contexte
                match = matches[0]
                start_pos = max(0, match.start() - 50)
                end_pos = min(len(text), match.end() + 500)
                
                section_text = text[start_pos:end_pos].strip()
                sections[section_name] = section_text
        
        return sections
    
    def _extract_facts(self, text: str) -> Dict[str, List[str]]:
        """Extrait les faits structurés du texte"""
        facts = {}
        
        for fact_type, patterns in self.fact_patterns.items():
            found_facts = []
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                found_facts.extend(matches)
            
            # Déduplication et nettoyage
            unique_facts = list(set(found_facts))
            facts[fact_type] = [fact.strip() for fact in unique_facts if fact.strip()]
        
        return facts
    
    def find_text_citations(self, search_text: str, pages: List[ExtractedPage]) -> List[Dict[str, Any]]:
        """Trouve les citations d'un texte avec références de page"""
        citations = []
        search_lower = search_text.lower().strip()
        
        for page in pages:
            # Recherche dans le texte de la page
            page_text_lower = page.text.lower()
            if search_lower in page_text_lower:
                # Trouver la position exacte
                start_pos = page_text_lower.find(search_lower)
                end_pos = start_pos + len(search_lower)
                
                # Contexte autour du texte trouvé
                context_start = max(0, start_pos - 100)
                context_end = min(len(page.text), end_pos + 100)
                context = page.text[context_start:context_end].strip()
                
                # Essayer de trouver l'élément correspondant pour la position XY
                matching_element = None
                for element in page.elements:
                    if search_lower in element.text.lower():
                        matching_element = element
                        break
                
                citation = {
                    "page_number": page.page_number,
                    "text_found": page.text[start_pos:end_pos],
                    "context": context,
                    "position": {
                        "x": matching_element.x if matching_element else None,
                        "y": matching_element.y if matching_element else None
                    },
                    "reference": f"p.{page.page_number}"
                }
                
                if matching_element:
                    citation["reference"] += f" (x:{int(matching_element.x)}, y:{int(matching_element.y)})"
                
                citations.append(citation)
        
        return citations
    
    def estimate_reading_time(self, text: str) -> Dict[str, int]:
        """Estime le temps de lecture"""
        word_count = len(text.split())
        
        # Vitesses de lecture moyennes (mots/minute)
        reading_speeds = {
            "slow": 150,
            "average": 250,
            "fast": 400
        }
        
        return {
            "word_count": word_count,
            "slow_reader_minutes": max(1, word_count // reading_speeds["slow"]),
            "average_reader_minutes": max(1, word_count // reading_speeds["average"]),
            "fast_reader_minutes": max(1, word_count // reading_speeds["fast"])
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de traitement"""
        return self.processing_stats.copy()
