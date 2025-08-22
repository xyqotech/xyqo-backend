# 🚀 AUTOPILOT - Guide de Configuration Démo

## ✅ État Actuel

**Backend AUTOPILOT fonctionnel** avec :
- ✅ API FastAPI sur `http://localhost:8000`
- ✅ PostgreSQL + Redis via Docker
- ✅ Endpoints sécurisés et rate limiting
- ✅ Cache intelligent Redis
- ✅ Validation fichiers et guardrails
- ✅ Gestion d'erreurs robuste

## 🔧 Configuration Requise

### 1. Clé OpenAI
```bash
# Éditer le fichier .env
nano /Users/bassiroudiop/autopilot-demo/.env

# Remplacer :
OPENAI_API_KEY=your-openai-api-key-here
```

### 2. Configuration Jira (optionnel)
```bash
# Dans .env :
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=your-email@company.com  
JIRA_API_TOKEN=your-jira-api-token
```

## 🎯 Test de la Démo

### 1. Démarrer les services
```bash
cd /Users/bassiroudiop/autopilot-demo/infra
docker-compose up -d postgres redis

cd /Users/bassiroudiop/autopilot-demo/backend
source .venv/bin/activate
python app.py
```

### 2. Tester l'extraction
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Test extraction
curl -X POST "http://localhost:8000/api/v1/extract" \
  -F "file=@../data/samples/contract_1.txt"
```

### 3. Interface Web
- **API Docs** : http://localhost:8000/docs
- **Métriques** : http://localhost:8000/api/v1/metrics
- **Dashboard** : http://localhost:8000/api/v1/quality/dashboard

## 📊 Endpoints Disponibles

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/` | GET | Status API |
| `/api/v1/health` | GET | Health check |
| `/api/v1/ready` | GET | Readiness check |
| `/api/v1/extract` | POST | Extraction document |
| `/api/v1/metrics` | GET | Métriques Prometheus |
| `/api/v1/quality/dashboard` | GET | Dashboard qualité |
| `/api/v1/demo/reset` | POST | Reset environnement |

## 🔐 Sécurité Intégrée

- ✅ Validation fichiers (taille, type, contenu)
- ✅ Rate limiting (5 req/min/IP)
- ✅ Headers sécurité (CORS, CSP, XSS)
- ✅ PII redaction dans logs
- ✅ Antivirus ClamAV (production)

## 📈 Métriques & Monitoring

- **Cache Redis** : Hit rate, performance
- **Qualité LLM** : Confidence score, précision
- **Performance** : Latence P95, throughput
- **Business** : Conversions, coût par extraction

## 🎬 Démo Prête

L'API est **prête pour démonstration** avec :
- Interface Swagger interactive
- Échantillons de contrats
- Gestion d'erreurs élégante
- Métriques temps réel
- Mode sandbox sécurisé

**Prochaine étape** : Ajouter votre clé OpenAI pour activer l'extraction IA complète.
