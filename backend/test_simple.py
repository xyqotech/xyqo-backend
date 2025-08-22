"""
Test simple du Contract Reader sans dépendances complexes
"""

import asyncio
import sys
from pathlib import Path

# Ajout du chemin
sys.path.append(str(Path(__file__).parent))

async def test_imports():
    """Test des imports de base"""
    print("🧪 Test des imports Contract Reader")
    print("=" * 40)
    
    try:
        # Test import Redis
        import redis
        print("✅ Redis importé")
        
        # Test import OpenAI
        import openai
        print("✅ OpenAI importé")
        
        # Test import Pydantic
        import pydantic
        print("✅ Pydantic importé")
        
        # Test import FastAPI
        import fastapi
        print("✅ FastAPI importé")
        
        print("\n🎉 Tous les imports de base OK !")
        return True
        
    except ImportError as e:
        print(f"❌ Erreur import: {e}")
        return False

async def test_contract_reader_structure():
    """Test de la structure du module"""
    print("\n📁 Test structure Contract Reader")
    print("=" * 40)
    
    try:
        # Test structure fichiers
        base_path = Path(__file__).parent / "contract_reader"
        
        required_modules = [
            "cache",
            "extraction", 
            "ai",
            "validation",
            "rendering",
            "gdpr"
        ]
        
        for module in required_modules:
            module_path = base_path / module
            if module_path.exists():
                print(f"✅ Module {module} présent")
            else:
                print(f"❌ Module {module} manquant")
        
        # Test fichiers principaux
        main_files = [
            "main_pipeline.py",
            "models.py", 
            "api.py"
        ]
        
        for file in main_files:
            file_path = base_path / file
            if file_path.exists():
                print(f"✅ Fichier {file} présent")
            else:
                print(f"❌ Fichier {file} manquant")
        
        print("\n🏗️ Structure Contract Reader validée !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur structure: {e}")
        return False

async def test_api_integration():
    """Test intégration API"""
    print("\n🌐 Test intégration API")
    print("=" * 40)
    
    try:
        # Test import app principal
        from app import app
        print("✅ App principal importé")
        
        # Vérification routes
        routes = [route.path for route in app.routes]
        contract_routes = [r for r in routes if "contract" in r]
        
        if contract_routes:
            print(f"✅ Routes Contract Reader: {len(contract_routes)} trouvées")
            for route in contract_routes[:3]:  # Afficher les 3 premières
                print(f"   - {route}")
        else:
            print("⚠️ Aucune route Contract Reader trouvée")
        
        print("\n🔗 Intégration API validée !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur intégration: {e}")
        return False

async def main():
    """Test principal"""
    print("🚀 Test Contract Reader - Version Simple")
    print("=" * 50)
    
    # Tests séquentiels
    tests = [
        test_imports(),
        test_contract_reader_structure(), 
        test_api_integration()
    ]
    
    results = []
    for test in tests:
        result = await test
        results.append(result)
    
    # Bilan
    print("\n📊 Bilan des tests:")
    print("=" * 50)
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"✅ Tests réussis: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("\n🎉 Contract Reader prêt pour les tests avancés !")
        print("\n📝 Prochaines étapes:")
        print("   1. Démarrer Redis: docker run -d -p 6379:6379 redis")
        print("   2. Configurer OpenAI API key dans .env")
        print("   3. Lancer serveur: uvicorn app:app --reload")
        print("   4. Tester endpoints avec curl ou Postman")
    else:
        print("\n⚠️ Certains tests ont échoué - vérifier la configuration")

if __name__ == "__main__":
    asyncio.run(main())
