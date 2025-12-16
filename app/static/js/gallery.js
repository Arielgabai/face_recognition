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
            // Nouveau pipeline: reveal progressif par ligne (2 colonnes fixes)
            progressiveRows: true,
            minRowHeight: 140,
            maxRowHeight: 520,
            theme: 'light',  // 'light' | 'dark'
            size: 'normal',  // 'compact' | 'normal' | 'large'
            debug: false,
            ...options
        };

        this.images = [];
        this.currentIndex = 0;
        this.lightboxElement = null;
        this.galleryGrid = null;
        this.renderToken = 0;
        this.isDestroyed = false;

        // Gestes tactiles
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchMoved = false;
        this.touchActive = false;
        this.isZooming = false;

        // Resize/throttle
        this.resizeRaf = null;
        this.boundHandleViewportChange = this.handleViewportChange.bind(this);

        // PERF: flag pour ne pas lancer 50 fois le reflow en même temps
        this.adjustPending = false;

        this.init();
        this.bindGlobalEvents();
    }

    logDebug(...args) {
        if (!this.options?.debug) return;
        console.log('[ModernGallery]', ...args);
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
        // Invalider tout rendu en cours
        const token = ++this.renderToken;

        // Grille principale (vide au départ: aucune carte visible avant qu'une ligne soit prête)
        const galleryGrid = document.createElement('div');
        galleryGrid.className = 'modern-gallery';
        this.galleryGrid = galleryGrid;

        // Remplacer le contenu du container
        this.container.innerHTML = '';
        this.container.appendChild(galleryGrid);

        this.logDebug('renderGallery', {
            images: this.images.length,
            progressiveRows: this.options.progressiveRows
        });

        // Rendu progressif par ligne
        if (this.options.progressiveRows) {
            this.renderRowsProgressively(token);
        } else {
            // Fallback: rendu immédiat (toujours stable car on précharge par ligne)
            this.renderRowsProgressively(token);
        }
    }

    async renderRowsProgressively(token) {
        try {
            if (!this.galleryGrid) return;
            const cols = 2; // 2 colonnes fixes

            for (let i = 0; i < (this.images || []).length; i += cols) {
                if (this.isDestroyed || token !== this.renderToken) return;

                const a = this.images[i];
                const b = this.images[i + 1] || null;

                await this.appendRow(i, a, b, token);

                // Laisser le navigateur peindre entre les lignes
                await new Promise(r => requestAnimationFrame(r));
            }

            // Reflow final (au cas où la largeur a changé pendant le chargement)
            this.scheduleRowAdjust();
        } catch (e) {
            console.error('ModernGallery: renderRowsProgressively error', e);
        }
    }

    preloadImage(src) {
        return new Promise((resolve) => {
            try {
                if (!src) {
                    resolve({ ok: false, img: null, w: 0, h: 0 });
                    return;
                }
                const img = new Image();
                img.decoding = 'async';
                img.onload = () => resolve({
                    ok: true,
                    img,
                    w: img.naturalWidth || 0,
                    h: img.naturalHeight || 0
                });
                img.onerror = () => resolve({ ok: false, img: null, w: 0, h: 0 });
                img.src = src;
            } catch (e) {
                resolve({ ok: false, img: null, w: 0, h: 0 });
            }
        });
    }

    getGridMetrics() {
        const grid = this.galleryGrid;
        if (!grid) return { cols: 2, colWidth: 200, gap: 0, gridWidth: 400 };
        const style = window.getComputedStyle(grid);
        const gap = parseFloat(style.columnGap || style.gap || '0') || 0;
        const gridWidth = grid.clientWidth || 400;
        const cols = 2;
        const colWidth = (gridWidth - gap) / cols;
        return { cols, colWidth, gap, gridWidth };
    }

    clamp(n, min, max) {
        return Math.max(min, Math.min(max, n));
    }

    async appendRow(startIndex, imgA, imgB, token) {
        if (!this.galleryGrid) return;
        if (!imgA) return;

        const { colWidth } = this.getGridMetrics();

        const [a, b] = await Promise.all([
            this.preloadImage(imgA.src),
            imgB ? this.preloadImage(imgB.src) : Promise.resolve({ ok: false, img: null, w: 0, h: 0 })
        ]);

        if (this.isDestroyed || token !== this.renderToken) return;

        // Calcul des ratios (si erreur, on garde une estimation pour ne pas bloquer la ligne)
        const ratioA = (a.ok && a.w && a.h) ? (a.w / a.h) : (imgA.aspectRatio || this.estimateAspectRatio(imgA) || 1.5);
        const ratioB = imgB
            ? ((b.ok && b.w && b.h) ? (b.w / b.h) : (imgB.aspectRatio || this.estimateAspectRatio(imgB) || 1.5))
            : null;

        imgA.aspectRatio = ratioA;
        if (imgB) imgB.aspectRatio = ratioB;

        const projectedA = colWidth / ratioA;
        const projectedB = imgB ? (colWidth / (ratioB || 1.5)) : 0;

        const rowHeight = this.clamp(
            Math.max(projectedA, projectedB || 0),
            this.options.minRowHeight || 140,
            this.options.maxRowHeight || 520
        );

        const frag = document.createDocumentFragment();
        frag.appendChild(this.createReadyCard(imgA, startIndex, a.ok ? a.img : null, ratioA, colWidth, rowHeight));
        if (imgB) {
            frag.appendChild(this.createReadyCard(imgB, startIndex + 1, b.ok ? b.img : null, ratioB, colWidth, rowHeight));
        }

        this.galleryGrid.appendChild(frag);
    }

    createReadyCard(image, index, loadedImg, ratio, colWidth, rowHeight) {
        const card = document.createElement('div');
        card.className = 'gallery-photo-card';
        card.setAttribute('data-index', index);
        card.style.position = 'relative';
        card.dataset.aspectRatio = String(ratio || 1.5);
        card.dataset.loaded = '1';
        card.style.height = `${Math.round(rowHeight)}px`;

        const img = loadedImg || document.createElement('img');
        img.alt = image.alt || `Image ${index + 1}`;
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'contain';
        img.decoding = 'async';
        img.loading = 'eager';
        if (!loadedImg) img.src = image.src;

        const projectedHeight = colWidth / (ratio || 1.5);
        if (rowHeight - projectedHeight > 2) {
            card.classList.add('needs-centering');
            card.style.setProperty('--bg-image', `url(${image.src})`);
        } else {
            card.classList.remove('needs-centering');
            card.style.removeProperty('--bg-image');
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
            this.reflowExistingRows();
        });
    }

    reflowExistingRows() {
        if (!this.galleryGrid) return;
        const cards = Array.from(this.galleryGrid.querySelectorAll('.gallery-photo-card'));
        if (!cards.length) return;

        // Réordonner par index pour retrouver les paires
        cards.sort((a, b) => (parseInt(a.dataset.index || '0', 10) - parseInt(b.dataset.index || '0', 10)));

        const { colWidth } = this.getGridMetrics();
        for (let i = 0; i < cards.length; i += 2) {
            const c1 = cards[i];
            const c2 = cards[i + 1] || null;
            const r1 = parseFloat(c1.dataset.aspectRatio || '1.5') || 1.5;
            const r2 = c2 ? (parseFloat(c2.dataset.aspectRatio || '1.5') || 1.5) : null;

            const p1 = colWidth / r1;
            const p2 = c2 ? (colWidth / (r2 || 1.5)) : 0;
            const rowHeight = this.clamp(
                Math.max(p1, p2 || 0),
                this.options.minRowHeight || 140,
                this.options.maxRowHeight || 520
            );

            this.applyRowSizing(c1, r1, colWidth, rowHeight);
            if (c2) this.applyRowSizing(c2, r2, colWidth, rowHeight);
        }
    }

    applyRowSizing(card, ratio, colWidth, rowHeight) {
        if (!card) return;
        const img = card.querySelector('img');
        card.style.height = `${Math.round(rowHeight)}px`;

        const projected = colWidth / (ratio || 1.5);
        if (rowHeight - projected > 2) {
            card.classList.add('needs-centering');
            if (img?.src) card.style.setProperty('--bg-image', `url(${img.src})`);
        } else {
            card.classList.remove('needs-centering');
            card.style.removeProperty('--bg-image');
        }
    }

    isCardFullyLoaded(card) {
        if (!card) return false;
        if (card.dataset.loaded === '1') return true;
        const img = card.querySelector('img');
        const ok = !!(img && img.complete && img.naturalWidth > 0 && img.naturalHeight > 0);
        return ok;
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
        this.isDestroyed = true;
        this.renderToken++;
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
