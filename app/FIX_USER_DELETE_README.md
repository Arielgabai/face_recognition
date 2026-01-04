# Fix : Erreur de suppression d'utilisateur

## 🐛 Problème

Lors de la suppression d'un utilisateur, l'erreur suivante apparaissait :

```
ForeignKeyViolation: update or delete on table "users" violates foreign key constraint 
"password_reset_tokens_user_id_fkey" on table "password_reset_tokens"
```

## ✅ Solution appliquée

### 1. Modifications du code (✓ Déjà fait)

**`main.py`** : Ajout de la suppression explicite des tokens de réinitialisation
```python
# Ligne ajoutée dans l'endpoint @app.delete("/api/admin/users/{user_id}")
db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()
```

**`models.py`** : Ajout de CASCADE à la contrainte de clé étrangère
```python
# Modification de la ligne 179
user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
```

### 2. Migration de la base de données (À faire maintenant)

Pour que le changement du modèle prenne effet sur votre base de données existante, vous devez appliquer la migration :

#### Option A : Via script Python (Recommandé)

```bash
cd face_recognition/app
python apply_cascade_migration.py
```

#### Option B : Via SQL direct

Connectez-vous à votre base PostgreSQL et exécutez :

```bash
psql -U votre_user -d votre_database -f migration_fix_password_reset_cascade.sql
```

Ou copiez-collez le contenu du fichier `migration_fix_password_reset_cascade.sql` dans votre client SQL.

### 3. Redémarrer l'application

Après avoir appliqué la migration :

```bash
# Redémarrez votre serveur FastAPI
# Si vous utilisez uvicorn directement :
# Ctrl+C puis relancer

# Ou si vous utilisez un service systemd/docker :
systemctl restart votre-service
# ou
docker-compose restart
```

## 🧪 Test

Pour vérifier que le fix fonctionne :

1. Créez un utilisateur test
2. Demandez une réinitialisation de mot de passe pour cet utilisateur (cela créera un token)
3. Essayez de supprimer l'utilisateur depuis l'interface admin
4. ✓ La suppression devrait maintenant fonctionner sans erreur

## 📝 Détails techniques

### Avant le fix

- La table `password_reset_tokens` avait une contrainte `FOREIGN KEY` vers `users` **sans CASCADE**
- Lors de la suppression d'un utilisateur, PostgreSQL refusait l'opération car des tokens existaient encore
- Le code ne supprimait pas les tokens avant de supprimer l'utilisateur

### Après le fix

- **Protection double couche** :
  1. Le code supprime explicitement les tokens (ligne ajoutée dans `main.py`)
  2. La base de données les supprime automatiquement via `ON DELETE CASCADE`
- Même si le code oublie de supprimer les tokens, la base de données le fera automatiquement
- Principe de **défense en profondeur** : redondance pour plus de robustesse

## 🔍 Vérification de la migration

Pour vérifier que la contrainte CASCADE est bien en place :

```sql
SELECT 
    tc.table_name, 
    tc.constraint_name,
    rc.delete_rule
FROM information_schema.table_constraints tc
LEFT JOIN information_schema.referential_constraints rc 
    ON tc.constraint_name = rc.constraint_name
WHERE tc.table_name = 'password_reset_tokens'
    AND tc.constraint_type = 'FOREIGN KEY';
```

Résultat attendu : `delete_rule = 'CASCADE'`

## 🚀 Prêt !

Une fois la migration appliquée et l'application redémarrée, vous pourrez supprimer des utilisateurs sans erreur, même s'ils ont des tokens de réinitialisation de mot de passe actifs.

