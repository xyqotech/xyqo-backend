"""
Résumeur IA optimisé pour Contract Reader
Pipeline 2 étages avec validation et métriques
"""

import os
import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from openai import AsyncOpenAI
from ..models import ContractSummary, SummaryMode, ProcessingMetrics
from ..extraction.text_processor import ProcessedDocument
from ..config import contract_reader_config

logger = logging.getLogger(__name__)

class AISummarizer:
    """Résumeur IA avec optimisation des coûts"""
    
    def __init__(self):
        """Initialise le service de résumé IA basé sur la configuration"""
        self.config = contract_reader_config
        
        if self.config.use_real_openai:
            self.client = AsyncOpenAI(api_key=self.config.openai_api_key)
            logger.info("OpenAI API activée pour Contract Reader")
        else:
            self.client = None
            if self.config.simulation_mode:
                logger.info("Mode simulation activé pour Contract Reader")
            else:
                logger.warning("OpenAI désactivé - mode simulation forcé")
        
        self.summarizer_stats = {
            "total_summaries": 0,
            "successful_summaries": 0,
            "avg_processing_time_ms": 0,
            "avg_cost_cents": 0.0,
            "accuracy_score": 0.0
        }
    
    async def generate_summary(self, extracted_text: str, filename: str, summary_mode: str = "standard") -> Dict[str, Any]:
        """
        Génère un résumé optimisé avec OpenAI GPT-4o-mini
        Pipeline 2 étages: optimisation locale + IA cloud
        """
        start_time = time.time()
        
        try:
            if not extracted_text:
                return {
                    'success': False,
                    'error': 'No text content to summarize'
                }
            
            # FORCE REAL MODE - Pas de simulation
            if not self.config.use_real_openai:
                logger.error("OpenAI API REQUIRED but not configured properly")
                return {
                    'success': False,
                    'error': 'OpenAI API required for real contract analysis'
                }
            
            # Étape 1: Optimisation du texte d'entrée (réduction tokens)
            optimized_text = self._optimize_input_text(extracted_text, summary_mode)
            
            # Étape 2: Estimation coût
            estimated_tokens = len(optimized_text.split()) * 1.3  # Approximation
            estimated_cost_cents = (estimated_tokens / 1000) * 0.15  # GPT-4o-mini pricing
            
            if estimated_cost_cents > self.config.max_cost_cents:  # Limite sécurité configurable
                return {
                    'success': False,
                    'error': f'Cost too high: {estimated_cost_cents:.2f}¢ > 10¢ limit'
                }
            
            # Étape 3: Appel OpenAI GPT-4o-mini
            logger.info(f"Generating summary with OpenAI for {filename}")
            
            from .prompts import get_system_prompt, format_user_prompt
            
            system_prompt = get_system_prompt(summary_mode)
            user_prompt = format_user_prompt(optimized_text, filename)
            
            response = await self.client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,  # Précision maximale pour extraction factuelle
                max_tokens=3000,  # Plus de tokens pour analyse complète
                response_format={"type": "json_object"}
            )
            
            try:
                # Traitement de la réponse
                content = response.choices[0].message.content
                
                # Nettoyage du contenu pour enlever les balises markdown potentielles
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                content = content.strip()
                
                try:
                    summary_data = json.loads(content)
                except json.JSONDecodeError as json_error:
                    logger.error(f"Erreur parsing JSON: {json_error}")
                    logger.error(f"Contenu reçu: {content[:500]}...")
                    
                    # Fallback vers structure minimale UniversalContractV2
                    summary_data = self._create_fallback_universal_contract(
                        error_message=f"Erreur parsing JSON: {str(json_error)}"
                    )
                
                # Validation des champs requis UniversalContractV2
                summary_data = self._validate_universal_contract_schema(summary_data)
                
                # Calcul du coût réel
                tokens_used = response.usage.total_tokens
                actual_cost_cents = (tokens_used / 1000) * 0.15
                processing_time = time.time() - start_time
                
                logger.info(f"Summary generated successfully. Tokens: {tokens_used}, Cost: {actual_cost_cents:.2f}¢")
                
                return {
                    'success': True,
                    'summary': summary_data,
                    'cost_euros': actual_cost_cents / 100,
                    'processing_time': processing_time,
                    'tokens_used': tokens_used
                }
                
            except Exception as e:
                logger.error(f"Erreur API OpenAI: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'processing_time': time.time() - start_time
                }
            
        except Exception as e:
            logger.error(f"Erreur API OpenAI: {e}")
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _optimize_input_text(self, text_content: str, summary_mode: str) -> str:
        """Optimise le texte d'entrée pour réduire les tokens"""
        # Suppression des espaces multiples et caractères inutiles
        cleaned_text = ' '.join(text_content.split())
        
        # Limitation selon le mode - AUGMENTÉE pour ne pas perdre les montants
        max_chars = {
            'quick': 5000,
            'standard': 10000,
            'detailed': 15000
        }.get(summary_mode, 10000)
        
        if len(cleaned_text) > max_chars:
            # Garde le début et la fin du document pour ne pas perdre les infos importantes
            half_size = max_chars // 2
            cleaned_text = cleaned_text[:half_size] + "\n[...CONTENU TRONQUÉ...]\n" + cleaned_text[-half_size:]
        
        return cleaned_text
    
    def _create_fallback_universal_contract(self, error_message: str) -> Dict[str, Any]:
        """Crée une structure UniversalContractV2 minimale en cas d'erreur"""
        from datetime import datetime
        
        return {
            "meta": {
                "generator": "ContractSummarizer",
                "version": "2.0",
                "language": "fr",
                "generated_at": datetime.now().isoformat(),
                "locale_guess": "fr-FR",
                "source_doc_info": {
                    "title": None,
                    "doc_type": None,
                    "signing_method": None,
                    "signatures_present": False,
                    "version_label": None,
                    "effective_date": None
                }
            },
            "parties": {
                "list": [],
                "third_parties": []
            },
            "contract": {
                "object": None,
                "scope": {
                    "deliverables": [],
                    "exclusions": []
                },
                "location_or_site": None,
                "dates": {
                    "start_date": None,
                    "end_date": None,
                    "minimum_term_months": None,
                    "renewal": None,
                    "notice_period_days": None,
                    "milestones": []
                },
                "obligations": {
                    "by_provider": [],
                    "by_customer": [],
                    "by_other": []
                },
                "service_levels": {
                    "kpi_list": [],
                    "sla": None,
                    "penalties": None
                },
                "ip_rights": {
                    "ownership": None,
                    "license_terms": None
                },
                "data_privacy": {
                    "rgpd": None,
                    "processing_roles": None,
                    "subprocessors": [],
                    "data_locations": [],
                    "security_measures": []
                }
            },
            "financials": {
                "price_model": None,
                "items": [],
                "currency": None,
                "payment_terms": None,
                "late_fees": None,
                "indexation": None
            },
            "governance": {
                "termination": {
                    "by_provider": None,
                    "by_customer": None,
                    "effects": None
                },
                "liability": None,
                "warranties": None,
                "compliance": None,
                "law": None,
                "jurisdiction": None,
                "insurance": None,
                "confidentiality": None,
                "force_majeure": None
            },
            "summary_plain": f"Erreur lors de l'analyse du contrat: {error_message}. Veuillez réessayer ou contacter le support technique.",
            "risks_red_flags": [f"Erreur technique: {error_message}"],
            "missing_info": ["Analyse complète impossible due à une erreur technique"],
            "operational_actions": {
                "jira_summary": None,
                "key_dates": [],
                "renewal_window_days": None
            }
        }
    
    def _validate_universal_contract_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et complète la structure UniversalContractV2"""
        required_fields = [
            "meta", "parties", "contract", "financials", 
            "governance", "summary_plain", "risks_red_flags", 
            "missing_info", "operational_actions"
        ]
        
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
                
        if missing_fields:
            logger.warning(f"Champs manquants dans la réponse AI: {missing_fields}")
            # Compléter avec la structure fallback
            fallback = self._create_fallback_universal_contract("Champs manquants dans la réponse AI")
            for field in missing_fields:
                data[field] = fallback[field]
        
        return data
    
    async def _call_openai_api(self, optimized_text: str, summary_mode: str) -> Dict[str, Any]:
        """Appel à l'API OpenAI GPT-4o-mini"""
        try:
            # Étape 3: Appel OpenAI avec prompts optimisés
            system_prompt = get_system_prompt(summary_mode)
            user_prompt = format_user_prompt(optimized_text, "filename")
            
            logger.info(f"Calling OpenAI API with {len(optimized_text)} chars, mode: {summary_mode}")
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,  # Précision maximale pour extraction factuelle
                max_tokens=3000,  # Plus de tokens pour analyse complète
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except json.JSONDecodeError as e:
            logger.error(f"Erreur JSON OpenAI: {e}")
            # Fallback vers simulation en cas d'erreur
            return self._get_fallback_summary(optimized_text)
        except Exception as e:
            logger.error(f"Erreur API OpenAI: {e}")
            # Fallback vers simulation en cas d'erreur
            return self._get_fallback_summary(optimized_text)
    
    def _get_system_prompt(self, summary_mode: str) -> str:
        """Prompt système optimisé pour l'extraction française"""
        return f"""
Tu es un expert juridique français spécialisé dans l'analyse de contrats.
Ton rôle est de produire un résumé structuré et précis en français.

Mode d'analyse: {summary_mode}

Tu dois retourner un JSON avec cette structure exacte:
{{
    "title": "Titre du contrat",
    "tldr": "Résumé en 2-3 phrases",
    "key_clauses": ["Clause 1", "Clause 2"],
    "red_flags": ["Alerte 1", "Alerte 2"],
    "parties": ["Partie A", "Partie B"],
    "amounts": ["Montant 1", "Montant 2"],
    "dates": ["Date 1", "Date 2"],
    "glossary": {{"terme": "définition"}},
    "confidence_score": 0.85
}}

Sois précis, factuel et identifie les risques potentiels.
"""
    
    def _get_user_prompt(self, text_content: str, summary_mode: str) -> str:
        """Prompt utilisateur avec le contenu du contrat"""
        return f"""
Analyse ce contrat français et produis un résumé structuré:

{text_content}

Mode: {summary_mode}

Retourne uniquement le JSON demandé, sans texte supplémentaire.
"""
    
    def _get_fallback_summary(self, text_content: str) -> Dict[str, Any]:
        """Résumé de fallback en cas d'erreur API"""
        return {
            "title": "Contrat analysé (mode fallback)",
            "tldr": "Analyse effectuée en mode dégradé suite à une erreur API",
            "key_clauses": ["Analyse détaillée non disponible"],
            "red_flags": ["Vérification manuelle recommandée"],
            "parties": ["Parties non identifiées"],
            "amounts": [],
            "dates": [],
            "glossary": {},
            "confidence_score": 0.3
        }
    
    def _process_ai_response(self, ai_response: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """Post-traitement et validation de la réponse IA"""
        # Validation des champs obligatoires
        required_fields = ['title', 'tldr', 'key_clauses', 'red_flags', 'parties', 'amounts', 'dates', 'glossary']
        
        for field in required_fields:
            if field not in ai_response:
                ai_response[field] = [] if field in ['key_clauses', 'red_flags', 'parties', 'amounts', 'dates'] else {} if field == 'glossary' else 'Non spécifié'
        
        # Validation du score de confiance
        if 'confidence_score' not in ai_response or not isinstance(ai_response['confidence_score'], (int, float)):
            ai_response['confidence_score'] = 0.75
        
        # Limitation des listes pour éviter les réponses trop longues
        for list_field in ['key_clauses', 'red_flags', 'parties', 'amounts', 'dates']:
            if isinstance(ai_response[list_field], list) and len(ai_response[list_field]) > 10:
                ai_response[list_field] = ai_response[list_field][:10]
        
        return ai_response
    
    def _calculate_confidence_score(self, summary_data: Dict[str, Any], original_text: str) -> float:
        """Calcule un score de confiance basique"""
        score = 0.0
        
        # Vérifier la présence des sections requises
        required_fields = ["title", "tldr", "key_clauses", "parties"]
        present_fields = sum(1 for field in required_fields if field in summary_data and summary_data[field])
        score += (present_fields / len(required_fields)) * 0.4
        
        # Longueur raisonnable du résumé
        tldr_length = len(summary_data.get("tldr", ""))
        if 50 <= tldr_length <= 500:
            score += 0.3
        
        # Présence de clauses clés
        key_clauses = summary_data.get("key_clauses", [])
        if isinstance(key_clauses, list) and len(key_clauses) > 0:
            score += 0.2
        
        # Score de confiance fourni par l'IA
        ai_confidence = summary_data.get("confidence_score", 0.5)
        if isinstance(ai_confidence, (int, float)):
            score += ai_confidence * 0.1
        
        return min(1.0, score)
    
    def validate_summary_accuracy(self, summary_data: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """Validation basique de l'exactitude du résumé"""
        
        validation_result = {
            "basic_validation": True,
            "confidence_score": summary_data.get('confidence_score', 0.75),
            "issues_found": [],
            "validation_method": "basic"
        }
        
        # Vérifications basiques
        if not summary_data.get('title'):
            validation_result["issues_found"].append("Titre manquant")
        
        if not summary_data.get('tldr'):
            validation_result["issues_found"].append("Résumé TLDR manquant")
        
        if not summary_data.get('key_clauses') or len(summary_data.get('key_clauses', [])) == 0:
            validation_result["issues_found"].append("Clauses clés manquantes")
        
        # Score final
        if validation_result["issues_found"]:
            validation_result["confidence_score"] *= 0.8  # Pénalité pour erreurs
            validation_result["basic_validation"] = False
        
        return validation_result
    
    def _update_summarizer_stats(self, processing_time: int, cost: float, confidence: float, success: bool):
        """Met à jour les statistiques du résumeur"""
        self.summarizer_stats["total_summaries"] += 1
        
        if success:
            self.summarizer_stats["successful_summaries"] += 1
            
            # Moyennes mobiles
            total = self.summarizer_stats["successful_summaries"]
            self.summarizer_stats["avg_processing_time_ms"] = (
                (self.summarizer_stats["avg_processing_time_ms"] * (total - 1) + processing_time) / total
            )
            self.summarizer_stats["avg_cost_cents"] = (
                (self.summarizer_stats["avg_cost_cents"] * (total - 1) + cost) / total
            )
            self.summarizer_stats["accuracy_score"] = (
                (self.summarizer_stats["accuracy_score"] * (total - 1) + confidence) / total
            )
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Rapport de performance du résumeur IA"""
        success_rate = (
            self.summarizer_stats["successful_summaries"] / 
            max(1, self.summarizer_stats["total_summaries"])
        ) * 100
        
        return {
            "summarizer_stats": self.summarizer_stats.copy(),
            "success_rate_percent": round(success_rate, 2),
            "cost_optimizer_report": self.cost_optimizer.get_cost_report(),
            "dod_compliance": {
                "avg_cost_under_5_cents": self.summarizer_stats["avg_cost_cents"] <= 5.0,
                "accuracy_over_95_percent": self.summarizer_stats["accuracy_score"] >= 0.95,
                "success_rate_over_90_percent": success_rate >= 90.0
            }
        }
