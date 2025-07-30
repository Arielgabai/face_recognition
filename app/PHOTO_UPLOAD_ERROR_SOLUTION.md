# Solution pour l'erreur d'upload de photos

## 🚨 Problème
L'application échoue lors de l'upload de photos avec l'erreur :
```
psycopg2.errors.UndefinedColumn: column "photo_data" of relation "photos" does not exist
```

## 🔍 Cause
Le modèle `Photo` dans `models.py` définit des colonnes qui n'existent pas dans la base de données :
- `photo_data` - Données binaires de la photo
- `content_type` - Type MIME de l'image

## ✅ Solution

### Étape 1 : Corriger le schéma de la base de données

**Pour le déploiement Render :**

1. Allez sur votre dashboard Render
2. Naviguez vers votre service
3. Cliquez sur l'onglet "Shell"
4. Exécutez la commande :
   ```bash
   python fix_database_schema.py
   ```

**Pour le développement local :**
```bash
cd app
python fix_database_schema.py
```

### Étape 2 : Vérifier que le schéma est correct

Exécutez le script de test :
```bash
python test_database_schema.py
```

### Étape 3 : Redémarrer l'application

L'application devrait maintenant fonctionner correctement.

## 🔧 Scripts mis à jour

1. **`fix_database_schema.py`** - Corrige automatiquement le schéma (mis à jour)
2. **`test_database_schema.py`** - Vérifie que le schéma est correct (mis à jour)
3. **`start.sh`** - Inclut la vérification automatique

## 📋 Colonnes ajoutées

### Table `users`
- `selfie_data` (BYTEA/BLOB) - Données binaires des selfies

### Table `photos`
- `photo_data` (BYTEA/BLOB) - Données binaires des photos
- `content_type` (VARCHAR/TEXT) - Type MIME des images

## 🚀 Déploiement automatique

Le script `start.sh` a été mis à jour pour :
- Vérifier et corriger automatiquement le schéma au démarrage
- Tester que le schéma est correct pour toutes les tables
- Arrêter l'application si le schéma est incorrect

## 📝 Migration des données existantes

Si vous avez des photos existantes, vous pouvez les migrer vers la base de données :
```bash
python migrate_photos_to_db.py
```

## 🔒 Prévention

Pour éviter ce problème à l'avenir :
1. Utilisez des migrations de base de données (Alembic)
2. Testez les changements de schéma en local
3. Vérifiez la compatibilité avant le déploiement

## 📞 Support

Si le problème persiste :
1. Vérifiez les logs Render pour plus de détails
2. Exécutez `python test_database_schema.py` pour diagnostiquer
3. Contactez l'équipe de développement 