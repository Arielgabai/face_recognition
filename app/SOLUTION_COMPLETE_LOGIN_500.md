# 🎯 Solution Complète : Erreur 500 Login Après Migration

## 📊 État Actuel

✅ **Migration SQL** : Appliquée avec succès
- Colonne `event_id` créée ✓
- Contraintes composites créées ✓
- Anciennes contraintes supprimées ✓

❌ **Login** : Erreur 500 persiste

---

## 🔍 Diagnostic : 3 Causes Possibles

### Cause 1 : Application AWS Pas Redémarrée ⭐ (PLUS PROBABLE)

L'application AWS App Runner **cache le code en mémoire**. Même après une migration SQL, elle continue d'utiliser l'ancien modèle SQLAlchemy compilé.

**Solution** : Forcer un redéploiement complet

---

### Cause 2 : Conflit de Contraintes

SQLAlchemy au démarrage essaie de créer des contraintes qui existent déjà ou qui ne matchent pas.

**Solution** : Vérifier les logs de démarrage

---

### Cause 3 : Code Non Synchronisé

Le code déployé n'est pas celui avec les modifications `event_id`.

**Solution** : Rebuild et redéployer

---

## ✅ SOLUTION COMPLÈTE (15 minutes)

### Étape 1 : Rebuild l'Image avec Diagnostic

```bash
cd face_recognition/app

# Build version 87 avec outils de diagnostic
docker build -t findme-prod:v87 .
```

### Étape 2 : Push vers ECR

```bash
# Tag
docker tag findme-prod:v87 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v87

# Login ECR
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com

# Push
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v87
```

### Étape 3 : Update Service AWS

**Modifier `update-image.json` ligne 6** :

```json
"ImageIdentifier": "801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v87",
```

Puis :

```bash
cd ../..
aws apprunner update-service --cli-input-json file://face_recognition/app/update-image.json --region eu-west-3
```

### Étape 4 : Attendre le Déploiement (5-10 min)

Suivre les logs en temps réel :

```bash
# Si AWS CLI installé
aws logs tail /aws/apprunner/findme-prod-v7/service --follow --region eu-west-3
```

Ou dans la **console AWS App Runner** : Operations → Logs

**Chercher dans les logs** :
- `🚀 Démarrage de l'application...`
- `🌐 Démarrage du serveur avec Gunicorn...`
- `[INFO] Booting worker with pid: ...` (5 fois)
- Toute ligne avec `ERROR` ou `Traceback`

---

### Étape 5 : Tester Health Check

```bash
curl https://g62bncafk2.eu-west-3.awsapprunner.com/api/health-check
```

**Attendu** :
```json
{
  "status": "healthy",
  "database": {
    "event_id_column_exists": true,
    "composite_constraints": ["users_email_event_unique", "users_username_event_unique"]
  }
}
```

---

### Étape 6 : Tester Login avec Erreur Détaillée

```bash
curl -X POST https://g62bncafk2.eu-west-3.awsapprunner.com/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"ton_username","password":"ton_password"}'
```

**Si erreur 500**, tu verras maintenant :
```json
{
  "detail": "Erreur interne: [ERREUR EXACTE ICI]"
}
```

---

## 🔧 Si l'Erreur Persiste

### Vérification 1 : Le Bon Code est-il Déployé ?

Dans les logs AWS, chercher :

```
[INFO] Application startup complete
[FaceRecognition][AWS] Using region: eu-west-1
```

Si absent → Le déploiement a échoué, vérifier les logs de build.

---

### Vérification 2 : SQLAlchemy Metadata Conflict

**Symptôme dans les logs** :
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) 
duplicate key value violates constraint "ix_users_email"
```

**Solution** : Les anciennes contraintes existent encore ! Retourner dans psql :

```sql
-- Lister TOUTES les contraintes
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'users'::regclass;

-- Supprimer toute contrainte unique sur email/username seuls
ALTER TABLE users DROP CONSTRAINT IF EXISTS ix_users_email;
ALTER TABLE users DROP CONSTRAINT IF EXISTS ix_users_username;
DROP INDEX IF EXISTS ix_users_email;
DROP INDEX IF EXISTS ix_users_username;
```

---

### Vérification 3 : Clear SQLAlchemy Cache

Si vraiment rien ne fonctionne, ajouter ce code temporairement au début de `main.py` (après imports) :

```python
# TEMPORARY: Force SQLAlchemy to ignore metadata mismatches
from sqlalchemy import MetaData
from database import Base
Base.metadata.clear()
```

Puis rebuild et redéployer.

---

## 📋 Checklist Complète

- [ ] Migration SQL appliquée ✓ (tu l'as fait)
- [ ] Anciennes contraintes ix_users_email supprimées ✓ (tu l'as fait)
- [ ] Code models.py avec event_id (vérifier dans ton éditeur)
- [ ] Code main.py avec event_id (vérifier dans ton éditeur)
- [ ] Image Docker rebuildée avec nouveau code
- [ ] Image pushée vers ECR
- [ ] update-image.json mis à jour avec v87
- [ ] Service AWS mis à jour
- [ ] Logs AWS vérifiés (chercher ERROR)
- [ ] Health check testé
- [ ] Login testé avec message d'erreur détaillé

---

## 🎯 Action Immédiate

**Redéploie avec la version v87** qui contient :
- Endpoint `/api/health-check` pour diagnostic
- Meilleur logging sur `/api/login` qui affichera l'erreur exacte

Une fois déployé, **teste le health-check et le login**, et partage-moi :
1. Le résultat du health-check
2. Le message d'erreur détaillé du login
3. Un extrait des logs AWS CloudWatch

Avec ces infos, je pourrai identifier le problème exact ! 🔍

---

*Guide créé le : 2025-01-05*

