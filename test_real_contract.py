#!/usr/bin/env python3
"""
Test XYQO backend with real contract samples
"""

import os
import json
from xyqo_backend import XYQOHandler

def test_with_real_contract():
    """Test analysis with real contract from samples"""
    
    # Test with the first available contract
    samples_dir = "/Users/bassiroudiop/autopilot-demo/data/samples"
    contracts = [
        "Modele-de-contrat-de-consultance.pdf",
        "contrat_168602_domiciliation.pdf", 
        "contrat_SCF_JAS_WORK4YOU_28022023_01_DIOP_Bassirou.pdf"
    ]
    
    # Create a mock handler for testing
    class MockHandler:
        def __init__(self):
            pass
        
        def _analyze_document_with_openai(self, content, filename):
            from xyqo_backend import XYQOHandler
            temp_handler = type('TempHandler', (), {})()
            for attr in dir(XYQOHandler):
                if not attr.startswith('__') and attr.startswith('_'):
                    setattr(temp_handler, attr, getattr(XYQOHandler, attr))
            return temp_handler._analyze_document_with_openai(temp_handler, content, filename)
    
    handler = MockHandler()
    
    for contract_file in contracts:
        contract_path = os.path.join(samples_dir, contract_file)
        if os.path.exists(contract_path):
            print(f"\n📄 Testing with: {contract_file}")
            
            try:
                # Read the PDF file
                with open(contract_path, 'rb') as f:
                    file_content = f.read()
                
                # Analyze the document
                analysis = handler._analyze_document_with_openai(file_content, contract_file)
                
                if analysis:
                    print("✅ Analysis successful")
                    print(f"📋 Contract Object: {analysis.get('contract', {}).get('object', 'N/A')}")
                    print(f"👥 Parties: {len(analysis.get('parties', {}).get('list', []))}")
                    print(f"💰 Price Model: {analysis.get('financials', {}).get('price_model', 'N/A')}")
                    print(f"📝 Summary: {analysis.get('summary_plain', 'N/A')[:100]}...")
                    
                    # Test JSON serialization
                    json_str = json.dumps(analysis, ensure_ascii=False, indent=2)
                    print(f"📊 JSON size: {len(json_str)} characters")
                    
                else:
                    print("❌ Analysis failed")
                    
            except Exception as e:
                print(f"❌ Error testing {contract_file}: {e}")
            
            break  # Test only the first available contract
    
    print("\n🎯 Real contract test completed")

if __name__ == '__main__':
    test_with_real_contract()
