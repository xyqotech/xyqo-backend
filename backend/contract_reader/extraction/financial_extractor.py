"""
Extracteur spécialisé pour les informations financières dans les contrats
Pré-processing avant envoi à GPT pour garantir l'extraction des montants
"""

import re
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class FinancialExtractor:
    """Extracteur spécialisé pour les montants et conditions financières"""
    
    def __init__(self):
        # Patterns pour détecter les montants
        self.amount_patterns = [
            r'(\d+(?:,\d+)?(?:\.\d+)?)\s*€\s*(?:HT|TTC)?(?:/(?:heure|jour|mois|an|km))?',
            r'(\d+(?:,\d+)?(?:\.\d+)?)\s*EUR\s*(?:HT|TTC)?(?:/(?:heure|jour|mois|an|km))?',
            r'(?:tarif|prix|coût|montant|frais).*?(\d+(?:,\d+)?(?:\.\d+)?)\s*€',
            r'(\d+(?:,\d+)?(?:\.\d+)?)\s*euros?(?:\s*(?:HT|TTC))?',
        ]
        
        # Patterns pour les conditions de paiement
        self.payment_patterns = [
            r'(?:paiement|règlement|factur).*?(\d+)\s*jours?',
            r'(\d+)\s*jours?\s*(?:fin de mois|net)',
            r'(?:mensuel|trimestriel|annuel)lement?',
            r'(?:à\s*)?(\d+)\s*jours?\s*(?:de\s*)?(?:la\s*)?(?:facture|livraison)',
        ]
    
    def extract_financial_info(self, text: str) -> Dict:
        """
        Extrait les informations financières du texte
        Retourne un dict avec les montants trouvés et conditions
        """
        financial_info = {
            "amounts_found": [],
            "payment_terms_found": [],
            "currency": None,
            "has_financial_data": False
        }
        
        try:
            # Recherche des montants
            amounts = self._extract_amounts(text)
            if amounts:
                financial_info["amounts_found"] = amounts
                financial_info["has_financial_data"] = True
                
            # Recherche des conditions de paiement
            payment_terms = self._extract_payment_terms(text)
            if payment_terms:
                financial_info["payment_terms_found"] = payment_terms
                
            # Détection de la devise
            if "€" in text or "EUR" in text:
                financial_info["currency"] = "EUR"
                
            logger.info(f"Financial extraction found {len(amounts)} amounts, {len(payment_terms)} payment terms")
            
        except Exception as e:
            logger.error(f"Error in financial extraction: {e}")
            
        return financial_info
    
    def _extract_amounts(self, text: str) -> List[Dict]:
        """Extrait tous les montants du texte"""
        amounts = []
        
        for pattern in self.amount_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                amount_str = match.group(1).replace(',', '.')
                try:
                    amount = float(amount_str)
                    
                    # Détermine le contexte (heure, jour, etc.)
                    context = self._get_amount_context(match.group(0), text, match.start())
                    
                    amounts.append({
                        "amount": amount,
                        "raw_text": match.group(0),
                        "context": context,
                        "position": match.start()
                    })
                except ValueError:
                    continue
                    
        # Déduplique et trie par position
        amounts = self._deduplicate_amounts(amounts)
        return sorted(amounts, key=lambda x: x["position"])
    
    def _extract_payment_terms(self, text: str) -> List[str]:
        """Extrait les conditions de paiement"""
        terms = []
        
        for pattern in self.payment_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                terms.append(match.group(0))
                
        return list(set(terms))  # Déduplique
    
    def _get_amount_context(self, amount_text: str, full_text: str, position: int) -> str:
        """Détermine le contexte d'un montant (heure, jour, forfait, etc.)"""
        # Regarde autour du montant pour comprendre le contexte
        start = max(0, position - 50)
        end = min(len(full_text), position + len(amount_text) + 50)
        context_text = full_text[start:end].lower()
        
        if "/heure" in amount_text.lower() or "heure" in context_text:
            return "horaire"
        elif "/jour" in amount_text.lower() or "jour" in context_text:
            return "journalier"
        elif "/mois" in amount_text.lower() or "mensuel" in context_text:
            return "mensuel"
        elif "/an" in amount_text.lower() or "annuel" in context_text:
            return "annuel"
        elif "/km" in amount_text.lower() or "kilomètre" in context_text:
            return "kilométrique"
        elif "forfait" in context_text:
            return "forfait"
        else:
            return "inconnu"
    
    def _deduplicate_amounts(self, amounts: List[Dict]) -> List[Dict]:
        """Supprime les doublons en gardant le plus précis"""
        if not amounts:
            return []
            
        # Groupe par montant similaire
        grouped = {}
        for amount in amounts:
            key = round(amount["amount"], 2)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(amount)
            
        # Garde le plus précis pour chaque groupe
        deduplicated = []
        for group in grouped.values():
            # Préfère celui avec le plus de contexte
            best = max(group, key=lambda x: len(x["context"]) + len(x["raw_text"]))
            deduplicated.append(best)
            
        return deduplicated
    
    def format_for_prompt(self, financial_info: Dict) -> str:
        """Formate les infos financières pour injection dans le prompt"""
        if not financial_info["has_financial_data"]:
            return ""
            
        prompt_section = "\n\n=== INFORMATIONS FINANCIÈRES DÉTECTÉES ===\n"
        
        if financial_info["amounts_found"]:
            prompt_section += "MONTANTS TROUVÉS:\n"
            for amount in financial_info["amounts_found"]:
                prompt_section += f"- {amount['amount']}€ ({amount['context']}) - Texte: '{amount['raw_text']}'\n"
                
        if financial_info["payment_terms_found"]:
            prompt_section += "\nCONDITIONS DE PAIEMENT:\n"
            for term in financial_info["payment_terms_found"]:
                prompt_section += f"- {term}\n"
                
        prompt_section += "\nATTENTION: Utilise ces informations pour remplir la section 'financials' du JSON.\n"
        prompt_section += "=== FIN INFORMATIONS FINANCIÈRES ===\n\n"
        
        return prompt_section
