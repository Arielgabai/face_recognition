import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { photoService } from '../services/api';

interface JoinEventProps {
  onEventJoined: () => void;
}

const JoinEvent: React.FC<JoinEventProps> = ({ onEventJoined }) => {
  const { user } = useAuth();
  const [eventCode, setEventCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleJoinEvent = async () => {
    if (!eventCode.trim()) {
      setError('Veuillez entrer un code événement');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setSuccess('');

      await photoService.joinEvent(eventCode);
      
      setSuccess('Inscrit avec succès à l\'événement !');
      setEventCode('');
      onEventJoined();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'inscription à l\'événement');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Rejoindre un événement
        </Typography>
        
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Entrez le code de l'événement que vous souhaitez rejoindre.
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        <Box display="flex" gap={2} alignItems="center">
          <TextField
            label="Code événement"
            value={eventCode}
            onChange={(e) => setEventCode(e.target.value.toUpperCase())}
            placeholder="Ex: ABC12345"
            fullWidth
            disabled={loading}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleJoinEvent();
              }
            }}
          />
          <Button
            variant="contained"
            onClick={handleJoinEvent}
            disabled={loading || !eventCode.trim()}
            sx={{ minWidth: 120 }}
          >
            {loading ? <CircularProgress size={20} /> : 'Rejoindre'}
          </Button>
        </Box>

        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          Le code événement vous a été fourni par l'organisateur de l'événement.
        </Typography>
      </CardContent>
    </Card>
  );
};

export default JoinEvent; 