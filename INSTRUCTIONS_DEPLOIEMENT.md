# 🚀 Instructions de déploiement

## Problème actuel

Vous avez l'erreur 500 sur `/api/photographer/events/4/photos` car la colonne `show_in_general` n'existe pas encore dans votre base PostgreSQL.

## Solution

J'ai créé un script qui s'exécute automatiquement au démarrage et ajoute la colonne si elle n'existe pas.

## Étapes de déploiement

### 1. Commiter les changements

```bash
git add .
git commit -m "feat: Add photo selection for Général tab with auto-migration"
git push origin main
```

### 2. Attendre le redémarrage

Votre service cloud (AWS App Runner) va automatiquement :
- Détecter le nouveau code
- Rebuilder l'application
- Redémarrer le service

Au démarrage, le script `add_show_in_general_column.py` va automatiquement ajouter la colonne dans votre PostgreSQL.

### 3. Vérifier les logs

Dans les logs de démarrage de votre application, vous devriez voir :

```
[Startup] Database tables created/verified
Adding show_in_general column to photos table...
✓ Column show_in_general added successfully!
```

Ou si la colonne existe déjà :

```
✓ Column show_in_general already exists
```

### 4. Tester

1. Rafraîchissez votre interface photographe (Ctrl+F5)
2. Vous devriez maintenant voir vos photos
3. Les nouveaux boutons "✓ Afficher dans Général" et "✗ Masquer de Général" devraient être visibles

## Si l'erreur persiste

Si après le redémarrage vous avez toujours l'erreur 500 :

### Vérifier les logs

Regardez les logs de votre application pour voir si le script de migration s'est bien exécuté.

### Solution manuelle (dernier recours)

Si le script automatique ne fonctionne pas, connectez-vous à votre console PostgreSQL et exécutez :

```sql
-- Vérifier si la colonne existe
SELECT column_name 
FROM information_schema.columns 
WHERE table_name='photos' AND column_name='show_in_general';

-- Si elle n'existe pas, l'ajouter
ALTER TABLE photos 
ADD COLUMN show_in_general BOOLEAN DEFAULT NULL;

-- Vérifier que c'est ajouté
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name='photos' AND column_name='show_in_general';
```

Puis redémarrez votre application.

## Fichiers modifiés

- ✅ `face_recognition/app/models.py` - Ajout du champ
- ✅ `face_recognition/app/main.py` - Nouveaux endpoints + appel de la migration au startup
- ✅ `face_recognition/app/add_show_in_general_column.py` - Script de migration auto
- ✅ `face_recognition/app/frontend/...` - Interface photographe
- ✅ Documentation

## Questions ?

Si vous avez des problèmes, envoyez-moi :
1. Les logs de démarrage de votre application
2. Le message d'erreur exact que vous recevez

