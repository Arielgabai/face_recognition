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
  Link,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { photoService } from '../services/api';

interface RegisterWithEventCodeProps {
  eventCode?: string;
}

const RegisterWithEventCode: React.FC<RegisterWithEventCodeProps> = ({ eventCode }) => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    eventCode: eventCode || '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleInputChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [field]: event.target.value,
    });
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (formData.password !== formData.confirmPassword) {
      setError('Les mots de passe ne correspondent pas');
      return;
    }

    if (!formData.eventCode.trim()) {
      setError('Veuillez entrer un code événement');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setSuccess('');

      await photoService.registerWithEventCode(
        {
          username: formData.username,
          email: formData.email,
          password: formData.password,
          user_type: 'user',
        },
        formData.eventCode
      );

      setSuccess('Inscription réussie ! Vous pouvez maintenant vous connecter.');
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'inscription');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        bgcolor: 'background.default',
      }}
    >
      <Card sx={{ maxWidth: 400, width: '100%', mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" component="h1" gutterBottom align="center">
            Inscription avec code événement
          </Typography>
          
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }} align="center">
            Créez votre compte pour accéder aux photos de l'événement
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

          <Box component="form" onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label="Nom d'utilisateur"
              value={formData.username}
              onChange={handleInputChange('username')}
              margin="normal"
              required
              disabled={loading}
            />
            
            <TextField
              fullWidth
              label="Email"
              type="email"
              value={formData.email}
              onChange={handleInputChange('email')}
              margin="normal"
              required
              disabled={loading}
            />
            
            <TextField
              fullWidth
              label="Mot de passe"
              type="password"
              value={formData.password}
              onChange={handleInputChange('password')}
              margin="normal"
              required
              disabled={loading}
            />
            
            <TextField
              fullWidth
              label="Confirmer le mot de passe"
              type="password"
              value={formData.confirmPassword}
              onChange={handleInputChange('confirmPassword')}
              margin="normal"
              required
              disabled={loading}
            />
            
            <TextField
              fullWidth
              label="Code événement"
              value={formData.eventCode}
              onChange={handleInputChange('eventCode')}
              margin="normal"
              required
              disabled={loading}
              placeholder="Ex: ABC12345"
              helperText="Le code vous a été fourni par l'organisateur de l'événement"
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? (
                <>
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  Inscription en cours...
                </>
              ) : (
                'S\'inscrire'
              )}
            </Button>

            <Box sx={{ textAlign: 'center' }}>
              <Link href="/login" variant="body2">
                Déjà un compte ? Se connecter
              </Link>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default RegisterWithEventCode; 