# Guide - Sélection des photos pour l'onglet "Général"

## Vue d'ensemble

Cette fonctionnalité permet aux photographes de **sélectionner manuellement** quelles photos apparaissent dans l'onglet "Général" de la galerie publique.

### Comportement

1. **"Vos photos" (Mes photos)** : Affiche toutes les photos où l'utilisateur apparaît (comportement inchangé)
2. **"Général"** : 
   - Si le photographe a sélectionné des photos → affiche uniquement les photos sélectionnées
   - Si aucune photo n'est sélectionnée → affiche toutes les photos (fallback automatique)

## Déploiement

### Étape 1 : Migration de la base de données

Vous avez **deux options** pour exécuter la migration :

#### Option A : Script Python (Recommandé)

```bash
cd face_recognition/app
python migrate_add_show_in_general.py
```

Assurez-vous que la variable d'environnement `DATABASE_URL` est configurée correctement pour pointer vers votre base PostgreSQL cloud.

#### Option B : SQL Direct

Si vous préférez exécuter le SQL directement sur votre base PostgreSQL :

```bash
psql $DATABASE_URL -f face_recognition/app/migration_show_in_general.sql
```

Ou connectez-vous à votre console PostgreSQL cloud et exécutez le contenu du fichier `migration_show_in_general.sql`.

### Étape 2 : Déployer le code

Une fois la migration effectuée, déployez le nouveau code sur votre serveur :

```bash
git add .
git commit -m "feat: Add photo selection for Général tab"
git push origin main
```

Votre plateforme de déploiement (Render, Heroku, etc.) devrait automatiquement déployer les changements.

### Étape 3 : Redémarrer l'application

Redémarrez votre application backend pour que les changements prennent effet.

## Utilisation pour les photographes

### Interface photographe (Dashboard React)

1. **Connectez-vous** en tant que photographe
2. **Sélectionnez votre événement** dans le dropdown
3. Vous verrez la liste de toutes les photos de l'événement
4. Pour chaque photo, vous pouvez voir :
   - Badge **"Visible dans Général"** (vert) : La photo est sélectionnée
   - Badge **"Masqué de Général"** (orange) : La photo est explicitement masquée
   - Pas de badge : La photo suivra le comportement par défaut

### Actions disponibles

**Sélection de photos :**
- Cliquez sur les photos pour les sélectionner (bordure rouge)
- Bouton **"Désélectionner"** : Retire toutes les sélections
- Bouton **"Tout sélectionner"** : Sélectionne toutes les photos

**Gestion de la visibilité :**
- Bouton **"✓ Afficher dans Général"** : Marque les photos sélectionnées comme visibles dans "Général"
- Bouton **"✗ Masquer de Général"** : Masque les photos sélectionnées de "Général"
- Bouton **"🗑 Supprimer"** : Supprime définitivement les photos sélectionnées

### Stratégies d'utilisation

#### Scénario 1 : Sélection manuelle (recommandé)
1. Ne rien faire au début → tous les utilisateurs voient toutes les photos
2. Une fois l'événement terminé, sélectionnez uniquement les meilleures photos
3. Les utilisateurs ne verront que cette sélection dans "Général"
4. Leurs photos personnelles restent visibles dans "Mes photos"

#### Scénario 2 : Masquage de photos spécifiques
1. Si vous voulez masquer quelques photos ratées sans tout reconfigurer
2. Sélectionnez les photos à masquer
3. Cliquez sur "Masquer de Général"

#### Scénario 3 : Revenir à l'affichage complet
Si vous avez fait une sélection mais voulez revenir au comportement par défaut (tout afficher) :
- Il faut actuellement réinitialiser manuellement via la base de données (feature à venir)
- Ou supprimer/re-uploader les photos

## Changements techniques

### Modèle de données

Nouvelle colonne ajoutée à la table `photos` :

```python
show_in_general = Column(Boolean, nullable=True, default=None)
```

- `NULL` (par défaut) : Fallback, photo visible si aucune sélection n'existe
- `True` : Explicitement visible dans "Général"
- `False` : Explicitement masquée de "Général"

### API Endpoints

**Nouveaux endpoints :**

```
PUT /api/photos/{photo_id}/show-in-general
Body: { "show_in_general": true/false }
```

```
PUT /api/photos/bulk/show-in-general
Body: { "photo_ids": [1, 2, 3], "show_in_general": true/false }
```

**Endpoints modifiés :**

- `GET /api/all-photos` : Applique la logique de sélection
- `GET /api/user/events/{event_id}/all-photos` : Applique la logique de sélection

### Logique de fallback

```python
# Vérifier s'il existe des photos explicitement sélectionnées
selected_count = db.query(Photo).filter(
    Photo.event_id == event_id,
    Photo.show_in_general == True
).count()

# Si des photos sont sélectionnées, n'afficher que celles-là
if selected_count > 0:
    photos = photos.filter(Photo.show_in_general == True)
# Sinon, afficher toutes les photos (fallback)
```

## Modifications de l'interface utilisateur

### Tab "Mes photos" (anciennement "Vos photos")

- Le titre a été changé de "Vos photos" à "Mes photos"
- Le badge "Match" a été retiré car toutes les photos de cet onglet sont par définition des matches
- Comportement fonctionnel inchangé

### Tab "Général"

- Les badges "Match" sont conservés pour indiquer les photos où l'utilisateur apparaît
- Applique maintenant la logique de sélection du photographe
- Fallback automatique sur toutes les photos si aucune sélection

## Vérification

Pour vérifier que la migration a bien fonctionné :

```sql
-- Vérifier que la colonne existe
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name='photos' AND column_name='show_in_general';

-- Vérifier les valeurs actuelles
SELECT id, original_filename, show_in_general 
FROM photos 
LIMIT 10;
```

Toutes les photos existantes devraient avoir `show_in_general = NULL`.

## Support

Si vous rencontrez des problèmes :

1. Vérifiez que la migration s'est bien exécutée
2. Vérifiez les logs de votre application
3. Testez avec le compte photographe sur un événement test
4. Vérifiez que l'API répond correctement aux nouveaux endpoints

## Notes importantes

- ✅ La fonctionnalité est rétrocompatible : si aucune photo n'est sélectionnée, le comportement par défaut s'applique
- ✅ Les photos existantes ne sont pas affectées
- ✅ "Mes photos" continue de fonctionner exactement comme avant
- ⚠️ Le photographe doit explicitement sélectionner des photos pour activer le filtrage dans "Général"

