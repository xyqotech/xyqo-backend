"""
AUTOPILOT - Client Jira Cloud
Création automatique de tickets avec mapping YAML
"""

import httpx
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from base64 import b64encode

from models import ContractExtraction, JiraTicket
from config import settings


class JiraClient:
    """Client Jira Cloud avec retry logic"""
    
    def __init__(self):
        self.base_url = settings.JIRA_URL
        self.email = settings.JIRA_EMAIL
        self.api_token = settings.JIRA_API_TOKEN
        self.project_key = settings.JIRA_PROJECT_KEY
        self.sandbox_key = settings.SANDBOX_PROJECT_KEY
        
        # Auth header
        auth_string = f"{self.email}:{self.api_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    async def create_ticket(
        self, 
        extraction_result: ContractExtraction, 
        filename: str,
        demo_mode: bool = True
    ) -> Optional[JiraTicket]:
        """Créer ticket Jira avec retry logic"""
        
        # Mode démo : simuler la création de ticket
        if settings.DEMO_MODE:
            return self._create_demo_ticket(extraction_result, filename)
        
        project_key = self.sandbox_key if demo_mode else self.project_key
        
        # Préparer payload Jira
        ticket_data = self._build_ticket_payload(
            extraction_result, 
            filename, 
            project_key
        )
        
        # Tentatives avec backoff exponentiel
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{self.base_url}/rest/api/3/issue",
                        headers=self.headers,
                        json=ticket_data
                    )
                    
                    if response.status_code == 201:
                        ticket_response = response.json()
                        return JiraTicket(
                            key=ticket_response["key"],
                            url=f"{self.base_url}/browse/{ticket_response['key']}",
                            summary=ticket_data["fields"]["summary"],
                            description=ticket_data["fields"]["description"],
                            project_key=project_key,
                            issue_type=ticket_data["fields"]["issuetype"]["name"],
                            priority=ticket_data["fields"]["priority"]["name"],
                            created_at=datetime.utcnow(),
                            demo_mode=demo_mode
                        )
                    
                    elif response.status_code == 400:
                        # Erreur de validation, pas de retry
                        print(f"Jira validation error: {response.text}")
                        break
                    
                    else:
                        print(f"Jira API error (attempt {attempt + 1}): {response.status_code} - {response.text}")
                        
            except Exception as e:
                print(f"Jira connection error (attempt {attempt + 1}): {str(e)}")
            
            # Backoff exponentiel
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
        
        return None
    
    def _create_demo_ticket(self, extraction_result: ContractExtraction, filename: str) -> JiraTicket:
        """Créer un ticket de démonstration simulé"""
        import random
        import string
        
        # Générer une clé de ticket simulée
        ticket_id = ''.join(random.choices(string.digits, k=4))
        ticket_key = f"DEMO-{ticket_id}"
        
        # Créer le résumé du ticket
        summary = f"Contrat {extraction_result.contract_type.value} - {extraction_result.parties[0] if extraction_result.parties else 'Document'}"
        
        # Description détaillée
        description = f"""*Ticket généré automatiquement par AUTOPILOT*

📄 *Document traité:* {filename}
🤖 *Confiance d'extraction:* {extraction_result.confidence_score:.0%}

*Parties contractuelles:*
{chr(10).join([f"• {party}" for party in extraction_result.parties])}

*Détails du contrat:*
• Type: {extraction_result.contract_type.value}
• Montant: {extraction_result.amount:,.0f} {extraction_result.currency} (si applicable)
• Période: {extraction_result.start_date} → {extraction_result.end_date}

*Termes clés identifiés:*
{chr(10).join([f"• {term}" for term in extraction_result.key_terms[:10]])}

*Résumé:*
{extraction_result.summary}

---
_Ce ticket a été créé en mode démonstration. Dans un environnement de production, il serait créé dans votre instance Jira réelle._"""

        return JiraTicket(
            key=ticket_key,
            url=f"https://xyqo.atlassian.net/browse/{ticket_key}",
            summary=summary,
            description=description,
            project_key="DEMO",
            issue_type="Task",
            priority="Medium",
            created_at=datetime.utcnow(),
            demo_mode=True
        )
    
    def _build_ticket_payload(
        self, 
        extraction: ContractExtraction, 
        filename: str, 
        project_key: str
    ) -> Dict[str, Any]:
        """Construire payload Jira selon mapping"""
        
        # Mapping des types de contrats vers priorités
        priority_mapping = {
            "service": "High",
            "purchase": "High", 
            "employment": "Highest",
            "lease": "Medium",
            "other": "Low"
        }
        
        # Construire description riche
        description_parts = [
            f"*Fichier traité:* {filename}",
            f"*Type de contrat:* {extraction.contract_type.value.title()}",
            f"*Parties:* {', '.join(extraction.parties)}",
            "",
            f"*Résumé:*",
            extraction.summary,
            ""
        ]
        
        if extraction.amount and extraction.currency:
            description_parts.append(f"*Montant:* {extraction.amount:,.2f} {extraction.currency}")
        
        if extraction.start_date:
            description_parts.append(f"*Date début:* {extraction.start_date}")
        
        if extraction.end_date:
            description_parts.append(f"*Date fin:* {extraction.end_date}")
        
        if extraction.key_terms:
            description_parts.extend([
                "",
                "*Termes clés:*",
                *[f"• {term}" for term in extraction.key_terms[:10]]
            ])
        
        description_parts.extend([
            "",
            f"*Score de confiance:* {extraction.confidence_score:.1%}",
            f"*Traité automatiquement par AUTOPILOT le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')}*"
        ])
        
        # Générer titre intelligent
        summary = self._generate_smart_summary(extraction, filename)
        
        # Format Atlassian Document pour la description
        description_doc = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": f"Fichier traité: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": filename}
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": f"Type de contrat: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": extraction.contract_type.value.title()}
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": f"Parties: ", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": ', '.join(extraction.parties)}
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Résumé:", "marks": [{"type": "strong"}]}
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": extraction.summary}
                    ]
                }
            ]
        }
        
        # Ajouter montant si disponible
        if extraction.amount and extraction.currency:
            description_doc["content"].append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": f"Montant: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": f"{extraction.amount:,.2f} {extraction.currency}"}
                ]
            })
        
        # Ajouter dates si disponibles
        if extraction.start_date:
            description_doc["content"].append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": f"Date début: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": extraction.start_date}
                ]
            })
        
        if extraction.end_date:
            description_doc["content"].append({
                "type": "paragraph",
                "content": [
                    {"type": "text", "text": f"Date fin: ", "marks": [{"type": "strong"}]},
                    {"type": "text", "text": extraction.end_date}
                ]
            })
        
        # Ajouter score de confiance
        description_doc["content"].append({
            "type": "paragraph",
            "content": [
                {"type": "text", "text": f"Score de confiance: ", "marks": [{"type": "strong"}]},
                {"type": "text", "text": f"{extraction.confidence_score:.1%}"}
            ]
        })
        
        return {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": description_doc,
                "issuetype": {"name": "Tâche"},
                "priority": {"name": priority_mapping.get(extraction.contract_type.value, "Medium")},
                "labels": [
                    "autopilot",
                    f"contract-{extraction.contract_type.value}",
                    f"confidence-{int(extraction.confidence_score * 100)}"
                ]
            }
        }
    
    def _generate_smart_summary(self, extraction: ContractExtraction, filename: str) -> str:
        """Générer titre intelligent du ticket"""
        
        contract_type_fr = {
            "service": "Contrat de service",
            "purchase": "Bon de commande", 
            "employment": "Contrat de travail",
            "lease": "Contrat de bail",
            "other": "Document contractuel"
        }
        
        type_label = contract_type_fr.get(extraction.contract_type.value, "Document")
        
        # Identifier partie principale (première non-générique)
        main_party = "Partie inconnue"
        for party in extraction.parties:
            if len(party) > 5 and not any(word in party.lower() for word in ["société", "company", "client", "fournisseur"]):
                main_party = party[:30]
                break
        
        # Ajouter montant si significatif
        amount_info = ""
        if extraction.amount and extraction.amount > 1000:
            amount_info = f" - {extraction.amount:,.0f} {extraction.currency or '€'}"
        
        return f"{type_label} - {main_party}{amount_info}"
    
    async def test_connection(self) -> bool:
        """Test de connexion à Jira Cloud"""
        # Mode démo : simuler une connexion réussie
        if settings.DEMO_MODE:
            print("Mode démo : simulation de connexion Jira réussie")
            return True
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/rest/api/3/myself",
                    headers=self.headers,
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            print(f"Erreur connexion Jira: {str(e)}")
            return False
    
    async def get_project_info(self, project_key: str) -> Optional[Dict[str, Any]]:
        """Récupérer infos projet"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/rest/api/3/project/{project_key}",
                    headers=self.headers
                )
                if response.status_code == 200:
                    return response.json()
        except:
            pass
        return None
