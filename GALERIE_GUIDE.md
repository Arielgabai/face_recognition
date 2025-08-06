# 📸 Galerie d'Images Moderne - Guide d'Utilisation

Une galerie d'images responsive et moderne inspirée de Google Photos, Pinterest et memento.photo qui s'adapte automatiquement aux différentes proportions d'images.

## 🌟 Fonctionnalités

- **Grille responsive** : Adaptation automatique à toutes les tailles d'écran
- **Proportions intelligentes** : Détection automatique des ratios (portrait, paysage, carré)
- **Lightbox intégré** : Navigation fluide entre les images
- **Animations élégantes** : Effets de transition et d'apparition
- **Navigation clavier** : Support complet des raccourcis clavier
- **Lazy loading** : Chargement optimisé des images
- **Thèmes** : Mode clair et sombre
- **Accessibilité** : Conforme aux standards WCAG

## 🚀 Installation Rapide

### Option 1 : Template Flask (Prêt à l'emploi)

1. Copiez le fichier `app/templates/gallery.html` dans vos templates
2. Le template utilise les variables Flask : `user_id`, `photos_match`, `photos_all`

```html
<!-- Dans votre route Flask -->
@app.route('/gallery/<user_id>')
def gallery(user_id):
    photos_match = get_user_photos(user_id)
    photos_all = get_all_photos()
    return render_template('gallery.html', 
                         user_id=user_id, 
                         photos_match=photos_match, 
                         photos_all=photos_all)
```

### Option 2 : Fichiers CSS/JS séparés (Réutilisable)

1. Incluez les fichiers CSS et JS :

```html
<link rel="stylesheet" href="/static/css/gallery.css">
<script src="/static/js/gallery.js"></script>
```

2. Créez votre galerie :

```html
<div id="ma-galerie"></div>

<script>
const images = [
    { src: 'image1.jpg', alt: 'Description 1' },
    { src: 'image2.jpg', alt: 'Description 2' },
    // ...
];

const gallery = new ModernGallery('#ma-galerie');
gallery.loadImages(images);
</script>
```

## 📋 Usage JavaScript

### Initialisation basique

```javascript
// Méthode simple
const gallery = createGallery('#container', images);

// Méthode avec options
const gallery = new ModernGallery('#container', {
    theme: 'dark',
    size: 'large',
    lightbox: true,
    animations: true
});

gallery.loadImages(images);
```

### Format des images

```javascript
const images = [
    {
        src: 'https://example.com/image1.jpg',
        alt: 'Description de l\'image',
        aspectRatio: 1.5 // Optionnel (largeur/hauteur)
    },
    // ...
];
```

### Options disponibles

```javascript
const options = {
    autoDetectRatio: true,      // Détection automatique des proportions
    lightbox: true,             // Activer le lightbox
    keyboardNavigation: true,   // Navigation clavier
    animations: true,           // Animations d'apparition
    lazy: true,                 // Lazy loading
    theme: 'light',            // 'light' ou 'dark'
    size: 'normal'             // 'compact', 'normal', 'large'
};
```

### Méthodes principales

```javascript
// Charger des images
gallery.loadImages(images);

// Ajouter des images
gallery.addImages(newImages);

// Supprimer une image
gallery.removeImage(index);

// Vider la galerie
gallery.clear();

// Changer les options
gallery.updateOptions({ theme: 'dark' });

// Détruire la galerie
gallery.destroy();
```

## 🎨 Personnalisation CSS

### Classes CSS principales

```css
.gallery-container         /* Container principal */
.modern-gallery           /* Grille d'images */
.gallery-photo-card       /* Carte d'image individuelle */
.gallery-photo-overlay    /* Overlay au hover */
.gallery-lightbox         /* Modal lightbox */
```

### Modifier la grille

```css
/* Taille des colonnes personnalisée */
.modern-gallery {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
}

/* Pour mobile uniquement */
@media (max-width: 480px) {
    .modern-gallery {
        grid-template-columns: repeat(2, 1fr);
    }
}
```

### Personnaliser les couleurs

```css
/* Thème personnalisé */
.gallery-theme-custom {
    --primary-color: #your-color;
    --accent-color: #your-accent;
}

.gallery-theme-custom .gallery-photo-overlay {
    background: linear-gradient(45deg, 
                var(--primary-color), 
                var(--accent-color));
}
```

## 📱 Responsive Design

La galerie s'adapte automatiquement :

- **Desktop (>1024px)** : 4-5 images par ligne
- **Tablette (768-1024px)** : 3-4 images par ligne  
- **Mobile (480-768px)** : 2-3 images par ligne
- **Petit mobile (<480px)** : 2 images par ligne

### Points de rupture personnalisés

```css
@media (max-width: 1200px) {
    .modern-gallery {
        grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    }
}
```

## 🖼️ Adaptation aux proportions

### Détection automatique

La galerie détecte automatiquement les proportions :

- **Portrait** (ratio < 0.7) : Prend 2 lignes
- **Paysage** (ratio > 1.8) : Prend 2 colonnes
- **Carré/Standard** : Taille normale

### Forcer les proportions

```html
<div class="gallery-photo-card portrait">...</div>
<div class="gallery-photo-card landscape">...</div>
<div class="gallery-photo-card large">...</div>
```

## ⌨️ Navigation clavier

- **Échap** : Fermer le lightbox
- **← →** : Naviguer entre les images
- **Entrée/Espace** : Ouvrir une image en lightbox
- **Tab** : Navigation entre les images

## 🔧 Intégration avec React

```jsx
import { useEffect, useRef } from 'react';

function GalleryComponent({ images }) {
    const containerRef = useRef(null);
    const galleryRef = useRef(null);
    
    useEffect(() => {
        if (containerRef.current && !galleryRef.current) {
            galleryRef.current = new ModernGallery(containerRef.current);
        }
        
        if (galleryRef.current) {
            galleryRef.current.loadImages(images);
        }
        
        return () => {
            if (galleryRef.current) {
                galleryRef.current.destroy();
            }
        };
    }, [images]);
    
    return <div ref={containerRef} />;
}
```

## 🎯 Exemples pratiques

### Galerie événementielle

```javascript
// Photos d'un événement avec métadonnées
const eventPhotos = [
    {
        src: '/photos/event/img1.jpg',
        alt: 'Cérémonie d\'ouverture',
        timestamp: '2024-01-15T10:00:00Z'
    },
    // ...
];

const gallery = new ModernGallery('#event-gallery', {
    theme: 'light',
    size: 'large'
});

gallery.loadImages(eventPhotos);
```

### Portfolio d'artiste

```javascript
const portfolioOptions = {
    size: 'large',
    animations: true,
    autoDetectRatio: true
};

const portfolio = new ModernGallery('#portfolio', portfolioOptions);
```

### Galerie de produits e-commerce

```javascript
const productOptions = {
    size: 'compact',
    lightbox: true,
    lazy: true
};

const productGallery = new ModernGallery('#products', productOptions);
```

## 🔧 Performance

### Optimisations incluses

- **Lazy loading** : Images chargées à la demande
- **Animations GPU** : Utilisation de `transform` et `opacity`
- **Débounce** : Events optimisés pour le resize
- **Memory management** : Nettoyage automatique des listeners

### Conseils pour de meilleures performances

```javascript
// Précharger les images critiques
const criticalImages = images.slice(0, 6);
gallery.loadImages(criticalImages);

// Charger le reste plus tard
setTimeout(() => {
    gallery.addImages(images.slice(6));
}, 1000);
```

## 🛠️ Dépannage

### Image ne s'affiche pas

1. Vérifiez l'URL de l'image
2. Contrôlez les CORS si domaine externe
3. Vérifiez la console pour les erreurs

### Lightbox ne fonctionne pas

1. Assurez-vous que l'option `lightbox: true`
2. Vérifiez qu'il n'y a pas de conflits CSS z-index
3. Contrôlez les event listeners

### Performance lente

1. Activez le lazy loading : `lazy: true`
2. Réduisez la taille des images
3. Limitez le nombre d'animations simultanées

## 🌐 Compatibilité navigateurs

- ✅ Chrome 60+
- ✅ Firefox 60+
- ✅ Safari 12+
- ✅ Edge 79+
- ✅ Mobile Safari iOS 12+
- ✅ Chrome Mobile 60+

## 📄 Licence

Ce code est fourni sous licence MIT. Libre d'utilisation pour projets personnels et commerciaux.

---

**🎉 Votre galerie est maintenant prête !** 

Pour toute question ou suggestion d'amélioration, n'hésitez pas à consulter la documentation ou à ouvrir une issue. 