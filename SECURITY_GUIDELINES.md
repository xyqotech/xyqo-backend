# 🔐 SÉCURITÉ XYQO - CLÉS API ET DONNÉES SENSIBLES

## ⚠️ RÈGLES CRITIQUES DE SÉCURITÉ

### **JAMAIS COMMITER EN PRODUCTION :**
- ❌ **Clés OpenAI** (`OPENAI_API_KEY`)
- ❌ **Clés API** de services tiers
- ❌ **Mots de passe** ou tokens
- ❌ **Données contractuelles** réelles
- ❌ **Informations personnelles** (RGPD)

---

## 🛡️ PROTECTION DES CLÉS API

### **Configuration Locale (.env)**
```bash
# ✅ Fichier .env (JAMAIS commité)
OPENAI_API_KEY=sk-proj-VOTRE_CLE_REELLE_ICI
```

### **Configuration Production**
```bash
# ✅ Variables d'environnement serveur
export OPENAI_API_KEY="sk-proj-PRODUCTION_KEY"
```

### **Vérification .gitignore**
```bash
# ✅ Déjà protégé dans .gitignore
.env
.env.local
.env.production
```

---

## 🔍 VALIDATION AVANT COMMIT

### **Checklist Obligatoire :**
- [ ] **Aucune clé API** dans le code source
- [ ] **Fichiers .env** ignorés par Git
- [ ] **Données de test** anonymisées
- [ ] **Logs** sans informations sensibles

### **Commandes de Vérification :**
```bash
# Rechercher des clés potentielles
grep -r "sk-" . --exclude-dir=.git --exclude-dir=venv
grep -r "API_KEY" . --exclude-dir=.git --exclude-dir=venv

# Vérifier .gitignore
git check-ignore .env
```

---

## 🚨 PROCÉDURE D'URGENCE

### **Si Clé Commitée par Erreur :**
1. **Révoquer immédiatement** la clé sur OpenAI
2. **Générer nouvelle clé** 
3. **Nettoyer l'historique Git** (git filter-branch)
4. **Mettre à jour** la production

### **Rotation des Clés :**
- **Mensuelle** pour la production
- **Après incident** de sécurité
- **Avant déploiement** majeur

---

## 📋 BONNES PRATIQUES

### **Développement Local :**
- ✅ Utiliser `.env.example` comme template
- ✅ Documenter les variables requises
- ✅ Tester sans clés (mode fallback)

### **Production :**
- ✅ Variables d'environnement serveur
- ✅ Monitoring des accès API
- ✅ Logs sans données sensibles
- ✅ Backup sécurisé des configurations

---

## 🎯 COHÉRENCE PROD/LOCAL

**Objectif atteint :** Même comportement entre environnements
- ✅ **Local** : OpenAI + analyse IA complète
- ✅ **Production** : OpenAI + analyse IA complète
- ✅ **Fallback** : Mode dégradé si clé indisponible

**Cette cohérence garantit des tests fiables et un déploiement sans surprise.**
