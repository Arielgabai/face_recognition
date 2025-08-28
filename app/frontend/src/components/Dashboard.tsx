import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  Grid,
  Card,
  CardMedia,
  CardContent,
  Button,
  Alert,
  CircularProgress,
  Paper,
  Dialog,
  DialogContent,
  IconButton,
  Fade,
  Backdrop,
} from '@mui/material';
import { 
  Close as CloseIcon, 
  ArrowBack as ArrowBackIcon, 
  ArrowForward as ArrowForwardIcon 
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { photoService } from '../services/api';
import { Photo, UserProfile } from '../types';
import SelfieUpload from './SelfieUpload';
import PhotoUpload from './PhotoUpload';
import EventSelector from './EventSelector';
import JoinEvent from './JoinEvent';
import PhotographerEventManager from './PhotographerEventManager';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

// Composant Galerie moderne intégré
interface ModernGalleryProps {
  photos: Photo[];
  title?: string;
  loading?: boolean;
  error?: string | null;
}

const ModernGallery: React.FC<ModernGalleryProps> = ({ 
  photos, 
  title, 
  loading = false, 
  error 
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
    <Box sx={{ width: '100%' }}>
      {title && (
        <Typography 
          variant="h6" 
          component="h2" 
          sx={{ 
            mb: 2, 
            fontWeight: 'medium',
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
          
          // Déterminer la taille de la grille (on peut améliorer avec l'aspect ratio plus tard)
          let gridRowSpan = 1;
          let gridColSpan = 1;

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
                image={`/api/photo/${photo.id}`}
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
                  src={`/api/photo/${photos[selectedPhoto].id}`}
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

const Dashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const [myPhotos, setMyPhotos] = useState<Photo[]>([]);
  const [allPhotos, setAllPhotos] = useState<Photo[]>([]);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentEventId, setCurrentEventId] = useState<number | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, [currentEventId]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      if (user?.user_type === 'user' && currentEventId) {
        // Pour les utilisateurs, charger les photos de l'événement sélectionné
        const [profileData, myPhotosData, allPhotosData] = await Promise.all([
          photoService.getProfile(),
          photoService.getUserEventPhotos(currentEventId),
          photoService.getAllEventPhotos(currentEventId),
        ]);
        
        setProfile(profileData.data);
        setMyPhotos(myPhotosData.data);
        setAllPhotos(allPhotosData.data);
      } else {
        // Chargement normal pour les photographes ou sans événement sélectionné
        const [profileData, myPhotosData, allPhotosData] = await Promise.all([
          photoService.getProfile(),
          photoService.getMyPhotos(),
          photoService.getAllPhotos(),
        ]);
        
        setProfile(profileData.data);
        setMyPhotos(myPhotosData.data);
        setAllPhotos(allPhotosData.data);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement des données');
    } finally {
      setLoading(false);
    }
  };

  const handleEventChange = (eventId: number) => {
    setCurrentEventId(eventId);
  };

  const handleEventJoined = () => {
    // Recharger les données après avoir rejoint un événement
    loadDashboardData();
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleLogout = () => {
    logout();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4, mb: 4 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h4" component="h1">
            Tableau de bord
          </Typography>
          <Button variant="outlined" onClick={handleLogout}>
            Déconnexion
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Paper sx={{ mb: 3, p: 2 }}>
          <Typography variant="h6" gutterBottom>
            Bonjour, {user?.username} !
          </Typography>
          {profile && (
            <Typography variant="body2" color="text.secondary">
              Vous avez {profile.photos_with_face} photos où vous apparaissez sur un total de {profile.total_photos} photos.
            </Typography>
          )}
        </Paper>

        {/* Gestion des événements selon le type d'utilisateur */}
        {user?.user_type === 'user' && (
          <Box sx={{ mb: 3 }}>
            <EventSelector onEventChange={handleEventChange} currentEventId={currentEventId ?? undefined} />
            <JoinEvent onEventJoined={handleEventJoined} />
          </Box>
        )}

        {user?.user_type === 'photographer' && (
          <Box sx={{ mb: 3 }}>
            <PhotographerEventManager onEventChange={handleEventChange} currentEventId={currentEventId ?? undefined} />
          </Box>
        )}

        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={tabValue} onChange={handleTabChange}>
            <Tab label="Mes Photos" />
            <Tab label="Toutes les Photos" />
            <Tab label="Upload Selfie" />
            {user?.user_type === 'photographer' && (
              <Tab label="Upload Photo" />
            )}
            <Tab label="Mon Profil" />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <ModernGallery 
            photos={myPhotos}
            title={`📸 Vos photos (${myPhotos.length})`}
            loading={loading && myPhotos.length === 0}
            error={error}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <ModernGallery 
            photos={allPhotos}
            title={`🖼 Toutes les photos disponibles (${allPhotos.length})`}
            loading={loading && allPhotos.length === 0}
            error={error}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <SelfieUpload onSuccess={loadDashboardData} />
        </TabPanel>

        {user?.user_type === 'photographer' && (
          <TabPanel value={tabValue} index={3}>
            <PhotoUpload onSuccess={loadDashboardData} eventId={currentEventId ?? undefined} />
          </TabPanel>
        )}

        <TabPanel value={tabValue} index={user?.user_type === 'photographer' ? 4 : 3}>
          <Typography variant="h6" gutterBottom>
            Informations du profil
          </Typography>
          {profile && (
            <Box>
              <Typography variant="body1">
                <strong>Nom d'utilisateur:</strong> {profile.user.username}
              </Typography>
              <Typography variant="body1">
                <strong>Email:</strong> {profile.user.email}
              </Typography>
              <Typography variant="body1">
                <strong>Type de compte:</strong> {profile.user.user_type}
              </Typography>
              <Typography variant="body1">
                <strong>Total de photos:</strong> {profile.total_photos}
              </Typography>
              <Typography variant="body1">
                <strong>Photos où vous apparaissez:</strong> {profile.photos_with_face}
              </Typography>
            </Box>
          )}
        </TabPanel>
      </Box>
    </Container>
  );
};

export default Dashboard; 