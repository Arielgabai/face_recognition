# 🔍 Diagnostic : Pourquoi l'Email Est-il Toujours Bloqué ?

## 🎯 Problème

Malgré la migration SQL et le redéploiement :
- ❌ Impossible de créer un compte avec un email déjà utilisé (même pour un autre événement)
- ❌ Impossible de réutiliser un email d'un utilisateur supprimé

---

## 🔍 2 Causes Possibles

### Cause A : Anciennes Contraintes Encore en BDD ⚠️

Les anciennes contraintes `unique` globales n'ont peut-être pas été complètement supprimées.

### Cause B : Code Backend Pas à Jour 🔄

Le code déployé utilise toujours l'ancienne validation globale au lieu de la validation par événement.

---

## ✅ VÉRIFICATION 1 : Base de Données

**Exécute dans psql** :

```sql
-- 1. Vérifier les contraintes unique actuelles
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname LIKE '%unique%';
```

**Résultat ATTENDU** :
```
users_email_event_unique      | ... (email, COALESCE(event_id, '-1'::integer))
users_username_event_unique   | ... (username, COALESCE(event_id, '-1'::integer))
```

**Si tu vois aussi** :
```
ix_users_email      ← ❌ PROBLÈME
ix_users_username   ← ❌ PROBLÈME
```

→ **Ces contraintes bloquent tout ! Il faut les supprimer** :

```sql
DROP INDEX IF EXISTS ix_users_email;
DROP INDEX IF EXISTS ix_users_username;

-- Vérifier
SELECT indexname FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname IN ('ix_users_email', 'ix_users_username');

-- DOIT retourner 0 ligne
```

---

## ✅ VÉRIFICATION 2 : Code Backend Déployé

**Teste l'endpoint** `/api/health-check` :

```
https://g62bncafk2.eu-west-3.awsapprunner.com/api/health-check
```

**Vérifie dans la réponse** :
```json
{
  "database": {
    "old_constraints_present": []  ← DOIT être vide []
  },
  "warnings": [null, null, null]  ← DOIT être que des null
}
```

**Si `old_constraints_present` n'est PAS vide** → Retour à Vérification 1

---

## ✅ VÉRIFICATION 3 : Test d'Inscription Direct

**Via curl ou Postman**, teste directement l'API :

```bash
# Essayer de créer un utilisateur pour l'événement 1
curl -X POST https://g62bncafk2.eu-west-3.awsapprunner.com/api/register-invite-with-selfie \
  -F "username=testuser1" \
  -F "email=test@duplicate.com" \
  -F "password=TestPassword123!" \
  -F "event_code=VOTRE_EVENT_CODE_1" \
  -F "file=@chemin/vers/selfie.jpg"
```

**Message d'erreur attendu si email déjà utilisé** :
```
"Email déjà utilisé pour cet événement"  ← Nouveau message
```

**Si tu vois** :
```
"Email déjà utilisé"  ← Ancien message (SANS "pour cet événement")
```

→ **Le code backend n'est PAS à jour !**

---

## 🔧 SOLUTION SELON LA CAUSE

### Si Cause A : Contraintes en BDD

```sql
-- Dans psql, exécuter :
DROP INDEX IF EXISTS ix_users_email;
DROP INDEX IF EXISTS ix_users_username;
```

**Puis redémarrer l'app** (ou attendre 1-2 minutes qu'elle se reconnecte)

---

### Si Cause B : Code Pas à Jour

**Redéployer v88** :

```bash
cd face_recognition/app

# Build
docker build -t findme-prod:v88 .

# Push
docker tag findme-prod:v88 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v88
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v88

# Update service (update-image.json déjà mis à jour vers v88)
cd ../..
aws apprunner update-service --cli-input-json file://face_recognition/app/update-image.json --region eu-west-3
```

---

## 🧪 Test Complet : Vérifier Que Ça Marche

### Scénario 1 : Même Email, Événements Différents

```sql
-- Dans psql, test manuel :
BEGIN;

-- User 1 : test@example.com pour événement 1
INSERT INTO users (username, email, hashed_password, user_type, event_id)
VALUES ('user_ev1', 'test@example.com', 'hash123', 'user', 1);

-- User 2 : MÊME email pour événement 2
INSERT INTO users (username, email, hashed_password, user_type, event_id)
VALUES ('user_ev2', 'test@example.com', 'hash456', 'user', 2);

-- Si ces 2 INSERT réussissent → BDD OK ✓
-- Si erreur "duplicate key" → Anciennes contraintes encore présentes ✗

ROLLBACK;  -- Annuler les tests
```

---

### Scénario 2 : Suppression et Réutilisation

```sql
-- Dans psql :
BEGIN;

-- Créer un user
INSERT INTO users (username, email, hashed_password, user_type, event_id)
VALUES ('temp_user', 'temp@test.com', 'hash', 'user', 1)
RETURNING id;

-- Noter l'ID retourné (par exemple 123)

-- Supprimer ce user
DELETE FROM users WHERE id = 123;

-- Recréer avec le même email
INSERT INTO users (username, email, hashed_password, user_type, event_id)
VALUES ('temp_user2', 'temp@test.com', 'hash2', 'user', 1);

-- Si réussit → Suppression fonctionne ✓
-- Si erreur → Problème de suppression ✗

ROLLBACK;  -- Annuler les tests
```

---

## 📋 Actions Immédiates

1. **Exécute Vérification 1** (contraintes BDD)
2. **Exécute Vérification 2** (health-check)
3. **Exécute Test Complet** (INSERT manuels)

**Partage-moi les résultats** :
- Quelles contraintes sont présentes ?
- Que dit le health-check ?
- Les INSERT manuels réussissent-ils ?

Avec ces infos, je saurai exactement où est le problème ! 🎯

---

*Guide créé le : 2025-01-05*

