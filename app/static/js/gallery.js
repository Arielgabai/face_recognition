/**
 * Galerie Photos Moderne - JavaScript (version optimisée)
 * Layout en CSS Grid + égalisation des hauteurs par ligne.
 * - Lazy loading progressif
 * - Lightbox avec navigation, clavier, gestes tactiles
 * - Téléchargement / partage
 */

class ModernGallery {
    constructor(container, options = {}) {
        this.container =
            typeof container === 'string' ? document.querySelector(container) : container;

        this.options = {
            autoDetectRatio: true,
            lightbox: true,
            keyboardNavigation: true,
            animations: true,
            lazy: true,
            theme: 'light',  // 'light' | 'dark'
            size: 'normal',  // 'compact' | 'normal' | 'large'
            batchSize: 10,
            ...options
        };

        this.images = [];
        this.currentIndex = 0;
        this.lightboxElement = null;
        this.galleryGrid = null;

        // Gestes tactiles
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchMoved = false;
        this.touchActive = false;
        this.isZooming = false;

        // Resize/throttle
        this.resizeRaf = null;
        this.boundHandleViewportChange = this.handleViewportChange.bind(this);

        // PERF: flag pour ne pas lancer 50 fois adjustRowHeights en même temps
        this.adjustPending = false;

        this.init();
        this.bindGlobalEvents();
    }

    /* ------------------------------------------------------------------ */
    /* Init & événements globaux                                          */
    /* ------------------------------------------------------------------ */

    init() {
        if (!this.container) {
            console.error('ModernGallery: container introuvable');
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

    bindGlobalEvents() {
        if (typeof window === 'undefined') return;

        window.addEventListener('resize', this.boundHandleViewportChange);

        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', this.boundHandleViewportChange);
            window.visualViewport.addEventListener('scroll', this.boundHandleViewportChange);
        }
    }

    /* ------------------------------------------------------------------ */
    /* Chargement d’images                                                 */
    /* ------------------------------------------------------------------ */

    /**
     * Charge et affiche une liste d'images
     * @param {Array} images - [{ src, alt?, aspectRatio? }, ...]
     */
    loadImages(images) {
        this.images = images || [];
        this.renderGallery();
    }

    /**
     * Ajoute des images à la galerie existante
     * @param {Array} newImages
     */
    addImages(newImages) {
        this.images = [...this.images, ...(newImages || [])];
        this.renderGallery(); // plus simple : on re-rend tout
    }

    /* ------------------------------------------------------------------ */
    /* Rendu principal                                                     */
    /* ------------------------------------------------------------------ */

    renderGallery() {
        // Grille principale
        const galleryGrid = document.createElement('div');
        galleryGrid.className = 'modern-gallery';
        this.galleryGrid = galleryGrid;

        // Créer toutes les cartes
        this.images.forEach((image, index) => {
            const card = this.createImageCard(image, index);
            galleryGrid.appendChild(card);
        });

        // Remplacer le contenu du container
        this.container.innerHTML = '';
        this.container.appendChild(galleryGrid);

        // Lazy loading progressif
        if (this.options.lazy) {
            this.setupProgressiveLoading(galleryGrid);
        }

        // Ajuster les hauteurs de ligne après rendu (une seule fois, debouncée)
        setTimeout(() => this.scheduleRowAdjust(), 120);

        // Animations d'apparition
        if (this.options.animations) {
            this.animateCards();
        }
    }

    /**
     * Chargement progressif des images, en gardant l’ordre d’affichage
     */
    setupProgressiveLoading(galleryGrid) {
        const cards = Array.from(galleryGrid.querySelectorAll('.gallery-photo-card'));
        const batchSize = this.options.batchSize;

        // Premier batch : chargé immédiatement
        const firstBatch = cards.slice(0, batchSize);
        firstBatch.forEach(card => {
            const img = card.querySelector('img');
            if (img && img.dataset.lazySrc) {
                img.src = img.dataset.lazySrc;
                delete img.dataset.lazySrc;
            }
        });

        // Le reste : petit à petit
        const remainingCards = cards.slice(batchSize);
        remainingCards.forEach((card, idx) => {
            const delay = Math.floor(idx / 5) * 50; // groupes de 5
            setTimeout(() => {
                const img = card.querySelector('img');
                if (img && img.dataset.lazySrc) {
                    img.src = img.dataset.lazySrc;
                    delete img.dataset.lazySrc;
                }
            }, delay);
        });
    }

    /* ------------------------------------------------------------------ */
    /* Gestion du layout (hauteurs de lignes + fond flou)                  */
    /* ------------------------------------------------------------------ */

    /**
     * PERF: regroupe les appels à adjustRowHeights dans un seul rAF
     */
    scheduleRowAdjust() {
        if (this.adjustPending) return;
        this.adjustPending = true;

        requestAnimationFrame(() => {
            this.adjustPending = false;
            this.adjustRowHeights();
        });
    }

    /**
     * Ajuste les hauteurs des cartes ligne par ligne, pour que toutes
     * les photos d’une même ligne aient la même hauteur.
     */
    adjustRowHeights(retryCount = 0) {
        const cards = this.container.querySelectorAll('.gallery-photo-card');
        if (!cards.length) return;

        // Grouper les cartes par "ligne visuelle" (offsetTop)
        const rows = {};
        cards.forEach(card => {
            const top = Math.round(card.offsetTop / 10) * 10;
            if (!rows[top]) rows[top] = [];
            rows[top].push(card);
        });

        Object.values(rows).forEach(rowCards => {
            let maxRowHeight = 0;
            const cardWidth = rowCards[0].offsetWidth || 200;

            // Calculer la hauteur projetée pour chaque carte
            rowCards.forEach(card => {
                let ratio = parseFloat(card.dataset.aspectRatio || '1.5');

                if (!ratio || ratio <= 0) {
                    const img = card.querySelector('img');
                    if (img && img.naturalWidth && img.naturalHeight) {
                        ratio = img.naturalWidth / img.naturalHeight;
                        card.dataset.aspectRatio = ratio;
                    } else {
                        ratio = 1.5;
                    }
                }

                const projectedHeight = cardWidth / ratio;
                maxRowHeight = Math.max(maxRowHeight, projectedHeight);
            });

            // Appliquer la même hauteur à toutes les cartes de la ligne
            rowCards.forEach(card => {
                card.style.height = `${Math.round(maxRowHeight)}px`;

                const img = card.querySelector('img');
                const ratio = parseFloat(card.dataset.aspectRatio || '1.5');
                const projectedHeight = cardWidth / ratio;

                if (img) {
                    img.style.width = '100%';
                    img.style.height = 'auto';
                    img.style.objectFit = 'contain';
                    img.style.position = 'relative';
                    img.style.zIndex = '1';
                }

                // Si l’image réelle est plus petite que la hauteur max,
                // on active l’effet de fond flou centré.
                if (maxRowHeight - projectedHeight > 2) {
                    card.classList.add('needs-centering');
                    if (img) {
                        card.style.setProperty('--bg-image', `url(${img.src})`);
                    }
                } else {
                    card.classList.remove('needs-centering');
                    card.style.removeProperty('--bg-image');
                }
            });
        });

        // Réessayer tant que certaines images ne sont pas encore chargées
        const needsRetry = Array.from(cards).some(card => card.dataset.loaded !== '1');
        if (needsRetry && retryCount < 4) { // PERF: limite abaissée de 8 à 4
            const waitTime = Math.min(400 + retryCount * 120, 1000);
            setTimeout(() => this.adjustRowHeights(retryCount + 1), waitTime);
        }
    }

    handleViewportChange() {
        if (!this.container) return;
        if (this.resizeRaf) cancelAnimationFrame(this.resizeRaf);

        this.resizeRaf = requestAnimationFrame(() => {
            this.scheduleRowAdjust();
        });
    }

    /* ------------------------------------------------------------------ */
    /* Utilitaires ratio                                                   */
    /* ------------------------------------------------------------------ */

    estimateAspectRatio(image) {
        if (image.aspectRatio && image.aspectRatio > 0) return image.aspectRatio;

        const src = image.src || '';

        if (src.includes('square') || src.includes('1x1') || src.includes('sq_')) return 1.0;
        if (src.includes('portrait') || src.includes('vert') || src.includes('9x16')) return 0.75;
        if (src.includes('landscape') || src.includes('horiz') || src.includes('16x9')) return 1.78;
        if (src.includes('wide') || src.includes('panorama') || src.includes('pano')) return 2.5;
        if (src.includes('tall') || src.includes('long')) return 0.6;

        const commonRatios = [1.0, 1.33, 1.5, 1.78, 0.8, 0.75, 0.67];
        const hash = this.simpleHash(src);
        return commonRatios[hash % commonRatios.length];
    }

    simpleHash(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash |= 0;
        }
        return Math.abs(hash);
    }

    /* ------------------------------------------------------------------ */
    /* Création d’une carte image                                         */
    /* ------------------------------------------------------------------ */

    createImageCard(image, index) {
        const card = document.createElement('div');
        card.className = 'gallery-photo-card';
        card.setAttribute('data-index', index);
        card.style.position = 'relative';

        const estimatedRatio =
            image.aspectRatio || this.estimateAspectRatio(image) || 1.5;
        card.dataset.aspectRatio = String(estimatedRatio);
        card.dataset.loaded = '0';

        const img = document.createElement('img');
        img.alt = image.alt || `Image ${index + 1}`;
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'contain';

        if (this.options.lazy) {
            img.loading = 'lazy';
        }

        img.onload = () => {
            const aspectRatio = (img.naturalWidth && img.naturalHeight)
                ? (img.naturalWidth / img.naturalHeight)
                : estimatedRatio;

            image.aspectRatio = aspectRatio;
            card.dataset.aspectRatio = String(aspectRatio);
            card.dataset.loaded = '1';
            card.classList.remove('loading');

            // Réajuster les lignes après chargement (debouncé)
            this.scheduleRowAdjust();
        };

        img.onerror = () => {
            card.classList.add('error');
            card.innerHTML =
                '<div class="gallery-photo-loading">❌ Erreur de chargement</div>';
        };

        if (this.options.lazy) {
            img.dataset.lazySrc = image.src;
            card.classList.add('loading');
            const loader = document.createElement('div');
            loader.className = 'gallery-photo-loading';
            loader.textContent = '⏳';
            card.appendChild(loader);
        } else {
            img.src = image.src;
        }

        const overlay = document.createElement('div');
        overlay.className = 'gallery-photo-overlay';
        overlay.innerHTML = '<span>Voir en grand</span>';

        card.appendChild(img);
        card.appendChild(overlay);

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

    /* ------------------------------------------------------------------ */
    /* Lightbox                                                            */
    /* ------------------------------------------------------------------ */

    createLightbox() {
        const lightbox = document.createElement('div');
        lightbox.className = 'gallery-lightbox';
        lightbox.innerHTML = `
            <span class="gallery-lightbox-close" title="Fermer">&times;</span>
            <div class="gallery-lightbox-nav gallery-lightbox-prev" title="Précédente">‹</div>
            <div class="gallery-lightbox-nav gallery-lightbox-next" title="Suivante">›</div>
            <img src="" alt="">
            <div class="gallery-photo-counter">1 / 1</div>
            <button class="gallery-download-btn" title="Enregistrer">⬇︎ Enregistrer</button>
        `;

        document.body.appendChild(lightbox);
        this.lightboxElement = lightbox;

        const closeBtn = lightbox.querySelector('.gallery-lightbox-close');
        const prevBtn = lightbox.querySelector('.gallery-lightbox-prev');
        const nextBtn = lightbox.querySelector('.gallery-lightbox-next');
        const downloadBtn = lightbox.querySelector('.gallery-download-btn');

        closeBtn.addEventListener('click', () => this.closeLightbox());
        prevBtn.addEventListener('click', () => this.previousImage());
        nextBtn.addEventListener('click', () => this.nextImage());

        lightbox.addEventListener('click', (e) => {
            if (e.target === lightbox) this.closeLightbox();
        });

        if (downloadBtn) {
            const handleDownload = (e) => {
                e.stopPropagation();
                e.preventDefault();
                this.downloadCurrentImage();
                return false;
            };
            downloadBtn.addEventListener('click', handleDownload);
            downloadBtn.addEventListener('touchend', handleDownload);
            downloadBtn.addEventListener('mousedown', (e) => e.stopPropagation());
            downloadBtn.addEventListener('pointerdown', (e) => e.stopPropagation());
        }

        this.setupTouchNavigation(lightbox);
    }

    setupTouchNavigation(lightbox) {
        const onTouchStart = (clientX, clientY, touchCount) => {
            if (touchCount >= 2) {
                this.isZooming = true;
                this.touchActive = false;
                return;
            }
            this.touchStartX = clientX;
            this.touchStartY = clientY;
            this.touchMoved = false;
            this.touchActive = true;
        };

        const onTouchMove = (clientX, clientY, touchCount, e) => {
            if (touchCount >= 2) {
                this.isZooming = true;
                this.touchActive = false;
                return;
            }
            if (!this.touchActive) return;

            const dx = clientX - this.touchStartX;
            const dy = clientY - this.touchStartY;

            if (Math.abs(dx) > Math.abs(dy)) {
                this.touchMoved = true;
                if (e && typeof e.preventDefault === 'function') e.preventDefault();
            }
        };

        const onTouchEnd = (clientX, touchCount) => {
            if (this.isZooming) {
                setTimeout(() => { this.isZooming = false; }, 300);
                this.touchActive = false;
                return;
            }
            if (!this.touchActive) return;

            const dx = clientX - this.touchStartX;
            const threshold = 40;

            if (Math.abs(dx) >= threshold) {
                if (dx < 0) this.nextImage();
                else this.previousImage();
            }
            this.touchActive = false;
        };

        // Touch
        lightbox.addEventListener('touchstart', (e) => {
            if (!e.touches || !e.touches.length) return;
            const t = e.touches[0];
            onTouchStart(t.clientX, t.clientY, e.touches.length);
        }, { passive: true });

        lightbox.addEventListener('touchmove', (e) => {
            if (!e.touches || !e.touches.length) return;
            const t = e.touches[0];
            onTouchMove(t.clientX, t.clientY, e.touches.length, e);
        }, { passive: false });

        lightbox.addEventListener('touchend', (e) => {
            const t = (e.changedTouches && e.changedTouches[0]) || null;
            const touchCount = e.touches ? e.touches.length : 0;
            if (t) onTouchEnd(t.clientX, touchCount);
        });

        // Pointer (souris / trackpad)
        let pointerDown = false;
        lightbox.addEventListener('pointerdown', (e) => {
            pointerDown = true;
            onTouchStart(e.clientX, e.clientY, 1);
        });

        lightbox.addEventListener('pointermove', (e) => {
            if (!pointerDown) return;
            onTouchMove(e.clientX, e.clientY, 1, e);
        });

        lightbox.addEventListener('pointerup', (e) => {
            if (!pointerDown) return;
            pointerDown = false;
            onTouchEnd(e.clientX, 1);
        });

        // Empêcher la navigation sur zoom via Ctrl + scroll
        lightbox.addEventListener('wheel', (e) => {
            if (e.ctrlKey || e.metaKey) {
                e.stopPropagation();
                return;
            }
        }, { passive: true });
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

        prevBtn.style.display = index > 0 ? 'flex' : 'none';
        nextBtn.style.display = index < this.images.length - 1 ? 'flex' : 'none';

        this.lightboxElement.classList.add('active');
        document.body.style.overflow = 'hidden';
        document.body.classList.add('lightbox-open');

        const menu = document.getElementById('hamburgerMenu');
        if (menu) menu.style.display = 'none';

        this.lightboxElement.focus();
    }

    closeLightbox() {
        if (!this.lightboxElement) return;

        this.lightboxElement.classList.remove('active');
        document.body.style.overflow = '';
        document.body.classList.remove('lightbox-open');

        const menu = document.getElementById('hamburgerMenu');
        if (menu) menu.style.display = '';

        this.handleViewportChange();
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

    /* ------------------------------------------------------------------ */
    /* Téléchargement / partage                                            */
    /* ------------------------------------------------------------------ */

    downloadCurrentImage() {
        const image = this.images[this.currentIndex];
        if (!image) return;

        const fileName = (image.alt || 'photo') + '.jpg';

        fetch(image.src, { cache: 'no-store' })
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.blob();
            })
            .then(blob => {
                try {
                    const file = new File([blob], fileName, {
                        type: blob.type || 'image/jpeg'
                    });
                    if (navigator.canShare && navigator.canShare({ files: [file] })) {
                        return navigator.share({ files: [file], title: 'Photo' });
                    }
                } catch (e) {
                    // fallback classique
                }

                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = fileName;
                a.style.display = 'none';
                document.body.appendChild(a);
                a.click();

                setTimeout(() => {
                    try {
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                    } catch (e) {}
                }, 100);
            })
            .catch(e => {
                console.error('Erreur lors du téléchargement de la photo:', e);
                console.log(
                    'Pour télécharger manuellement, faites clic droit > Enregistrer l\'image'
                );
            });
    }

    /* ------------------------------------------------------------------ */
    /* Accessibilité / clavier                                             */
    /* ------------------------------------------------------------------ */

    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            if (!this.lightboxElement?.classList.contains('active')) return;

            switch (e.key) {
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

    /* ------------------------------------------------------------------ */
    /* Animations                                                          */
    /* ------------------------------------------------------------------ */

    animateCards() {
        const cards = this.container.querySelectorAll('.gallery-photo-card');
        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.1}s`;
        });
    }

    /* ------------------------------------------------------------------ */
    /* API publique                                                        */
    /* ------------------------------------------------------------------ */

    updateOptions(newOptions) {
        this.options = { ...this.options, ...newOptions };
        this.renderGallery();
    }

    removeImage(index) {
        if (index >= 0 && index < this.images.length) {
            this.images.splice(index, 1);
            this.renderGallery();
        }
    }

    clear() {
        this.images = [];
        this.container.innerHTML =
            '<div class="gallery-empty-state"><h3>Aucune image</h3><p>La galerie est vide</p></div>';
    }

    destroy() {
        if (this.lightboxElement) {
            this.lightboxElement.remove();
        }

        this.container.innerHTML = '';
        this.container.classList.remove(
            'gallery-container',
            'gallery-theme-dark',
            'gallery-compact',
            'gallery-large'
        );

        if (typeof window !== 'undefined' && this.boundHandleViewportChange) {
            window.removeEventListener('resize', this.boundHandleViewportChange);
            if (window.visualViewport) {
                window.visualViewport.removeEventListener('resize', this.boundHandleViewportChange);
                window.visualViewport.removeEventListener('scroll', this.boundHandleViewportChange);
            }
        }

        if (this.resizeRaf) {
            cancelAnimationFrame(this.resizeRaf);
            this.resizeRaf = null;
        }
    }
}

/* Utilitaire simple */
function createGallery(container, images, options = {}) {
    const gallery = new ModernGallery(container, options);
    gallery.loadImages(images);
    return gallery;
}

// Export CommonJS
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ModernGallery, createGallery };
}

// Global
window.ModernGallery = ModernGallery;
window.createGallery = createGallery;
