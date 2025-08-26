import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Container,
  Alert,
  Link,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { photoService } from '../services/api';

const Register: React.FC = () => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    user_type: 'user' as 'user' | 'photographer',
    eventCode: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleInputChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value,
    }));
  };

  const handleSelectChange = (event: any) => {
    setFormData(prev => ({
      ...prev,
      user_type: event.target.value as 'user' | 'photographer',
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (formData.password !== formData.confirmPassword) {
      setError('Les mots de passe ne correspondent pas');
      return;
    }

    if (!formData.eventCode.trim()) {
      setError('Le code événement est obligatoire');
      return;
    }

    setIsLoading(true);

    try {
      // Inscription utilisateur liée à un événement (obligatoire)
      await photoService.registerWithEventCode(
        {
          username: formData.username,
          email: formData.email,
          password: formData.password,
          user_type: 'user',
        },
        formData.eventCode
      );
      navigate('/login');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'inscription');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container component="main" maxWidth="xs">
      <Box
        sx={{
          marginTop: 8,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        <Paper
          elevation={3}
          sx={{
            padding: 4,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
          }}
        >
          <Typography component="h1" variant="h5">
            Inscription
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ width: '100%', mt: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
            <TextField
              margin="normal"
              required
              fullWidth
              id="username"
              label="Nom d'utilisateur"
              name="username"
              autoComplete="username"
              autoFocus
              value={formData.username}
              onChange={handleInputChange('username')}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              id="email"
              label="Email"
              name="email"
              autoComplete="email"
              type="email"
              value={formData.email}
              onChange={handleInputChange('email')}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Mot de passe"
              type="password"
              id="password"
              autoComplete="new-password"
              value={formData.password}
              onChange={handleInputChange('password')}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="confirmPassword"
              label="Confirmer le mot de passe"
              type="password"
              id="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleInputChange('confirmPassword')}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="eventCode"
              label="Code événement"
              id="eventCode"
              value={formData.eventCode}
              onChange={handleInputChange('eventCode')}
              helperText="Obtenu via le QR code ou auprès de l'organisateur"
            />
            <FormControl fullWidth margin="normal" disabled>
              <InputLabel id="user-type-label">Type de compte</InputLabel>
              <Select
                labelId="user-type-label"
                id="user-type"
                value={formData.user_type}
                label="Type de compte"
                onChange={handleSelectChange}
              >
                <MenuItem value="user">Utilisateur</MenuItem>
                <MenuItem value="photographer">Photographe</MenuItem>
              </Select>
            </FormControl>
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={isLoading}
            >
              {isLoading ? 'Inscription...' : 'S\'inscrire'}
            </Button>
            <Box sx={{ textAlign: 'center' }}>
              <Link href="/login" variant="body2">
                {"Déjà un compte ? Se connecter"}
              </Link>
              <br />
              <Link href="/register-with-code" variant="body2">
                Première connexion avec un code événement
              </Link>
            </Box>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default Register; 