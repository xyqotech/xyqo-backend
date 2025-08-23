#!/usr/bin/env python3
"""
Test complet de l'intégration frontend-backend XYQO
"""

import requests
import os
import time
from datetime import datetime

def test_frontend_backend_integration():
    """Test l'intégration complète frontend-backend"""
    
    print("🧪 Test Frontend-Backend Integration XYQO")
    print("=" * 60)
    
    # 1. Vérifier que le backend est accessible
    backend_url = "http://localhost:8002"
    frontend_url = "http://localhost:3002"
    
    print(f"🔗 Backend URL: {backend_url}")
    print(f"🌐 Frontend URL: {frontend_url}")
    
    # Test backend health
    try:
        health_response = requests.get(f"{backend_url}/health", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"✅ Backend accessible - OpenAI: {health_data.get('openai_available', False)}")
        else:
            print(f"❌ Backend health check failed: {health_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return False
    
    # Test frontend accessibility
    try:
        frontend_response = requests.get(frontend_url, timeout=10)
        if frontend_response.status_code == 200:
            print("✅ Frontend accessible")
        else:
            print(f"❌ Frontend not accessible: {frontend_response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to frontend: {e}")
        return False
    
    # Test avec un contrat réel via l'API backend
    print(f"\n📄 Testing contract upload simulation...")
    
    contract_path = "/Users/bassiroudiop/autopilot-demo/data/samples/Modele-de-contrat-de-consultance.pdf"
    
    if os.path.exists(contract_path):
        try:
            with open(contract_path, 'rb') as f:
                files = {'file': ('test_contract.pdf', f, 'application/pdf')}
                
                start_time = time.time()
                response = requests.post(
                    f"{backend_url}/api/v1/contract/analyze",
                    files=files,
                    timeout=60
                )
                analysis_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Contract analysis successful ({analysis_time:.2f}s)")
                
                # Vérifier la structure de réponse attendue par le frontend
                if 'analysis' in result and 'metadata' in result:
                    analysis = result['analysis']
                    metadata = result['metadata']
                    
                    print(f"📋 Contract Object: {analysis.get('contract', {}).get('object', 'N/A')}")
                    print(f"👥 Parties: {len(analysis.get('parties', {}).get('list', []))}")
                    print(f"📥 Download URL: {metadata.get('download_url', 'N/A')}")
                    
                    # Test du téléchargement PDF
                    if metadata.get('download_url'):
                        download_response = requests.get(f"{backend_url}{metadata['download_url']}")
                        if download_response.status_code == 200:
                            print(f"✅ PDF download working ({len(download_response.content)} bytes)")
                        else:
                            print(f"❌ PDF download failed: {download_response.status_code}")
                    
                    print("✅ Response structure compatible with frontend")
                    return True
                else:
                    print("❌ Response structure incompatible with frontend")
                    print(f"Response keys: {list(result.keys())}")
                    return False
            else:
                print(f"❌ Contract analysis failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error during contract test: {e}")
            return False
    else:
        print(f"❌ Test contract not found: {contract_path}")
        return False

def main():
    """Test principal"""
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = test_frontend_backend_integration()
    
    print(f"\n{'='*60}")
    if success:
        print("🎉 INTÉGRATION FRONTEND-BACKEND RÉUSSIE!")
        print("✅ Le système XYQO est prêt pour les tests utilisateur")
        print(f"🌐 Accédez au frontend: http://localhost:3002/contract-reader")
        print(f"🔗 Backend API: http://localhost:8002")
    else:
        print("❌ PROBLÈME D'INTÉGRATION DÉTECTÉ")
        print("🔧 Vérifiez que le backend et le frontend sont démarrés")
    
    print(f"🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    main()
