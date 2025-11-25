# 🎨 Guide - Interfaces HTML Statiques

## Important

Vous utilisez principalement les **interfaces HTML statiques** (et non React). Voici ce qui a été modifié.

## Changements dans l'interface photographe (photographer.html)

### Nouveaux boutons ajoutés

Dans la barre de sélection des photos, vous avez maintenant 5 boutons :

1. **Tout sélectionner** - Sélectionne toutes les photos
2. **Désélectionner** - Retire toutes les sélections
3. **✓ Afficher dans Général (X)** - Marque les photos sélectionnées comme visibles dans "Général" 
4. **✗ Masquer de Général (X)** - Masque les photos sélectionnées de "Général"
5. **🗑 Supprimer (X)** - Supprime les photos sélectionnées

### Badges visuels

Sur chaque photo, vous verrez :
- **Badge vert "✓ Visible"** + bordure verte = Photo visible dans "Général"
- **Badge orange "✗ Masqué"** + bordure orange = Photo masquée de "Général"
- **Pas de badge** = Comportement par défaut (visible si aucune sélection globale)

### Utilisation

1. **Connectez-vous** sur `https://votre-url/static/photographer.html`
2. **Sélectionnez un événement** dans le dropdown
3. **Cliquez sur les photos** pour les sélectionner (elles deviennent bleues)
4. **Cliquez sur le bouton approprié** :
   - "✓ Afficher dans Général" si vous voulez que seules ces photos soient visibles
   - "✗ Masquer de Général" si vous voulez masquer ces photos

## Changements dans l'interface utilisateur (index.html)

### Labels mis à jour

- **"Vos Photos"** → **"Mes photos"** (plus naturel en français)
- Le comportement reste identique : affiche toutes les photos où l'utilisateur apparaît

### Onglet "Général"

- Si le photographe a sélectionné des photos → **affiche uniquement ces photos**
- Si aucune sélection → **affiche toutes les photos** (comportement par défaut)

## Déploiement

```bash
git add .
git commit -m "feat: Add photo selection in static HTML interfaces"
git push origin main
```

Attendez le redémarrage de l'application (1-2 minutes).

## Test après déploiement

### 1. Interface photographe

1. **Déconnectez-vous et reconnectez-vous** (le 401 que vous avez c'est juste un token expiré)
2. Allez sur `/static/photographer.html`
3. Vérifiez que vous voyez vos photos
4. Vérifiez que les nouveaux boutons sont présents
5. Sélectionnez quelques photos et testez "✓ Afficher dans Général"

### 2. Interface utilisateur

1. Allez sur `/static/index.html` avec un compte utilisateur
2. Vérifiez que l'onglet est maintenant "Mes photos" (et non "Vos photos")
3. Vérifiez que "Général" n'affiche que les photos sélectionnées par le photographe

## Problèmes connus et solutions

### Erreur 401 (Unauthorized)

**Cause** : Votre token d'authentification a expiré.

**Solution** : 
1. Déconnectez-vous
2. Reconnectez-vous
3. Le nouveau token sera valide

### Les boutons n'apparaissent pas

**Vérifications** :
1. Avez-vous vidé le cache du navigateur ? (Ctrl+F5)
2. Le déploiement est-il terminé ?
3. Êtes-vous bien sur `/static/photographer.html` ?

### Les photos ne sont pas visibles

**Vérifications** :
1. Êtes-vous connecté en tant que photographe ?
2. Avez-vous sélectionné un événement ?
3. L'événement a-t-il des photos uploadées ?

## Différence React vs HTML Statique

| Fonctionnalité | React (frontend/) | HTML Statique (static/) |
|----------------|-------------------|-------------------------|
| Interface photographe | PhotographerEventManager.tsx | photographer.html |
| Interface utilisateur | Dashboard.tsx | index.html |
| Sélection photos | ✅ Implémentée | ✅ Implémentée |
| Badges visuels | ✅ Implémentés | ✅ Implémentés |

Les deux interfaces ont maintenant la fonctionnalité complète !

## URLs des interfaces

- **Photographe React** : `https://votre-url/` (puis login photographe)
- **Photographe HTML** : `https://votre-url/static/photographer.html`
- **Utilisateur React** : `https://votre-url/` (puis login utilisateur)
- **Utilisateur HTML** : `https://votre-url/static/index.html`

## Notes importantes

- ✅ Les deux interfaces (React et HTML) ont maintenant la fonctionnalité
- ✅ Les modifications sont compatibles avec votre infrastructure existante
- ✅ Le backend gère la logique de sélection automatiquement
- ⚠️ N'oubliez pas de vider le cache du navigateur après le déploiement (Ctrl+F5)

