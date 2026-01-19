# 🚀 DÉPLOIEMENT IMMÉDIAT - FIX TIMEOUT v101

## ✅ Modifications appliquées

1. **`main.py`** (ligne 5200) : Migration du matching vers ThreadPool dans `/api/register-with-event-code`
2. **`start.sh`** : Utilisation de `gunicorn_config.py` pour configuration simplifiée
3. Scripts de déploiement créés

## 📋 Variables d'environnement AWS App Runner

**CRITIQUE : Configurez ces variables AVANT le déploiement dans AWS Console**

```bash
# === THREADPOOL (NOUVEAU - CRITIQUE) ===
MATCHING_THREAD_POOL_SIZE=10

# === GUNICORN ===
GUNICORN_WORKERS=3
PORT=10000
TIMEOUT=120

# === PERFORMANCE ===
BCRYPT_ROUNDS=8
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# === AWS REKOGNITION ===
AWS_ACCESS_KEY_ID=<votre_clé>
AWS_SECRET_ACCESS_KEY=<votre_secret>
AWS_REGION=eu-west-3
AWS_REKOGNITION_COLLECTION_ID=<votre_collection>

# === BASE DE DONNÉES ===
DATABASE_URL=<votre_postgres_url>

# === JWT ===
SECRET_KEY=<votre_secret_min_32_chars>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=525600
```

## 🛠️ Étape 1 : Configurer les variables dans AWS Console

1. Allez sur AWS App Runner Console :
   ```
   https://eu-west-3.console.aws.amazon.com/apprunner/home?region=eu-west-3#/services
   ```

2. Sélectionnez votre service `findme-prod-v7`

3. Cliquez sur **Configuration** → **Edit**

4. Ajoutez/modifiez les variables d'environnement listées ci-dessus

5. **IMPORTANT** : Ajoutez `MATCHING_THREAD_POOL_SIZE=10` (nouvelle variable)

6. Cliquez **Save**

## 🚀 Étape 2 : Build et déployer l'image

### Option A : Script automatique (Windows PowerShell)

```powershell
cd face_recognition/app
chmod +x deploy_fix_timeout.sh
bash deploy_fix_timeout.sh
```

### Option B : Manuelle (si script échoue)

```powershell
# 1. Variables
$AWS_REGION = "eu-west-3"
$ECR_REGISTRY = "801541932532.dkr.ecr.eu-west-3.amazonaws.com"
$ECR_REPO = "findme-prod"
$IMAGE_TAG = "v101"

# 2. Login ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# 3. Build
docker build -t "${ECR_REPO}:${IMAGE_TAG}" -f Dockerfile .

# 4. Tag
docker tag "${ECR_REPO}:${IMAGE_TAG}" "${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}"

# 5. Push
docker push "${ECR_REGISTRY}/${ECR_REPO}:${IMAGE_TAG}"

# 6. Update App Runner
aws apprunner update-service --cli-input-json file://update-image.json --region $AWS_REGION
```

## ⏳ Étape 3 : Attendre le déploiement

Le déploiement prend **5-10 minutes**.

Surveillez les logs dans AWS Console :
```
https://eu-west-3.console.aws.amazon.com/apprunner/home?region=eu-west-3#/services/findme-prod-v7/logs
```

**Logs attendus** :
```
[Init] ThreadPool matching initialisé avec 10 workers
🚀 GUNICORN - CONFIGURATION
  Workers           : 3
  Worker class      : uvicorn.workers.UvicornWorker
  ThreadPool Matching: 10
```

## 🧪 Étape 4 : Test de charge

Après déploiement, testez immédiatement :

```powershell
cd face_recognition/app
locust -f locust_file.py --host=https://votre-app-url.com
```

**Ouvrez** : http://localhost:8089

**Paramètres du test** :
- **Nombre d'utilisateurs** : 30
- **Spawn rate** : 5 users/seconde

**Cliquez** : Start swarming

## 📊 Résultats attendus

| Endpoint | Latence médiane | Taux d'échec | Notes |
|----------|----------------|--------------|-------|
| `/api/register-with-event-code` | **< 5s** | **0%** | Était 11s avant |
| `/api/upload-selfie` | **< 10s** | **0%** | Était 45s avec 20% fail |
| `/api/check-user-availability` | < 2s | 0% | - |
| `/api/login` | < 3s | 0% | - |

**Logs attendus (pas d'erreurs)** :
```
[RegisterEventCode] Matching scheduled in thread pool for user_id=XXX
[MATCH-SELFIE] START user_id=XXX event_id=YYY
✅ PAS DE "WORKER TIMEOUT"
✅ PAS DE "Worker was sent code 134"
```

## ❌ Si ça échoue encore

### Symptôme 1 : Toujours des timeouts

**Vérifiez** :
1. Variable `MATCHING_THREAD_POOL_SIZE=10` bien configurée dans AWS Console
2. Logs de démarrage montrent : `[Init] ThreadPool matching initialisé avec 10 workers`
3. Si absent → variable non configurée → REDÉPLOYEZ avec la variable

### Symptôme 2 : Erreurs de matching

**Vérifiez** :
- AWS Rekognition collection existe et contient des faces indexées
- Variables AWS (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) correctes
- IAM role a les permissions Rekognition

### Symptôme 3 : Build Docker échoue

```powershell
# Vérifiez Docker est lancé
docker ps

# Vérifiez AWS CLI configuré
aws configure list

# Rebuild avec logs détaillés
docker build -t test-build -f Dockerfile . --progress=plain
```

## 🎯 Checklist finale

- [ ] Variables d'environnement configurées dans AWS Console
- [ ] `MATCHING_THREAD_POOL_SIZE=10` ajouté
- [ ] Image Docker buildée et pushée vers ECR (v101)
- [ ] App Runner service mis à jour
- [ ] Logs montrent "ThreadPool matching initialisé avec 10 workers"
- [ ] Test Locust 30 users : 0% échec
- [ ] Aucun "WORKER TIMEOUT" dans les logs

## 📞 Support

Si problème :
1. Capturez les logs AWS App Runner
2. Capturez les résultats Locust (screenshot)
3. Partagez ici pour diagnostic

---

**Date** : 19/01/2026  
**Version** : v101  
**Status** : ✅ **PRÊT POUR DÉPLOIEMENT**
