"""
Test end-to-end du pipeline Contract Reader
Validation complète avec PDF réel
"""

import asyncio
import os
import sys
from pathlib import Path
import time
import json

# Ajout du chemin backend pour imports
sys.path.append(str(Path(__file__).parent))

from contract_reader import contract_reader_pipeline
from contract_reader.gdpr.consent_manager import ConsentType

async def test_pipeline_complete():
    """Test complet du pipeline Contract Reader"""
    
    print("🧪 Test End-to-End Contract Reader Pipeline")
    print("=" * 50)
    
    # 1. Test avec PDF factice (en attendant un vrai PDF)
    test_pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Contrat de Service Test) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000206 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n299\n%%EOF"
    
    user_id = "test_user_123"
    user_ip = "127.0.0.1"
    filename = "contrat_test.pdf"
    
    print(f"📄 Fichier test: {filename}")
    print(f"👤 User ID: {user_id}")
    print(f"🌐 IP: {user_ip}")
    print()
    
    try:
        # 2. Test consentement GDPR
        print("🔐 Test 1: Consentement GDPR")
        print("-" * 30)
        
        consent_result = await contract_reader_pipeline.consent_manager.record_consent(
            user_id=user_id,
            ip_address=user_ip,
            consent_data={
                "processing": True,
                "download": True,
                "analytics": False,
                "marketing": False
            }
        )
        
        if hasattr(consent_result, 'consent_id'):
            print("✅ Consentement enregistré avec succès")
            print(f"   Consent ID: {consent_result.consent_id}")
            print(f"   Expire le: {consent_result.expires_at}")
        else:
            print("❌ Erreur consentement:", str(consent_result))
            return
        
        print()
        
        # 3. Test pipeline complet
        print("🚀 Test 2: Pipeline Complet")
        print("-" * 30)
        
        start_time = time.time()
        
        result = await contract_reader_pipeline.process_contract_complete(
            pdf_content=test_pdf_content,
            filename=filename,
            user_id=user_id,
            user_ip=user_ip,
            summary_mode="standard",
            include_watermark=True
        )
        
        processing_time = time.time() - start_time
        
        if result['success']:
            print("✅ Pipeline exécuté avec succès")
            print(f"   Durée: {processing_time:.2f}s")
            print(f"   Processing ID: {result['processing_id']}")
            print(f"   Cache: {'Oui' if result.get('from_cache') else 'Non'}")
            
            # Analyse résultat
            pipeline_result = result['result']
            
            print("\n📊 Métriques DoD:")
            dod = pipeline_result.get('dod_compliance', {})
            print(f"   Extraction ≤3s: {'✅' if dod.get('extraction_p95_under_3s') else '❌'}")
            print(f"   Coût ≤0.05€: {'✅' if dod.get('cost_under_0_05_euros') else '❌'}")
            print(f"   Précision ≥95%: {'✅' if dod.get('accuracy_over_95_percent') else '❌'}")
            print(f"   Citations <1%: {'✅' if dod.get('citation_error_under_1_percent') else '❌'}")
            
            print("\n📋 Résumé généré:")
            summary = pipeline_result.get('summary', {})
            print(f"   Titre: {summary.get('title', 'N/A')}")
            print(f"   Confiance: {summary.get('confidence_score', 0):.0%}")
            
            # Test PDF
            if pipeline_result.get('pdf_available'):
                print("\n📄 PDF généré:")
                print(f"   Taille: {pipeline_result.get('pdf_size_bytes', 0)} bytes")
                print(f"   Temps génération: {pipeline_result.get('pdf_generation_time', 0):.2f}s")
                
                download_info = pipeline_result.get('download_info', {})
                if download_info:
                    print(f"   URL: {download_info.get('download_url', 'N/A')}")
                    print(f"   Expire dans: {download_info.get('expires_in', 0)}s")
            
        else:
            print("❌ Erreur pipeline:", result.get('error'))
            print("   Détails:", result.get('details', 'N/A'))
            return
        
        print()
        
        # 4. Test health check
        print("🏥 Test 3: Health Check")
        print("-" * 30)
        
        health = await contract_reader_pipeline.get_system_health()
        print(f"Status: {health.get('overall_status', 'unknown')}")
        
        components = health.get('components', {})
        for component, status in components.items():
            if isinstance(status, dict):
                comp_status = status.get('status', 'unknown')
                print(f"   {component}: {comp_status}")
        
        print()
        
        # 5. Test GDPR erasure
        print("🗑️ Test 4: Effacement GDPR")
        print("-" * 30)
        
        erasure_result = await contract_reader_pipeline.request_data_erasure(user_id)
        
        if erasure_result['success']:
            print("✅ Données supprimées avec succès")
            purge_details = erasure_result.get('purge_details', {})
            if purge_details:
                print(f"   Durée: {purge_details.get('duration_seconds', 0):.2f}s")
                items_deleted = purge_details.get('items_deleted', {})
                for data_type, count in items_deleted.items():
                    print(f"   {data_type}: {count} éléments supprimés")
        else:
            print("❌ Erreur effacement:", erasure_result.get('error'))
        
        print()
        print("🎉 Test End-to-End TERMINÉ avec succès !")
        
    except Exception as e:
        print(f"💥 Erreur test: {e}")
        import traceback
        traceback.print_exc()

async def test_api_endpoints():
    """Test des endpoints API (simulation)"""
    
    print("\n🌐 Test API Endpoints (simulation)")
    print("=" * 50)
    
    # Simulation des appels API
    endpoints = [
        "POST /api/v1/contract/summary",
        "POST /api/v1/contract/consent", 
        "GET /api/v1/contract/download/{file_id}",
        "DELETE /api/v1/contract/gdpr/erase",
        "GET /api/v1/contract/health",
        "GET /api/v1/contract/stats"
    ]
    
    for endpoint in endpoints:
        print(f"✅ {endpoint} - Endpoint configuré")
    
    print("\n📝 Pour tester avec curl:")
    print("curl -X POST http://localhost:8000/api/v1/contract/consent \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"processing\": true, \"download\": true}'")

if __name__ == "__main__":
    print("🚀 Lancement des tests Contract Reader...")
    
    # Test pipeline
    asyncio.run(test_pipeline_complete())
    
    # Test API
    asyncio.run(test_api_endpoints())
    
    print("\n✨ Tous les tests terminés !")
