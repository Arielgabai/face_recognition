# 🔧 Fix : Un Compte par Événement + Réutilisation des Emails

## 🐛 Problèmes Identifiés

### 1. **Impossible de créer plusieurs comptes avec le même email**
- Un utilisateur ne pouvait pas créer un compte pour un événement différent avec le même email
- Les contraintes `unique=True` sur `email` et `username` étaient globales

### 2. **Email bloqué après suppression**
- Après suppression d'un compte, l'email ne pouvait pas être réutilisé
- (Ce problème devrait être résolu par la vraie suppression que nous avons déjà fixée)

## ✅ Solution Implémentée

### Concept
**Unicité par événement** : Un utilisateur peut créer un compte par événement avec le même email/username.

- **Utilisateurs** (type=USER) : Unicité `(email, event_id)` et `(username, event_id)`
- **Photographes/Admins** : Unicité globale (event_id=NULL)

---

## 📝 Changements Apportés

### 1. **Modèle de Données** (`models.py`)

#### Ajouts :
- Nouvelle colonne `event_id` dans la table `User` (nullable, ForeignKey vers `events`)
- Contraintes unique composites : `(email, COALESCE(event_id, -1))` et `(username, COALESCE(event_id, -1))`
- Suppression des contraintes `unique=True` simples sur `email` et `username`

```python
class User(Base):
    # ...
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True)
    
    __table_args__ = (
        Index('users_email_event_unique', 'email', func.coalesce(event_id, -1), unique=True),
        Index('users_username_event_unique', 'username', func.coalesce(event_id, -1), unique=True),
    )
```

#### Pourquoi COALESCE(event_id, -1) ?
- Les photographes/admins ont `event_id=NULL`
- SQL traite deux `NULL` comme différents dans les contraintes unique
- `COALESCE(event_id, -1)` convertit `NULL` en `-1` pour garantir l'unicité des photographes/admins entre eux

---

### 2. **Endpoints d'Inscription** (`main.py`)

Modifiés pour vérifier l'unicité **par événement** :

#### A. Pour les utilisateurs (avec event_code) :
```python
# Avant
existing_user = db.query(User).filter(
    (User.username == username) | (User.email == email)
).first()

# Après  
existing_user = db.query(User).filter(
    ((User.username == username) | (User.email == email)) &
    (User.event_id == event.id)
).first()
```

Et lors de la création :
```python
db_user = User(
    username=username,
    email=email,
    hashed_password=hashed_password,
    user_type=UserType.USER,
    event_id=event.id  # ← NOUVEAU
)
```

#### B. Pour les photographes/admins :
```python
# Vérifier uniquement parmi les autres photographes/admins
existing_user = db.query(User).filter(
    ((User.username == username) | (User.email == email)) &
    (User.event_id == None)  # event_id=NULL pour photographes/admins
).first()
```

#### Endpoints modifiés :
- ✅ `/api/register-invite` 
- ✅ `/api/register-invite-with-selfie` (principal)
- ✅ `/api/register-with-event-code`
- ✅ `/api/admin/photographers` (création photographe)
- ✅ `/api/admin/register-admin` (premier admin)
- ✅ `/api/admin/create-admin` (admin par admin)

---

### 3. **Migration SQL** (`migration_unique_per_event.sql`)

Script complet pour migrer la base de données existante :

#### Étapes de la migration :
1. Ajouter la colonne `event_id` (nullable)
2. Remplir `event_id` pour les utilisateurs existants (depuis `UserEvent`)
3. Supprimer les anciennes contraintes unique globales
4. Créer les nouvelles contraintes unique composites
5. Créer les index pour les performances

---

## 🚀 Déploiement

### Étape 1 : Appliquer la Migration SQL

```bash
# Se connecter à la base de données PostgreSQL
psql -U votre_user -d votre_database

# Exécuter le script
\i face_recognition/app/migration_unique_per_event.sql

# Ou directement
psql -U votre_user -d votre_database -f face_recognition/app/migration_unique_per_event.sql
```

**⚠️ IMPORTANT** : Faire un backup avant la migration !

```bash
pg_dump -U votre_user -d votre_database > backup_before_migration.sql
```

### Étape 2 : Déployer le Nouveau Code

```bash
# Les fichiers modifiés sont déjà acceptés :
# - models.py
# - main.py

# Rebuild l'image Docker
cd face_recognition/app
docker build -t findme-prod:v9 .

# Push vers ECR
docker tag findme-prod:v9 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v9
aws ecr get-login-password --region eu-west-3 | docker login --username AWS --password-stdin 801541932532.dkr.ecr.eu-west-3.amazonaws.com
docker push 801541932532.dkr.ecr.eu-west-3.amazonaws.com/findme-prod:v9

# Update service AWS
cd ../..
# Mettre à jour ImageIdentifier dans service.json à v9
aws apprunner update-service --cli-input-json file://service.json --region eu-west-3
```

---

## ✅ Vérifications Post-Déploiement

### 1. Vérifier la structure de la base de données

```sql
-- Vérifier que la colonne event_id existe
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'event_id';

-- Vérifier les contraintes unique
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users' 
AND (indexname LIKE '%unique%' OR indexname LIKE '%event%');

-- Devrait afficher :
-- users_email_event_unique    ... USING btree (email, COALESCE(event_id, '-1'::integer))
-- users_username_event_unique  ... USING btree (username, COALESCE(event_id, '-1'::integer))
```

### 2. Tester les Scénarios

#### Test 1 : Même email, événements différents ✅
```
1. Créer un compte avec email@test.com pour l'événement A
2. Créer un compte avec email@test.com pour l'événement B
✓ Les deux comptes devraient être créés avec succès
```

#### Test 2 : Même email, même événement ✗
```
1. Créer un compte avec email@test.com pour l'événement A
2. Essayer de créer un autre compte avec email@test.com pour l'événement A
✗ Devrait échouer avec "Email déjà utilisé pour cet événement"
```

#### Test 3 : Photographe avec email existant ✅
```
1. Créer un compte utilisateur avec email@test.com pour événement A
2. Créer un photographe avec email@test.com
✓ Le photographe devrait être créé (event_id=NULL vs event_id=A)
```

#### Test 4 : Suppression et réutilisation ✅
```
1. Créer un compte avec email@test.com pour événement A
2. Supprimer ce compte (admin)
3. Recréer un compte avec email@test.com pour événement A
✓ Devrait fonctionner (le compte est vraiment supprimé)
```

### 3. Vérifier les Logs

Chercher dans les logs AWS CloudWatch :
```
# Inscription réussie
[INFO] User created with event_id=...

# Tentative de doublon
[ERROR] Email déjà utilisé pour cet événement
```

---

## 📊 Impact sur les Données Existantes

### Utilisateurs Existants
- Leur `event_id` sera rempli automatiquement par la migration (premier événement de `UserEvent`)
- Ils gardent leur unicité par événement

### Photographes/Admins Existants
- Leur `event_id` reste `NULL`
- Ils gardent leur unicité globale entre eux

### UserEvent
- La table `UserEvent` reste inchangée
- Continue à gérer les inscriptions multi-événements
- Un user peut rejoindre d'autres événements après inscription

---

## 🔧 Configuration

### Variables d'Environnement
Aucune nouvelle variable nécessaire. Le comportement est contrôlé par le modèle.

### Compatibilité
- **PostgreSQL** : ✅ Supporté (COALESCE, Index composites)
- **SQLite** : ⚠️ Limité (pas de COALESCE dans les index, utiliser SQL brut)

---

## 🐛 Troubleshooting

### Erreur : "duplicate key value violates unique constraint"

**Cause** : Des doublons existent déjà avant la migration

**Solution** :
```sql
-- Identifier les doublons
SELECT email, event_id, COUNT(*) 
FROM users 
GROUP BY email, event_id 
HAVING COUNT(*) > 1;

-- Supprimer ou fusionner manuellement
```

### Erreur : "column event_id does not exist"

**Cause** : Migration SQL pas appliquée

**Solution** : Exécuter `migration_unique_per_event.sql`

### Les photographes ne peuvent pas s'inscrire

**Cause** : Oubli du filtre `event_id == None` dans l'endpoint

**Solution** : Vérifier que tous les endpoints photographes/admins filtrent par `event_id == None`

---

## 🔄 Rollback (si nécessaire)

Si la migration cause des problèmes, rollback disponible dans le script SQL :

```sql
-- Voir section ROLLBACK dans migration_unique_per_event.sql
BEGIN;
DROP INDEX IF EXISTS users_email_event_unique;
DROP INDEX IF EXISTS users_username_event_unique;
ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email);
ALTER TABLE users ADD CONSTRAINT users_username_key UNIQUE (username);
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_event_id_fkey;
ALTER TABLE users DROP COLUMN IF EXISTS event_id;
COMMIT;
```

**⚠️ Attention** : Le rollback supprime `event_id` → perte de l'association événement principal

---

## 📚 Exemples de Cas d'Usage

### Cas 1 : Mariage d'Alice
```
- Alice crée un compte alice@email.com pour le mariage Smith (event_id=1)
- Alice peut voir ses photos du mariage Smith
```

### Cas 2 : Mariage de Bob (Alice invitée)
```
- Alice crée un AUTRE compte alice@email.com pour le mariage Martin (event_id=2)
- Ce sont 2 comptes distincts, 2 selfies différents
- Alice a des photos matchées différentes pour chaque événement
```

### Cas 3 : Photographe Pro
```
- Le photographe crée un compte pro@photo.com (event_id=NULL)
- Il peut uploader des photos pour tous les mariages
- Son email reste unique parmi les photographes
```

---

## 🎯 Résumé

| Aspect | Avant | Après |
|--------|-------|-------|
| **Email unique** | Global | Par événement |
| **Comptes par user** | 1 seul | 1 par événement |
| **Photographes** | Global unique | Global unique (inchangé) |
| **Suppression/réutilisation** | ❌ Bloqué | ✅ Fonctionne |
| **Migration BDD** | N/A | ✅ Script fourni |

---

## ✅ Checklist de Déploiement

- [ ] Backup de la base de données effectué
- [ ] Migration SQL testée en local/staging
- [ ] Migration SQL appliquée en production
- [ ] Code déployé (models.py + main.py)
- [ ] Tests des 4 scénarios effectués
- [ ] Logs vérifiés (pas d'erreurs)
- [ ] Documentation partagée avec l'équipe
- [ ] Utilisateurs informés du changement

---

*Documentation créée le : 2025-01-05*
*Version : 1.0*
*Auteur : Assistant AI*

