import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Chip,
  Grid,
  CardMedia,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { photoService } from '../services/api';
import { Photo } from '../types';
import PhotoUpload from './PhotoUpload';

interface Event {
  id: number;
  name: string;
  event_code: string;
  date: string;
  photographer_id: number;
}

interface PhotographerEventManagerProps {
  onEventChange: (eventId: number) => void;
  currentEventId?: number;
}

const PhotographerEventManager: React.FC<PhotographerEventManagerProps> = ({ 
  onEventChange, 
  currentEventId 
}) => {
  const { user } = useAuth();
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<number | ''>('');
  const [eventPhotos, setEventPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadEvents();
  }, []);

  useEffect(() => {
    if (currentEventId) {
      setSelectedEventId(currentEventId);
      loadEventPhotos(currentEventId);
    } else if (events.length > 0) {
      setSelectedEventId(events[0].id);
      onEventChange(events[0].id);
      loadEventPhotos(events[0].id);
    }
  }, [events, currentEventId, onEventChange]);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const response = await photoService.getPhotographerEvents();
      setEvents(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement des événements');
    } finally {
      setLoading(false);
    }
  };

  const loadEventPhotos = async (eventId: number) => {
    try {
      const response = await photoService.getEventPhotos(eventId);
      setEventPhotos(response.data);
    } catch (err: any) {
      console.error('Erreur lors du chargement des photos:', err);
    }
  };

  const handleEventChange = (eventId: number) => {
    setSelectedEventId(eventId);
    onEventChange(eventId);
    loadEventPhotos(eventId);
  };

  const handlePhotoUploadSuccess = () => {
    if (selectedEventId) {
      loadEventPhotos(selectedEventId);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={2}>
        <CircularProgress />
      </Box>
    );
  }

  if (events.length === 0) {
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Aucun événement assigné
          </Typography>
          <Typography color="text.secondary">
            Vous n'avez aucun événement assigné. Contactez l'administrateur.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Gérer vos événements
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Événement</InputLabel>
            <Select
              value={selectedEventId}
              label="Événement"
              onChange={(e) => handleEventChange(e.target.value as number)}
            >
              {events.map((event) => (
                <MenuItem key={event.id} value={event.id}>
                  <Box>
                    <Typography variant="body1">{event.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Code: {event.event_code} • {new Date(event.date).toLocaleDateString()}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {selectedEventId && (
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Événement sélectionné:
              </Typography>
              {events
                .filter((event) => event.id === selectedEventId)
                .map((event) => (
                  <Box key={event.id} display="flex" alignItems="center" gap={1}>
                    <Chip label={event.name} color="primary" />
                    <Typography variant="body2" color="text.secondary">
                      Code: {event.event_code}
                    </Typography>
                  </Box>
                ))}
            </Box>
          )}
        </CardContent>
      </Card>

      {selectedEventId && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Photos de l'événement ({eventPhotos.length})
            </Typography>
            
            {eventPhotos.length === 0 ? (
              <Typography color="text.secondary">
                Aucune photo uploadée pour cet événement.
              </Typography>
            ) : (
              <Grid container spacing={2}>
                {eventPhotos.map((photo) => (
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
          </CardContent>
        </Card>
      )}

      {selectedEventId && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Uploader des photos pour cet événement
            </Typography>
            <PhotoUpload onSuccess={handlePhotoUploadSuccess} eventId={selectedEventId} />
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default PhotographerEventManager; 