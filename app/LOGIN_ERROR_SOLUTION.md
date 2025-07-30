# Solution pour l'erreur de connexion

## 🚨 Problème
L'application échoue lors de la connexion avec l'erreur :
```
psycopg2.errors.UndefinedColumn: column users.selfie_data does not exist
```

## 🔍 Cause
Le modèle `User` dans `models.py` définit une colonne `selfie_data` :
```python
selfie_data = Column(LargeBinary, nullable=True)
```

Mais la table `users` dans la base de données n'a pas cette colonne, ce qui fait échouer SQLAlchemy lors de la requête.

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

## 🔧 Scripts créés

1. **`fix_database_schema.py`** - Corrige automatiquement le schéma
2. **`test_database_schema.py`** - Vérifie que le schéma est correct
3. **`start.sh`** - Mis à jour pour inclure la vérification automatique

## 📋 Vérification

Après avoir appliqué la correction :

1. **Testez la connexion** - L'endpoint `/api/login` devrait fonctionner
2. **Vérifiez les logs** - Plus d'erreurs de colonne manquante
3. **Testez l'upload de selfie** - Les nouvelles selfies devraient fonctionner

## 🚀 Déploiement automatique

Le script `start.sh` a été mis à jour pour :
- Vérifier et corriger automatiquement le schéma au démarrage
- Tester que le schéma est correct
- Arrêter l'application si le schéma est incorrect

## 📝 Migration des données existantes

Si vous avez des selfies existantes, vous pouvez les migrer vers la base de données :
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