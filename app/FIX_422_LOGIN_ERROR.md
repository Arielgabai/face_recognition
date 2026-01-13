# 🔧 Fix Urgent : Erreur 422 Login

## 🐛 Problème

```
POST /api/login 422 (Unprocessable Entity)
```

**Cause** : J'ai modifié `/api/login` pour accepter `user_id` en paramètre, mais le modèle Pydantic `UserLogin` ne le contenait pas.

---

## ✅ Solution Appliquée

### 1. Mise à Jour du Schéma Pydantic (schemas.py) ✅

```python
class UserLogin(BaseModel):
    username: str
    password: str
    user_id: Optional[int] = None  # ← NOUVEAU : optionnel
```

### 2. Correction de l'Endpoint (main.py) ✅

```python
# Utiliser user_credentials.user_id au lieu de user_id = Body(None)
if user_credentials.user_id:
    user = db.query(User).filter(User.id == user_credentials.user_id).first()
```

---

## 🚀 Déploiement v89 (15 min)

```bash
cd face_recognition/app

# Build
docker build -t findme-prod:v89 .

# Tag & Push
docker tag findme-prod:v89 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v89
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v89

# Update (update-image.json déjà pointé vers v89)
cd ../..
aws apprunner update-service --cli-input-json file://face_recognition/app/update-image.json --region eu-west-3
```

---

## ✅ Tests Après Déploiement

### Login Admin
```
Username: admin
Password: ***
→ ✓ Devrait fonctionner (pas d'erreur 422)
```

### Login Photographe
```
Username: photographe
Password: ***
→ ✓ Devrait fonctionner
```

### Login User
```
Email: user@email.com
Password: ***
→ ✓ Devrait fonctionner
```

---

## 📋 Résumé v89

**Fichiers modifiés** :
- `schemas.py` - UserLogin avec user_id optionnel ✓
- `main.py` - Utilisation de user_credentials.user_id ✓
- `update-image.json` - Pointé vers v89 ✓

**Corrections incluses** :
1. Fix erreur 422 login ✓
2. Support multi-comptes ✓
3. /api/check-user-availability par événement ✓
4. Page /select-event ✓

---

*Fix appliqué : 2025-01-05*
*Version : v89*
*Status : Prêt à déployer* ✅

