#!/usr/bin/env python3
"""
Test de l'intégration OpenAI avec le nouveau prompt utilisateur
"""

import requests
import os
import time
import json
from datetime import datetime

def test_openai_integration():
    """Test l'intégration OpenAI avec le nouveau format JSON"""
    
    print("🧪 Test Intégration OpenAI XYQO - Nouveau Format")
    print("=" * 60)
    
    backend_url = "http://localhost:8002"
    contract_path = "/Users/bassiroudiop/autopilot-demo/data/samples/Modele-de-contrat-de-consultance.pdf"
    
    # Test health check
    try:
        health_response = requests.get(f"{backend_url}/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            openai_available = health_data.get('openai_available', False)
            print(f"✅ Backend accessible")
            print(f"🤖 OpenAI Available: {openai_available}")
            
            if not openai_available:
                print("❌ OpenAI non disponible - vérifiez la clé API")
                return False
        else:
            print(f"❌ Backend health check failed: {health_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return False
    
    # Test contract analysis avec OpenAI
    if os.path.exists(contract_path):
        try:
            print("📄 Testing OpenAI contract analysis...")
            
            with open(contract_path, 'rb') as f:
                files = {'file': ('test_contract.pdf', f, 'application/pdf')}
                
                start_time = time.time()
                response = requests.post(
                    f"{backend_url}/api/v1/contract/analyze",
                    files=files,
                    timeout=120  # Plus de temps pour OpenAI
                )
                analysis_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ OpenAI analysis successful ({analysis_time:.2f}s)")
                
                # Vérifier la nouvelle structure JSON
                if 'analysis' in result:
                    analysis = result['analysis']
                    
                    # Vérifier les champs du nouveau format
                    expected_fields = [
                        'executive_summary', 'parties', 'details', 'obligations',
                        'financials', 'governance', 'risks', 'missing_info', 'legal_warning'
                    ]
                    
                    missing_fields = []
                    for field in expected_fields:
                        if field not in analysis:
                            missing_fields.append(field)
                    
                    if not missing_fields:
                        print("✅ Nouveau format JSON complet")
                        
                        # Afficher quelques détails
                        print(f"📋 Résumé: {analysis.get('executive_summary', 'N/A')[:100]}...")
                        print(f"👥 Parties trouvées: {len(analysis.get('parties', []))}")
                        print(f"💰 Modèle de prix: {analysis.get('financials', {}).get('pricing_model', 'N/A')}")
                        print(f"⚠️  Risques identifiés: {len(analysis.get('risks', []))}")
                        
                        # Test du téléchargement PDF
                        if 'metadata' in result and 'download_url' in result['metadata']:
                            download_url = result['metadata']['download_url']
                            download_response = requests.get(f"{backend_url}{download_url}")
                            if download_response.status_code == 200:
                                print(f"✅ PDF download working ({len(download_response.content)} bytes)")
                            else:
                                print(f"❌ PDF download failed: {download_response.status_code}")
                        
                        return True
                    else:
                        print(f"❌ Champs manquants dans le JSON: {missing_fields}")
                        return False
                else:
                    print("❌ Pas de champ 'analysis' dans la réponse")
                    return False
            else:
                print(f"❌ OpenAI analysis failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error during OpenAI test: {e}")
            return False
    else:
        print(f"❌ Test contract not found: {contract_path}")
        return False

def main():
    """Test principal"""
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = test_openai_integration()
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 INTÉGRATION OPENAI RÉUSSIE!")
        print("✅ Le nouveau format JSON fonctionne parfaitement")
        print("🤖 OpenAI GPT-4 mini analyse les contrats avec le prompt utilisateur")
        print("📄 PDF généré avec le nouveau contenu structuré")
    else:
        print("❌ PROBLÈME D'INTÉGRATION OPENAI")
        print("🔧 Vérifiez la clé API et la connectivité")
    
    print(f"🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()
