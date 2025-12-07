import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  Button,
  Alert,
  CircularProgress,
  Paper,
  Dialog,
  DialogContent,
  IconButton,
  Fade,
  Backdrop,
  Chip,
  Badge,
} from '@mui/material';
import { 
  Close as CloseIcon, 
  ArrowBack as ArrowBackIcon, 
  ArrowForward as ArrowForwardIcon,
  Face as FaceIcon,
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material';
import PhotoAlbum from 'react-photo-album';
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
      {value === index && <Box sx={{ p: { xs: 1, sm: 2, md: 3 } }}>{children}</Box>}
    </div>
  );
}

// Composant Galerie avec react-photo-album
interface ModernGalleryProps {
  photos: Photo[];
  title?: string;
  loading?: boolean;
  error?: string | null;
  showMatchTag?: boolean;
}

const ModernGallery: React.FC<ModernGalleryProps> = ({ 
  photos, 
  title, 
  loading = false, 
  error,
  showMatchTag = true
}) => {
  const [selectedPhoto, setSelectedPhoto] = useState<number | null>(null);
  

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

  

  // Charger les cadres de visages pour la photo sélectionnée
  

  // Simuler des dimensions variées pour un rendu plus naturel
  const getAspectRatio = (index: number) => {
    const aspectRatios = [
      { width: 800, height: 600 },   // 4:3 paysage
      { width: 600, height: 800 },   // 3:4 portrait
      { width: 800, height: 800 },   // 1:1 carré
      { width: 1200, height: 600 },  // 2:1 panoramique
      { width: 600, height: 900 },   // 2:3 portrait
      { width: 900, height: 600 },   // 3:2 paysage
    ];
    return aspectRatios[index % aspectRatios.length];
  };

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

      {/* Galerie avec grille personnalisée pour afficher les tags */}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: 'repeat(2, 1fr)',
            sm: 'repeat(auto-fill, minmax(250px, 1fr))',
            md: 'repeat(auto-fill, minmax(300px, 1fr))',
            lg: 'repeat(auto-fill, minmax(320px, 1fr))',
          },
          gap: { xs: 1, sm: 2 },
          gridAutoRows: 'minmax(200px, auto)',
          justifyContent: 'center',
        }}
      >
        {photos.map((photo, index) => {
          const aspectRatio = getAspectRatio(index);
          const isPortrait = aspectRatio.height > aspectRatio.width;
          const isPanorama = aspectRatio.width / aspectRatio.height > 1.8;
          
          // Debug pour le premier rendu
          if (index === 0) {
            console.log('[DEBUG] Rendering photos, first photo has_face_match:', photo.has_face_match);
          }
          
          return (
            <Box
              key={photo.id}
              sx={{
                gridRowEnd: isPortrait ? 'span 2' : 'span 1',
                gridColumnEnd: isPanorama ? 'span 2' : 'span 1',
                position: 'relative',
                cursor: 'pointer',
                borderRadius: 2,
                overflow: 'hidden',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: '0 8px 25px rgba(0,0,0,0.2)',
                },
              }}
              onClick={() => openLightbox(index)}
            >
              {/* Tag de matching (uniquement dans l'onglet Général) */}
              {showMatchTag && photo.has_face_match && (
                <Chip
                  icon={<FaceIcon />}
                  label="Match"
                  size="small"
                  sx={{
                    position: 'absolute',
                    top: 8,
                    right: 8,
                    zIndex: 2,
                    backgroundColor: 'success.main',
                    color: 'white',
                    fontWeight: 'bold',
                    '& .MuiChip-icon': {
                      color: 'white',
                    },
                  }}
                />
              )}
              
              {/* Image avec lazy loading pour charger progressivement */}
              <Box
                component="img"
                src={photoService.getImage(photo.filename)}
                alt={photo.original_filename || 'Photo'}
                loading="lazy"
                sx={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain',
                  display: 'block',
                }}
              />
            </Box>
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

              {/* Image principale + overlays */}
              <Fade in={true} timeout={300}>
                <Box
                  component="img"
                  src={photoService.getImage(photos[selectedPhoto].filename)}
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
  
  // États de chargement séparés pour améliorer la réactivité
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [loadingMyPhotos, setLoadingMyPhotos] = useState(false);
  const [loadingAllPhotos, setLoadingAllPhotos] = useState(false);
  
  const [error, setError] = useState<string | null>(null);
  const [currentEventId, setCurrentEventId] = useState<number | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, [currentEventId]);

  const loadDashboardData = async () => {
    try {
      // Ne pas bloquer l'interface globale
      setError(null);
      setLoadingProfile(true);
      setLoadingMyPhotos(true);
      setLoadingAllPhotos(true);
      
      // 1. Charger le profil (très rapide)
      photoService.getProfile()
        .then(res => setProfile(res.data))
        .catch(err => console.error("Erreur profil", err))
        .finally(() => setLoadingProfile(false));

      if (user?.user_type === 'user' && currentEventId) {
        // 2. Charger MES photos (prioritaire)
        photoService.getUserEventPhotos(currentEventId)
          .then(res => setMyPhotos(res.data))
          .catch(err => console.error("Erreur mes photos", err))
          .finally(() => setLoadingMyPhotos(false));

        // 3. Charger TOUTES les photos (peut être lent, ne bloque pas le reste)
        photoService.getAllEventPhotos(currentEventId)
          .then(res => {
            setAllPhotos(res.data);
            console.log('[DEBUG] All photos loaded:', res.data.length);
          })
          .catch(err => console.error("Erreur toutes les photos", err))
          .finally(() => setLoadingAllPhotos(false));
          
      } else {
        // Mode photographe ou sans événement
        photoService.getMyPhotos()
          .then(res => setMyPhotos(res.data))
          .catch(err => console.error("Erreur mes photos", err))
          .finally(() => setLoadingMyPhotos(false));

        photoService.getAllPhotos()
          .then(res => setAllPhotos(res.data))
          .catch(err => console.error("Erreur toutes les photos", err))
          .finally(() => setLoadingAllPhotos(false));
      }
      
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'initialisation');
      setLoadingProfile(false);
      setLoadingMyPhotos(false);
      setLoadingAllPhotos(false);
    }
  };

  const handleEventChange = (eventId: number) => {
    setCurrentEventId(eventId);
  };

  const handleEventJoined = () => {
    // Recharger les données après avoir rejoint un événement
    loadDashboardData();
  };

  // Précharger une liste d'URLs d'images de manière non-bloquante
  // Ne pas attendre que toutes les images soient chargées - juste démarrer le chargement
  const preloadImages = (urls: string[], timeoutMs = 3000): Promise<void> => {
    return new Promise((resolve) => {
      try {
        if (!urls || urls.length === 0) { resolve(); return; }
        
        // Limiter le nombre d'images à précharger simultanément (évite de surcharger le navigateur)
        const maxConcurrent = 10;
        const urlsToPreload = urls.slice(0, 100); // Précharger seulement les 100 premières images
        
        let loaded = 0;
        let done = false;
        const finish = () => {
          if (!done) { done = true; resolve(); }
        };
        
        // Précharger par batch pour ne pas surcharger
        const preloadBatch = (batch: string[]) => {
          batch.forEach((u) => {
            const img = new Image();
            img.onload = () => { loaded++; };
            img.onerror = () => { loaded++; };
            // Empêcher le cache agressif
            const bust = `${u}${u.includes('?') ? '&' : '?'}t=${Date.now()}`;
            img.src = bust;
          });
        };
        
        // Précharger par batch de maxConcurrent images
        for (let i = 0; i < urlsToPreload.length; i += maxConcurrent) {
          const batch = urlsToPreload.slice(i, i + maxConcurrent);
          setTimeout(() => preloadBatch(batch), i * 50); // Espacer les batches de 50ms
        }
        
        // Résoudre rapidement (ne pas attendre que toutes les images soient chargées)
        setTimeout(finish, timeoutMs);
      } catch {
        resolve();
      }
    });
  };

  // Attendre qu'il y ait une croissance (nouvelles correspondances) puis précharger les images en arrière-plan
  // Ne bloque PAS le loader - les images se chargent progressivement
  const waitForDashboardGrowthAndImages = async (baselineMyLen: number, baselineMatches: number, timeoutMs = 30000, intervalMs = 2000) => {
    const start = Date.now();
    try {
      // Ne pas remettre setLoading(true) - les données sont déjà chargées
      setError(null);
      while (Date.now() - start < timeoutMs) {
        if (user?.user_type === 'user' && currentEventId) {
          const [profileData, myPhotosData] = await Promise.all([
            photoService.getProfile(),
            photoService.getUserEventPhotos(currentEventId),
          ]);
          const matchesNow = profileData.data?.photos_with_face ?? 0;
          const myNow = myPhotosData.data ?? [];
          setProfile(profileData.data);
          setMyPhotos(myNow);
          // Si croissance détectée, précharger en arrière-plan et terminer
          if (matchesNow > baselineMatches || myNow.length > baselineMyLen) {
            const myUrls = myNow.map((p: any) => photoService.getImage(p.filename));
            // Précharger en arrière-plan sans bloquer
            preloadImages(myUrls).catch(() => {}); // Ignorer les erreurs
            try {
              (window as any).__myPhotosPrimedReact = true;
            } catch {}
            return;
          }
        } else {
          const [profileData, myPhotosData] = await Promise.all([
            photoService.getProfile(),
            photoService.getMyPhotos(),
          ]);
          const matchesNow = profileData.data?.photos_with_face ?? 0;
          const myNow = myPhotosData.data ?? [];
          setProfile(profileData.data);
          setMyPhotos(myNow);
          if (matchesNow > baselineMatches || myNow.length > baselineMyLen) {
            const myUrls = myNow.map((p: any) => photoService.getImage(p.filename));
            // Précharger en arrière-plan sans bloquer
            preloadImages(myUrls).catch(() => {}); // Ignorer les erreurs
            try { (window as any).__myPhotosPrimedReact = true; } catch {}
            return;
          }
        }
        await new Promise((r) => setTimeout(r, intervalMs));
      }
      // Timeout: pas de croissance -> on considère qu'il n'y a pas de photos à afficher
    } catch (err) {
      console.error('waitForDashboardGrowthAndImages error:', err);
    }
    // Ne pas mettre setLoading(false) ici - le loader est déjà masqué
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleLogout = () => {
    logout();
  };

  if (false) { // Désactivation du loader global bloquant
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
          {loadingProfile && !profile ? (
             <Box display="flex" alignItems="center" gap={2}>
               <CircularProgress size={20} />
               <Typography variant="body2">Chargement du profil...</Typography>
             </Box>
          ) : (
            <>
              <Typography variant="h6" gutterBottom>
                Bonjour, {user?.username} !
              </Typography>
              {profile && (
                <Typography variant="body2" color="text.secondary">
                  Vous avez {profile.photos_with_face} photos où vous apparaissez sur un total de {profile.total_photos} photos.
                </Typography>
              )}
            </>
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
            <Tab label={`Mes Photos ${loadingMyPhotos ? '...' : ''}`} />
            <Tab label={`Général ${loadingAllPhotos ? '...' : ''}`} />
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
            title={`Mes photos (${myPhotos.length})`}
            loading={loadingMyPhotos}
            error={error}
            showMatchTag={false}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <ModernGallery 
            photos={allPhotos}
            title={`Général (${allPhotos.length})`}
            loading={loadingAllPhotos}
            error={error}
            showMatchTag={true}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <SelfieUpload onSuccess={async () => {
            const baselineMyLen = myPhotos.length;
            const baselineMatches = profile?.photos_with_face ?? baselineMyLen;
            await waitForDashboardGrowthAndImages(baselineMyLen, baselineMatches);
          }} />
        </TabPanel>

        {user?.user_type === 'photographer' && (
          <TabPanel value={tabValue} index={3}>
            <PhotoUpload onSuccess={async () => {
              // Recharger les données en arrière-plan
              const baselineMyLen = myPhotos.length;
              const baselineMatches = profile?.photos_with_face ?? baselineMyLen;
              loadDashboardData(); // Ne plus attendre ici pour ne pas bloquer
              await waitForDashboardGrowthAndImages(baselineMyLen, baselineMatches);
            }} eventId={currentEventId ?? undefined} />
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