# 🧪 GUIDE DE TEST LOCAL XYQO BACKEND

## 🚀 DÉMARRAGE RAPIDE

### Prérequis
```bash
cd /Users/bassiroudiop/xyqo-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration
```bash
# Copier le fichier d'environnement
cp .env.example .env

# Éditer .env avec vos clés API
# OPENAI_API_KEY=your_openai_api_key_here
```

### Lancement
```bash
source venv/bin/activate
python3 xyqo_backend.py
```

**Backend disponible sur : http://localhost:8002**

---

## 🧪 TESTS OBLIGATOIRES

### Test 1 : Health Check
```bash
curl http://localhost:8002/health
```
**Attendu :** `{"status": "healthy", "openai_available": true/false}`

### Test 2 : Analyse Contrat
```bash
curl -X POST http://localhost:8002/api/v1/contract/analyze \
  -F "file=@test_contract.pdf" \
  -H "Content-Type: multipart/form-data"
```

**Attendu :** JSON UniversalContractV3 avec `summary_plain` structuré

### Test 3 : Téléchargement PDF
```bash
# Utiliser l'URL retournée par l'analyse
curl http://localhost:8002/download/{analysis_id}.pdf -o test_output.pdf
```

**Attendu :** PDF avec résumé Board-Ready V2.3

---

## ✅ CHECKLIST DE VALIDATION

### Backend Fonctionnel
- [ ] Port 8002 accessible
- [ ] Health check répond
- [ ] OpenAI configuré (si clé disponible)
- [ ] Analyse PDF fonctionne
- [ ] Génération PDF opérationnelle

### Qualité des Résultats
- [ ] JSON conforme UniversalContractV3
- [ ] `summary_plain` avec 9 rubriques
- [ ] Mapping par famille de contrat
- [ ] PDF lisible et structuré
- [ ] Données sensibles masquées

### Performance
- [ ] Analyse < 30 secondes
- [ ] PDF généré < 5 secondes
- [ ] Pas de fuite mémoire
- [ ] Logs propres

---

## 🔧 DÉPANNAGE

### Erreur Port 8002 Occupé
```bash
lsof -ti:8002 | xargs kill -9
```

### Erreur OpenAI
- Vérifier clé API dans `.env`
- Mode fallback disponible sans OpenAI

### Erreur Dépendances
```bash
pip install --upgrade -r requirements.txt
```

---

**Ce guide garantit un backend local fonctionnel pour les tests bout en bout.**
