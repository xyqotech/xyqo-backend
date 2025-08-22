"""
Pipeline principal Contract Reader avec intégration complète
Orchestration de toutes les phases : extraction → IA → validation → PDF → GDPR
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import hashlib
import logging

from .cache.redis_client import RedisClient
from .cache.budget_control import BudgetControl
from .cache.metrics import MetricsCollector
from .extraction.extraction_pipeline import ExtractionPipeline
from .ai.ai_summarizer import AISummarizer
from .validation.cross_validator import CrossValidator
from .validation.validator import validate_contract_summary
from .rendering.pdf_generator import PDFGenerator
from .rendering.storage_manager import StorageManager
from .gdpr.consent_manager import ConsentManager, ConsentType
from .gdpr.data_purge import DataPurgeManager
from .gdpr.audit_logger import AuditLogger, AuditEventType
from .models import ContractSummary, ProcessingMetrics

logger = logging.getLogger(__name__)

class ContractReaderPipeline:
    """Pipeline principal avec toutes les phases intégrées"""
    
    def __init__(self):
        # Initialisation composants
        self.redis_client = RedisClient()
        self.budget_control = BudgetControl(self.redis_client)
        self.metrics = MetricsCollector(self.redis_client)
        
        # Pipelines de traitement
        self.extraction_pipeline = ExtractionPipeline()
        self.ai_summarizer = AISummarizer()
        self.cross_validator = CrossValidator()
        
        # Rendu et stockage
        self.pdf_generator = PDFGenerator(self.redis_client)
        self.storage_manager = StorageManager(self.redis_client)
        
        # GDPR
        self.consent_manager = ConsentManager(self.redis_client)
        self.data_purge = DataPurgeManager(self.redis_client)
        self.audit_logger = AuditLogger(self.redis_client)
    
    async def process_contract_complete(self,
                                      pdf_content: bytes,
                                      filename: str,
                                      user_id: str,
                                      user_ip: str = None,
                                      summary_mode: str = "standard",
                                      include_watermark: bool = False) -> Dict[str, Any]:
        """
        Traitement complet d'un contrat avec toutes les phases
        
        Args:
            pdf_content: Contenu PDF
            filename: Nom du fichier
            user_id: Identifiant utilisateur
            user_ip: IP utilisateur
            summary_mode: Mode de résumé (standard, clauses, red_flags)
            include_watermark: Filigrane version démo
            
        Returns:
            Dict avec résultat complet du traitement
        """
        start_time = datetime.now()
        processing_id = self._generate_processing_id(user_id, filename)
        
        try:
            # 🔐 Phase 0: Vérification consentement GDPR - Configurable
            from .config import contract_reader_config
            
            if contract_reader_config.require_gdpr_consent:
                consent_check = await self.consent_manager.check_consent(
                    user_id=user_id,
                    required_consent=ConsentType.PROCESSING
                )
                
                if not consent_check or not consent_check.get('valid'):
                    await self.audit_logger.log_error_event(
                        user_id=user_id,
                        error_type="consent_required",
                        error_message="Consentement GDPR requis pour traitement"
                    )
                    return {
                        'success': False,
                        'error': 'consent_required',
                        'consent_details': consent_check
                    }
            else:
                logger.info("GDPR consent check disabled by configuration")
            
            # 📊 Phase 1: Vérification budget et quotas
            budget_status = await self.budget_control.check_budget_status(user_ip or user_id)
            
            if not budget_status['can_process']:
                await self.audit_logger.log_error_event(
                    user_id=user_id,
                    error_type="budget_exceeded",
                    error_message=f"Budget ou quota dépassé: {budget_status.get('error', 'Unknown budget error')}"
                )
                return {
                    'success': False,
                    'error': 'budget_exceeded',
                    'budget_status': budget_status
                }
            
            # 🔍 Phase 2: Vérification cache
            document_hash = hashlib.sha256(pdf_content).hexdigest()
            cached_result = await self.redis_client.get_cached_summary(document_hash)
            
            if cached_result:
                await self.metrics.record_cache_hit(document_hash)
                await self.audit_logger.log_data_access(
                    user_id=user_id,
                    accessed_data="cached_summary",
                    access_reason="cache_hit",
                    ip_address=user_ip
                )
                
                # Génération PDF si demandé
                if cached_result.get('generate_pdf', False):
                    pdf_result = await self._generate_and_store_pdf(
                        summary=cached_result['summary'],
                        citations=cached_result.get('citations', {}),
                        validation_notes=cached_result.get('validation_notes', []),
                        filename=filename,
                        user_id=user_id,
                        user_ip=user_ip,
                        include_watermark=include_watermark
                    )
                    cached_result.update(pdf_result)
                
                return {
                    'success': True,
                    'from_cache': True,
                    'processing_id': processing_id,
                    'result': cached_result
                }
            
            await self.metrics.record_cache_miss(document_hash)
            
            # 📄 Phase 3: Extraction locale + OCR
            extraction_start = datetime.now()
            
            await self.audit_logger.log_data_processing(
                user_id=user_id,
                processing_type="pdf_extraction",
                data_categories=["document_content", "metadata"],
                purpose="contract_analysis",
                legal_basis="consent"
            )
            
            extraction_result = await self.extraction_pipeline.extract_contract_data(
                pdf_bytes=pdf_content,
                filename=filename
            )
            
            if extraction_result.get('error'):
                await self.audit_logger.log_error_event(
                    user_id=user_id,
                    error_type="extraction_failed",
                    error_message=extraction_result.get('error', 'Unknown extraction error')
                )
                return {
                    'success': False,
                    'error': 'extraction_failed',
                    'details': extraction_result
                }
            
            extraction_time = (datetime.now() - extraction_start).total_seconds()
            
            # 🤖 Phase 4: Résumé IA ciblé
            ai_start = datetime.now()
            
            await self.audit_logger.log_data_processing(
                user_id=user_id,
                processing_type="ai_summarization",
                data_categories=["extracted_text", "contract_facts"],
                purpose="summary_generation",
                legal_basis="consent"
            )
            
            ai_result = await self.ai_summarizer.generate_summary(
                extracted_text=extraction_result.get('extracted_text', ''),
                filename=filename,
                summary_mode=summary_mode
            )
            
            if not ai_result['success']:
                await self.audit_logger.log_error_event(
                    user_id=user_id,
                    error_type="ai_summarization_failed",
                    error_message=ai_result.get('error', 'Unknown AI error')
                )
                return {
                    'success': False,
                    'error': 'ai_summarization_failed',
                    'details': ai_result
                }
            
            ai_time = (datetime.now() - ai_start).total_seconds()
            
            # ✅ Phase 5: Validation Pydantic UniversalContractV3 + validation croisée
            validation_start = datetime.now()
            
            # Validation Pydantic stricte
            pydantic_valid, validated_model, pydantic_report = validate_contract_summary(ai_result['summary'])
            
            if not pydantic_valid:
                logger.warning(f"Validation Pydantic échouée: {len(pydantic_report.get('errors', []))} erreurs")
                await self.audit_logger.log_error_event(
                    user_id=user_id,
                    error_type="pydantic_validation_failed",
                    error_message=f"Erreurs de schéma: {pydantic_report.get('errors', [])[:3]}"
                )
            
            # Validation croisée traditionnelle
            validation_result = await self.cross_validator.validate_summary_with_citations(
                summary=ai_result['summary'],
                original_data=extraction_result,
                target_accuracy=0.95,
                max_citation_error_rate=0.01
            )
            
            await self.audit_logger.log_validation_performed(
                user_id=user_id,
                validation_type="pydantic_and_cross_validation",
                accuracy_score=validation_result.get('accuracy_score', 0.0),
                citations_count=len(validation_result.get('citations', {}))
            )
            
            validation_time = (datetime.now() - validation_start).total_seconds()
            
            # 📊 Enregistrement coût et métriques
            total_cost = ai_result.get('cost_cents', 0.0) / 100  # Conversion cents -> euros
            tokens_used = ai_result.get('tokens_used', 0)
            await self.budget_control.record_processing_cost(
                user_ip or user_id, 
                total_cost
            )
            
            # 📋 Assemblage résultat complet
            complete_result = {
                'summary': ai_result['summary'],
                'citations': validation_result.get('citations', {}),
                'validation_report': pydantic_report if pydantic_valid else validation_result.get('validation_report', {}),
                'validation_notes': validation_result.get('validation_notes', []),
                'confidence_score': validation_result.get('accuracy_score', 0.0),
                'pydantic_validation': {
                    'is_valid': pydantic_valid,
                    'errors': pydantic_report.get('errors', []),
                    'warnings': pydantic_report.get('warnings', []),
                    'model_version': 'UniversalContractV3'
                },
                'processing_metrics': {
                    'extraction_time': extraction_time,
                    'ai_time': ai_time,
                    'validation_time': validation_time,
                    'total_cost_euros': total_cost,
                    'document_hash': document_hash
                },
                'dod_compliance': {
                    'extraction_p95_under_3s': extraction_time <= 3.0,
                    'cost_under_0_05_euros': total_cost <= 0.05,
                    'accuracy_over_95_percent': validation_result.get('accuracy_score', 0.0) >= 0.95,
                    'citation_error_under_1_percent': validation_result.get('citation_error_rate', 1.0) < 0.01,
                    'pydantic_schema_valid': pydantic_valid
                }
            }
            
            # 💾 Mise en cache
            try:
                await self.redis_client.cache_summary(
                    document_hash=document_hash,
                    summary_data=complete_result,
                    ttl=86400  # 24h
                )
            except Exception as cache_error:
                logger.warning(f"Erreur mise en cache: {cache_error}")
            
            # 🎯 Phase 6: Génération PDF et stockage sécurisé
            pdf_result = await self._generate_and_store_pdf(
                summary_data=complete_result,
                processing_id=processing_id,
                user_id=user_id
            )
            
            # 📄 Phase 6.5: Génération PDF résumé professionnel
            try:
                pdf_summary_result = await self._generate_summary_pdf(
                    summary_data=complete_result.get('summary', {}),
                    processing_id=processing_id,
                    user_id=user_id
                )
                
                if pdf_result:
                    complete_result.update(pdf_result)
                    
                if pdf_summary_result:
                    complete_result.update({
                        'pdf_summary_available': True,
                        'pdf_summary_download_url': f"/api/v1/contract/download/summary_{processing_id}"
                    })
                    
            except Exception as pdf_error:
                logger.warning(f"Erreur génération PDF: {pdf_error}")
                complete_result.update({
                    'pdf_available': False,
                    'pdf_error': str(pdf_error)
                })
            
            # 📊 Métriques finales
            total_time = (datetime.now() - start_time).total_seconds()
            
            await self.metrics.record_processing_metrics({
                "processing_time_ms": total_time * 1000,
                "cost_cents": total_cost,
                "cache_hit": False,
                "tokens_used": tokens_used,
                "user_id": user_id,
                "doc_hash": document_hash
            })
            
            logger.info(f"Traitement complet terminé: {processing_id}, durée: {total_time:.2f}s")
            
            return {
                'success': True,
                'from_cache': False,
                'processing_id': processing_id,
                'result': complete_result
            }
            
        except Exception as e:
            error_time = (datetime.now() - start_time).total_seconds()
            
            # Utiliser un hash par défaut si document_hash n'est pas défini
            doc_hash = locals().get('document_hash', 'unknown_hash')
            
            await self.audit_logger.log_error_event(
                user_id=user_id,
                error_type="pipeline_error",
                error_message=str(e)
            )
            
            await self.metrics.record_processing_metrics({
                "processing_time_ms": error_time * 1000,
                "cost_cents": 0,
                "cache_hit": False,
                "tokens_used": 0,
                "user_id": user_id,
                "doc_hash": doc_hash
            })
            
            logger.error(f"Erreur pipeline {processing_id}: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'processing_id': processing_id
            }

    async def _generate_and_store_pdf(self,
                                    summary: Dict[str, Any],
                                    citations: Dict[str, str],
                                    validation_notes: List[str],
                                    filename: str,
                                    user_id: str,
                                    user_ip: str = None,
                                    include_watermark: bool = False) -> Dict[str, Any]:
        """Génère et stocke le PDF de manière sécurisée"""
        try:
            # Vérification consentement réelle
            download_consent = await self.consent_manager.check_consent(
                user_id=user_id,
                required_consent=ConsentType.DOWNLOAD
            )
            
            if not download_consent['valid']:
                return {
                    'pdf_available': False,
                    'pdf_error': 'download_consent_required',
                    'consent_details': download_consent
                }
            
            # Génération PDF
            pdf_start = datetime.now()
            
            # Génération PDF réelle
            pdf_bytes = await self.pdf_generator.generate_summary_pdf(
                summary=summary,
                citations=citations,
                validation_notes=validation_notes,
                include_watermark=include_watermark
            )
            
            pdf_time = (datetime.now() - pdf_start).total_seconds()
            
            # Stockage sécurisé réel
            access_token = await self.secure_storage.store_pdf(
                pdf_bytes=pdf_bytes,
                user_id=user_id,
                filename=f"summary_{filename}",
                expiry_hours=24
            )
            
            # URL signée réelle
            download_info = await self.secure_storage.generate_signed_url(
                access_token=access_token,
                user_id=user_id
            )
            
            # Audit PDF
            document_hash = hashlib.sha256(pdf_bytes).hexdigest()[:16]
            
            # Audit PDF réel
            await self.audit_logger.log_pdf_generation(
                user_id=user_id,
                document_hash=document_hash,
                pdf_size_bytes=len(pdf_bytes),
                generation_time_seconds=pdf_time,
                access_token=access_token,
                user_ip=user_ip
            )
            
            return {
                'pdf_available': True,
                'pdf_access_token': access_token,
                'download_info': download_info,
                'pdf_size_bytes': len(pdf_bytes),
                'pdf_generation_time': pdf_time
            }
            
        except Exception as e:
            logger.error(f"Erreur génération/stockage PDF: {e}")
            return {
                'pdf_available': False,
                'pdf_error': 'generation_failed',
                'error_details': str(e)
            }
    
    async def download_secure_pdf(self,
                                file_id: str,
                                timestamp: int,
                                signature: str,
                                user_id: str,
                                user_ip: str = None) -> Optional[Tuple[bytes, str]]:
        """Téléchargement sécurisé de PDF avec audit"""
        try:
            # Service fichier sécurisé
            file_result = await self.storage_manager.serve_secure_file(
                file_id=file_id,
                timestamp=timestamp,
                signature=signature,
                user_ip=user_ip
            )
            
            if file_result:
                file_content, filename = file_result
                
                # Audit téléchargement
                await self.audit_logger.log_pdf_download(
                    user_id=user_id,
                    file_id=file_id,
                    download_count=1,  # TODO: récupérer count réel
                    ip_address=user_ip
                )
                
                return file_content, filename
            
            return None
            
        except Exception as e:
            await self.audit_logger.log_error_event(
                user_id=user_id,
                error_type="pdf_download_failed",
                error_message=str(e),
                context={'file_id': file_id}
            )
            return None
    
    async def request_data_erasure(self, user_id: str) -> Dict[str, Any]:
        """Demande d'effacement GDPR (droit à l'oubli)"""
        try:
            # Vérification consentement existant
            consent_summary = await self.consent_manager.get_consent_summary(user_id)
            
            if not consent_summary['has_consent']:
                return {
                    'success': False,
                    'error': 'no_data_found'
                }
            
            # Retrait consentement
            withdrawal_result = await self.consent_manager.withdraw_consent(user_id)
            
            # Programmation purge immédiate
            purge_result = await self.data_purge.execute_immediate_purge(user_id)
            
            return {
                'success': True,
                'consent_withdrawn': withdrawal_result['success'],
                'data_purged': purge_result['success'],
                'purge_details': purge_result.get('purge_results', {})
            }
            
        except Exception as e:
            logger.error(f"Erreur demande effacement: {e}")
            return {
                'success': False,
                'error': 'erasure_failed',
                'details': str(e)
            }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """État de santé complet du système"""
        try:
            # Santé composants
            redis_health = await self.redis_client.health_check()
            budget_stats = await self.budget_control.get_budget_stats()
            metrics_stats = await self.metrics.get_system_health()
            
            # Stats GDPR
            consent_stats = await self.consent_manager.get_consent_stats()
            purge_stats = await self.data_purge.get_purge_stats()
            audit_stats = await self.audit_logger.get_audit_stats()
            
            # Stats PDF
            pdf_stats = await self.pdf_generator.get_pdf_stats()
            storage_stats = await self.storage_manager.get_storage_stats()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'healthy' if redis_health['status'] == 'healthy' else 'degraded',
                'components': {
                    'redis': redis_health,
                    'budget_control': budget_stats,
                    'metrics': metrics_stats,
                    'pdf_generation': pdf_stats,
                    'secure_storage': storage_stats
                },
                'gdpr_compliance': {
                    'consent_management': consent_stats,
                    'data_purge': purge_stats,
                    'audit_logging': audit_stats
                },
                'dod_compliance': {
                    'cache_hit_rate': metrics_stats.get('cache_hit_rate', 0.0),
                    'avg_processing_time': metrics_stats.get('avg_processing_time', 0.0),
                    'cost_per_summary': budget_stats.get('avg_cost_per_processing', 0.0),
                    'accuracy_score': metrics_stats.get('avg_accuracy', 0.0)
                }
            }
            
        except Exception as e:
            logger.error(f"Erreur health check: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'overall_status': 'error',
                'error': str(e)
            }
    
    def _generate_processing_id(self, user_id: str, filename: str) -> str:
        """Génère un ID unique pour le traitement"""
        data = f"{user_id}:{filename}:{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def cleanup_expired_data(self):
        """Nettoyage automatique des données expirées"""
        try:
            # Nettoyage fichiers PDF
            await self.storage_manager.cleanup_expired_files()
            
            # Nettoyage fichiers temporaires PDF
            await self.pdf_generator.cleanup_temp_files()
            
            # Exécution purges programmées
            await self.data_purge.run_scheduled_purges()
            
            logger.info("Nettoyage automatique terminé")
            
        except Exception as e:
            logger.error(f"Erreur nettoyage automatique: {e}")


# Instance globale pour utilisation dans l'API
contract_reader_pipeline = ContractReaderPipeline()
