# ⚡ ACTION IMMÉDIATE : 3 Étapes pour Tout Résoudre

## 🎯 Plan d'Action (20 minutes total)

---

## ÉTAPE 1 : Nettoyer les Doublons en BDD (5 min)

### A. Identifier le Problème

**Dans psql, exécuter** :

```sql
-- Trouver les doublons (même email + même event_id)
SELECT 
    email, 
    event_id, 
    COUNT(*) as count,
    ARRAY_AGG(id) as ids,
    ARRAY_AGG(username) as usernames
FROM users 
WHERE event_id IS NOT NULL
GROUP BY email, event_id 
HAVING COUNT(*) > 1;
```

**Si des lignes apparaissent** → Tu as des doublons à nettoyer

---

### B. Nettoyer les Doublons

**Option 1 : Script Python (recommandé)**

```bash
# Voir sans supprimer
python fix_doublon_meme_event.py --dry-run

# Supprimer (garde le plus ancien)
python fix_doublon_meme_event.py --fix
```

**Option 2 : SQL Manuel**

```sql
-- Remplacer ID_DU_DOUBLON par l'ID à supprimer
DELETE FROM user_events WHERE user_id = ID_DU_DOUBLON;
DELETE FROM face_matches WHERE user_id = ID_DU_DOUBLON;
DELETE FROM password_reset_tokens WHERE user_id = ID_DU_DOUBLON;
DELETE FROM users WHERE id = ID_DU_DOUBLON;
```

---

### C. Vérifier les Contraintes UNIQUE

```sql
-- Vérifier que les contraintes contiennent bien "UNIQUE"
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
AND indexname IN ('users_email_event_unique', 'users_username_event_unique');

-- Dans indexdef, DOIT voir "UNIQUE"
```

**Si pas UNIQUE**, recréer :

```sql
DROP INDEX IF EXISTS users_email_event_unique;
DROP INDEX IF EXISTS users_username_event_unique;

CREATE UNIQUE INDEX users_email_event_unique 
ON users (email, COALESCE(event_id, -1));

CREATE UNIQUE INDEX users_username_event_unique 
ON users (username, COALESCE(event_id, -1));
```

---

## ÉTAPE 2 : Déployer v90 (15 min)

```bash
cd face_recognition/app

docker build -t findme-prod:v90 .

docker tag findme-prod:v90 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v90

aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com

docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v90

cd ../..

aws apprunner update-service --cli-input-json file://face_recognition/app/update-image.json --region eu-west-3
```

**Attendre 5-10 minutes**

---

## ÉTAPE 3 : Tests de Validation (2 min)

### Test 1 : Validation Temps Réel ✅
```
1. Ouvrir formulaire d'inscription
2. Taper un email existant
→ Message "Email déjà utilisé" apparaît immédiatement
```

### Test 2 : Protection Doublons ✅
```
1. Créer test@test.com pour événement A
2. Essayer de recréer test@test.com pour événement A
→ Devrait échouer "Email déjà utilisé pour cet événement"
```

### Test 3 : Multi-Événements ✅
```
1. Créer test@test.com (user_A) pour événement A
2. Créer test@test.com (user_B) pour événement B
→ Les 2 comptes créés avec succès
```

### Test 4 : Login ✅
```
1. Login avec user_A → Direct A
2. Login avec user_B → Direct B
3. Login avec test@test.com :
   - Si mdps différents → Direct au compte qui match
   - Si même mdp → Sélection événement
```

---

## ✅ Résultat Final

Après ces 3 étapes :

✅ **Validation temps réel** : Fonctionne
✅ **Protection doublons** : Empêche les doublons
✅ **Multi-événements** : Fonctionne  
✅ **Login intelligent** : Gère tous les cas
✅ **Mots de passe** : Chaque compte indépendant

---

## 📊 Changements v90

**Fichiers modifiés** :
- `main.py` - /api/check-user-availability intelligent
- Outils créés : diagnostic + nettoyage

**Corrections** :
1. Validation temps réel restaurée ✓
2. Protection doublons renforcée ✓
3. Mots de passe documentés ✓

---

## 🎯 En Résumé

**MAINTENANT** :
1. Nettoyer doublons BDD (5 min)
2. Vérifier contraintes UNIQUE (2 min)
3. Déployer v90 (15 min)

**RÉSULTAT** :
- Tout fonctionne parfaitement ✅
- Plus de blocage email ✅
- Plus de doublons possibles ✅
- UX fluide ✅

---

**Commence par l'Étape 1 (nettoyage BDD) maintenant !** 🚀

---

*Guide créé le : 2025-01-05*
*Version finale : v90*

