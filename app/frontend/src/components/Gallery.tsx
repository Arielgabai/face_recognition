import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardMedia,
  Dialog,
  DialogContent,
  IconButton,
  CircularProgress,
  Alert,
  Fade,
  Backdrop,
} from '@mui/material';
import { 
  Close as CloseIcon, 
  ArrowBack as ArrowBackIcon, 
  ArrowForward as ArrowForwardIcon 
} from '@mui/icons-material';

export interface Photo {
  id: number;
  filename: string;
  original_filename: string;
  url?: string;
  alt?: string;
  aspectRatio?: number;
}

interface GalleryProps {
  photos: Photo[];
  title?: string;
  loading?: boolean;
  error?: string;
  getImageUrl: (photo: Photo) => string;
}

const Gallery: React.FC<GalleryProps> = ({ 
  photos, 
  title, 
  loading = false, 
  error,
  getImageUrl
}) => {
  const [selectedPhoto, setSelectedPhoto] = useState<number | null>(null);
  const [imageLoaded, setImageLoaded] = useState<{ [key: number]: boolean }>({});

  const handleImageLoad = (photoId: number) => {
    setImageLoaded(prev => ({ ...prev, [photoId]: true }));
  };

  const openLightbox = (index: number) => {
    setSelectedPhoto(index);
  };

  const closeLightbox = () => {
    setSelectedPhoto(null);
  };

  const goToPrevious = () => {
    if (selectedPhoto !== null && selectedPhoto > 0) {
      setSelectedPhoto(selectedPhoto - 1);
    }
  };

  const goToNext = () => {
    if (selectedPhoto !== null && selectedPhoto < photos.length - 1) {
      setSelectedPhoto(selectedPhoto + 1);
    }
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (selectedPhoto !== null) {
      switch (event.key) {
        case 'Escape':
          closeLightbox();
          break;
        case 'ArrowLeft':
          goToPrevious();
          break;
        case 'ArrowRight':
          goToNext();
          break;
      }
    }
  };

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedPhoto]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!photos || photos.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', p: 4 }}>
        <Typography variant="h6" color="text.secondary">
          Aucune photo à afficher
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%', p: { xs: 1, sm: 2 } }}>
      {title && (
        <Typography 
          variant="h4" 
          component="h1" 
          sx={{ 
            mb: 3, 
            textAlign: 'center',
            fontWeight: 'light',
            color: 'text.primary' 
          }}
        >
          {title}
        </Typography>
      )}

      {/* Grille responsive moderne */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'repeat(auto-fill, minmax(150px, 1fr))',
            sm: 'repeat(auto-fill, minmax(200px, 1fr))',
            md: 'repeat(auto-fill, minmax(250px, 1fr))',
            lg: 'repeat(auto-fill, minmax(280px, 1fr))',
          },
          gap: { xs: 1, sm: 1.5, md: 2 },
          gridAutoRows: 'minmax(150px, auto)',
          gridAutoFlow: 'row dense',
        }}
      >
        {photos.map((photo, index) => {
          const isLoaded = imageLoaded[photo.id];
          const imageUrl = getImageUrl(photo);
          
          // Logique pour déterminer la taille de la grille basée sur l'aspect ratio
          const aspectRatio = photo.aspectRatio || 1;
          let gridRowSpan = 1;
          let gridColSpan = 1;
          
          // Images hautes (portrait)
          if (aspectRatio < 0.7) {
            gridRowSpan = 2;
          }
          // Images très larges (panorama)
          else if (aspectRatio > 1.8) {
            gridColSpan = 2;
          }
          // Images carrées ou légèrement rectangulaires restent par défaut

          return (
            <Card
              key={photo.id}
              sx={{
                gridRowEnd: `span ${gridRowSpan}`,
                gridColumnEnd: `span ${gridColSpan}`,
                cursor: 'pointer',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                borderRadius: 2,
                overflow: 'hidden',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                position: 'relative',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: '0 8px 25px rgba(0,0,0,0.2)',
                  '& .overlay': {
                    opacity: 1,
                  }
                },
              }}
              onClick={() => openLightbox(index)}
            >
              {/* Overlay au hover */}
              <Box
                className="overlay"
                sx={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  right: 0,
                  bottom: 0,
                  background: 'linear-gradient(45deg, rgba(25,118,210,0.8), rgba(220,0,78,0.8))',
                  opacity: 0,
                  transition: 'opacity 0.3s ease',
                  zIndex: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: 'white', 
                    fontWeight: 'bold',
                    textShadow: '0 1px 3px rgba(0,0,0,0.5)'
                  }}
                >
                  Voir en grand
                </Typography>
              </Box>

              {/* Placeholder de chargement */}
              {!isLoaded && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: 'grey.100',
                    zIndex: 2,
                  }}
                >
                  <CircularProgress size={24} />
                </Box>
              )}

              <CardMedia
                component="img"
                image={imageUrl}
                alt={photo.original_filename}
                onLoad={() => handleImageLoad(photo.id)}
                sx={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  display: 'block',
                  opacity: isLoaded ? 1 : 0,
                  transition: 'opacity 0.3s ease',
                }}
              />
            </Card>
          );
        })}
      </Box>

      {/* Lightbox Modal */}
      <Dialog
        open={selectedPhoto !== null}
        onClose={closeLightbox}
        maxWidth={false}
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: 'transparent',
            boxShadow: 'none',
            maxWidth: '95vw',
            maxHeight: '95vh',
          }
        }}
        BackdropComponent={Backdrop}
        BackdropProps={{
          timeout: 300,
          sx: { backgroundColor: 'rgba(0, 0, 0, 0.9)' }
        }}
      >
        <DialogContent
          sx={{
            p: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
            backgroundColor: 'transparent',
          }}
        >
          {selectedPhoto !== null && (
            <>
              {/* Bouton de fermeture */}
              <IconButton
                onClick={closeLightbox}
                sx={{
                  position: 'absolute',
                  top: 16,
                  right: 16,
                  zIndex: 3,
                  backgroundColor: 'rgba(0, 0, 0, 0.5)',
                  color: 'white',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.7)',
                  },
                }}
              >
                <CloseIcon />
              </IconButton>

              {/* Navigation précédente */}
              {selectedPhoto > 0 && (
                <IconButton
                  onClick={goToPrevious}
                  sx={{
                    position: 'absolute',
                    left: 16,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    zIndex: 3,
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    color: 'white',
                    '&:hover': {
                      backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    },
                  }}
                >
                  <ArrowBackIcon />
                </IconButton>
              )}

              {/* Navigation suivante */}
              {selectedPhoto < photos.length - 1 && (
                <IconButton
                  onClick={goToNext}
                  sx={{
                    position: 'absolute',
                    right: 16,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    zIndex: 3,
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    color: 'white',
                    '&:hover': {
                      backgroundColor: 'rgba(0, 0, 0, 0.7)',
                    },
                  }}
                >
                  <ArrowForwardIcon />
                </IconButton>
              )}

              {/* Image principale */}
              <Fade in={true} timeout={300}>
                <Box
                  component="img"
                  src={getImageUrl(photos[selectedPhoto])}
                  alt={photos[selectedPhoto].original_filename}
                  sx={{
                    maxWidth: '100%',
                    maxHeight: '100%',
                    objectFit: 'contain',
                    borderRadius: 1,
                  }}
                />
              </Fade>

              {/* Compteur de photos */}
              <Typography
                variant="body2"
                sx={{
                  position: 'absolute',
                  bottom: 16,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  backgroundColor: 'rgba(0, 0, 0, 0.7)',
                  color: 'white',
                  px: 2,
                  py: 1,
                  borderRadius: 1,
                  zIndex: 3,
                }}
              >
                {selectedPhoto + 1} / {photos.length}
              </Typography>
            </>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default Gallery; 