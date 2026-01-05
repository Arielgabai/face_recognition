# 🚨 ÉTAPES POUR RÉSOUDRE L'ERREUR 500 LOGIN

## ✅ Ce qui a été fait
- [x] Migration SQL appliquée dans la base de données
- [x] Code modifié (models.py + main.py avec event_id)
- [x] Outils de diagnostic ajoutés

## ❌ Problème
L'application AWS renvoie toujours erreur 500 sur le login.

---

## 🎯 SOLUTION : Redéployer avec la Version de Diagnostic

### 1️⃣ Build l'Image (2 min)

```bash
cd face_recognition/app
docker build -t findme-prod:v87 .
```

**Vérifie que ça build sans erreur** ✓

---

### 2️⃣ Push vers ECR (3 min)

```bash
# Tag
docker tag findme-prod:v87 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v87

# Login
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com

# Push
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v87
```

---

### 3️⃣ Mettre à Jour le Service (1 min)

**Édite `update-image.json` ligne 6** :

```json
"ImageIdentifier": "801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v87",
```

Puis :

```bash
cd ../..
aws apprunner update-service --cli-input-json file://face_recognition/app/update-image.json --region eu-west-3
```

**Attendre 5-10 minutes** ⏱️

---

### 4️⃣ Tester les Diagnostics (1 min)

#### A. Health Check (Dans ton navigateur)
```
https://g62bncafk2.eu-west-3.awsapprunner.com/api/health-check
```

**Attendu** :
```json
{
  "status": "healthy",
  "database": {
    "event_id_column_exists": true,
    "old_constraints_present": []
  }
}
```

**Si `status": "degraded"`** → Note les warnings

---

#### B. Test SQL Direct
```
https://g62bncafk2.eu-west-3.awsapprunner.com/api/db-raw-test
```

**Attendu** :
```json
{
  "status": "ok",
  "sample_user": {
    "username": "photographe",
    "event_id": null
  }
}
```

---

#### C. Test Login
```
https://g62bncafk2.eu-west-3.awsapprunner.com/api/login
```

Via interface photographe habituelle.

**Si erreur 500**, le message contiendra maintenant **l'erreur EXACTE** :
```json
{
  "detail": "Erreur interne: [TYPE D'ERREUR]: [DÉTAILS]"
}
```

---

## 🔍 Interprétation des Résultats

### Résultat 1 : Health Check = "healthy" ✅
→ BDD OK, modèle OK, contraintes OK
→ Le problème est ailleurs (vérifier logs AWS)

### Résultat 2 : Health Check = "degraded" ⚠️
→ Lire les `warnings` pour voir ce qui manque
→ Appliquer les corrections suggérées

### Résultat 3 : db-raw-test fonctionne mais pas login ❌
→ Problème dans le code de login ou vérification password
→ Partager l'erreur exacte du login

---

## 📞 Prochaines Étapes

**Après avoir testé les 3 endpoints ci-dessus**, tu auras :
1. L'état exact de la base de données ✓
2. La confirmation que SQL fonctionne ✓
3. **L'erreur EXACTE qui cause le 500** ✓

→ Partage-moi ces 3 résultats et je pourrai identifier le problème précis !

---

## ⚡ Raccourci : Console AWS

Si tu n'as pas Docker/AWS CLI localement :

1. **Build dans le cloud** : Push ton code sur GitHub
2. **AWS App Runner** : Configure pour auto-deploy depuis GitHub
3. **Déploiement** : Automatique à chaque push

Ou utilise l'interface AWS manuelle pour update l'image.

---

## 🆘 En Cas d'Urgence

Si tu as besoin que l'app fonctionne **maintenant** :

```bash
# Rollback vers la dernière version qui fonctionnait
# update-image.json → retour à v86 ou version précédente
aws apprunner update-service --cli-input-json file://update-image.json --region eu-west-3
```

Puis on corrigera le problème de migration à tête reposée.

---

**ACTION NOW** : Déploie v87 et teste les 3 endpoints ! 🚀

