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
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { photoService } from '../services/api';
import { Photo, UserProfile } from '../types';
import SelfieUpload from './SelfieUpload';
import PhotoUpload from './PhotoUpload';

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

const Dashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const [myPhotos, setMyPhotos] = useState<Photo[]>([]);
  const [allPhotos, setAllPhotos] = useState<Photo[]>([]);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [profileData, myPhotosData, allPhotosData] = await Promise.all([
        photoService.getProfile(),
        photoService.getMyPhotos(),
        photoService.getAllPhotos(),
      ]);
      
      setProfile(profileData.data);
      setMyPhotos(myPhotosData.data);
      setAllPhotos(allPhotosData.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement des données');
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
          <Typography variant="h6" gutterBottom>
            Photos où vous apparaissez
          </Typography>
          {myPhotos.length === 0 ? (
            <Typography color="text.secondary">
              Aucune photo trouvée où vous apparaissez.
            </Typography>
          ) : (
            <Grid container spacing={2}>
              {myPhotos.map((photo) => (
                <Grid item xs={12} sm={6} md={4} key={photo.id}>
                  <Card>
                    <CardMedia
                      component="img"
                      height="200"
                      image={photoService.getImage(photo.filename)}
                      alt={photo.original_filename}
                    />
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        {photo.original_filename}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <Typography variant="h6" gutterBottom>
            Toutes les photos disponibles
          </Typography>
          {allPhotos.length === 0 ? (
            <Typography color="text.secondary">
              Aucune photo disponible.
            </Typography>
          ) : (
            <Grid container spacing={2}>
              {allPhotos.map((photo) => (
                <Grid item xs={12} sm={6} md={4} key={photo.id}>
                  <Card>
                    <CardMedia
                      component="img"
                      height="200"
                      image={photoService.getImage(photo.filename)}
                      alt={photo.original_filename}
                    />
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        {photo.original_filename}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <SelfieUpload onSuccess={loadDashboardData} />
        </TabPanel>

        {user?.user_type === 'photographer' && (
          <TabPanel value={tabValue} index={3}>
            <PhotoUpload onSuccess={loadDashboardData} />
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