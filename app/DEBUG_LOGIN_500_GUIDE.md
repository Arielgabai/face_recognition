# 🔍 Guide de Diagnostic : Erreur 500 Login

## 🎯 Objectif
Identifier la cause exacte de l'erreur 500 sur `/api/login` après la migration.

---

## 📋 Étape 1 : Redéployer avec les Outils de Diagnostic

J'ai ajouté deux outils de diagnostic au code :

### A. Endpoint `/api/health-check`
Vérifie automatiquement :
- Connexion base de données ✓
- Présence de la colonne `event_id` ✓
- Contraintes composites ✓
- Modèle Python ✓

### B. Logging amélioré sur `/api/login`
Capture et affiche l'erreur exacte dans les logs.

### Commandes de Déploiement

```bash
cd face_recognition/app

# 1. Rebuild avec les nouveaux outils
docker build -t findme-prod:v87 .

# 2. Tag et push
docker tag findme-prod:v87 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v87
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v87

# 3. Update service
cd ../..
# Modifier update-image.json ligne 6 : ...findme-prod:v87
aws apprunner update-service --cli-input-json file://update-image.json --region eu-west-3
```

**Attendre 5-10 minutes** que le déploiement soit terminé.

---

## 📋 Étape 2 : Tester le Health Check

```bash
# Depuis ton navigateur ou terminal
curl https://g62bncafk2.eu-west-3.awsapprunner.com/api/health-check
```

**Résultat attendu** :
```json
{
  "status": "healthy",
  "database": {
    "connected": true,
    "event_id_column_exists": true,
    "composite_constraints": ["users_email_event_unique", "users_username_event_unique"],
    "user_count": 50
  },
  "model": {
    "has_event_id_field": true,
    "has_table_args": true
  },
  "message": "All checks passed"
}
```

### Si "status": "degraded" ou erreur
→ La migration n'a pas été correctement appliquée ou le code n'est pas à jour.

---

## 📋 Étape 3 : Tester le Login et Capturer l'Erreur

```bash
# Test de login depuis le terminal
curl -X POST https://g62bncafk2.eu-west-3.awsapprunner.com/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"ton_photographe","password":"ton_password"}'
```

**Si erreur 500**, le message contiendra maintenant **l'erreur exacte** :
```json
{
  "detail": "Erreur interne lors de la connexion: ProgrammingError: column 'event_id' does not exist"
}
```

---

## 📋 Étape 4 : Accéder aux Logs AWS CloudWatch

### Option A : Via AWS Console (Interface Web)

1. Va sur : https://console.aws.amazon.com/cloudwatch/
2. Région : **eu-west-3** (Paris)
3. Menu gauche : **Logs** → **Log groups**
4. Chercher : `/aws/apprunner/findme-prod-v7` ou similaire
5. Cliquer sur le dernier **Log stream**
6. Chercher dans les logs : `LOGIN ERROR` ou `Traceback`

### Option B : Via AWS CLI

```bash
# Liste les log groups
aws logs describe-log-groups --region eu-west-3 | grep findme

# Voir les logs en temps réel
aws logs tail /aws/apprunner/findme-prod-v7/service --follow --region eu-west-3
```

---

## 🔍 Erreurs Possibles et Solutions

### Erreur 1 : "column 'event_id' does not exist"

**Cause** : Le code est déployé mais la migration SQL n'a pas été appliquée
**Solution** : Réappliquer la migration SQL (voir migration_unique_per_event.sql)

---

### Erreur 2 : "duplicate key value violates constraint 'ix_users_email'"

**Cause** : Les anciennes contraintes unique globales sont toujours présentes
**Solution** : 
```sql
DROP INDEX IF EXISTS ix_users_email;
DROP INDEX IF EXISTS ix_users_username;
```

---

### Erreur 3 : "relation 'users_email_event_unique' does not exist"

**Cause** : Les nouvelles contraintes composites n'ont pas été créées
**Solution** : Réexécuter la partie de la migration qui crée les index

---

### Erreur 4 : SQLAlchemy cache / metadata stale

**Cause** : L'app AWS n'a pas rechargé le modèle après la migration
**Solution** : Forcer un redéploiement complet
```bash
# Dans AWS Console App Runner :
# Operations → Deploy → Manual deployment
```

---

## 🛠️ Solution de Dépannage : Vérification Manuelle

Si le problème persiste, exécute ces vérifications dans `psql` :

```sql
-- 1. Vérifier la structure exacte
\d users

-- 2. Lister TOUS les index
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'users';

-- 3. Vérifier qu'il n'y a PAS ces anciennes contraintes :
SELECT indexname FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname IN ('ix_users_email', 'ix_users_username');
-- Résultat attendu : 0 lignes

-- 4. Tester une insertion manuelle
INSERT INTO users (username, email, hashed_password, user_type, event_id)
VALUES ('test_user_event1', 'test@test.com', 'hash123', 'user', 1);

INSERT INTO users (username, email, hashed_password, user_type, event_id)
VALUES ('test_user_event2', 'test@test.com', 'hash456', 'user', 2);
-- Les deux devraient réussir ✓

-- Nettoyer les tests
DELETE FROM users WHERE username LIKE 'test_user_%';
```

---

## 📞 Actions Immédiates

1. **Redéploie** avec le nouveau code (health-check + meilleur logging)
2. **Teste** `/api/health-check` pour voir l'état
3. **Essaie** le login et capture le message d'erreur détaillé
4. **Regarde** les logs AWS CloudWatch pour le stacktrace complet
5. **Partage** l'erreur exacte pour que je puisse t'aider précisément

---

## 🎯 Prochaines Étapes

Une fois le déploiement fait :

```bash
# Test 1
curl https://g62bncafk2.eu-west-3.awsapprunner.com/api/health-check

# Test 2
curl -X POST https://g62bncafk2.eu-west-3.awsapprunner.com/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"photographe","password":"mdp"}'
```

**Le message d'erreur détaillé te dira exactement ce qui bloque.** 🎯

---

*Guide créé le : 2025-01-05*

