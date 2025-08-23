#!/usr/bin/env python3
"""
Test XYQO backend integration with real contract upload
"""

import requests
import os
import json

def test_backend_with_real_contract():
    """Test the backend with a real contract upload"""
    
    backend_url = "http://localhost:8002"
    
    # Test health check first
    try:
        health_response = requests.get(f"{backend_url}/health")
        if health_response.status_code == 200:
            health_data = health_response.json()
            print("✅ Backend health check passed")
            print(f"📊 OpenAI Available: {health_data.get('openai_available', False)}")
        else:
            print("❌ Backend health check failed")
            return
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return
    
    # Test with real contract
    contract_path = "/Users/bassiroudiop/autopilot-demo/data/samples/Modele-de-contrat-de-consultance.pdf"
    
    if not os.path.exists(contract_path):
        print(f"❌ Contract file not found: {contract_path}")
        return
    
    print(f"\n📄 Testing contract upload: {os.path.basename(contract_path)}")
    
    try:
        with open(contract_path, 'rb') as f:
            files = {'file': (os.path.basename(contract_path), f, 'application/pdf')}
            
            response = requests.post(
                f"{backend_url}/api/v1/contract/analyze",
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            print("✅ Contract analysis successful")
            
            try:
                result = response.json()
                
                print(f"📋 Contract Object: {result.get('analysis', {}).get('contract', {}).get('object', 'N/A')}")
                print(f"👥 Parties: {len(result.get('analysis', {}).get('parties', {}).get('list', []))}")
                print(f"💰 Price Model: {result.get('analysis', {}).get('financials', {}).get('price_model', 'N/A')}")
                
                # Test download URL
                download_url = result.get('metadata', {}).get('download_url')
                if download_url:
                    print(f"📥 Download URL: {download_url}")
                    
                    # Test PDF download
                    download_response = requests.get(f"{backend_url}{download_url}")
                    if download_response.status_code == 200:
                        print("✅ PDF download successful")
                        print(f"📄 PDF size: {len(download_response.content)} bytes")
                    else:
                        print(f"❌ PDF download failed: {download_response.status_code}")
                
                print("✅ Full integration test passed")
                
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON response: {e}")
                print(f"Response: {response.text[:500]}...")
                
        else:
            print(f"❌ Contract analysis failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during contract upload: {e}")

if __name__ == '__main__':
    print("🧪 Testing XYQO Backend Integration")
    print("=" * 50)
    test_backend_with_real_contract()
    print("\n🎯 Integration test completed")
