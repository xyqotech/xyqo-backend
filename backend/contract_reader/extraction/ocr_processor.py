"""
Processeur OCR avec Tesseract pour PDFs non-extractibles
Fallback robuste avec détection de layout et positions
"""

import io
import os
import time
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from PIL import Image
import pytesseract
from pdf2image import convert_from_bytes
from .pdf_extractor import TextElement, ExtractedPage

@dataclass
class OCRConfig:
    """Configuration OCR"""
    language: str = "fra+eng"  # Français + Anglais
    dpi: int = 300
    psm: int = 6  # Page Segmentation Mode: uniform block of text
    oem: int = 3  # OCR Engine Mode: default
    confidence_threshold: int = 30  # Seuil de confiance minimum

class OCRProcessor:
    """Processeur OCR avec Tesseract"""
    
    def __init__(self, config: OCRConfig = None):
        self.config = config or OCRConfig()
        self.ocr_stats = {
            "total_pages_processed": 0,
            "avg_confidence": 0,
            "avg_time_per_page_ms": 0,
            "successful_extractions": 0
        }
        
        # Vérifier que Tesseract est installé
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            raise Exception("Tesseract OCR n'est pas installé. Installer avec: brew install tesseract")
    
    def extract_with_ocr(self, pdf_bytes: bytes) -> Tuple[List[ExtractedPage], Dict[str, Any]]:
        """
        Extraction OCR complète d'un PDF
        Convertit PDF → images → OCR avec positions
        """
        start_time = time.time()
        
        try:
            # Convertir PDF en images
            images = convert_from_bytes(pdf_bytes, dpi=self.config.dpi)
            
            pages = []
            total_confidence = 0
            successful_pages = 0
            
            for page_num, image in enumerate(images, 1):
                try:
                    page_data = self._process_page_ocr(image, page_num)
                    pages.append(page_data)
                    
                    # Calculer confiance moyenne de la page
                    page_confidence = self._calculate_page_confidence(page_data.elements)
                    total_confidence += page_confidence
                    successful_pages += 1
                    
                except Exception as e:
                    print(f"Erreur OCR page {page_num}: {e}")
                    # Créer une page vide en cas d'erreur
                    pages.append(ExtractedPage(
                        page_number=page_num,
                        text="",
                        elements=[],
                        width=image.width,
                        height=image.height,
                        extraction_method="ocr_failed"
                    ))
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Mettre à jour les statistiques
            self.ocr_stats["total_pages_processed"] += len(images)
            self.ocr_stats["successful_extractions"] += successful_pages
            
            if successful_pages > 0:
                avg_confidence = total_confidence / successful_pages
                self.ocr_stats["avg_confidence"] = (
                    (self.ocr_stats["avg_confidence"] * (self.ocr_stats["total_pages_processed"] - len(images)) + avg_confidence * len(images))
                    / self.ocr_stats["total_pages_processed"]
                )
            
            self.ocr_stats["avg_time_per_page_ms"] = processing_time // len(images)
            
            stats = {
                "extraction_time_ms": processing_time,
                "method_used": "tesseract_ocr",
                "pages_processed": len(images),
                "successful_pages": successful_pages,
                "avg_confidence": total_confidence / max(successful_pages, 1),
                "total_text_length": sum(len(p.text) for p in pages)
            }
            
            return pages, stats
            
        except Exception as e:
            raise Exception(f"Erreur OCR: {str(e)}")
    
    def _process_page_ocr(self, image: Image.Image, page_num: int) -> ExtractedPage:
        """Traite une page avec OCR et extraction des positions"""
        
        # Configuration Tesseract
        custom_config = f'--oem {self.config.oem} --psm {self.config.psm} -l {self.config.language}'
        
        # Extraire le texte complet
        page_text = pytesseract.image_to_string(image, config=custom_config)
        
        # Extraire les données détaillées avec positions
        data = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
        
        elements = []
        current_line = []
        current_line_top = None
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            confidence = int(data['conf'][i])
            
            # Ignorer les éléments avec faible confiance ou vides
            if confidence < self.config.confidence_threshold or not text:
                continue
            
            x = data['left'][i]
            y = data['top'][i]
            width = data['width'][i]
            height = data['height'][i]
            
            # Grouper les mots sur la même ligne
            if current_line_top is None or abs(y - current_line_top) < 10:
                current_line.append({
                    'text': text,
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height,
                    'confidence': confidence
                })
                current_line_top = y
            else:
                # Nouvelle ligne, traiter la ligne précédente
                if current_line:
                    line_element = self._merge_line_elements(current_line, page_num)
                    if line_element:
                        elements.append(line_element)
                
                # Commencer nouvelle ligne
                current_line = [{
                    'text': text,
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': height,
                    'confidence': confidence
                }]
                current_line_top = y
        
        # Traiter la dernière ligne
        if current_line:
            line_element = self._merge_line_elements(current_line, page_num)
            if line_element:
                elements.append(line_element)
        
        return ExtractedPage(
            page_number=page_num,
            text=page_text,
            elements=elements,
            width=image.width,
            height=image.height,
            extraction_method="tesseract_ocr"
        )
    
    def _merge_line_elements(self, line_words: List[Dict], page_num: int) -> Optional[TextElement]:
        """Fusionne les mots d'une ligne en un élément de texte"""
        if not line_words:
            return None
        
        # Combiner le texte
        text = " ".join(word['text'] for word in line_words)
        
        # Calculer la boîte englobante
        min_x = min(word['x'] for word in line_words)
        min_y = min(word['y'] for word in line_words)
        max_x = max(word['x'] + word['width'] for word in line_words)
        max_y = max(word['y'] + word['height'] for word in line_words)
        
        # Confiance moyenne
        avg_confidence = sum(word['confidence'] for word in line_words) / len(line_words)
        
        return TextElement(
            text=text,
            page=page_num,
            x=min_x,
            y=min_y,
            width=max_x - min_x,
            height=max_y - min_y,
            font_size=max_y - min_y,  # Approximation basée sur la hauteur
            font_name=f"ocr_confidence_{int(avg_confidence)}"
        )
    
    def _calculate_page_confidence(self, elements: List[TextElement]) -> float:
        """Calcule la confiance moyenne d'une page"""
        if not elements:
            return 0
        
        confidences = []
        for element in elements:
            if element.font_name and "ocr_confidence_" in element.font_name:
                try:
                    conf = int(element.font_name.split("_")[-1])
                    confidences.append(conf)
                except:
                    pass
        
        return sum(confidences) / len(confidences) if confidences else 0
    
    def enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Améliore l'image pour un meilleur OCR"""
        # Convertir en niveaux de gris
        if image.mode != 'L':
            image = image.convert('L')
        
        # Redimensionner si trop petit
        width, height = image.size
        if width < 1000:
            scale_factor = 1000 / width
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def get_ocr_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques OCR"""
        return self.ocr_stats.copy()
