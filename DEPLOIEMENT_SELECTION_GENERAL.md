# 🚀 Déploiement - Sélection des photos dans "Général"

## ✅ Ce qui a été implémenté

### Nouvelle fonctionnalité
Les photographes peuvent maintenant **sélectionner manuellement** quelles photos apparaissent dans l'onglet "Général" de la galerie publique.

**Comportement :**
- Si le photographe sélectionne des photos → seules ces photos apparaissent dans "Général"
- Si aucune sélection → aucune photo n'apparaît (comportement par défaut sécurisé)
- "Mes photos" continue de fonctionner exactement comme avant

## 🔧 Déploiement (SUPER SIMPLE)

### Étape unique : Déployer !

```bash
git add .
git commit -m "feat: Add manual photo selection for Général tab"
git push origin main
```

**C'est tout !** 🎉

Au redémarrage de votre application, SQLAlchemy va **automatiquement** :
1. Détecter que la colonne `show_in_general` est manquante dans la table `photos`
2. Créer cette colonne avec les bonnes caractéristiques (BOOLEAN DEFAULT NULL)
3. Rendre la fonctionnalité opérationnelle

### Pourquoi c'est automatique ?

Votre application exécute un script de migration au démarrage (dans `main.py`, ligne 58) :

```python
@app.on_event("startup")
def _startup_create_tables():
    try:
        create_tables()
        print("[Startup] Database tables created/verified")
        
        # Ajouter la colonne show_in_general si elle n'existe pas
        from add_show_in_general_column import add_show_in_general_column
        add_show_in_general_column()  # ← Ajoute automatiquement la colonne
        
    except Exception as e:
        print(f"[Startup] Warning: Could not create tables (non-critical): {e}")
```

Au démarrage, l'application :
1. Crée les tables si nécessaire
2. Vérifie si la colonne `show_in_general` existe
3. Si elle n'existe pas, l'ajoute automatiquement avec `ALTER TABLE`

## ✨ Utilisation pour les photographes

Après le déploiement, dans l'interface photographe :

1. **Sélectionnez votre événement**
2. **Cliquez sur les photos** pour les sélectionner (bordure rouge)
3. **Utilisez les boutons** :
   - `✓ Afficher dans Général` (vert) - Rend les photos visibles dans "Général"
   - `✗ Masquer de Général` (orange) - Masque les photos de "Général"
   - `🗑 Supprimer` - Supprime les photos

### Indicateurs visuels

- Badge **vert** "Visible dans Général" : Photo sélectionnée pour "Général"
- Badge **orange** "Masqué de Général" : Photo explicitement masquée
- Pas de badge : Comportement par défaut (visible si aucune sélection globale)

## 🎨 Changements d'interface

### Pour les utilisateurs finaux

- **"Vos photos"** → **"Mes photos"** (plus naturel en français)
- Suppression du badge "Match" dans "Mes photos" (redondant car toutes les photos de cet onglet sont des matches)
- Conservation du badge "Match" dans "Général" (utile pour repérer ses photos parmi toutes)

## 📊 Vérification

### 1. Vérifier que la colonne a été créée

Connectez-vous à votre PostgreSQL et exécutez :

```sql
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name='photos' AND column_name='show_in_general';
```

Résultat attendu :
```
column_name      | data_type | is_nullable | column_default
-----------------+-----------+-------------+----------------
show_in_general  | boolean   | YES         | NULL
```

### 2. Tester la fonctionnalité

1. **Compte photographe** :
   - Connectez-vous en tant que photographe
   - Vérifiez que vous voyez vos photos
   - Vérifiez que les nouveaux boutons apparaissent
   - Sélectionnez quelques photos et cliquez sur "✓ Afficher dans Général"

2. **Compte utilisateur** :
   - Connectez-vous en tant qu'utilisateur du même événement
   - Vérifiez que "Général" n'affiche que les photos sélectionnées
   - Vérifiez que "Mes photos" affiche toutes vos photos personnelles

### 3. Tester le comportement

- **Sans sélection** : "Général" doit être vide (photos masquées par défaut)
- **Avec sélection** : "Général" doit afficher uniquement les photos sélectionnées

## 🐛 Résolution de problèmes

### "Erreur lors du chargement des photos" (500)

**Cause probable :** La colonne n'a pas été créée automatiquement.

**Solution :**
1. Vérifiez les logs de votre application au démarrage
2. Vérifiez que `create_tables()` s'est bien exécuté
3. Si nécessaire, créez la colonne manuellement :

```sql
ALTER TABLE photos ADD COLUMN show_in_general BOOLEAN DEFAULT NULL;
```

### Les boutons n'apparaissent pas

**Vérifications :**
1. Le frontend React a-t-il été recompilé ? (`npm run build`)
2. Le cache du navigateur a-t-il été vidé ? (Ctrl+F5)
3. Êtes-vous connecté en tant que photographe ?

### La sélection ne fonctionne pas

**Vérifications :**
1. La colonne `show_in_general` existe-t-elle dans la base ?
2. Les endpoints `/api/photos/bulk/show-in-general` répondent-ils ?
3. Vérifiez les logs backend pour voir les erreurs

## 📝 Fichiers modifiés

- `face_recognition/app/models.py` - Ajout du champ `show_in_general`
- `face_recognition/app/main.py` - Nouveaux endpoints + logique de sélection
- `face_recognition/app/frontend/src/types/index.ts` - Type TypeScript mis à jour
- `face_recognition/app/frontend/src/services/api.ts` - Nouveaux services API
- `face_recognition/app/frontend/src/components/PhotographerEventManager.tsx` - Nouvelle UI
- `face_recognition/app/frontend/src/components/Dashboard.tsx` - Labels mis à jour
- `face_recognition/app/static/index.html` - Labels mis à jour

## 💡 Cas d'usage

### Scénario 1 : Mariage
1. Pendant l'événement : toutes les photos sont visibles
2. Après : sélection des 50 meilleures photos
3. Résultat : invités voient seulement les 50 meilleures dans "Général"

### Scénario 2 : Événement sportif  
1. Upload de toutes les photos
2. Pas de sélection manuelle
3. Résultat : tous les participants voient toutes les photos

### Scénario 3 : Soirée d'entreprise
1. Upload de 200 photos
2. Masquage de 20 photos ratées
3. Résultat : participants voient 180 bonnes photos

## 🎉 Félicitations !

Votre nouvelle fonctionnalité est prête. Un simple déploiement suffit grâce à SQLAlchemy qui gère automatiquement les modifications de schéma !

