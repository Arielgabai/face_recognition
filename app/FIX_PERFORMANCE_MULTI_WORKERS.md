# 🚀 Fix Performance : Multi-Workers pour 30+ Utilisateurs Simultanés

## 📊 Diagnostic du Problème

### Symptômes Observés
- ✗ **30 utilisateurs** simultanés causaient des lags et bugs
- ✗ **CPU à 40%** maximum alors qu'il y a 2 vCPU disponibles
- ✗ Ressources sous-utilisées malgré la charge

### Cause Racine Identifiée 🎯
**1 seul worker Uvicorn** → Toutes les requêtes traitées séquentiellement !

```bash
# AVANT (problématique)
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --log-level info
# ⚠️ 1 seul processus = 1 seul cœur utilisé = 50% CPU max sur 2 vCPU
```

**Résultat** : Les requêtes s'accumulent dans la queue au lieu d'être traitées en parallèle.

---

## ✅ Solutions Mises en Place

### 1. 🔧 Multi-Workers avec Gunicorn

**Fichier modifié** : `start.sh`

```bash
# APRÈS (optimisé)
WORKERS=${GUNICORN_WORKERS:-5}  # (2 x CPU) + 1 = 5 workers

exec gunicorn main:app \
  --workers ${WORKERS} \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-10000} \
  --timeout 120 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --log-level info
```

**Bénéfices** :
- ✓ **5 processus** travaillent en parallèle
- ✓ **Utilisation CPU** : 70-90% sous charge (vs 40% avant)
- ✓ **30+ utilisateurs** supportés simultanément
- ✓ **Graceful restarts** : les workers se recyclent automatiquement

---

### 2. ⚡ Augmentation Concurrence AWS Rekognition

**Fichier modifié** : `service.json` + `ENV_AWS_PRODUCTION.txt`

```bash
# AVANT
AWS_CONCURRENT_REQUESTS=10  # Trop bas pour 5 workers

# APRÈS
AWS_CONCURRENT_REQUESTS=20  # 4 requêtes/worker en moyenne
```

**Impact** : Les requêtes de reconnaissance faciale ne bloquent plus les autres workers.

---

### 3. 🗄️ Pool de Connexions DB Augmenté

**Fichier modifié** : `service.json`

```bash
# AVANT
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=50  # Total: 70 connexions

# APRÈS
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=70  # Total: 100 connexions
```

**Formule recommandée** : 
- Pool size = workers × 6 connexions/worker
- Overflow = marge pour les pics de charge

---

### 4. 📦 Ajout de Gunicorn

**Fichier modifié** : `requirements.txt`

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
gunicorn==21.2.0  # ← NOUVEAU
```

---

## 📈 Résultats Attendus

| Métrique | Avant | Après |
|----------|-------|-------|
| **Workers** | 1 😱 | 5 ✅ |
| **Requêtes parallèles** | 1 | 5-10+ |
| **AWS concurrent** | 10 | 20 |
| **DB connexions** | 70 max | 100 max |
| **Utilisation CPU** | 40% | 80-90% ✅ |
| **Utilisateurs fluides** | ~5 | **30+** ✅ |
| **Temps de réponse** | Variable | Stable |

---

## 🚀 Déploiement

### Étape 1 : Mise à Jour des Dépendances

```bash
cd face_recognition/app
pip install -r requirements.txt
```

### Étape 2 : Vérifier la Configuration

Vérifiez que `service.json` contient les nouvelles variables :

```json
"RuntimeEnvironmentVariables": {
  "GUNICORN_WORKERS": "5",
  "AWS_CONCURRENT_REQUESTS": "20",
  "DB_POOL_SIZE": "30",
  "DB_MAX_OVERFLOW": "70"
}
```

### Étape 3 : Déployer sur AWS

```bash
# Build et push de la nouvelle image Docker
docker build -t findme-prod:v8 .
docker tag findme-prod:v8 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v8
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v8

# Mise à jour du service AWS App Runner
aws apprunner update-service \
  --cli-input-json file://service.json \
  --region eu-west-3
```

### Étape 4 : Vérification Post-Déploiement

#### A. Vérifier que les workers tournent

Connectez-vous à votre instance AWS (logs ou SSH) et exécutez :

```bash
ps aux | grep gunicorn
```

**Résultat attendu** : 6 processus
```
gunicorn: master [main:app]        # 1 master
gunicorn: worker [main:app]        # worker 1
gunicorn: worker [main:app]        # worker 2
gunicorn: worker [main:app]        # worker 3
gunicorn: worker [main:app]        # worker 4
gunicorn: worker [main:app]        # worker 5
```

#### B. Vérifier les logs de démarrage

Dans AWS CloudWatch ou logs App Runner, cherchez :

```
🌐 Démarrage du serveur avec Gunicorn...
  - Workers: 5
  - Port: 10000
  - Timeout: 120s
[INFO] Booting worker with pid: ...
[INFO] Booting worker with pid: ...
[INFO] Booting worker with pid: ...
[INFO] Booting worker with pid: ...
[INFO] Booting worker with pid: ...
```

#### C. Test de Charge

Utilisez un outil comme `ab` (Apache Bench) ou `wrk` :

```bash
# Test avec 30 connexions simultanées
ab -n 1000 -c 30 https://votre-app.amazonaws.com/

# Résultat attendu:
# - Requests per second: > 100
# - Time per request: < 300ms (moyenne)
# - Failed requests: 0
```

---

## 🎯 Configuration Adaptative

### Pour Plus de Charge (50+ utilisateurs)

**Option 1** : Augmenter les workers (si vous passez à 4 vCPU)

```bash
# Pour 4 vCPU: (2 × 4) + 1 = 9 workers
GUNICORN_WORKERS=9
AWS_CONCURRENT_REQUESTS=30
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
```

**Option 2** : Auto-scaling AWS App Runner

Votre configuration actuelle utilise déjà l'auto-scaling :
```json
"AutoScalingConfigurationArn": "arn:aws:apprunner:eu-west-3:801541932532:autoscalingconfiguration/findme-autoscaling-v2/1/..."
```

→ AWS créera automatiquement des instances supplémentaires si la charge dépasse les capacités.

---

### Pour Économiser (Environnement de Test)

```bash
# Configuration minimale
GUNICORN_WORKERS=2
AWS_CONCURRENT_REQUESTS=5
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

---

## 🔍 Monitoring et Diagnostic

### Métriques à Surveiller

#### 1. Utilisation CPU (CloudWatch)

**Attendu** : 70-90% sous charge normale

Si < 50% : Workers insuffisamment utilisés
Si > 95% : Augmenter les ressources ou l'auto-scaling

#### 2. Connexions Base de Données

**Attendu** : 15-40 connexions actives avec 30 utilisateurs

Commande PostgreSQL :
```sql
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
```

Si > 80 connexions : Augmenter `DB_MAX_OVERFLOW`

#### 3. Temps de Réponse AWS Rekognition

**Attendu** : 200-500ms par requête

Dans les logs, cherchez :
```
[aws_face_recognizer] IndexFaces: 245ms
[aws_face_recognizer] SearchFaces: 312ms
```

Si > 1000ms : Possible throttling AWS → Vérifier les quotas

#### 4. Queue Gunicorn

**Attendu** : < 10 requêtes en attente

Si > 50 : Augmenter `GUNICORN_WORKERS` ou activer l'auto-scaling

---

## ⚠️ Points d'Attention

### 1. Instance Configuration

**IMPORTANT** : Votre `service.json` indique actuellement :
```json
"InstanceConfiguration": { "Cpu": "1 vCPU", "Memory": "4 GB" }
```

**Recommandation** : Si vous avez vraiment 2 vCPU (comme mentionné), mettez à jour :
```json
"InstanceConfiguration": { "Cpu": "2 vCPU", "Memory": "4 GB" }
```

Sinon, ajustez `GUNICORN_WORKERS` à **3** pour 1 vCPU : `(2 × 1) + 1 = 3`

### 2. Quotas AWS Rekognition

Vérifiez vos limites dans la console AWS :
- **IndexFaces** : 50 TPS (transactions par seconde) par défaut
- **SearchFaces** : 50 TPS par défaut

Avec 20 requêtes concurrentes, vous pouvez atteindre ces limites.

**Solution** : Demander une augmentation de quota via AWS Support si nécessaire.

### 3. Coûts AWS

Plus de workers = plus de requêtes parallèles = coûts AWS Rekognition potentiellement plus élevés.

**Monitoring** : Activez AWS Cost Explorer et surveillez :
- Nombre d'appels Rekognition
- Coût par jour/mois

---

## 🐛 Troubleshooting

### Problème : Workers ne démarrent pas

**Symptôme** : 1 seul processus gunicorn visible

**Causes possibles** :
1. Gunicorn pas installé → Vérifier `pip list | grep gunicorn`
2. Variable `GUNICORN_WORKERS` pas définie → Vérifier les env vars
3. Erreur dans `start.sh` → Vérifier les logs de démarrage

**Solution** :
```bash
# Test manuel
gunicorn main:app --workers 5 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:10000
```

---

### Problème : Timeouts fréquents

**Symptôme** : Erreurs 504 Gateway Timeout

**Causes possibles** :
1. Workers surchargés → Augmenter `GUNICORN_WORKERS`
2. Timeout trop court → Augmenter `--timeout` dans start.sh
3. Requêtes AWS lentes → Vérifier throttling

**Solution** :
```bash
# Dans start.sh, augmenter le timeout
--timeout 180  # au lieu de 120
```

---

### Problème : Erreurs de connexion DB

**Symptôme** : `psycopg2.OperationalError: connection pool exhausted`

**Cause** : Trop de connexions simultanées

**Solution** :
```bash
DB_POOL_SIZE=40
DB_MAX_OVERFLOW=100
```

---

## 📚 Références

### Documentation Gunicorn
- Settings : https://docs.gunicorn.org/en/stable/settings.html
- Workers : https://docs.gunicorn.org/en/stable/design.html#how-many-workers

### Formule Workers
```
workers = (2 × CPU) + 1
```

Source : https://docs.gunicorn.org/en/stable/design.html#how-many-workers

### AWS Rekognition Quotas
- https://docs.aws.amazon.com/rekognition/latest/dg/limits.html

---

## ✅ Checklist Finale

Avant de considérer le déploiement terminé :

- [ ] `gunicorn` ajouté à `requirements.txt` ✓
- [ ] `start.sh` modifié avec multi-workers ✓
- [ ] Variables d'environnement mises à jour dans `service.json` ✓
- [ ] Configuration CPU/Memory vérifiée dans AWS
- [ ] Image Docker buildée et pushée
- [ ] Service AWS App Runner mis à jour
- [ ] Logs de démarrage vérifiés (6 processus gunicorn)
- [ ] Test de charge effectué (30+ utilisateurs)
- [ ] Monitoring CPU activé (70-90% attendu)
- [ ] Quotas AWS Rekognition vérifiés
- [ ] Documentation équipe partagée

---

## 🎉 Résumé

**Le problème** : 1 worker = 1 cœur = 50% CPU max = lags avec 30 users

**La solution** : 5 workers = parallélisation = 90% CPU = 30+ users fluides

**Impact estimé** :
- **6x plus de capacité** (1 → 5 workers)
- **2x plus de requêtes AWS** (10 → 20 concurrent)
- **1.4x plus de connexions DB** (70 → 100 max)
- **= Support de 30+ utilisateurs simultanés sans lag** ✅

---

*Documentation créée le : 2025-01-05*
*Version : 1.0*

