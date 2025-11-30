# 🎨 Fix - Layout 2 colonnes centré pleine largeur

## Problème
Après les correctifs de zoom, la galerie affichait :
- **1 seule photo par ligne** au lieu de 2
- Les photos **ne prenaient pas toute la largeur**
- Layout différent de l'original

## Solution appliquée

### 1. ✅ Grid forcé à 2 colonnes strictes (partout)

**Avant** :
```css
grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
```
→ Créait un nombre variable de colonnes selon la largeur

**Après** :
```css
grid-template-columns: repeat(2, 1fr);
```
→ Force exactement 2 colonnes de largeur égale

**Fichier** : `face_recognition/app/static/css/gallery.css`

---

### 2. ✅ Media queries mises à jour

**Tablette (≤768px)** :
```css
@media (max-width: 768px) {
    .modern-gallery,
    #myModernGallery,
    #allModernGallery {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 4px !important;
        width: 100vw !important;
        /* Déborde du container pour prendre toute la largeur */
        margin-left: -20px !important;
        margin-right: -20px !important;
        padding: 0 20px !important;
    }
}
```

**Mobile (≤480px)** :
```css
@media (max-width: 480px) {
    .modern-gallery,
    #myModernGallery,
    #allModernGallery {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 2px !important;
        width: 100vw !important;
        margin-left: -20px !important;
        margin-right: -20px !important;
        padding: 0 20px !important;
    }
}
```

---

### 3. ✅ Cartes avec aspect-ratio et hauteur minimale

```css
.gallery-photo-card {
    /* ... */
    width: 100%;
    min-height: 200px;    /* ← Ajouté */
    aspect-ratio: 3/4;    /* ← Ajouté (format portrait standard) */
}
```

**Effet** : Les cartes ont maintenant une taille cohérente et remplissent l'espace.

---

### 4. ✅ Images en mode "cover"

**Avant** :
```css
object-fit: contain;  /* Garde l'image entière, peut laisser des espaces */
```

**Après** :
```css
object-fit: cover;  /* Remplit toute la carte, crop si nécessaire */
```

**Effet** : Les photos remplissent complètement leurs cellules sans espaces vides.

---

### 5. ✅ JavaScript mobile aligné

Dans `index.html`, les overrides JavaScript pour mobile utilisent maintenant :
```javascript
galleryElement.style.gridTemplateColumns = 'repeat(2, 1fr)';
```
Au lieu de `repeat(auto-fit, minmax(150px, 1fr))`

---

## 🎯 Résultat

### Layout
```
┌─────────────────────────────────────────┐
│         CONTAINER (max 1200px)          │
│                                          │
│  ┌─────────────┐  ┌─────────────┐      │
│  │   Photo 1   │  │   Photo 2   │      │
│  │   (3:4)     │  │   (3:4)     │      │
│  └─────────────┘  └─────────────┘      │
│                                          │
│  ┌─────────────┐  ┌─────────────┐      │
│  │   Photo 3   │  │   Photo 4   │      │
│  │   (3:4)     │  │   (3:4)     │      │
│  └─────────────┘  └─────────────┘      │
│                                          │
└─────────────────────────────────────────┘
```

### Caractéristiques
- ✅ **2 colonnes exactement** (partout : desktop, tablette, mobile)
- ✅ **Chaque colonne = 50% de la largeur** (moins le gap)
- ✅ **Photos remplissent leurs cartes** (object-fit: cover)
- ✅ **Aspect-ratio cohérent** (3:4 = format portrait)
- ✅ **Centré dans le viewport**
- ✅ **Prend quasi toute la largeur disponible**

---

## 📱 Comportement responsive

### Desktop (>768px)
- Container : `max-width: 1200px` centré
- Grid : 2 colonnes de `~590px` chaque (moins gap)
- Gap : 8px

### Tablette (≤768px)
- Grid : `width: 100vw` (déborde du container)
- Grid : 2 colonnes égales
- Gap : 4px
- Padding : 0 20px (marges respirantes)

### Mobile (≤480px)
- Grid : `width: 100vw` (déborde du container)
- Grid : 2 colonnes égales
- Gap : 2px (minimal pour effet "collé")
- Padding : 0 20px

---

## 🚀 Déployer

```bash
git add .
git commit -m "fix: Restore 2-column grid layout with full width"
git push origin main
```

---

## 🧪 Test attendu

1. **Desktop** : Se connecter → ✅ 2 colonnes centrées, largeur ~1200px
2. **Tablette** : Réduire fenêtre → ✅ 2 colonnes pleine largeur
3. **Mobile** : Sur téléphone → ✅ 2 colonnes serrées pleine largeur
4. **Zoom** : Zoom/dézoom → ✅ Layout reste correct
5. **Centrage** : ✅ Toujours centré horizontalement

C'est exactement le layout d'avant : 2 colonnes bien centrées qui prennent quasi toute la largeur ! 🎉

