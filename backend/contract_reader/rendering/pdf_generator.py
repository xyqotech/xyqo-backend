"""
Générateur PDF avec WeasyPrint
Rendu HTML vers PDF optimisé pour impression
"""

import os
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
import weasyprint
from weasyprint import HTML, CSS
from datetime import datetime, timedelta
import hashlib
import logging

from .html_templates import HTMLTemplates
from ..models import ContractSummary
from ..cache.redis_client import RedisClient

logger = logging.getLogger(__name__)

class PDFGenerator:
    """Générateur PDF avec cache et optimisations"""
    
    def __init__(self, redis_client: RedisClient):
        self.redis_client = redis_client
        self.temp_dir = Path(tempfile.gettempdir()) / "contract_reader_pdfs"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Configuration WeasyPrint
        self.pdf_options = {
            'presentational_hints': True,
            'optimize_images': True,
            'pdf_version': '1.7',
            'pdf_forms': False
        }
    
    async def generate_summary_pdf(self, 
                                 summary: ContractSummary,
                                 citations: Dict[str, str] = None,
                                 validation_notes: List[str] = None,
                                 include_watermark: bool = False) -> bytes:
        """
        Génère un PDF du résumé avec citations
        
        Args:
            summary: Résumé structuré
            citations: Citations avec positions
            validation_notes: Notes de validation
            include_watermark: Ajouter filigrane (version démo)
            
        Returns:
            bytes: PDF généré
        """
        try:
            start_time = datetime.now()
            
            # Génération HTML
            html_content = HTMLTemplates.generate_summary_html(
                summary=summary,
                citations=citations or {},
                validation_notes=validation_notes or []
            )
            
            # Ajout filigrane si nécessaire
            if include_watermark:
                html_content = self._add_watermark(html_content)
            
            # Cache key basé sur le contenu
            cache_key = self._generate_pdf_cache_key(html_content)
            
            # Vérification cache
            cached_pdf = await self.redis_client.get_cached_pdf(cache_key)
            if cached_pdf:
                logger.info(f"PDF trouvé en cache: {cache_key[:12]}...")
                return cached_pdf
            
            # Génération PDF
            pdf_bytes = await self._render_html_to_pdf(html_content)
            
            # Mise en cache (TTL 1h pour PDFs)
            await self.redis_client.cache_pdf(cache_key, pdf_bytes, ttl=3600)
            
            # Métriques
            generation_time = (datetime.now() - start_time).total_seconds()
            await self._record_pdf_metrics(
                cache_key=cache_key,
                generation_time=generation_time,
                pdf_size=len(pdf_bytes),
                cache_hit=False
            )
            
            logger.info(f"PDF généré en {generation_time:.2f}s, taille: {len(pdf_bytes)} bytes")
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Erreur génération PDF: {e}")
            raise
    
    async def _render_html_to_pdf(self, html_content: str) -> bytes:
        """Rendu HTML vers PDF avec WeasyPrint"""
        try:
            # CSS personnalisé pour PDF
            pdf_css = CSS(string="""
                @page {
                    size: A4;
                    margin: 2cm;
                    @top-center {
                        content: "Résumé de Contrat - AUTOPILOT";
                        font-size: 10px;
                        color: #6b7280;
                    }
                    @bottom-center {
                        content: "Page " counter(page) " sur " counter(pages);
                        font-size: 10px;
                        color: #6b7280;
                    }
                }
                
                .page-break {
                    page-break-before: always;
                }
                
                .no-break {
                    page-break-inside: avoid;
                }
                
                h1, h2, h3 {
                    page-break-after: avoid;
                }
                
                .section {
                    page-break-inside: avoid;
                }
                
                .clause {
                    page-break-inside: avoid;
                }
            """)
            
            # Création document HTML
            html_doc = HTML(string=html_content)
            
            # Rendu PDF
            pdf_bytes = html_doc.write_pdf(
                stylesheets=[pdf_css],
                **self.pdf_options
            )
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f"Erreur rendu WeasyPrint: {e}")
            raise
    
    def _add_watermark(self, html_content: str) -> str:
        """Ajoute un filigrane version démo"""
        watermark_css = """
        <style>
        .watermark {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: 72px;
            color: rgba(59, 130, 246, 0.1);
            font-weight: bold;
            z-index: -1;
            pointer-events: none;
        }
        </style>
        """
        
        watermark_html = '<div class="watermark">VERSION DÉMO</div>'
        
        # Insertion après <body>
        html_content = html_content.replace(
            '<body>',
            f'<body>{watermark_css}{watermark_html}'
        )
        
        return html_content
    
    def _generate_pdf_cache_key(self, html_content: str) -> str:
        """Génère clé cache pour PDF"""
        content_hash = hashlib.sha256(html_content.encode()).hexdigest()
        return f"pdf:{content_hash[:16]}"
    
    async def _record_pdf_metrics(self, 
                                cache_key: str,
                                generation_time: float,
                                pdf_size: int,
                                cache_hit: bool):
        """Enregistre métriques PDF"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cache_key': cache_key,
                'generation_time': generation_time,
                'pdf_size': pdf_size,
                'cache_hit': cache_hit
            }
            
            # Stockage métriques Redis
            await self.redis_client.redis.lpush(
                "contract_reader:pdf_metrics",
                str(metrics)
            )
            
            # Limite à 1000 entrées
            await self.redis_client.redis.ltrim(
                "contract_reader:pdf_metrics",
                0, 999
            )
            
        except Exception as e:
            logger.warning(f"Erreur enregistrement métriques PDF: {e}")
    
    async def get_pdf_stats(self) -> Dict[str, Any]:
        """Statistiques génération PDF"""
        try:
            # Métriques récentes
            metrics_raw = await self.redis_client.redis.lrange(
                "contract_reader:pdf_metrics", 0, 99
            )
            
            if not metrics_raw:
                return {
                    'total_generated': 0,
                    'cache_hit_rate': 0.0,
                    'avg_generation_time': 0.0,
                    'avg_pdf_size': 0
                }
            
            # Parsing métriques
            metrics = []
            for metric_str in metrics_raw:
                try:
                    metric = eval(metric_str.decode())
                    metrics.append(metric)
                except:
                    continue
            
            if not metrics:
                return {
                    'total_generated': 0,
                    'cache_hit_rate': 0.0,
                    'avg_generation_time': 0.0,
                    'avg_pdf_size': 0
                }
            
            # Calculs
            total = len(metrics)
            cache_hits = sum(1 for m in metrics if m.get('cache_hit', False))
            cache_hit_rate = cache_hits / total if total > 0 else 0.0
            
            generation_times = [m.get('generation_time', 0) for m in metrics if not m.get('cache_hit', False)]
            avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else 0.0
            
            pdf_sizes = [m.get('pdf_size', 0) for m in metrics]
            avg_pdf_size = sum(pdf_sizes) / len(pdf_sizes) if pdf_sizes else 0
            
            return {
                'total_generated': total,
                'cache_hit_rate': cache_hit_rate,
                'avg_generation_time': avg_generation_time,
                'avg_pdf_size': int(avg_pdf_size)
            }
            
        except Exception as e:
            logger.error(f"Erreur stats PDF: {e}")
            return {
                'total_generated': 0,
                'cache_hit_rate': 0.0,
                'avg_generation_time': 0.0,
                'avg_pdf_size': 0
            }
    
    async def cleanup_temp_files(self, max_age_hours: int = 24):
        """Nettoyage fichiers temporaires"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for file_path in self.temp_dir.glob("*.pdf"):
                if file_path.stat().st_mtime < cutoff_time.timestamp():
                    file_path.unlink()
                    logger.debug(f"Fichier temporaire supprimé: {file_path.name}")
                    
        except Exception as e:
            logger.warning(f"Erreur nettoyage fichiers temporaires: {e}")


# Extension Redis pour cache PDF
class RedisClient:
    """Extension pour cache PDF"""
    
    async def get_cached_pdf(self, cache_key: str) -> Optional[bytes]:
        """Récupère PDF du cache"""
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return cached
            return None
        except Exception as e:
            logger.warning(f"Erreur récupération PDF cache: {e}")
            return None
    
    async def cache_pdf(self, cache_key: str, pdf_bytes: bytes, ttl: int = 3600):
        """Met en cache un PDF"""
        try:
            await self.redis.setex(cache_key, ttl, pdf_bytes)
        except Exception as e:
            logger.warning(f"Erreur mise en cache PDF: {e}")
