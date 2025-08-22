"""
Extracteur PDF robuste avec repères de position
Support PyPDF2 + pdfplumber pour extraction optimale
"""

import io
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from PyPDF2 import PdfReader
import pdfplumber

@dataclass
class TextElement:
    """Élément de texte avec position"""
    text: str
    page: int
    x: float
    y: float
    width: float
    height: float
    font_size: Optional[float] = None
    font_name: Optional[str] = None

@dataclass
class ExtractedPage:
    """Page extraite avec métadonnées"""
    page_number: int
    text: str
    elements: List[TextElement]
    width: float
    height: float
    extraction_method: str  # "pypdf2" ou "pdfplumber"

class PDFExtractor:
    """Extracteur PDF avec fallback et repères de position"""
    
    def __init__(self):
        self.extraction_stats = {
            "total_extractions": 0,
            "pypdf2_success": 0,
            "pdfplumber_success": 0,
            "ocr_fallback": 0,
            "avg_time_ms": 0
        }
    
    def extract_text_with_positions(self, pdf_bytes: bytes) -> Tuple[List[ExtractedPage], Dict[str, Any]]:
        """
        Extraction principale avec repères de position
        Essaie PyPDF2 puis pdfplumber si nécessaire
        """
        start_time = time.time()
        
        try:
            # Méthode 1: pdfplumber (plus précis pour les positions)
            pages = self._extract_with_pdfplumber(pdf_bytes)
            method = "pdfplumber"
            self.extraction_stats["pdfplumber_success"] += 1
            
        except Exception as e1:
            try:
                # Méthode 2: PyPDF2 (fallback)
                pages = self._extract_with_pypdf2(pdf_bytes)
                method = "pypdf2"
                self.extraction_stats["pypdf2_success"] += 1
                
            except Exception as e2:
                # Méthode 3: OCR sera appelé par OCRProcessor
                raise Exception(f"Extraction PDF échouée - PyPDF2: {e1}, pdfplumber: {e2}")
        
        extraction_time = int((time.time() - start_time) * 1000)
        
        # Statistiques
        self.extraction_stats["total_extractions"] += 1
        self.extraction_stats["avg_time_ms"] = (
            (self.extraction_stats["avg_time_ms"] * (self.extraction_stats["total_extractions"] - 1) + extraction_time)
            / self.extraction_stats["total_extractions"]
        )
        
        stats = {
            "extraction_time_ms": extraction_time,
            "method_used": method,
            "pages_extracted": len(pages),
            "total_text_length": sum(len(p.text) for p in pages),
            "elements_found": sum(len(p.elements) for p in pages)
        }
        
        return pages, stats
    
    def _extract_with_pdfplumber(self, pdf_bytes: bytes) -> List[ExtractedPage]:
        """Extraction avec pdfplumber (positions précises)"""
        pages = []
        
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Extraire le texte complet
                page_text = page.extract_text() or ""
                
                # Extraire les éléments avec positions
                elements = []
                chars = page.chars
                
                # Grouper les caractères en mots/phrases
                current_word = ""
                word_chars = []
                
                for char in chars:
                    if char.get('text', '').strip():
                        current_word += char['text']
                        word_chars.append(char)
                    else:
                        if current_word.strip():
                            # Créer un élément pour le mot
                            if word_chars:
                                x = min(c['x0'] for c in word_chars)
                                y = min(c['top'] for c in word_chars)
                                width = max(c['x1'] for c in word_chars) - x
                                height = max(c['bottom'] for c in word_chars) - y
                                
                                elements.append(TextElement(
                                    text=current_word.strip(),
                                    page=page_num,
                                    x=x,
                                    y=y,
                                    width=width,
                                    height=height,
                                    font_size=word_chars[0].get('size'),
                                    font_name=word_chars[0].get('fontname')
                                ))
                        
                        current_word = ""
                        word_chars = []
                
                # Dernier mot de la page
                if current_word.strip() and word_chars:
                    x = min(c['x0'] for c in word_chars)
                    y = min(c['top'] for c in word_chars)
                    width = max(c['x1'] for c in word_chars) - x
                    height = max(c['bottom'] for c in word_chars) - y
                    
                    elements.append(TextElement(
                        text=current_word.strip(),
                        page=page_num,
                        x=x,
                        y=y,
                        width=width,
                        height=height,
                        font_size=word_chars[0].get('size'),
                        font_name=word_chars[0].get('fontname')
                    ))
                
                pages.append(ExtractedPage(
                    page_number=page_num,
                    text=page_text,
                    elements=elements,
                    width=page.width,
                    height=page.height,
                    extraction_method="pdfplumber"
                ))
        
        return pages
    
    def _extract_with_pypdf2(self, pdf_bytes: bytes) -> List[ExtractedPage]:
        """Extraction avec PyPDF2 (fallback, positions approximatives)"""
        pages = []
        
        pdf_file = io.BytesIO(pdf_bytes)
        reader = PdfReader(pdf_file)
        
        for page_num, page in enumerate(reader.pages, 1):
            page_text = page.extract_text()
            
            # PyPDF2 ne donne pas les positions exactes
            # On crée des éléments approximatifs
            elements = []
            lines = page_text.split('\n')
            y_pos = 700  # Position Y approximative (haut de page)
            
            for line in lines:
                if line.strip():
                    elements.append(TextElement(
                        text=line.strip(),
                        page=page_num,
                        x=50,  # Marge gauche approximative
                        y=y_pos,
                        width=500,  # Largeur approximative
                        height=12,  # Hauteur ligne approximative
                        font_size=12
                    ))
                    y_pos -= 15  # Espacement entre lignes
            
            # Dimensions de page approximatives
            mediabox = page.mediabox
            width = float(mediabox.width) if mediabox.width else 595
            height = float(mediabox.height) if mediabox.height else 842
            
            pages.append(ExtractedPage(
                page_number=page_num,
                text=page_text,
                elements=elements,
                width=width,
                height=height,
                extraction_method="pypdf2"
            ))
        
        return pages
    
    def find_text_position(self, pages: List[ExtractedPage], search_text: str) -> Optional[TextElement]:
        """Trouve la position d'un texte spécifique"""
        search_text = search_text.lower().strip()
        
        for page in pages:
            for element in page.elements:
                if search_text in element.text.lower():
                    return element
        
        return None
    
    def get_page_sections(self, page: ExtractedPage) -> Dict[str, List[TextElement]]:
        """Divise une page en sections logiques basées sur la position"""
        sections = {
            "header": [],
            "body": [],
            "footer": []
        }
        
        # Seuils basés sur la hauteur de page
        header_threshold = page.height * 0.85  # 15% du haut
        footer_threshold = page.height * 0.15  # 15% du bas
        
        for element in page.elements:
            if element.y >= header_threshold:
                sections["header"].append(element)
            elif element.y <= footer_threshold:
                sections["footer"].append(element)
            else:
                sections["body"].append(element)
        
        return sections
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques d'extraction"""
        return self.extraction_stats.copy()
