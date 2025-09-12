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
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

// Composant Galerie avec react-photo-album
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
  const [faceBoxes, setFaceBoxes] = useState<Array<{ top: number; left: number; width: number; height: number; matched?: boolean; confidence?: number }>>([]);
  const [facesLoading, setFacesLoading] = useState(false);
  const imgRef = React.useRef<HTMLImageElement | null>(null);
  const [overlaySize, setOverlaySize] = useState<{ width: number; height: number }>({ width: 0, height: 0 });

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

  // Mesurer l'image affichée pour calibrer les overlays
  const measureOverlay = () => {
    const img = imgRef.current;
    if (!img) return;
    const w = img.clientWidth || img.naturalWidth || 0;
    const h = img.clientHeight || img.naturalHeight || 0;
    if (w && h) setOverlaySize({ width: w, height: h });
  };

  useEffect(() => {
    measureOverlay();
    const onResize = () => measureOverlay();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [selectedPhoto]);

  // Charger les cadres de visages pour la photo sélectionnée
  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    const loadFaces = async () => {
      if (selectedPhoto === null) { setFaceBoxes([]); return; }
      try {
        setFacesLoading(true);
        const photo = photos[selectedPhoto];
        if (!photo) return;
        const res = await photoService.getPhotoFaces(photo.id);
        if (cancelled) return;
        const boxes = (res.data?.boxes || []) as Array<any>;
        const norm = boxes.map((b) => ({
          top: Math.min(1, Math.max(0, Number(b.top) || 0)),
          left: Math.min(1, Math.max(0, Number(b.left) || 0)),
          width: Math.min(1, Math.max(0, Number(b.width) || 0)),
          height: Math.min(1, Math.max(0, Number(b.height) || 0)),
          matched: Boolean(b.matched),
          confidence: Number.isFinite(b.confidence) ? Number(b.confidence) : undefined,
        })).filter((b) => b.width > 0 && b.height > 0);
        setFaceBoxes(norm);
      } catch {
        if (!cancelled) setFaceBoxes([]);
      } finally {
        if (!cancelled) setFacesLoading(false);
      }
    };
    loadFaces();
    return () => { cancelled = true; controller.abort(); };
  }, [selectedPhoto, photos]);

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
            xs: 'repeat(auto-fill, minmax(200px, 1fr))',
            sm: 'repeat(auto-fill, minmax(250px, 1fr))',
            md: 'repeat(auto-fill, minmax(300px, 1fr))',
            lg: 'repeat(auto-fill, minmax(320px, 1fr))',
          },
          gap: 2,
          gridAutoRows: 'minmax(200px, auto)',
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
              {/* Tag de matching */}
              {photo.has_face_match && (
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
              
              {/* Image */}
              <Box
                component="img"
                src={photoService.getImage(photo.filename)}
                alt={photo.original_filename || 'Photo'}
                sx={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
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
                <Box sx={{ position: 'relative', maxWidth: '100%', maxHeight: '100%' }}>
                  <Box
                    component="img"
                    ref={imgRef}
                    onLoad={measureOverlay}
                    src={photoService.getImage(photos[selectedPhoto].filename)}
                    alt={photos[selectedPhoto].original_filename}
                    sx={{
                      maxWidth: '100%',
                      maxHeight: '100%',
                      objectFit: 'contain',
                      borderRadius: 1,
                      display: 'block',
                    }}
                  />
                  {/* Container centré de la taille exacte de l'image affichée */}
                  <Box sx={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    width: `${overlaySize.width}px`,
                    height: `${overlaySize.height}px`,
                    pointerEvents: 'none',
                    zIndex: 2,
                  }}>
                    {faceBoxes && faceBoxes.map((b, i) => (
                      <Box
                        key={`face-${i}`}
                        sx={{
                          position: 'absolute',
                          top: `${b.top * overlaySize.height}px`,
                          left: `${b.left * overlaySize.width}px`,
                          width: `${b.width * overlaySize.width}px`,
                          height: `${b.height * overlaySize.height}px`,
                          border: b.matched ? '3px solid #4caf50' : '2px solid rgba(255,255,255,0.9)',
                          borderRadius: '6px',
                          boxShadow: b.matched ? '0 0 12px rgba(76,175,80,0.8)' : '0 0 8px rgba(0,0,0,0.6)',
                        }}
                      >
                        {(b.matched || (typeof b.confidence === 'number')) && (
                          <Box sx={{
                            position: 'absolute',
                            top: '-28px',
                            left: 0,
                            backgroundColor: b.matched ? 'success.main' : 'rgba(0,0,0,0.7)',
                            color: 'white',
                            px: 1,
                            py: 0.5,
                            borderRadius: '4px',
                            fontSize: '12px',
                            fontWeight: 700,
                          }}>
                            {b.matched ? 'Match' : 'Visage'}{typeof b.confidence === 'number' ? ` · ${b.confidence}%` : ''}
                          </Box>
                        )}
                      </Box>
                    ))}
                  </Box>
                  {facesLoading && (
                    <Box sx={{ position: 'absolute', top: 8, left: 8, backgroundColor: 'rgba(0,0,0,0.5)', color: 'white', px: 1, py: 0.5, borderRadius: '4px', zIndex: 3, fontSize: '12px' }}>
                      Détection des visages…
                    </Box>
                  )}
                </Box>
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
        console.log('[DEBUG] All photos loaded (event):', allPhotosData.data.length);
        console.log('[DEBUG] Photos with face match (event):', allPhotosData.data.filter(p => p.has_face_match).length);
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
        console.log('[DEBUG] All photos loaded (normal):', allPhotosData.data.length);
        console.log('[DEBUG] Photos with face match (normal):', allPhotosData.data.filter(p => p.has_face_match).length);
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

  // Précharger une liste d'URLs d'images et résoudre uniquement quand tout est chargé (ou timeout)
  const preloadImages = (urls: string[], timeoutMs = 20000): Promise<void> => {
    return new Promise((resolve) => {
      try {
        if (!urls || urls.length === 0) { resolve(); return; }
        let remaining = urls.length;
        let done = false;
        const finish = () => {
          if (!done) { done = true; resolve(); }
        };
        const onSettled = () => { remaining -= 1; if (remaining <= 0) finish(); };
        urls.forEach((u) => {
          const img = new Image();
          img.onload = onSettled;
          img.onerror = onSettled;
          // Empêcher le cache agressif
          const bust = `${u}${u.includes('?') ? '&' : '?'}t=${Date.now()}`;
          img.src = bust;
        });
        setTimeout(finish, timeoutMs);
      } catch {
        resolve();
      }
    });
  };

  // Attendre qu'il y ait une croissance (nouvelles correspondances) puis que les images soient chargées
  const waitForDashboardGrowthAndImages = async (baselineMyLen: number, baselineMatches: number, timeoutMs = 90000, intervalMs = 2000) => {
    // Toujours repartir d'un refetch complet (éviter cache)
    const start = Date.now();
    try {
      setLoading(true);
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
          // Si croissance détectée, précharger et terminer
          if (matchesNow > baselineMatches || myNow.length > baselineMyLen) {
            const myUrls = myNow.map((p: any) => photoService.getImage(p.filename));
            await preloadImages(myUrls);
            await new Promise((r) => setTimeout(r, 150));
            try {
              // Indicateur global (optionnel) pour ré-ouv. ultérieure des onglets : primed
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
            await preloadImages(myUrls);
            await new Promise((r) => setTimeout(r, 150));
            try { (window as any).__myPhotosPrimedReact = true; } catch {}
            return;
          }
        }
        await new Promise((r) => setTimeout(r, intervalMs));
      }
      // Timeout: pas de croissance -> on considère qu'il n'y a pas de photos à afficher
    } finally {
      setLoading(false);
    }
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
            <Tab label="Général" />
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
          <SelfieUpload onSuccess={async () => {
            const baselineMyLen = myPhotos.length;
            const baselineMatches = profile?.photos_with_face ?? baselineMyLen;
            await waitForDashboardGrowthAndImages(baselineMyLen, baselineMatches);
          }} />
        </TabPanel>

        {user?.user_type === 'photographer' && (
          <TabPanel value={tabValue} index={3}>
            <PhotoUpload onSuccess={async () => {
              // Recharger toutes les photos + mes photos, attendre images
              const baselineMyLen = myPhotos.length;
              const baselineMatches = profile?.photos_with_face ?? baselineMyLen;
              await loadDashboardData();
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