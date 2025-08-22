# 🚀 AUTOPILOT - IA d'Automatisation de Processus Métier

## 🎯 Vue d'ensemble

**AUTOPILOT** transforme vos documents métier en actions automatiques dans vos systèmes d'information.

**Démo :** Document contractuel → Extraction IA → Ticket Jira automatique → Notification équipe

## 🏗️ Architecture

```
Frontend (xyqo.ai) ←→ AUTOPILOT API (FastAPI) ←→ Jira Cloud
                              ↓
                        PostgreSQL + Redis
```

## 🚀 Démarrage rapide

### 1. Installation
```bash
# Clone et setup
git clone <repo>
cd autopilot-demo

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Infrastructure
cd ../infra
docker-compose up -d
```

### 2. Configuration
```bash
cp .env.example .env
# Éditer .env avec vos clés API
```

### 3. Lancement
```bash
# Backend API
cd backend
uvicorn app:app --reload --port 8000

# Test
curl -X POST "http://localhost:8000/api/v1/extract" \
  -F "file=@../data/samples/contract_1.txt"
```

## 📁 Structure du projet

```
autopilot-demo/
├── backend/           # API FastAPI
├── infra/            # Docker + PostgreSQL
├── data/             # Échantillons et golden set
├── config/           # Configuration YAML
└── docs/             # Documentation
```

## 🔧 Endpoints principaux

- `POST /api/v1/extract` - Extraction de document
- `GET /api/v1/health` - Health check
- `GET /api/v1/metrics` - Métriques Prometheus
- `GET /api/v1/quality/dashboard` - Dashboard qualité

## 📊 Métriques de qualité

- **Précision** : ≥ 95% sur champs critiques
- **Latence** : < 8s (P95)
- **Coût** : ≤ 0,08€ par extraction
- **Disponibilité** : > 99.9%

## 🔐 Sécurité

- Validation stricte des fichiers (taille, type, antivirus)
- PII redaction dans les logs
- Rate limiting (5 req/min/IP)
- CORS et CSP configurés

## 🎬 Démo

1. Upload document (PDF/DOCX/TXT)
2. Extraction IA en temps réel
3. Ticket Jira créé automatiquement
4. Métriques qualité affichées

**Durée :** 3 minutes  
**Précision :** 95%+  
**Coût :** 0,08€ par extraction

---

Développé pour démontrer l'automatisation IA des processus métier.
