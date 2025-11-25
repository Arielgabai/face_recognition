# 📋 Résumé des changements - Sélection photos "Général"

## Ce qui a changé

### ✅ Backend
- **Nouveau champ** : `show_in_general` (Boolean, nullable) dans le modèle `Photo`
- **Nouveaux endpoints** :
  - `PUT /api/photos/{photo_id}/show-in-general` - Toggle une photo
  - `PUT /api/photos/bulk/show-in-general` - Toggle plusieurs photos en masse
- **Logique modifiée** : `/api/all-photos` et `/api/user/events/{event_id}/all-photos` utilisent maintenant la sélection avec fallback

### ✅ Frontend React
- **Nouveaux boutons** dans l'interface photographe pour sélectionner/masquer des photos
- **Badges visuels** : vert (visible), orange (masqué)
- **Labels améliorés** : "Vos photos" → "Mes photos"

### ✅ Frontend HTML
- **Labels mis à jour** : "Vos Photos" → "Mes photos"

## Déploiement

```bash
git add .
git commit -m "feat: Add manual photo selection for Général tab"
git push origin main
```

**C'est tout !** SQLAlchemy créera automatiquement la colonne `show_in_general` au redémarrage de l'application.

## Comportement

### Onglet "Mes photos"
- Affiche toutes les photos où l'utilisateur apparaît
- **Aucun changement de comportement**

### Onglet "Général"
- **Si des photos sont sélectionnées** → affiche uniquement ces photos
- **Si aucune sélection** → affiche toutes les photos (fallback)

## Utilisation photographe

1. Sélectionner un événement
2. Cliquer sur les photos pour les sélectionner
3. Utiliser les boutons :
   - `✓ Afficher dans Général` (vert)
   - `✗ Masquer de Général` (orange)
   - `🗑 Supprimer`

## Documentation complète

Voir `DEPLOIEMENT_SELECTION_GENERAL.md` pour tous les détails.

