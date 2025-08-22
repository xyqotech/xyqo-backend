#!/usr/bin/env python3
"""
Script de test pour reproduire l'erreur PDF
"""

import requests
import os

def test_pdf_extraction():
    """Test d'extraction avec un fichier PDF"""
    
    # Chemin vers un PDF de test
    pdf_path = "/Users/bassiroudiop/autopilot-demo/data/samples/Modele-de-contrat-de-consultance.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"Fichier PDF non trouvé: {pdf_path}")
        return
    
    print(f"Test d'extraction PDF: {pdf_path}")
    print(f"Taille: {os.path.getsize(pdf_path)} bytes")
    
    # Requête vers l'API
    url = "http://localhost:8000/api/v1/extract"
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            response = requests.post(url, files=files, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Extraction réussie!")
            print(f"Session ID: {data.get('session_id')}")
            print(f"Type: {data.get('extraction', {}).get('contract_type')}")
            print(f"Confiance: {data.get('extraction', {}).get('confidence_score')}")
        else:
            print("❌ Erreur d'extraction:")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Erreur de requête: {str(e)}")

if __name__ == "__main__":
    test_pdf_extraction()
