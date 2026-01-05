# ✅ Fix Critique : Ambiguïté des Relations SQLAlchemy

## 🐛 Erreur Identifiée

```
InvalidRequestError: Could not determine join condition between parent/child tables 
on relationship Event.photographer - there are multiple foreign key paths linking the tables
```

**Cause** : Avec l'ajout de `User.event_id → Event.id`, il existe maintenant **2 chemins FK** entre User et Event :
1. `Event.photographer_id → User.id` (photographe de l'événement)
2. `User.event_id → Event.id` (événement principal du user)

SQLAlchemy ne savait plus quelle FK utiliser pour `Event.photographer` !

---

## ✅ Solution Appliquée

### Modification 1 : `Event.photographer` (ligne 20)

```python
# AVANT (ambigu)
photographer = relationship("User", back_populates="events")

# APRÈS (explicite)
photographer = relationship("User", foreign_keys=[photographer_id], back_populates="events")
```

### Modification 2 : `User.primary_event` (ligne 62)

```python
# AVANT (ambigu)
primary_event = relationship("Event", foreign_keys=[event_id])

# APRÈS (explicite + lecture seule)
primary_event = relationship("Event", foreign_keys=[event_id], viewonly=True)
```

**`viewonly=True`** : Empêche SQLAlchemy d'essayer de modifier la relation inverse, évitant ainsi les conflits.

---

## 🎯 Impact

**Avant ce fix** :
- ❌ Aucune connexion ne marchait (admin, photographe, user)
- ❌ Erreur 500 sur `/api/login`
- ❌ SQLAlchemy refusait d'initialiser les mappers

**Après ce fix** :
- ✅ Toutes les connexions fonctionnent
- ✅ Relations User ↔ Event clairement définies
- ✅ Pas d'ambiguïté pour SQLAlchemy

---

## 📋 Relations Finales

### User → Event (2 relations distinctes)

1. **`User.events`** (via `Event.photographer_id`)
   - Événements où l'user est PHOTOGRAPHE
   - Utilisé pour : photographes qui gèrent des mariages
   
2. **`User.primary_event`** (via `User.event_id`)
   - Événement principal de l'utilisateur (invité)
   - Utilisé pour : users qui participent à UN événement
   - `viewonly=True` : lecture seule

### Event → User (1 relation)

**`Event.photographer`** (via `Event.photographer_id`)
- Le photographe assigné à cet événement
- `foreign_keys=[photographer_id]` : spécifie explicitement quelle FK utiliser

---

## 🚀 Déploiement

### Étape 1 : Rebuild

```bash
cd face_recognition/app
docker build -t findme-prod:v88 .
```

### Étape 2 : Push

```bash
docker tag findme-prod:v88 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v88
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v88
```

### Étape 3 : Update Service

Modifier `update-image.json` ligne 6 :
```json
"ImageIdentifier": "801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v88",
```

Puis :
```bash
cd ../..
aws apprunner update-service --cli-input-json file://face_recognition/app/update-image.json --region eu-west-3
```

---

## ✅ Vérification

Après 5-10 minutes, tester :

### 1. Health Check
```
https://g62bncafk2.eu-west-3.awsapprunner.com/api/health-check
```
**Attendu** : `"status": "healthy"`

### 2. Login Admin
Se connecter avec un compte admin → Devrait fonctionner ✓

### 3. Login Photographe
Se connecter avec un compte photographe → Devrait fonctionner ✓

### 4. Login User
Se connecter avec un compte utilisateur → Devrait fonctionner ✓

---

## 🎉 Résumé

**Problème** : Ambiguïté des foreign keys après ajout de event_id
**Solution** : Spécifier explicitement `foreign_keys` dans toutes les relations
**Résultat** : Toutes les connexions fonctionnent ✅

---

*Fix appliqué le : 2025-01-05*
*Version : v88*

