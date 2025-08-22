"""
Module d'extraction de texte pour Contract Reader
Extraction PDF robuste + OCR fallback + repères de position
"""

from .pdf_extractor import PDFExtractor
from .ocr_processor import OCRProcessor
from .text_processor import TextProcessor

__all__ = ["PDFExtractor", "OCRProcessor", "TextProcessor"]
