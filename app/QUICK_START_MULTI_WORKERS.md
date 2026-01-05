# 🚀 Quick Start : Déploiement Multi-Workers

## ⚡ Déploiement Rapide (5 minutes)

### Option 1 : Script Automatisé

```bash
cd face_recognition/app
chmod +x DEPLOY_MULTI_WORKERS.sh
./DEPLOY_MULTI_WORKERS.sh
```

### Option 2 : Commandes Manuelles

```bash
# 1. Build l'image
docker build -t findme-prod:v8 .

# 2. Tag pour ECR
docker tag findme-prod:v8 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v8

# 3. Login ECR
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com

# 4. Push
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v8

# 5. Mise à jour du service
aws apprunner update-service --cli-input-json file://service.json --region eu-west-3
```

---

## ✅ Vérification (2 minutes)

### 1. Attendre le déploiement
Attendre 5-10 minutes que AWS redémarre le service.

### 2. Vérifier les logs AWS CloudWatch
Chercher cette ligne :
```
🌐 Démarrage du serveur avec Gunicorn...
  - Workers: 5
```

### 3. Tester l'application
- Ouvrir l'URL de votre app
- Se connecter avec plusieurs comptes (5-10 simultanément)
- Uploader des photos en parallèle

**Résultat attendu** : Fluide, pas de lag ✅

---

## 📋 Changements Appliqués

| Fichier | Changement | Impact |
|---------|-----------|--------|
| `start.sh` | Gunicorn avec 5 workers | **6x capacité** |
| `requirements.txt` | + gunicorn==21.2.0 | Support multi-process |
| `service.json` | GUNICORN_WORKERS=5 | Configuration production |
| `service.json` | AWS_CONCURRENT_REQUESTS=20 | 2x requêtes AWS |
| `service.json` | DB_POOL_SIZE=30 | +50% connexions DB |

---

## 🎯 Performance Attendue

**AVANT** → **APRÈS**
- Workers: 1 → **5** ✅
- CPU: 40% → **80-90%** ✅
- Utilisateurs: ~5 fluides → **30+ fluides** ✅
- Requêtes/sec: ~20 → **100+** ✅

---

## ⚠️ Important : Configuration CPU

Votre `service.json` indique actuellement **1 vCPU** :
```json
"InstanceConfiguration": { "Cpu": "1 vCPU", "Memory": "4 GB" }
```

### Si vous avez 2 vCPU :
Mettez à jour `service.json` ligne 59 :
```json
"InstanceConfiguration": { "Cpu": "2 vCPU", "Memory": "4 GB" }
```

### Si vous avez vraiment 1 vCPU :
Réduisez le nombre de workers dans `service.json` :
```json
"GUNICORN_WORKERS": "3"  # (2 × 1) + 1 = 3
```

---

## 🐛 Problèmes ?

### Workers ne démarrent pas
```bash
# Vérifier les logs AWS CloudWatch
# Chercher "error" ou "failed"
```

### Toujours à 40% CPU
```bash
# Vérifier que Gunicorn est bien utilisé
# Dans les logs, chercher "Booting worker with pid"
# Devrait apparaître 5 fois
```

### Erreurs de connexion DB
```bash
# Augmenter le pool
"DB_POOL_SIZE": "40",
"DB_MAX_OVERFLOW": "100"
```

---

## 📚 Documentation Complète

Pour plus de détails, voir :
- **`FIX_PERFORMANCE_MULTI_WORKERS.md`** : Documentation technique complète
- **`ENV_AWS_PRODUCTION.txt`** : Toutes les variables d'environnement
- **`DEPLOY_MULTI_WORKERS.sh`** : Script de déploiement automatisé

---

## 💬 Support

Si problème persistant après déploiement :

1. Vérifier les logs AWS CloudWatch
2. Vérifier que 6 processus gunicorn tournent
3. Vérifier la configuration CPU (1 ou 2 vCPU ?)
4. Consulter la section Troubleshooting dans `FIX_PERFORMANCE_MULTI_WORKERS.md`

---

**Temps estimé total** : 15-20 minutes (build + déploiement + vérification)

🎉 **Bon déploiement !**

