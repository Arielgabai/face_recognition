# Implémentation - Sélection manuelle des photos dans "Général"

## ✅ Changements implémentés

### 1. Base de données (PostgreSQL)

**Fichiers créés :**
- `face_recognition/app/migrate_add_show_in_general.py` - Script de migration Python
- `face_recognition/app/migration_show_in_general.sql` - Script SQL direct

**Modification du modèle :**
- `face_recognition/app/models.py` - Ajout du champ `show_in_general` dans le modèle `Photo`

```python
show_in_general = Column(Boolean, nullable=True, default=None)
```

### 2. Backend (FastAPI)

**Fichier modifié :** `face_recognition/app/main.py`

**Endpoints modifiés :**
- `GET /api/all-photos` - Retourne uniquement les photos explicitement autorisées
- `GET /api/user/events/{event_id}/all-photos` - Retourne uniquement les photos explicitement autorisées

**Nouveaux endpoints :**
- `PUT /api/photos/{photo_id}/show-in-general` - Toggle une photo individuelle
- `PUT /api/photos/bulk/show-in-general` - Toggle plusieurs photos en masse

### 3. Frontend React (TypeScript)

**Fichiers modifiés :**

**`face_recognition/app/frontend/src/types/index.ts`**
- Ajout du champ `show_in_general?: boolean | null` dans l'interface `Photo`

**`face_recognition/app/frontend/src/services/api.ts`**
- `togglePhotoShowInGeneral()` - Toggle une photo
- `bulkTogglePhotosShowInGeneral()` - Toggle plusieurs photos

**`face_recognition/app/frontend/src/components/PhotographerEventManager.tsx`**
- Ajout de 2 nouveaux boutons : "✓ Afficher dans Général" et "✗ Masquer de Général"
- Badges visuels : 
  - Vert "Visible dans Général" pour les photos sélectionnées
  - Orange "Masqué de Général" pour les photos masquées
- Bordures colorées sur les cartes de photos selon leur statut

**`face_recognition/app/frontend/src/components/Dashboard.tsx`**
- Changement "Vos photos" → "Mes photos"
- Changement "Toutes les photos disponibles" → "Général"
- Suppression du badge "Match" dans l'onglet "Mes photos" (redondant)
- Conservation du badge "Match" dans l'onglet "Général"

### 4. Frontend HTML statique

**Fichier modifié :** `face_recognition/app/static/index.html`

- Changement "Vos Photos" → "Mes photos" dans les onglets
- Changement du label du bouton

### 5. Documentation

**Fichiers créés :**
- `face_recognition/GUIDE_SELECTION_PHOTOS_GENERAL.md` - Guide complet d'utilisation
- `face_recognition/IMPLEMENTATION_SELECTION_GENERAL.md` - Ce fichier

## 🚀 Étapes de déploiement

### 1. Exécuter la migration sur votre PostgreSQL cloud

**Option A - Script Python (recommandé) :**
```bash
# Assurez-vous que DATABASE_URL est configuré
export DATABASE_URL="postgresql://user:password@host:port/dbname"
cd face_recognition/app
python migrate_add_show_in_general.py
```

**Option B - SQL direct :**
```bash
# Connectez-vous à votre console PostgreSQL et exécutez :
psql $DATABASE_URL -f face_recognition/app/migration_show_in_general.sql
```

Ou via l'interface web de votre hébergeur cloud (Render, Heroku, AWS RDS, etc.).

### 2. Commiter et déployer

```bash
git add .
git commit -m "feat: Add manual photo selection for Général tab

- Add show_in_general column to photos table
- Add photographer UI to select photos for Général tab
- Update API endpoints with explicit selection logic
- Change Vos photos to Mes photos
- Add visual indicators in photographer interface"

git push origin main
```

### 3. Redémarrer l'application

Selon votre plateforme de déploiement, redémarrez l'application backend.

### 4. Tester la fonctionnalité

1. Connectez-vous en tant que photographe
2. Sélectionnez un événement
3. Essayez de sélectionner des photos et de les marquer comme "Afficher dans Général"
4. Connectez-vous en tant qu'utilisateur du même événement
5. Vérifiez que l'onglet "Général" n'affiche que les photos sélectionnées
6. Vérifiez que "Mes photos" continue de fonctionner normalement

## 📋 Checklist de vérification

- [ ] Migration exécutée sur la base PostgreSQL
- [ ] Colonne `show_in_general` existe dans la table `photos`
- [ ] Code backend déployé
- [ ] Code frontend React compilé et déployé
- [ ] Application redémarrée
- [ ] Tests effectués avec un compte photographe
- [ ] Tests effectués avec un compte utilisateur
- [ ] Vérification que l'onglet "Général" est vide tant qu'aucune photo n'est sélectionnée
- [ ] Vérification de la sélection (photos sélectionnées = seulement celles-là affichées)

## 🔍 Résolution de problèmes

### La migration échoue

**Problème :** `no such table: photos`
**Solution :** Vous êtes peut-être en local avec SQLite. La migration est conçue pour PostgreSQL. Assurez-vous d'exécuter sur votre base cloud.

**Problème :** `column already exists`
**Solution :** La migration a déjà été exécutée. Vous pouvez vérifier avec :
```sql
SELECT * FROM information_schema.columns WHERE table_name='photos' AND column_name='show_in_general';
```

### Les boutons n'apparaissent pas dans l'interface photographe

**Vérifications :**
1. Le frontend React a-t-il été recompilé ? (`npm run build` dans `face_recognition/app/frontend`)
2. Le navigateur a-t-il été rafraîchi (Ctrl+F5 pour forcer le refresh du cache)
3. Êtes-vous bien connecté en tant que photographe ?

### Les photos ne sont pas filtrées dans "Général"

**Vérifications :**
1. Avez-vous bien cliqué sur "✓ Afficher dans Général" après avoir sélectionné des photos ?
2. Vérifiez les valeurs dans la base :
```sql
SELECT id, original_filename, show_in_general FROM photos WHERE event_id = YOUR_EVENT_ID;
```
3. Vérifiez que l'API retourne bien les données filtrées (DevTools > Network > `/api/all-photos`)

## 📊 Structure de la fonctionnalité

```
Photographe sélectionne photos
         ↓
   show_in_general = TRUE
         ↓
API /api/all-photos
         ↓
    Retourner uniquement les photos avec show_in_general = TRUE
         ↓
   Affichage dans "Général"
```

## 🎨 Interface utilisateur

### Vue photographe

```
┌─────────────────────────────────────────┐
│ Événement: [Dropdown Sélection]         │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ Photos de l'événement (42)              │
│                                          │
│ [Désélectionner] [Tout sélectionner]   │
│ [✓ Afficher dans Général (3)]          │
│ [✗ Masquer de Général (0)]             │
│ [🗑 Supprimer (0)]                      │
│                                          │
│ ┌─────┐ ┌─────┐ ┌─────┐               │
│ │ 🟢  │ │     │ │ 🟠  │               │
│ │ IMG │ │ IMG │ │ IMG │               │
│ └─────┘ └─────┘ └─────┘               │
│   ✓       -       ✗                     │
└─────────────────────────────────────────┘

🟢 = Visible dans Général
🟠 = Masqué de Général
```

### Vue utilisateur

```
Onglet "Mes photos": Photos où l'utilisateur apparaît
                     (inchangé, toujours toutes ses photos)

Onglet "Général": Photos sélectionnées par le photographe uniquement
                  (vide tant que rien n'est sélectionné)
                  + Badge "Match" sur les photos où l'utilisateur apparaît
```

## 💡 Cas d'usage

### Cas 1 : Mariage - Sélection progressive

1. **Pendant l'événement** : Le photographe upload toutes les photos, mais rien n'apparaît dans "Général"
2. **Après l'événement** : Le photographe sélectionne les 50 meilleures photos
3. **Résultat** : Les invités voient maintenant seulement les 50 meilleures dans "Général", mais gardent toutes leurs photos personnelles dans "Mes photos"

### Cas 2 : Soirée d'entreprise - Contrôle de la qualité

1. Le photographe upload 200 photos
2. Il sélectionne uniquement les 180 photos présentables
3. Les 20 restantes restent masquées (valeur False)
4. Les participants ne voient que les 180 bonnes photos dans "Général"

### Cas 3 : Événement sportif - Affichage complet par sélection

1. Le photographe upload toutes les photos
2. Il utilise "Tout sélectionner" puis "✓ Afficher dans Général" pour tout rendre visible
3. Tous les participants voient toutes les photos (affichage explicite)
4. Chacun retrouve ses photos dans "Mes photos"

## ✨ Améliorations futures possibles

- [ ] Bouton "Réinitialiser la sélection" pour revenir au comportement par défaut
- [ ] Filtres supplémentaires (par date, par nombre de visages, etc.)
- [ ] Prévisualisation de ce que verront les utilisateurs
- [ ] Statistiques : "X photos visibles / Y photos totales"
- [ ] Sélection/désélection par glisser-déposer
- [ ] Mode "galerie" pour voir toutes les photos sélectionnées d'un coup

## 📞 Support

Pour toute question ou problème, référez-vous au fichier `GUIDE_SELECTION_PHOTOS_GENERAL.md` pour plus de détails.

