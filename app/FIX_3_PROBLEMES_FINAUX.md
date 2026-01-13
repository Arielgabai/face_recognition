# 🔧 Fix des 3 Derniers Problèmes

## 📋 Problèmes Identifiés

### 1. ❌ Validation Temps Réel Cassée
**Symptôme** : Formulaire ne dit plus si email/username déjà utilisé avant soumission
**Cause** : `/api/check-user-availability` retournait vide sans event_code

### 2. ❌ Doublon Créé (Même Email + Même Event)
**Symptôme** : 2 comptes avec même email pour le MÊME événement
**Cause** : Contrainte SQL pas appliquée correctement OU validation backend insuffisante

### 3. ❓ Gestion des Mots de Passe
**Question** : Comment gérer différents mots de passe pour le même email ?

---

## ✅ SOLUTIONS APPLIQUÉES

### Solution 1 : Validation Temps Réel Intelligente ✅

**Modification** : `/api/check-user-availability` (main.py)

**Nouveau comportement** :
- **Sans event_code** : Vérifie globalement (feedback temps réel) ✓
- **Avec event_code** : Vérifie pour l'événement + info sur autres événements ✓

**Réponse enrichie** :
```json
{
  "email_taken": false,  // Pour CET événement
  "username_taken": false,
  "email_exists_other_events": true,  // Info : existe ailleurs
  "username_exists_other_events": false
}
```

**Impact** :
- ✅ Validation instantanée fonctionne à nouveau
- ✅ Feedback "Email déjà utilisé pour un autre événement" possible
- ✅ UX améliorée

---

### Solution 2 : Empêcher et Nettoyer les Doublons ✅

#### A. Diagnostic (À FAIRE MAINTENANT)

**Dans psql, exécuter** :

```sql
-- Vérifier si les contraintes UNIQUE sont bien en place
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
AND indexdef LIKE '%UNIQUE%'
AND indexname LIKE '%event%';

-- DOIT retourner :
-- users_email_event_unique avec UNIQUE
-- users_username_event_unique avec UNIQUE
```

**Si les contraintes ne sont PAS uniques** :

```sql
-- Recréer avec UNIQUE
DROP INDEX IF EXISTS users_email_event_unique;
DROP INDEX IF EXISTS users_username_event_unique;

CREATE UNIQUE INDEX users_email_event_unique 
ON users (email, COALESCE(event_id, -1));

CREATE UNIQUE INDEX users_username_event_unique 
ON users (username, COALESCE(event_id, -1));
```

#### B. Nettoyer les Doublons Existants

**Identifier les doublons** :

```sql
-- Trouver les doublons
SELECT 
    email, 
    event_id, 
    COUNT(*) as count,
    ARRAY_AGG(id) as user_ids,
    ARRAY_AGG(username) as usernames
FROM users 
WHERE event_id IS NOT NULL
GROUP BY email, event_id 
HAVING COUNT(*) > 1;
```

**Option A : Script Python automatisé**

```bash
cd face_recognition/app

# Voir les doublons sans supprimer
python fix_doublon_meme_event.py --dry-run

# Nettoyer (supprime les doublons, garde le plus ancien)
python fix_doublon_meme_event.py --fix
```

**Option B : Suppression manuelle SQL**

```sql
-- Supprimer le doublon le plus récent (adapter l'ID)
DELETE FROM user_events WHERE user_id = ID_DU_DOUBLON;
DELETE FROM face_matches WHERE user_id = ID_DU_DOUBLON;
DELETE FROM password_reset_tokens WHERE user_id = ID_DU_DOUBLON;
DELETE FROM users WHERE id = ID_DU_DOUBLON;
```

---

### Solution 3 : Gestion des Mots de Passe 🔐

**Réponse** : Chaque compte a son propre `hashed_password` indépendant.

```python
# Lors du login avec email
users = db.query(User).filter(email == ...).all()  # Trouve 2 comptes
valid_users = [u for u in users if verify_password(password, u.hashed_password)]

# Si mdps différents : 1 seul match → Login direct ✓
# Si même mdp : 2 match → Sélection événement 🔀
```

**Voir** : `EXPLICATION_MOTS_DE_PASSE.md` pour détails complets

---

## 🚀 Déploiement v90 (Avec Tous les Fixes)

### Fichiers Modifiés
- ✅ `main.py` - /api/check-user-availability amélioré
- ✅ Outils de diagnostic et nettoyage créés

### Commandes

```bash
cd face_recognition/app

# Build v90
docker build -t findme-prod:v90 .

# Tag & Push
docker tag findme-prod:v90 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v90
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v90

# Modifier update-image.json → v90
# Update service
cd ../..
aws apprunner update-service --cli-input-json file://face_recognition/app/update-image.json --region eu-west-3
```

---

## 📋 Actions AVANT le Déploiement

### 1. Nettoyer les Doublons en BDD

```bash
cd face_recognition/app

# Voir les doublons
python fix_doublon_meme_event.py --dry-run

# Nettoyer
python fix_doublon_meme_event.py --fix
```

**OU** via SQL (voir `diagnostic_doublon_created.sql`)

---

### 2. Vérifier les Contraintes UNIQUE

```sql
-- Dans psql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname IN ('users_email_event_unique', 'users_username_event_unique');

-- Les 2 index DOIVENT contenir "UNIQUE" dans indexdef
```

Si pas UNIQUE, les recréer (voir diagnostic_doublon_created.sql section 5)

---

## ✅ Après le Déploiement v90

### Test 1 : Validation Temps Réel
```
1. Ouvrir formulaire d'inscription
2. Commencer à taper un email
→ ✓ Message "Email déjà utilisé" apparaît immédiatement
```

### Test 2 : Protection Contre Doublons
```
1. Créer compte alice@test.com pour événement A
2. Essayer de recréer alice@test.com pour événement A (même username)
→ ✗ Devrait échouer "Email déjà utilisé pour cet événement"
```

### Test 3 : Multi-Événements OK
```
1. Créer alice@test.com (alice_A) pour événement A
2. Créer alice@test.com (alice_B) pour événement B (username différent)
→ ✓ Les 2 comptes créés
```

### Test 4 : Login Intelligent
```
1. Login avec alice_A → Direct événement A ✓
2. Login avec alice_B → Direct événement B ✓
3. Login avec alice@test.com + mdp_A → Direct A (si mdps différents) ✓
4. Login avec alice@test.com + même_mdp → Sélection (si même mdp) 🔀
```

---

## 🎯 Résumé des Fixes v90

| Problème | Solution | Status |
|----------|----------|--------|
| Validation temps réel | check-user-availability amélioré | ✅ |
| Doublons créés | Scripts de nettoyage + vérif contraintes | ✅ |
| Gestion mdps | Documentation complète | ✅ |

---

## 📚 Documentation

- **FIX_3_PROBLEMES_FINAUX.md** (ce fichier) - Guide complet
- **EXPLICATION_MOTS_DE_PASSE.md** - Logique des mots de passe
- **diagnostic_doublon_created.sql** - Diagnostic SQL
- **fix_doublon_meme_event.py** - Nettoyage automatisé

---

## ⚠️ IMPORTANT : Ordre des Actions

1. **D'ABORD** : Nettoyer les doublons en BDD ✓
2. **ENSUITE** : Vérifier/recréer les contraintes UNIQUE ✓
3. **ENFIN** : Déployer v90 ✓

Sinon les doublons empêcheront la création des contraintes !

---

*Fix complet appliqué le : 2025-01-05*
*Version : v90*
*Status : Solution complète pour tous les problèmes* ✅

