#!/usr/bin/env python3
"""
Script de test pour l'intégration Jira
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv('/Users/bassiroudiop/autopilot-demo/.env')
sys.path.append('/Users/bassiroudiop/autopilot-demo/backend')

from jira_client import JiraClient
from models import ContractExtraction, ContractType

async def test_jira_connection():
    """Test de connexion Jira"""
    print("🔗 Test de connexion Jira...")
    
    jira_client = JiraClient()
    
    # Test de connexion
    is_connected = await jira_client.test_connection()
    
    if is_connected:
        print("✅ Connexion Jira réussie!")
        return True
    else:
        print("❌ Échec de connexion Jira")
        return False

async def test_ticket_creation():
    """Test de création de ticket"""
    print("\n🎫 Test de création de ticket...")
    
    # Créer une extraction de test
    test_extraction = ContractExtraction(
        contract_type=ContractType.SERVICE,
        parties=["XYQO TECHNOLOGIES", "CLIENT TEST"],
        amount=50000.0,
        currency="EUR",
        start_date="2024-01-15",
        end_date="2024-12-31",
        key_terms=["test", "démonstration", "automatisation"],
        summary="Contrat de test pour démonstration AUTOPILOT - création automatique de ticket Jira",
        confidence_score=0.95,
        extracted_fields={"test_mode": True}
    )
    
    jira_client = JiraClient()
    
    try:
        ticket = await jira_client.create_ticket(test_extraction, "test-contract.pdf", demo_mode=False)
        
        if ticket:
            print(f"✅ Ticket créé avec succès!")
            print(f"   Clé: {ticket.key}")
            print(f"   URL: {ticket.url}")
            print(f"   Résumé: {ticket.summary}")
            return ticket
        else:
            print("❌ Échec de création de ticket")
            return None
            
    except Exception as e:
        print(f"❌ Erreur lors de la création: {str(e)}")
        return None

async def main():
    """Test complet de l'intégration Jira"""
    print("🚀 Test d'intégration Jira AUTOPILOT\n")
    
    # Test 1: Connexion
    connection_ok = await test_jira_connection()
    
    if not connection_ok:
        print("\n❌ Impossible de continuer sans connexion Jira")
        return
    
    # Test 2: Création de ticket
    ticket = await test_ticket_creation()
    
    if ticket:
        print(f"\n🎉 Intégration Jira fonctionnelle!")
        print(f"   Consultez le ticket: {ticket.url}")
    else:
        print(f"\n⚠️  Problème avec la création de tickets")

if __name__ == "__main__":
    asyncio.run(main())
