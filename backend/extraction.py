"""
AUTOPILOT - Service d'extraction LLM
Extraction intelligente avec cache Redis
"""

import json
import hashlib
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis
from openai import AsyncOpenAI
import tiktoken

from models import ContractExtraction, ContractType
from config import settings


class ExtractionService:
    """Service d'extraction avec cache intelligent"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.redis_client = None
        self.cache_hits = {}
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
    async def _get_redis(self):
        """Connexion Redis lazy"""
        if not self.redis_client:
            self.redis_client = redis.from_url(settings.REDIS_URL)
        return self.redis_client
    
    async def extract_with_cache(
        self, 
        file_content: bytes, 
        filename: str, 
        file_hash: str
    ) -> ContractExtraction:
        """Extraction avec cache intelligent"""
        
        # 1. Vérifier cache avec gestionnaire intelligent
        from cache_manager import CacheManager
        cache_manager = CacheManager()
        
        cached_extraction = await cache_manager.get_cached_extraction(file_hash)
        if cached_extraction:
            self.cache_hits[file_hash] = True
            return cached_extraction
        
        # 2. Extraction LLM
        text_content = self._extract_text_from_file(file_content, filename)
        extraction_result = await self._extract_with_llm(text_content, filename)
        
        # 3. Mise en cache intelligente
        await cache_manager.cache_extraction(file_hash, extraction_result)
        
        self.cache_hits[file_hash] = False
        return extraction_result
    
    def _extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        """Extraction texte selon type de fichier"""
        file_ext = filename.lower().split('.')[-1]
        
        if file_ext == 'txt':
            return file_content.decode('utf-8', errors='ignore')
        
        elif file_ext == 'pdf':
            return self._extract_pdf_text(file_content, filename)
        
        elif file_ext in ['docx', 'doc']:
            # TODO: Implémenter extraction DOCX avec python-docx
            # Pour la démo, simuler extraction
            return f"[DOCX Content] {file_content.decode('utf-8', errors='ignore')[:2000]}"
        
        else:
            return file_content.decode('utf-8', errors='ignore')
    
    def _extract_pdf_text(self, file_content: bytes, filename: str) -> str:
        """Extraction robuste de texte PDF avec fallbacks multiples"""
        import io
        
        # Méthode 1: pdfplumber (plus robuste)
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                text_parts = []
                for page in pdf.pages[:10]:  # Limiter à 10 pages
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                
                if text_parts:
                    full_text = '\n'.join(text_parts)
                    return full_text[:8000]  # Limiter la taille
        except Exception as e:
            print(f"Erreur pdfplumber: {str(e)}")
        
        # Méthode 2: PyPDF2 (fallback)
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text_parts = []
            
            for page_num in range(min(len(pdf_reader.pages), 10)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            if text_parts:
                full_text = '\n'.join(text_parts)
                return full_text[:8000]
        except Exception as e:
            print(f"Erreur PyPDF2: {str(e)}")
        
        # Méthode 3: Extraction basique (dernier recours)
        try:
            # Tenter de trouver du texte lisible dans le PDF
            content_str = file_content.decode('utf-8', errors='ignore')
            # Chercher des patterns de texte dans le PDF
            import re
            text_matches = re.findall(r'[A-Za-z0-9\s\.,;:!?\-]{10,}', content_str)
            if text_matches:
                return ' '.join(text_matches[:100])[:2000]
        except Exception as e:
            print(f"Erreur extraction basique: {str(e)}")
        
        # Fallback final: contenu générique pour permettre l'extraction
        return f"""Document PDF: {filename}
        
Ce document PDF contient du contenu qui n'a pas pu être extrait automatiquement.
Il s'agit probablement d'un document avec des images, du texte scanné, ou un format PDF complexe.

Type de document: PDF
Nom du fichier: {filename}
Taille: {len(file_content)} bytes

Pour une extraction optimale, veuillez fournir un PDF avec du texte sélectionnable
ou convertir le document en format texte."""
    
    async def _extract_with_llm(self, text_content: str, filename: str) -> ContractExtraction:
        """Extraction avec GPT-4o-mini"""
        
        # Limiter tokens d'entrée (max 8000 pour garder marge)
        tokens = self.encoding.encode(text_content)
        if len(tokens) > 8000:
            text_content = self.encoding.decode(tokens[:8000])
        
        system_prompt = """Tu es un expert en analyse de contrats. Extrais les informations clés du document fourni.

Réponds UNIQUEMENT avec un JSON valide contenant:
{
  "contract_type": "service|purchase|employment|lease|other",
  "parties": ["Partie 1", "Partie 2"],
  "amount": 15000.50,
  "currency": "EUR",
  "start_date": "2024-01-15",
  "end_date": "2024-12-31",
  "key_terms": ["terme 1", "terme 2"],
  "summary": "Résumé concis du contrat",
  "confidence_score": 0.95,
  "extracted_fields": {"field1": "value1"}
}

Règles strictes:
- confidence_score entre 0.0 et 1.0
- parties: minimum 1, maximum 10
- key_terms: maximum 20 éléments
- summary: entre 10 et 1000 caractères
- dates au format YYYY-MM-DD si trouvées
- currency: code 3 lettres (EUR, USD, etc.)"""

        user_prompt = f"""Analyse ce document contractuel:

Nom du fichier: {filename}

Contenu:
{text_content}

Extrais les informations selon le format JSON demandé."""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1500
            )
            
            # Parser la réponse JSON
            json_response = response.choices[0].message.content.strip()
            
            # Nettoyer si markdown
            if json_response.startswith('```'):
                json_response = json_response.split('```')[1]
                if json_response.startswith('json'):
                    json_response = json_response[4:]
            
            extracted_data = json.loads(json_response)
            
            # Validation et création du modèle
            try:
                return ContractExtraction(**extracted_data)
            except Exception as validation_error:
                print(f"Erreur validation Pydantic: {str(validation_error)}")
                print(f"Données reçues: {extracted_data}")
                # Fallback avec correction des données
                return ContractExtraction(
                    contract_type=ContractType.OTHER,
                    parties=["Données de validation invalides"],
                    summary=f"Erreur de validation des données extraites: {str(validation_error)[:150]}",
                    confidence_score=0.1,
                    key_terms=["validation_error"],
                    amount=None,
                    currency=None,
                    start_date=None,
                    end_date=None,
                    extracted_fields={}
                )
            
        except json.JSONDecodeError as e:
            # Fallback avec données minimales
            return ContractExtraction(
                contract_type=ContractType.OTHER,
                parties=["Partie non identifiée"],
                summary=f"Erreur d'extraction JSON: {str(e)[:100]}",
                confidence_score=0.1,
                key_terms=["extraction_failed"],
                amount=None,
                currency=None,
                start_date=None,
                end_date=None,
                extracted_fields={}
            )
        
        except Exception as e:
            # Log l'erreur pour debug
            print(f"Erreur LLM extraction: {str(e)}")
            print(f"Type d'erreur: {type(e).__name__}")
            
            # Fallback d'urgence avec données valides garanties
            return ContractExtraction(
                contract_type=ContractType.OTHER,
                parties=["Document non analysable"],  # Garantir une partie non vide
                summary=f"Impossible d'extraire les informations du document. Erreur: {str(e)[:150]}",
                confidence_score=0.0,
                key_terms=["llm_error"],
                amount=None,
                currency=None,
                start_date=None,
                end_date=None,
                extracted_fields={}
            )
    
    def was_cached(self, file_hash: str) -> bool:
        """Vérifier si résultat était en cache"""
        return self.cache_hits.get(file_hash, False)
    
    async def clear_cache(self):
        """Nettoyer le cache (pour reset démo)"""
        redis_client = await self._get_redis()
        keys = await redis_client.keys("extraction:*")
        if keys:
            await redis_client.delete(*keys)
        self.cache_hits.clear()
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Statistiques du cache"""
        redis_client = await self._get_redis()
        info = await redis_client.info()
        keys_count = len(await redis_client.keys("extraction:*"))
        
        return {
            "total_keys": keys_count,
            "memory_usage_mb": info.get("used_memory", 0) / 1024 / 1024,
            "hit_rate": sum(self.cache_hits.values()) / len(self.cache_hits) if self.cache_hits else 0.0
        }
