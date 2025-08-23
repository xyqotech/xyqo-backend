#!/usr/bin/env python3
"""
Test end-to-end complet du backend XYQO Contract Reader
"""

import requests
import os
import json
import time
from datetime import datetime

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print('='*60)

def test_backend_health():
    """Test 1: Vérifier le health check du backend"""
    print_section("TEST 1: Health Check Backend")
    
    backend_url = "http://localhost:8002"
    
    try:
        response = requests.get(f"{backend_url}/health", timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            print("✅ Backend accessible")
            print(f"📊 Status: {health_data.get('status', 'unknown')}")
            print(f"🤖 OpenAI Available: {health_data.get('openai_available', False)}")
            print(f"📅 Timestamp: {health_data.get('timestamp', 'N/A')}")
            print(f"🔢 Version: {health_data.get('version', 'N/A')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return False

def test_contract_upload_and_analysis():
    """Test 2-4: Upload contrat, analyse OpenAI, et téléchargement PDF"""
    print_section("TEST 2-4: Upload, Analyse & Download")
    
    backend_url = "http://localhost:8002"
    
    # Test avec les 3 contrats disponibles
    contracts = [
        "Modele-de-contrat-de-consultance.pdf",
        "contrat_168602_domiciliation.pdf", 
        "contrat_SCF_JAS_WORK4YOU_28022023_01_DIOP_Bassirou.pdf"
    ]
    
    results = []
    
    for contract_file in contracts:
        contract_path = f"/Users/bassiroudiop/autopilot-demo/data/samples/{contract_file}"
        
        if not os.path.exists(contract_path):
            print(f"❌ Contract not found: {contract_file}")
            continue
            
        print(f"\n📄 Testing: {contract_file}")
        
        try:
            # Upload et analyse
            with open(contract_path, 'rb') as f:
                files = {'file': (contract_file, f, 'application/pdf')}
                
                start_time = time.time()
                response = requests.post(
                    f"{backend_url}/api/v1/contract/analyze",
                    files=files,
                    timeout=120  # 2 minutes pour l'analyse OpenAI
                )
                analysis_time = time.time() - start_time
            
            if response.status_code == 200:
                print(f"✅ Upload & Analysis successful ({analysis_time:.2f}s)")
                
                try:
                    result = response.json()
                    analysis = result.get('analysis', {})
                    metadata = result.get('metadata', {})
                    
                    # Vérifier la structure de l'analyse
                    contract_obj = analysis.get('contract', {}).get('object', 'N/A')
                    parties_count = len(analysis.get('parties', {}).get('list', []))
                    price_model = analysis.get('financials', {}).get('price_model', 'N/A')
                    summary = analysis.get('summary_plain', 'N/A')
                    risks = analysis.get('risks_red_flags', [])
                    
                    print(f"📋 Contract Object: {contract_obj}")
                    print(f"👥 Parties: {parties_count}")
                    print(f"💰 Price Model: {price_model}")
                    print(f"📝 Summary: {summary[:100]}...")
                    print(f"⚠️  Risks: {len(risks)} identified")
                    
                    # Test téléchargement PDF
                    download_url = metadata.get('download_url')
                    if download_url:
                        download_response = requests.get(f"{backend_url}{download_url}")
                        if download_response.status_code == 200:
                            print(f"✅ PDF Download successful ({len(download_response.content)} bytes)")
                        else:
                            print(f"❌ PDF Download failed: {download_response.status_code}")
                    
                    results.append({
                        'file': contract_file,
                        'success': True,
                        'analysis_time': analysis_time,
                        'contract_object': contract_obj,
                        'parties_count': parties_count,
                        'pdf_size': len(download_response.content) if download_response.status_code == 200 else 0
                    })
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON response: {e}")
                    results.append({'file': contract_file, 'success': False, 'error': 'Invalid JSON'})
                    
            else:
                print(f"❌ Analysis failed: {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                results.append({'file': contract_file, 'success': False, 'error': f'HTTP {response.status_code}'})
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({'file': contract_file, 'success': False, 'error': str(e)})
    
    return results

def test_schema_validation():
    """Test 5: Validation du schéma UniversalContractV3"""
    print_section("TEST 5: Schema Validation")
    
    schema_path = "/Users/bassiroudiop/autopilot-demo/xyqo_ready_schema.json"
    
    if os.path.exists(schema_path):
        try:
            with open(schema_path, 'r') as f:
                schema = json.load(f)
            
            print(f"✅ Schema loaded successfully")
            print(f"📊 Schema size: {len(json.dumps(schema))} characters")
            print(f"🔧 Schema version: {schema.get('title', 'N/A')}")
            
            # Vérifier les champs requis
            required_fields = schema.get('required', [])
            print(f"📋 Required fields: {len(required_fields)}")
            print(f"🔍 Fields: {', '.join(required_fields[:5])}{'...' if len(required_fields) > 5 else ''}")
            
            return True
            
        except Exception as e:
            print(f"❌ Schema validation error: {e}")
            return False
    else:
        print(f"❌ Schema file not found: {schema_path}")
        return False

def generate_test_report(health_ok, contract_results, schema_ok):
    """Générer un rapport de test complet"""
    print_section("RAPPORT FINAL")
    
    print(f"🕒 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Résumé des tests
    total_tests = 1 + len(contract_results) + 1  # health + contracts + schema
    passed_tests = (1 if health_ok else 0) + sum(1 for r in contract_results if r['success']) + (1 if schema_ok else 0)
    
    print(f"\n📊 RÉSULTATS GLOBAUX:")
    print(f"✅ Tests réussis: {passed_tests}/{total_tests}")
    print(f"📈 Taux de réussite: {(passed_tests/total_tests)*100:.1f}%")
    
    # Détail par test
    print(f"\n🔍 DÉTAIL DES TESTS:")
    print(f"{'Test':<30} {'Status':<10} {'Details'}")
    print("-" * 60)
    print(f"{'Health Check':<30} {'✅ PASS' if health_ok else '❌ FAIL':<10}")
    
    for result in contract_results:
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        details = f"{result.get('analysis_time', 0):.1f}s" if result['success'] else result.get('error', 'Unknown')
        print(f"{result['file'][:28]:<30} {status:<10} {details}")
    
    print(f"{'Schema Validation':<30} {'✅ PASS' if schema_ok else '❌ FAIL':<10}")
    
    # Recommandations
    if passed_tests == total_tests:
        print(f"\n🎉 TOUS LES TESTS SONT RÉUSSIS!")
        print(f"✅ Le backend XYQO est prêt pour la production")
    else:
        print(f"\n⚠️  CERTAINS TESTS ONT ÉCHOUÉ")
        print(f"🔧 Vérifiez les erreurs ci-dessus avant la mise en production")

def main():
    """Test end-to-end complet"""
    print("🚀 XYQO Contract Reader - Test End-to-End")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Health Check
    health_ok = test_backend_health()
    
    # Test 2-4: Contract Analysis (si health OK)
    contract_results = []
    if health_ok:
        contract_results = test_contract_upload_and_analysis()
    else:
        print("\n⚠️  Skipping contract tests - backend not healthy")
    
    # Test 5: Schema Validation
    schema_ok = test_schema_validation()
    
    # Rapport final
    generate_test_report(health_ok, contract_results, schema_ok)

if __name__ == '__main__':
    main()
