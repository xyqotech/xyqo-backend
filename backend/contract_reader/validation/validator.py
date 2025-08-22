"""
Validateur Pydantic pour UniversalContractV3
Validation stricte des données extraites
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
from pydantic import ValidationError
from .universal_contract_v3_models import UniversalContractV3

logger = logging.getLogger(__name__)

class UniversalContractV3Validator:
    """Validateur pour le schéma UniversalContractV3"""
    
    def __init__(self):
        self.validation_errors = []
        self.warnings = []
    
    def validate_json_data(self, json_data: Dict[str, Any]) -> Tuple[bool, Optional[UniversalContractV3], Dict[str, Any]]:
        """
        Valide les données JSON contre le schéma UniversalContractV3
        
        Args:
            json_data: Données JSON à valider
            
        Returns:
            Tuple (is_valid, validated_model, validation_report)
        """
        self.validation_errors = []
        self.warnings = []
        
        try:
            # Tentative de validation avec Pydantic
            validated_model = UniversalContractV3(**json_data)
            
            # Validations métier supplémentaires
            self._validate_business_rules(validated_model)
            
            validation_report = {
                "is_valid": True,
                "errors": [],
                "warnings": self.warnings,
                "model_version": "UniversalContractV3",
                "validation_timestamp": validated_model.meta.generated_at
            }
            
            logger.info(f"Validation réussie pour UniversalContractV3. Warnings: {len(self.warnings)}")
            return True, validated_model, validation_report
            
        except ValidationError as e:
            # Erreurs de validation Pydantic
            self.validation_errors = self._format_pydantic_errors(e.errors())
            
            validation_report = {
                "is_valid": False,
                "errors": self.validation_errors,
                "warnings": self.warnings,
                "model_version": "UniversalContractV3",
                "validation_timestamp": None,
                "raw_pydantic_errors": e.errors()
            }
            
            logger.error(f"Erreurs de validation Pydantic: {len(self.validation_errors)} erreurs")
            return False, None, validation_report
            
        except Exception as e:
            # Autres erreurs
            self.validation_errors = [f"Erreur inattendue lors de la validation: {str(e)}"]
            
            validation_report = {
                "is_valid": False,
                "errors": self.validation_errors,
                "warnings": self.warnings,
                "model_version": "UniversalContractV3",
                "validation_timestamp": None,
                "exception": str(e)
            }
            
            logger.error(f"Erreur inattendue lors de la validation: {e}")
            return False, None, validation_report
    
    def _format_pydantic_errors(self, errors: list) -> list:
        """Formate les erreurs Pydantic en messages lisibles"""
        formatted_errors = []
        
        for error in errors:
            location = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_type = error["type"]
            
            formatted_error = f"Champ '{location}': {message} (type: {error_type})"
            formatted_errors.append(formatted_error)
        
        return formatted_errors
    
    def _validate_business_rules(self, model: UniversalContractV3):
        """Validations métier supplémentaires"""
        
        # Vérification de la cohérence des dates
        if model.contract.dates.start_date and model.contract.dates.end_date:
            if model.contract.dates.start_date > model.contract.dates.end_date:
                self.warnings.append("Date de début postérieure à la date de fin")
        
        # Vérification de la cohérence financière
        if model.financials.items:
            for item in model.financials.items:
                if item.amount and item.amount < 0:
                    self.warnings.append(f"Montant négatif détecté pour '{item.label}'")
        
        # Vérification des parties
        if len(model.parties.list) < 2:
            self.warnings.append("Moins de 2 parties contractuelles identifiées")
        
        # Vérification du résumé
        if len(model.summary_plain.split()) < 20:
            self.warnings.append("Résumé très court (moins de 20 mots)")
        
        # Vérification des informations manquantes critiques
        critical_missing = []
        if not model.contract.dates.start_date and not model.contract.dates.end_date:
            critical_missing.append("Aucune date de contrat identifiée")
        
        if not model.financials.items and not model.financials.price_model:
            critical_missing.append("Aucune information financière identifiée")
        
        if critical_missing:
            self.warnings.extend(critical_missing)
    
    def validate_json_string(self, json_string: str) -> Tuple[bool, Optional[UniversalContractV3], Dict[str, Any]]:
        """
        Valide une chaîne JSON contre le schéma UniversalContractV3
        
        Args:
            json_string: Chaîne JSON à valider
            
        Returns:
            Tuple (is_valid, validated_model, validation_report)
        """
        try:
            json_data = json.loads(json_string)
            return self.validate_json_data(json_data)
        except json.JSONDecodeError as e:
            validation_report = {
                "is_valid": False,
                "errors": [f"JSON invalide: {str(e)}"],
                "warnings": [],
                "model_version": "UniversalContractV3",
                "validation_timestamp": None
            }
            return False, None, validation_report
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de la dernière validation"""
        return {
            "total_errors": len(self.validation_errors),
            "total_warnings": len(self.warnings),
            "errors": self.validation_errors,
            "warnings": self.warnings
        }

# Instance globale pour faciliter l'utilisation
validator = UniversalContractV3Validator()

def validate_contract_summary(json_data: Dict[str, Any]) -> Tuple[bool, Optional[UniversalContractV3], Dict[str, Any]]:
    """
    Fonction utilitaire pour valider un résumé de contrat
    
    Args:
        json_data: Données JSON du résumé
        
    Returns:
        Tuple (is_valid, validated_model, validation_report)
    """
    return validator.validate_json_data(json_data)

def validate_contract_summary_string(json_string: str) -> Tuple[bool, Optional[UniversalContractV3], Dict[str, Any]]:
    """
    Fonction utilitaire pour valider une chaîne JSON de résumé
    
    Args:
        json_string: Chaîne JSON du résumé
        
    Returns:
        Tuple (is_valid, validated_model, validation_report)
    """
    return validator.validate_json_string(json_string)
