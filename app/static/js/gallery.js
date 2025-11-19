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
        
        // Appliquer les styles mobile directement si nécessaire
        this.applyMobileStyles(galleryGrid);
        
        // Créer toutes les cartes d'abord
        this.images.forEach((image, index) => {
            const card = this.createImageCard(image, index);
            galleryGrid.appendChild(card);
        });
        
        // Remplace le contenu existant
        this.container.innerHTML = '';
        this.container.appendChild(galleryGrid);
        
        // Après le rendu, ajuster les hauteurs de ligne
        setTimeout(() => {
            this.adjustRowHeights();
        }, 100);
        
        if (this.options.animations) {
            this.animateCards();
        }
    }
    
    applyMobileStyles(galleryGrid) {
        const width = window.innerWidth;
        
        if (width <= 480) {
            // Mobile - appliquer les styles directement
            galleryGrid.style.display = 'grid';
            galleryGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(150px, 1fr))';
            galleryGrid.style.gap = '1px';
            galleryGrid.style.gridRowGap = '1px';
            galleryGrid.style.width = '100vw';
            galleryGrid.style.marginLeft = '-20px';
            galleryGrid.style.marginRight = '-20px';
            galleryGrid.style.padding = '0 20px';
            galleryGrid.style.alignItems = 'start';
        } else if (width <= 768) {
            // Tablette - appliquer les styles directement
            galleryGrid.style.display = 'grid';
            galleryGrid.style.gridTemplateColumns = 'repeat(auto-fit, minmax(160px, 1fr))';
            galleryGrid.style.gap = '2px';
            galleryGrid.style.gridRowGap = '2px';
            galleryGrid.style.width = '100vw';
            galleryGrid.style.marginLeft = '-20px';
            galleryGrid.style.marginRight = '-20px';
            galleryGrid.style.padding = '0 20px';
            galleryGrid.style.alignItems = 'start';
        }
    }
    
    adjustRowHeights(retryCount = 0) {
        const cards = this.container.querySelectorAll('.gallery-photo-card');
        if (!cards || cards.length === 0) return;

        const galleryGrid = this.container.querySelector('.modern-gallery');
        if (galleryGrid) {
            this.applyMobileStyles(galleryGrid);
        }

        // Grouper les cartes par ligne (offsetTop approché)
        const rows = {};
        cards.forEach(card => {
            const top = Math.round(card.offsetTop / 10) * 10;
            if (!rows[top]) rows[top] = [];
            rows[top].push(card);
        });

        Object.values(rows).forEach(rowCards => {
            let maxHeight = 0;

            rowCards.forEach(card => {
                const img = card.querySelector('img');
                const effectiveHeight = this.getEffectiveHeight(card, img);
                maxHeight = Math.max(maxHeight, effectiveHeight);
            });

            // Assurer une hauteur minimale raisonnable selon l'appareil
            const isMobile = window.innerWidth <= 768;
            const minRowHeight = isMobile ? 120 : 150;
            maxHeight = Math.max(maxHeight, minRowHeight);

            rowCards.forEach(card => {
                const img = card.querySelector('img');
                card.style.height = `${Math.round(maxHeight)}px`;
                
                if (img) {
                    // CORRECTION CLÉ: utiliser contain au lieu de cover pour éviter la déformation
                    img.style.width = 'auto';
                    img.style.height = 'auto';
                    img.style.maxWidth = '100%';
                    img.style.maxHeight = '100%';
                    img.style.objectFit = 'contain';
                }

                // Si l'image est plus petite que le conteneur, activer le fond flouté
                const imgHeight = img ? (img.naturalHeight || img.offsetHeight || maxHeight) : maxHeight;
                const imgWidth = img ? (img.naturalWidth || img.offsetWidth || card.offsetWidth) : card.offsetWidth;
                const cardWidth = card.offsetWidth;
                
                // Calculer si l'image remplit le conteneur
                const heightRatio = imgHeight / maxHeight;
                const widthRatio = imgWidth / cardWidth;
                
                // Activer le fond flouté si l'image ne remplit pas le conteneur
                if (heightRatio < 0.95 || widthRatio < 0.95) {
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

        const needsRetry = Array.from(cards).some(card => card.dataset.loaded !== '1');
        if (needsRetry && retryCount < 8) {
            const waitTime = Math.min(400 + retryCount * 120, 1500);
            setTimeout(() => this.adjustRowHeights(retryCount + 1), waitTime);
        }
    }

    getEffectiveHeight(card, img) {
        if (!card) return 150;
        const cardWidth = card.clientWidth || 200;
        
        // Obtenir le ratio d'aspect réel de l'image
        let ratio = parseFloat(card.dataset.aspectRatio || '0');
        
        if (img && img.naturalWidth && img.naturalHeight) {
            // Utiliser les dimensions natives pour calculer le ratio
            ratio = img.naturalWidth / img.naturalHeight;
            card.dataset.aspectRatio = String(ratio);
        }
        
        if (!ratio || !isFinite(ratio) || ratio <= 0) {
            ratio = 1.5; // Ratio par défaut
        }
        
        // Calculer la hauteur proportionnelle à la largeur de la carte
        let calculatedHeight = cardWidth / ratio;
        
        // Limiter les hauteurs extrêmes pour un affichage harmonieux
        const isMobile = window.innerWidth <= 768;
        const minHeight = isMobile ? 100 : 120;
        const maxHeight = isMobile ? 300 : 400;
        
        calculatedHeight = Math.max(minHeight, Math.min(maxHeight, calculatedHeight));
        
        return calculatedHeight;
    }
    
    renderDesktopStyle(galleryGrid) {
        const imagesPerRow = this.getImagesPerRow();
        
        for (let i = 0; i < this.images.length; i += imagesPerRow) {
            const rowImages = this.images.slice(i, i + imagesPerRow);
            const rowElement = document.createElement('div');
            rowElement.className = 'gallery-row';
            
            rowImages.forEach((image, index) => {
                const card = this.createImageCard(image, i + index);
                card.style.flex = '1 1 0';
                rowElement.appendChild(card);
            });
            
            galleryGrid.appendChild(rowElement);
        }
    }
    
    renderMobileJustifiedRows(galleryGrid) {
        const targetHeight = window.innerWidth <= 480 ? 120 : 150;
        const containerWidth = this.container.clientWidth || window.innerWidth - 20;
        const gap = window.innerWidth <= 480 ? 4 : 5;
        const maxPhotosPerRow = window.innerWidth <= 480 ? 2 : 3;
        
        // Grouper les images en lignes de 2-3 photos
        const rows = [];
        for (let i = 0; i < this.images.length; i += maxPhotosPerRow) {
            rows.push(this.images.slice(i, i + maxPhotosPerRow));
        }
        
        // Créer chaque ligne avec alignement parfait
        rows.forEach((rowImages, rowIndex) => {
            const isLastRow = rowIndex === rows.length - 1;
            this.createPerfectAlignedRow(galleryGrid, rowImages, containerWidth, targetHeight, gap, isLastRow);
        });
    }
    
    createPerfectAlignedRow(galleryGrid, rowImages, containerWidth, targetHeight, gap, isLastRow) {
        const rowElement = document.createElement('div');
        rowElement.className = 'gallery-row mobile-google-style';
        
        // Hauteur fixe pour alignement parfait (sauf dernière ligne)
        const rowHeight = isLastRow ? Math.min(targetHeight * 1.2, targetHeight) : targetHeight;
        rowElement.style.height = `${rowHeight}px`;
        
        // Calculer les largeurs pour remplir exactement la largeur
        const totalGaps = (rowImages.length - 1) * gap;
        const availableWidth = containerWidth - totalGaps;
        const imageWidth = availableWidth / rowImages.length;
        
        rowImages.forEach((image, index) => {
            const card = this.createImageCard(image, rowImages.indexOf(image));
            card.style.width = `${imageWidth}px`;
            card.style.flex = 'none';
            card.style.height = `${rowHeight}px`;
            rowElement.appendChild(card);
        });
        
        galleryGrid.appendChild(rowElement);
    }
    
    /**
     * Algorithme de partitioning linéaire inspiré de Google Photos
     * Optimise la répartition des photos pour minimiser les différences de hauteur
     */
    linearPartition(images, containerWidth, targetHeight, gap) {
        if (images.length === 0) return [];
        
        const maxPhotosPerRow = window.innerWidth <= 480 ? 2 : 3;
        const rows = [];
        let currentIndex = 0;
        
        while (currentIndex < images.length) {
            const remainingImages = images.length - currentIndex;
            const photosInThisRow = Math.min(maxPhotosPerRow, remainingImages);
            
            // Essayer différentes combinaisons pour trouver la meilleure
            let bestCombination = null;
            let bestScore = Infinity;
            
            for (let count = 1; count <= photosInThisRow; count++) {
                const rowImages = images.slice(currentIndex, currentIndex + count);
                const score = this.calculateRowScore(rowImages, containerWidth, targetHeight, gap);
                
                if (score < bestScore) {
                    bestScore = score;
                    bestCombination = { images: rowImages, count };
                }
            }
            
            if (bestCombination) {
                rows.push(bestCombination.images);
                currentIndex += bestCombination.count;
            } else {
                // Fallback: prendre une seule image
                rows.push([images[currentIndex]]);
                currentIndex++;
            }
        }
        
        return rows;
    }
    
    /**
     * Calcule un score pour évaluer la qualité d'une ligne
     * Plus le score est bas, meilleure est la ligne
     */
    calculateRowScore(rowImages, containerWidth, targetHeight, gap) {
        const totalGaps = (rowImages.length - 1) * gap;
        const availableWidth = containerWidth - totalGaps;
        const totalAspectRatio = rowImages.reduce((sum, img) => sum + img.aspectRatio, 0);
        
        // Hauteur nécessaire pour remplir la largeur
        const requiredHeight = availableWidth / totalAspectRatio;
        
        // Score basé sur la différence avec la hauteur cible
        const heightDifference = Math.abs(requiredHeight - targetHeight);
        
        // Pénalité forte pour hauteurs trop extrêmes (éviter les coupures importantes)
        let extremeHeightPenalty = 0;
        if (requiredHeight > targetHeight * 1.5) {
            extremeHeightPenalty = 100; // Très pénalisant si trop haut
        } else if (requiredHeight < targetHeight * 0.6) {
            extremeHeightPenalty = 80; // Pénalisant si trop bas
        }
        
        // Pénalité pour les lignes avec trop peu d'images
        const sparsityPenalty = rowImages.length === 1 ? 30 : 0;
        
        // Bonus pour les lignes avec 2-3 images (optimal sur mobile)
        const optimalSizeBonus = (rowImages.length >= 2 && rowImages.length <= 3) ? -10 : 0;
        
        return heightDifference + extremeHeightPenalty + sparsityPenalty + optimalSizeBonus;
    }
    
    /**
     * Crée une ligne parfaitement alignée avec hauteur fixe
     */
    createOptimizedMobileRow(galleryGrid, rowData, containerWidth, targetHeight, gap, isLastRow = false) {
        const rowElement = document.createElement('div');
        rowElement.className = 'gallery-row mobile-google-style';
        
        // Calculer les dimensions pour remplir exactement la largeur
        const totalGaps = (rowData.length - 1) * gap;
        const availableWidth = containerWidth - totalGaps;
        const totalAspectRatio = rowData.reduce((sum, item) => sum + item.aspectRatio, 0);
        
        // Pour l'alignement parfait, utiliser une hauteur fixe
        let finalHeight;
        if (isLastRow) {
            // Dernière ligne : hauteur calculée mais limitée pour rester visible
            const calculatedHeight = availableWidth / totalAspectRatio;
            finalHeight = Math.min(calculatedHeight, targetHeight * 1.3);
        } else {
            // Autres lignes : hauteur fixe pour alignement parfait
            finalHeight = targetHeight;
        }
        
        // Imposer la hauteur fixe pour alignement
        rowElement.style.height = `${finalHeight}px`;
        
        // Calculer les largeurs pour remplir exactement la largeur
        const scale = availableWidth / (totalAspectRatio * finalHeight);
        
        rowData.forEach((item, index) => {
            const card = this.createImageCard(item.image, item.index);
            const scaledWidth = item.aspectRatio * finalHeight * scale;
            
            card.style.width = `${scaledWidth}px`;
            card.style.flex = 'none';
            card.style.height = `${finalHeight}px`;
            
            rowElement.appendChild(card);
        });
        
        galleryGrid.appendChild(rowElement);
    }
    
    renderNewImages(newImages) {
        // Pour le layout justified, on recrée toute la galerie
        this.renderGallery();
    }
    
    /**
     * Détermine le nombre d'images par ligne selon la taille d'écran
     * @returns {number} Nombre d'images par ligne
     */
    getImagesPerRow() {
        const width = window.innerWidth;
        if (width < 480) return 1;
        if (width < 768) return 2;
        if (width < 1024) return 3;
        return 4;
    }
    
    /**
     * Crée des lignes justifiées avec hauteurs identiques (VERSION COMPLEXE - DÉSACTIVÉE)
     * @param {Array} images - Liste des images
     * @returns {Array} Lignes d'images avec dimensions calculées
     */
    createJustifiedRowsOLD(images) {
        const containerWidth = this.container.clientWidth || 800;
        const targetHeight = this.getTargetRowHeight();
        const gap = 8;
        
        const rows = [];
        let currentRow = [];
        let currentRowWidth = 0;
        
        images.forEach((image, globalIndex) => {
            // Estimer l'aspect ratio de l'image (par défaut 1.5 si non fourni)
            const aspectRatio = image.aspectRatio || this.estimateAspectRatio(image) || 1.5;
            const imageWidth = targetHeight * aspectRatio;
            
            const imageData = {
                data: image,
                aspectRatio: aspectRatio,
                globalIndex: globalIndex,
                width: imageWidth
            };
            
            // Vérifier si ajouter cette image dépasse la largeur
            const gapsInRow = currentRow.length > 0 ? currentRow.length : 0;
            const projectedWidth = currentRowWidth + imageWidth + (gapsInRow > 0 ? gap : 0);
            
            if (projectedWidth > containerWidth && currentRow.length > 0) {
                // Finaliser la ligne actuelle
                this.adjustRowToFitWidth(currentRow, containerWidth, gap);
                rows.push(currentRow);
                
                // Commencer une nouvelle ligne
                currentRow = [imageData];
                currentRowWidth = imageWidth;
            } else {
                // Ajouter à la ligne actuelle
                currentRow.push(imageData);
                currentRowWidth = projectedWidth;
            }
        });
        
        // Ajouter la dernière ligne si elle n'est pas vide
        if (currentRow.length > 0) {
            this.adjustRowToFitWidth(currentRow, containerWidth, gap);
            rows.push(currentRow);
        }
        
        return rows;
    }
    
    /**
     * Ajuste une ligne pour qu'elle remplisse exactement la largeur
     * @param {Array} row - Images de la ligne
     * @param {number} targetWidth - Largeur cible
     * @param {number} gap - Espacement entre images
     */
    adjustRowToFitWidth(row, targetWidth, gap) {
        const totalGaps = (row.length - 1) * gap;
        const availableWidth = targetWidth - totalGaps;
        const totalAspectRatio = row.reduce((sum, img) => sum + img.aspectRatio, 0);
        
        // Recalculer les ratios pour que la somme des largeurs = availableWidth
        const scale = availableWidth / (totalAspectRatio * this.getTargetRowHeight());
        
        row.forEach(image => {
            image.aspectRatio = image.aspectRatio * scale;
        });
    }
    
    /**
     * Calcule la hauteur cible des lignes selon la taille d'écran
     * @returns {number} Hauteur en pixels
     */
    getTargetRowHeight() {
        const width = window.innerWidth;
        if (width < 480) return 120;
        if (width < 768) return 150;
        if (width < 1024) return 180;
        return 200;
    }
    
    /**
     * Estime l'aspect ratio d'une image de manière plus intelligente
     * @param {Object} image - Objet image
     * @returns {number} Aspect ratio estimé
     */
    estimateAspectRatio(image) {
        // Si déjà calculé et valide, l'utiliser
        if (image.aspectRatio && image.aspectRatio > 0) return image.aspectRatio;
        
        // Essayer de détecter depuis l'URL ou le nom de fichier
        const src = image.src || '';
        
        // Heuristiques améliorées
        if (src.includes('square') || src.includes('1x1') || src.includes('sq_')) return 1.0;
        if (src.includes('portrait') || src.includes('vert') || src.includes('9x16')) return 0.75;
        if (src.includes('landscape') || src.includes('horiz') || src.includes('16x9')) return 1.78;
        if (src.includes('wide') || src.includes('panorama') || src.includes('pano')) return 2.5;
        if (src.includes('tall') || src.includes('long')) return 0.6;
        
        // Variations plus réalistes basées sur des ratios photo courants
        const commonRatios = [
            1.0,   // Carré (Instagram)
            1.33,  // 4:3 (photo classique)
            1.5,   // 3:2 (reflex)
            1.78,  // 16:9 (smartphone moderne)
            0.8,   // 4:5 (portrait)
            0.75,  // 3:4 (portrait classique)
            0.67   // 2:3 (portrait reflex)
        ];
        
        // Utiliser une distribution plus naturelle basée sur l'index
        const hash = this.simpleHash(src);
        return commonRatios[hash % commonRatios.length];
    }
    
    /**
     * Hash simple pour avoir une répartition cohérente
     */
    simpleHash(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convertir en 32bit integer
        }
        return Math.abs(hash);
    }
    

    
    createImageCard(image, index) {
        const card = document.createElement('div');
        card.className = 'gallery-photo-card';
        card.setAttribute('data-index', index);
        try { card.style.position = 'relative'; } catch {}
        
        const estimatedRatio = image.aspectRatio || this.estimateAspectRatio(image) || (image.hasFaceMatch ? 0.9 : 1.5);
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
        
        // Gestion du chargement d'image
        img.onload = () => {
            // Calculer et stocker l'aspect ratio réel
            const aspectRatio = img.naturalWidth && img.naturalHeight
                ? (img.naturalWidth / img.naturalHeight)
                : estimatedRatio;
            image.aspectRatio = aspectRatio;
            card.dataset.aspectRatio = String(aspectRatio);
            card.dataset.loaded = '1';
            
            if (this.options.autoDetectRatio) {
                this.detectAndApplyRatio(img, card);
            }
            
            card.classList.remove('loading');
            
            // Réajuster les hauteurs de ligne après chargement
            setTimeout(() => {
                this.adjustRowHeights();
            }, 50);
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

        // Badge "Vos photos" si l'image a un match facial
        try {
            if (image && (image.hasFaceMatch === true || image.has_face_match === true)) {
                const badge = document.createElement('div');
                badge.className = 'gallery-match-badge';
                badge.title = 'Aussi dans vos photos';
                badge.style.cssText = [
                    'position: absolute',
                    'top: 8px',
                    'right: 8px',
                    'background: rgba(76, 175, 80, 0.95)',
                    'color: #fff',
                    'padding: 4px 8px',
                    'border-radius: 12px',
                    'font-size: 12px',
                    'font-weight: 700',
                    'display: inline-flex',
                    'align-items: center',
                    'gap: 6px',
                    'z-index: 10',
                    'box-shadow: 0 2px 8px rgba(0,0,0,0.2)'
                ].join(';');
                const icon = document.createElement('span');
                icon.textContent = '✅';
                const txt = document.createElement('span');
                txt.textContent = 'Vos photos';
                badge.appendChild(icon);
                badge.appendChild(txt);
                card.appendChild(badge);
                card.setAttribute('data-has-match', '1');
            }
        } catch (e) {}
        
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
        // Layout masonry CSS natif - pas besoin de classes spéciales
        // Les images gardent leurs proportions naturelles
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
    
    async openLightbox(index) {
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

        // Suppression des cadres de visage: aucun overlay ni appel /faces
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