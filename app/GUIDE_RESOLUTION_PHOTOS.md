# Guide de résolution des problèmes d'accès aux photos

## 🔍 Problèmes identifiés

D'après les logs, vous avez deux problèmes principaux :

1. **Erreur de validation FastAPI** : Le schéma `PhotoSchema` attendait que `file_path` soit une chaîne, mais maintenant c'est `None` car les photos sont stockées en binaire.

2. **Erreur 404 pour `/api/my-selfie`** : L'utilisateur n'a pas de selfie dans la base de données.

## ✅ Corrections apportées

### 1. Correction du schéma PhotoSchema

Le fichier `app/schemas.py` a été corrigé pour accepter `file_path` comme optionnel :

```python
class Photo(PhotoBase):
    id: int
    filename: str
    file_path: Optional[str] = None  # Peut être None car les photos sont stockées en binaire
    user_id: Optional[int] = None
    photographer_id: Optional[int] = None
    uploaded_at: datetime
```

### 2. Scripts de diagnostic et migration

Deux nouveaux scripts ont été créés :

- **`debug_photo_access.py`** : Pour diagnostiquer l'état des photos et selfies
- **`migrate_existing_photos.py`** : Pour migrer les photos existantes vers le système binaire

## 🚀 Étapes de résolution

### Étape 1 : Vérifier l'état actuel

Exécutez le script de diagnostic pour comprendre la situation :

```bash
cd app
python debug_photo_access.py
```

Ce script vous dira :
- Combien d'utilisateurs ont des selfies
- Combien de photos ont des données binaires
- Quels événements sont associés aux utilisateurs
- Les suggestions de résolution

### Étape 2 : Migrer les photos existantes

Si le diagnostic montre des photos sans données binaires, exécutez la migration :

```bash
cd app
python migrate_existing_photos.py
```

Ce script va :
- Lire les fichiers photos existants
- Les stocker comme données binaires dans la base de données
- Migrer les selfies utilisateur
- Vous donner des statistiques détaillées

### Étape 3 : Tester l'accès

Après la migration, testez l'accès aux photos :

1. **Connectez-vous en tant qu'utilisateur**
2. **Vérifiez que vous pouvez voir vos photos**
3. **Vérifiez que vous pouvez uploader une selfie si vous n'en avez pas**

### Étape 4 : Uploader une selfie (si nécessaire)

Si vous n'avez pas de selfie :

1. Connectez-vous à l'interface utilisateur
2. Allez dans la section "Ma Selfie"
3. Uploadez une photo de votre visage
4. Vérifiez que la selfie s'affiche correctement

## 🔧 Dépannage

### Si vous avez encore des erreurs 404

1. **Vérifiez que l'utilisateur a une selfie** :
   ```bash
   python debug_photo_access.py
   ```

2. **Vérifiez un utilisateur spécifique** :
   Modifiez le script `debug_photo_access.py` et décommentez :
   ```python
   check_specific_user(1)  # Remplacez 1 par l'ID de votre utilisateur
   ```

### Si les photos ne s'affichent toujours pas

1. **Vérifiez que les photos ont des données binaires** :
   Le script de diagnostic vous le dira

2. **Forcez la migration** :
   ```bash
   python migrate_existing_photos.py
   ```

3. **Vérifiez les logs Render** :
   Regardez s'il y a des erreurs 500 ou 404

### Si vous avez des erreurs de validation

1. **Redémarrez l'application** :
   Les changements de schéma nécessitent un redémarrage

2. **Vérifiez que le déploiement est à jour** :
   Assurez-vous que les derniers changements sont déployés sur Render

## 📊 Monitoring

Pour surveiller l'état de votre application :

1. **Logs Render** : Vérifiez les logs pour les erreurs
2. **Script de diagnostic** : Exécutez-le régulièrement
3. **Interface utilisateur** : Testez régulièrement l'accès aux photos

## 🆘 Support

Si vous avez encore des problèmes :

1. **Exécutez le diagnostic** et partagez les résultats
2. **Vérifiez les logs Render** pour les erreurs spécifiques
3. **Testez avec un nouvel utilisateur** pour isoler le problème

## ✅ Checklist de vérification

- [ ] Le schéma `PhotoSchema` a été corrigé
- [ ] Les scripts de diagnostic et migration sont créés
- [ ] L'application a été redémarrée sur Render
- [ ] Le diagnostic a été exécuté
- [ ] La migration a été effectuée (si nécessaire)
- [ ] L'utilisateur a uploadé une selfie (si nécessaire)
- [ ] L'accès aux photos fonctionne
- [ ] L'accès aux selfies fonctionne 