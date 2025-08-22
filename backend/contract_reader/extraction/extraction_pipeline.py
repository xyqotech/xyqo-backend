"""
Pipeline d'extraction unifié pour Contract Reader
Orchestration PDF → OCR → Processing avec métriques
"""

import time
from typing import List, Dict, Any, Tuple
from .pdf_extractor import PDFExtractor, ExtractedPage
from .ocr_processor import OCRProcessor, OCRConfig
from .text_processor import TextProcessor, ProcessedDocument

class ExtractionPipeline:
    """Pipeline d'extraction unifié avec fallbacks"""
    
    def __init__(self):
        self.pdf_extractor = PDFExtractor()
        self.ocr_processor = OCRProcessor()
        self.text_processor = TextProcessor()
        
        self.pipeline_stats = {
            "total_extractions": 0,
            "pdf_success_rate": 0,
            "ocr_fallback_rate": 0,
            "avg_total_time_ms": 0,
            "p95_time_ms": 0,
            "recent_times": []  # Pour calculer p95
        }
    
    async def extract_contract_data(self, pdf_bytes: bytes, filename: str = "contract.pdf") -> Dict[str, Any]:
        """Extraction complète des données de contrat avec métriques"""
        start_time = time.time()
        
        try:
            # FORCE REAL PDF EXTRACTION - Pas de simulation
            if not pdf_bytes.startswith(b'%PDF'):
                return {
                    'success': False,
                    'error': 'Invalid PDF format - real PDF required',
                    'extracted_text': '',
                    'metadata': {}
                }
            
            # Extraction du document réel
            processed_doc, metrics = self.extract_document(pdf_bytes)
            
            # Conversion en format Contract Reader
            contract_data = {
                "text_content": processed_doc.full_text,
                "pages": len(processed_doc.pages),
                "extraction_method": processed_doc.extraction_method,
                "confidence_score": processed_doc.confidence_score,
                "word_count": len(processed_doc.full_text.split()),
                "processing_time_ms": int((time.time() - start_time) * 1000),
                "filename": filename,
                "metadata": {
                    "pdf_readable": metrics.get("pdf_success", False),
                    "ocr_used": metrics.get("ocr_used", False),
                    "extraction_quality": processed_doc.confidence_score
                }
            }
            
            return {
                'success': True,
                'extracted_text': contract_data['text_content'],
                'metadata': contract_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'extracted_text': '',
                'metadata': {
                    "error": str(e),
                    "text_content": "",
                    "pages": 0,
                    "extraction_method": "failed",
                    "confidence_score": 0.0,
                    "processing_time_ms": int((time.time() - start_time) * 1000),
                    "filename": filename
                }
            }

    def extract_document(self, pdf_bytes: bytes) -> Tuple[ProcessedDocument, Dict[str, Any]]:
        """
        Pipeline complet d'extraction
        PDF → OCR (si nécessaire) → Processing → Faits structurés
        """
        start_time = time.time()
        extraction_method = "unknown"
        pages = []
        extraction_stats = {}
        
        try:
            # Étape 1: Extraction PDF standard
            pages, extraction_stats = self.pdf_extractor.extract_text_with_positions(pdf_bytes)
            extraction_method = extraction_stats["method_used"]
            
            # Vérifier la qualité de l'extraction
            total_text = sum(len(p.text) for p in pages)
            if total_text < 100:  # Très peu de texte extrait
                raise Exception("Extraction PDF insuffisante, fallback OCR nécessaire")
                
        except Exception as e:
            # Étape 2: Fallback OCR
            try:
                pages, extraction_stats = self.ocr_processor.extract_with_ocr(pdf_bytes)
                extraction_method = "ocr_fallback"
                self.pipeline_stats["ocr_fallback_rate"] += 1
                
            except Exception as ocr_error:
                raise Exception(f"Extraction complètement échouée - PDF: {e}, OCR: {ocr_error}")
        
        # Étape 3: Traitement du texte
        processed_doc = self.text_processor.process_document(pages)
        
        total_time = int((time.time() - start_time) * 1000)
        
        # Mettre à jour les statistiques
        self._update_pipeline_stats(total_time, extraction_method)
        
        # Statistiques complètes
        complete_stats = {
            "extraction_method": extraction_method,
            "total_time_ms": total_time,
            "extraction_time_ms": extraction_stats.get("extraction_time_ms", 0),
            "processing_time_ms": processed_doc.processing_stats.get("processing_time_ms", 0),
            "pages_processed": len(pages),
            "text_length": len(processed_doc.cleaned_text),
            "facts_extracted": sum(len(facts) for facts in processed_doc.facts.values()),
            "sections_found": len(processed_doc.sections),
            "quality_score": self._calculate_quality_score(processed_doc),
            "meets_p95_target": total_time <= 3000  # DoD: p95 ≤ 3s
        }
        
        return processed_doc, complete_stats
    
    def _update_pipeline_stats(self, processing_time: int, method: str):
        """Met à jour les statistiques du pipeline"""
        self.pipeline_stats["total_extractions"] += 1
        
        # Taux de succès PDF
        if method in ["pypdf2", "pdfplumber"]:
            self.pipeline_stats["pdf_success_rate"] = (
                (self.pipeline_stats["pdf_success_rate"] * (self.pipeline_stats["total_extractions"] - 1) + 1)
                / self.pipeline_stats["total_extractions"]
            )
        
        # Temps moyen
        self.pipeline_stats["avg_total_time_ms"] = (
            (self.pipeline_stats["avg_total_time_ms"] * (self.pipeline_stats["total_extractions"] - 1) + processing_time)
            / self.pipeline_stats["total_extractions"]
        )
        
        # P95 (garde les 100 derniers temps)
        self.pipeline_stats["recent_times"].append(processing_time)
        if len(self.pipeline_stats["recent_times"]) > 100:
            self.pipeline_stats["recent_times"].pop(0)
        
        # Calculer P95
        if len(self.pipeline_stats["recent_times"]) >= 5:
            sorted_times = sorted(self.pipeline_stats["recent_times"])
            p95_index = int(len(sorted_times) * 0.95)
            self.pipeline_stats["p95_time_ms"] = sorted_times[p95_index]
    
    def _calculate_quality_score(self, doc: ProcessedDocument) -> float:
        """Calcule un score de qualité de l'extraction (0-1)"""
        score = 0.0
        
        # Longueur du texte (plus = mieux, jusqu'à un point)
        text_length = len(doc.cleaned_text)
        if text_length > 1000:
            score += 0.3
        elif text_length > 500:
            score += 0.2
        elif text_length > 100:
            score += 0.1
        
        # Nombre de faits extraits
        total_facts = sum(len(facts) for facts in doc.facts.values())
        if total_facts >= 10:
            score += 0.3
        elif total_facts >= 5:
            score += 0.2
        elif total_facts >= 1:
            score += 0.1
        
        # Sections identifiées
        if len(doc.sections) >= 5:
            score += 0.2
        elif len(doc.sections) >= 3:
            score += 0.15
        elif len(doc.sections) >= 1:
            score += 0.1
        
        # Qualité des pages (positions disponibles)
        pages_with_positions = sum(1 for page in doc.pages if page.elements)
        if pages_with_positions == len(doc.pages):
            score += 0.2
        elif pages_with_positions > 0:
            score += 0.1
        
        return min(1.0, score)
    
    def validate_extraction_quality(self, doc: ProcessedDocument) -> Dict[str, Any]:
        """Valide la qualité de l'extraction selon les DoD"""
        validation = {
            "meets_requirements": True,
            "issues": [],
            "quality_score": self._calculate_quality_score(doc),
            "text_extractable": len(doc.cleaned_text) > 50,
            "facts_found": sum(len(facts) for facts in doc.facts.values()) > 0,
            "positions_available": any(page.elements for page in doc.pages)
        }
        
        # Vérifications DoD
        if len(doc.cleaned_text) < 50:
            validation["meets_requirements"] = False
            validation["issues"].append("Texte extrait insuffisant (<50 caractères)")
        
        if not any(page.elements for page in doc.pages):
            validation["meets_requirements"] = False
            validation["issues"].append("Aucune position de texte disponible")
        
        if validation["quality_score"] < 0.3:
            validation["meets_requirements"] = False
            validation["issues"].append(f"Score de qualité trop bas: {validation['quality_score']:.2f}")
        
        return validation
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Rapport de performance du pipeline"""
        return {
            "pipeline_stats": self.pipeline_stats.copy(),
            "pdf_extractor_stats": self.pdf_extractor.get_extraction_stats(),
            "ocr_processor_stats": self.ocr_processor.get_ocr_stats(),
            "text_processor_stats": self.text_processor.get_processing_stats(),
            "dod_compliance": {
                "p95_under_3s": self.pipeline_stats["p95_time_ms"] <= 3000,
                "pdf_success_rate": self.pipeline_stats["pdf_success_rate"],
                "total_extractions": self.pipeline_stats["total_extractions"]
            }
        }
