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
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { photoService } from '../services/api';

interface Event {
  id: number;
  name: string;
  event_code: string;
  date: string;
  joined_at: string;
}

interface EventSelectorProps {
  onEventChange: (eventId: number) => void;
  currentEventId?: number;
}

const EventSelector: React.FC<EventSelectorProps> = ({ onEventChange, currentEventId }) => {
  const { user } = useAuth();
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<number | ''>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadEvents();
  }, []);

  useEffect(() => {
    if (currentEventId) {
      setSelectedEventId(currentEventId);
    } else if (events.length > 0) {
      setSelectedEventId(events[0].id);
      onEventChange(events[0].id);
    }
  }, [events, currentEventId, onEventChange]);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const response = await photoService.getUserEvents();
      setEvents(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement des événements');
    } finally {
      setLoading(false);
    }
  };

  const handleEventChange = (eventId: number) => {
    setSelectedEventId(eventId);
    onEventChange(eventId);
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
            Aucun événement
          </Typography>
          <Typography color="text.secondary">
            Vous n'êtes inscrit à aucun événement.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Sélectionner un événement
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
  );
};

export default EventSelector; 