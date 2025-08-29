/**
 * Galerie Photos Moderne - JavaScript
 * Système de galerie responsive inspiré de Google Photos et Pinterest
 * 
 * Usage:
 * const gallery = new ModernGallery(container, options);
 * gallery.loadImages(images);
 */

class ModernGallery {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' ? document.querySelector(container) : container;
        this.options = {
            autoDetectRatio: true,
            lightbox: true,
            keyboardNavigation: true,
            animations: true,
            lazy: true,
            theme: 'light', // 'light', 'dark'
            size: 'normal', // 'compact', 'normal', 'large'
            ...options
        };
        
        this.images = [];
        this.currentIndex = 0;
        this.lightboxElement = null;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchMoved = false;
        this.touchActive = false;
        
        this.init();
    }
    
    init() {
        if (!this.container) {
            console.error('Container not found');
            return;
        }
        
        this.container.classList.add('gallery-container');
        if (this.options.theme === 'dark') {
            this.container.classList.add('gallery-theme-dark');
        }
        if (this.options.size !== 'normal') {
            this.container.classList.add(`gallery-${this.options.size}`);
        }
        
        if (this.options.lightbox) {
            this.createLightbox();
        }
        
        if (this.options.keyboardNavigation) {
            this.setupKeyboardNavigation();
        }
    }
    
    /**
     * Charge et affiche une liste d'images
     * @param {Array} images - Array d'objets {src, alt, aspectRatio?}
     */
    loadImages(images) {
        this.images = images;
        this.renderGallery();
    }
    
    /**
     * Ajoute des images à la galerie existante
     * @param {Array} newImages - Nouvelles images à ajouter
     */
    addImages(newImages) {
        this.images = [...this.images, ...newImages];
        this.renderNewImages(newImages);
    }
    
    renderGallery() {
        const galleryGrid = document.createElement('div');
        galleryGrid.className = 'modern-gallery';
        galleryGrid.innerHTML = '';
        
        this.images.forEach((image, index) => {
            const card = this.createImageCard(image, index);
            galleryGrid.appendChild(card);
        });
        
        // Remplace le contenu existant
        this.container.innerHTML = '';
        this.container.appendChild(galleryGrid);
        
        if (this.options.animations) {
            this.animateCards();
        }
    }
    
    renderNewImages(newImages) {
        const galleryGrid = this.container.querySelector('.modern-gallery');
        const startIndex = this.images.length - newImages.length;
        
        newImages.forEach((image, index) => {
            const card = this.createImageCard(image, startIndex + index);
            galleryGrid.appendChild(card);
        });
        
        if (this.options.animations) {
            this.animateNewCards(galleryGrid.children.length - newImages.length);
        }
    }
    
    createImageCard(image, index) {
        const card = document.createElement('div');
        card.className = 'gallery-photo-card';
        card.setAttribute('data-index', index);
        
        const img = document.createElement('img');
        img.alt = image.alt || `Image ${index + 1}`;
        
        if (this.options.lazy) {
            img.loading = 'lazy';
        }
        
        // Gestion du chargement d'image
        img.onload = () => {
            if (this.options.autoDetectRatio) {
                this.detectAndApplyRatio(img, card);
            }
            
            card.classList.remove('loading');
        };
        
        img.onerror = () => {
            card.classList.add('error');
            card.innerHTML = '<div class="gallery-photo-loading">❌ Erreur de chargement</div>';
        };
        
        img.src = image.src;
        
        // Ajouter un indicateur de chargement
        if (this.options.lazy) {
            card.classList.add('loading');
            const loader = document.createElement('div');
            loader.className = 'gallery-photo-loading';
            loader.innerHTML = '⏳ Chargement...';
            card.appendChild(loader);
        }
        
        // Overlay d'interaction
        const overlay = document.createElement('div');
        overlay.className = 'gallery-photo-overlay';
        overlay.innerHTML = '<span>Voir en grand</span>';
        
        card.appendChild(img);
        card.appendChild(overlay);
        
        // Event listeners
        if (this.options.lightbox) {
            card.addEventListener('click', () => this.openLightbox(index));
            card.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.openLightbox(index);
                }
            });
            card.setAttribute('tabindex', '0');
        }
        
        return card;
    }
    
    detectAndApplyRatio(img, card) {
        const aspectRatio = img.naturalWidth / img.naturalHeight;
        
        // Retirer les classes existantes
        card.classList.remove('wide-landscape', 'tall-portrait');
        
        // Appliquer seulement les classes pour les cas extrêmes
        if (aspectRatio > 2.5) {
            // Paysage très large (panoramique)
            card.classList.add('wide-landscape');
        } else if (aspectRatio < 0.5) {
            // Portrait très étroit
            card.classList.add('tall-portrait');
        }
        
        // Laisser les autres images s'afficher naturellement
    }
    
    createLightbox() {
        this.lightboxElement = document.createElement('div');
        this.lightboxElement.className = 'gallery-lightbox';
        this.lightboxElement.innerHTML = `
            <span class="gallery-lightbox-close" title="Fermer">&times;</span>
            <div class="gallery-lightbox-nav gallery-lightbox-prev" title="Précédente">‹</div>
            <div class="gallery-lightbox-nav gallery-lightbox-next" title="Suivante">›</div>
            <img src="" alt="">
            <div class="gallery-photo-counter">1 / 1</div>
            <button class="gallery-download-btn" title="Enregistrer">⬇︎ Enregistrer</button>
        `;
        
        document.body.appendChild(this.lightboxElement);
        
        // Event listeners
        const closeBtn = this.lightboxElement.querySelector('.gallery-lightbox-close');
        const prevBtn = this.lightboxElement.querySelector('.gallery-lightbox-prev');
        const nextBtn = this.lightboxElement.querySelector('.gallery-lightbox-next');
        const downloadBtn = this.lightboxElement.querySelector('.gallery-download-btn');
        
        closeBtn.addEventListener('click', () => this.closeLightbox());
        prevBtn.addEventListener('click', () => this.previousImage());
        nextBtn.addEventListener('click', () => this.nextImage());
        
        // Fermer en cliquant à l'extérieur
        this.lightboxElement.addEventListener('click', (e) => {
            if (e.target === this.lightboxElement) {
                this.closeLightbox();
            }
        });

        // Télécharger l'image courante
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.downloadCurrentImage();
            });
        }

        // Gestes tactiles: swipe gauche/droite pour naviguer
        const onTouchStart = (clientX, clientY) => {
            this.touchStartX = clientX;
            this.touchStartY = clientY;
            this.touchMoved = false;
            this.touchActive = true;
        };
        const onTouchMove = (clientX, clientY, e) => {
            if (!this.touchActive) return;
            const dx = clientX - this.touchStartX;
            const dy = clientY - this.touchStartY;
            // Si mouvement horizontal dominant, empêcher le scroll
            if (Math.abs(dx) > Math.abs(dy)) {
                this.touchMoved = true;
                if (e && typeof e.preventDefault === 'function') e.preventDefault();
            }
        };
        const onTouchEnd = (clientX) => {
            if (!this.touchActive) return;
            const dx = clientX - this.touchStartX;
            const threshold = 40; // pixels
            if (Math.abs(dx) >= threshold) {
                if (dx < 0) {
                    this.nextImage();
                } else {
                    this.previousImage();
                }
            }
            this.touchActive = false;
        };

        // Support Touch Events
        this.lightboxElement.addEventListener('touchstart', (e) => {
            if (!e.touches || e.touches.length === 0) return;
            const t = e.touches[0];
            onTouchStart(t.clientX, t.clientY);
        }, { passive: true });
        this.lightboxElement.addEventListener('touchmove', (e) => {
            if (!e.touches || e.touches.length === 0) return;
            const t = e.touches[0];
            onTouchMove(t.clientX, t.clientY, e);
        }, { passive: false });
        this.lightboxElement.addEventListener('touchend', (e) => {
            const t = (e.changedTouches && e.changedTouches[0]) || null;
            if (t) onTouchEnd(t.clientX);
        });

        // Support Pointer Events (trackpads / souris bouton enfoncé)
        let pointerDown = false;
        this.lightboxElement.addEventListener('pointerdown', (e) => {
            pointerDown = true;
            onTouchStart(e.clientX, e.clientY);
        });
        this.lightboxElement.addEventListener('pointermove', (e) => {
            if (!pointerDown) return;
            onTouchMove(e.clientX, e.clientY, e);
        });
        this.lightboxElement.addEventListener('pointerup', (e) => {
            if (!pointerDown) return;
            pointerDown = false;
            onTouchEnd(e.clientX);
        });
    }
    
    openLightbox(index) {
        if (!this.lightboxElement || !this.images[index]) return;
        
        this.currentIndex = index;
        const image = this.images[index];
        
        const img = this.lightboxElement.querySelector('img');
        const counter = this.lightboxElement.querySelector('.gallery-photo-counter');
        const prevBtn = this.lightboxElement.querySelector('.gallery-lightbox-prev');
        const nextBtn = this.lightboxElement.querySelector('.gallery-lightbox-next');
        
        img.src = image.src;
        img.alt = image.alt || `Image ${index + 1}`;
        counter.textContent = `${index + 1} / ${this.images.length}`;
        
        // Afficher/masquer les boutons de navigation
        prevBtn.style.display = index > 0 ? 'flex' : 'none';
        nextBtn.style.display = index < this.images.length - 1 ? 'flex' : 'none';
        
        this.lightboxElement.classList.add('active');
        document.body.style.overflow = 'hidden';
        // Marquer l'état lightbox pour le CSS et masquer le hamburger
        document.body.classList.add('lightbox-open');
        try {
            const menu = document.getElementById('hamburgerMenu');
            if (menu) menu.style.display = 'none';
        } catch {}
        
        // Focus pour l'accessibilité
        this.lightboxElement.focus();
    }
    
    closeLightbox() {
        if (!this.lightboxElement) return;
        
        this.lightboxElement.classList.remove('active');
        document.body.style.overflow = 'auto';
        document.body.classList.remove('lightbox-open');
        // Réafficher le hamburger proprement
        try {
            const menu = document.getElementById('hamburgerMenu');
            if (menu) menu.style.display = '';
        } catch {}
    }
    
    previousImage() {
        if (this.currentIndex > 0) {
            this.openLightbox(this.currentIndex - 1);
        }
    }
    
    nextImage() {
        if (this.currentIndex < this.images.length - 1) {
            this.openLightbox(this.currentIndex + 1);
        }
    }

    async downloadCurrentImage() {
        try {
            const image = this.images[this.currentIndex];
            if (!image) return;
            const response = await fetch(image.src, { cache: 'no-store' });
            const blob = await response.blob();
            const fileName = (image.alt || 'photo') + '.jpg';

            // Utiliser l'API Web Share si disponible (meilleure expérience mobile)
            const file = new File([blob], fileName, { type: blob.type || 'image/jpeg' });
            if (navigator.canShare && navigator.canShare({ files: [file] })) {
                await navigator.share({ files: [file], title: 'Photo' });
                return;
            }

            // Fallback: lien de téléchargement
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 2000);
        } catch (e) {
            console.error('Erreur lors du téléchargement de l\'image:', e);
            // Fallback ultime: ouvrir l'image dans un nouvel onglet pour sauvegarde manuelle
            const image = this.images[this.currentIndex];
            if (image) window.open(image.src, '_blank');
        }
    }
    
    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            if (!this.lightboxElement?.classList.contains('active')) return;
            
            switch(e.key) {
                case 'Escape':
                    this.closeLightbox();
                    break;
                case 'ArrowLeft':
                    this.previousImage();
                    break;
                case 'ArrowRight':
                    this.nextImage();
                    break;
            }
        });
    }
    
    animateCards() {
        const cards = this.container.querySelectorAll('.gallery-photo-card');
        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.1}s`;
        });
    }
    
    animateNewCards(startIndex) {
        const cards = this.container.querySelectorAll('.gallery-photo-card');
        for (let i = startIndex; i < cards.length; i++) {
            cards[i].style.animationDelay = `${(i - startIndex) * 0.1}s`;
        }
    }
    
    /**
     * Actualise la galerie avec de nouvelles options
     * @param {Object} newOptions - Nouvelles options
     */
    updateOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
        this.renderGallery();
    }
    
    /**
     * Supprime une image par index
     * @param {number} index - Index de l'image à supprimer
     */
    removeImage(index) {
        if (index >= 0 && index < this.images.length) {
            this.images.splice(index, 1);
            this.renderGallery();
        }
    }
    
    /**
     * Vide la galerie
     */
    clear() {
        this.images = [];
        this.container.innerHTML = '<div class="gallery-empty-state"><h3>Aucune image</h3><p>La galerie est vide</p></div>';
    }
    
    /**
     * Détruit la galerie et nettoie les event listeners
     */
    destroy() {
        if (this.lightboxElement) {
            this.lightboxElement.remove();
        }
        this.container.innerHTML = '';
        this.container.classList.remove('gallery-container', 'gallery-theme-dark', 'gallery-compact', 'gallery-large');
    }
}

// Fonction utilitaire pour créer rapidement une galerie
function createGallery(container, images, options = {}) {
    const gallery = new ModernGallery(container, options);
    gallery.loadImages(images);
    return gallery;
}

// Export pour utilisation en module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ModernGallery, createGallery };
}

// Disponible globalement
window.ModernGallery = ModernGallery;
window.createGallery = createGallery; 