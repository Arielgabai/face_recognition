import React, { useState, useEffect } from 'react';
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
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { photoService, validationService } from '../services/api';

interface RegisterWithEventCodeProps {
  eventCode?: string;
}

const RegisterWithEventCode: React.FC<RegisterWithEventCodeProps> = ({ eventCode }) => {
  const navigate = useNavigate();
  const params = useParams<{ eventCode?: string }>();
  const location = useLocation();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    eventCode: eventCode || params.eventCode || new URLSearchParams(location.search).get('event_code') || '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [usernameError, setUsernameError] = useState('');
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [confirmPasswordError, setConfirmPasswordError] = useState('');
  const [eventCodeError, setEventCodeError] = useState('');
  const [success, setSuccess] = useState('');
  
  useEffect(() => {
    const fromPath = params.eventCode || '';
    const fromQuery = new URLSearchParams(location.search).get('event_code') || '';
    const resolved = eventCode || fromPath || fromQuery || '';
    if (resolved && resolved !== formData.eventCode) {
      setFormData(prev => ({ ...prev, eventCode: resolved }));
    }
  }, [eventCode, params.eventCode, location.search]);

  const handleInputChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [field]: event.target.value,
    });
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    setSuccess('');
    setUsernameError('');
    setEmailError('');
    setPasswordError('');
    setConfirmPasswordError('');
    setEventCodeError('');

    setLoading(true);

    let hasError = false;
    // Validations locales
    if (!formData.username.trim()) {
      setUsernameError("Le nom d'utilisateur est obligatoire");
      hasError = true;
    }
    if (!formData.email.trim()) {
      setEmailError("L'email est obligatoire");
      hasError = true;
    }
    if (!formData.eventCode.trim()) {
      setEventCodeError('Veuillez entrer un code événement');
      hasError = true;
    }
    if (formData.password !== formData.confirmPassword) {
      setConfirmPasswordError('Les mots de passe ne correspondent pas');
      hasError = true;
    }
    const strongPw = /^(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/;
    if (!strongPw.test(formData.password)) {
      setPasswordError("Mot de passe invalide: 8 caractères minimum, au moins 1 majuscule, 1 chiffre et 1 caractère spécial");
      hasError = true;
    }

    // Vérifier validité du code événement (pre-flight UX uniquement – la DB reste source de vérité)
    try {
      const { valid } = await validationService.checkEventCode(formData.eventCode);
      if (!valid) {
        setEventCodeError('Code événement invalide');
        hasError = true;
      }
    } catch {
      // Erreur réseau sur le pre-flight : on laisse l'appel principal trancher
    }

    // Vérifier disponibilité username/email pour afficher toutes les erreurs ensemble
    try {
      const availability = await validationService.checkUserAvailability({
        username: formData.username,
        email: formData.email,
        event_code: formData.eventCode,
      });
      if (availability?.username_taken) {
        setUsernameError("Nom d'utilisateur déjà pris pour cet événement");
        hasError = true;
      }
      if (availability?.email_taken) {
        setEmailError('Email déjà utilisé pour cet événement');
        hasError = true;
      }
    } catch {
      // Erreur réseau sur le pre-flight : on laisse l'appel principal trancher
    }

    if (hasError) {
      setLoading(false);
      return;
    }

    try {
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
      const status: number | undefined = err?.response?.status;
      const detail: string = err?.response?.data?.detail || '';
      const lower = detail.toLowerCase();

      if (status === 409) {
        // Conflit confirmé par la DB (race condition ou doublon)
        if (lower.includes('email')) {
          setEmailError(detail || 'Email déjà utilisé pour cet événement.');
        } else if (lower.includes('utilisateur')) {
          setUsernameError(detail || "Nom d'utilisateur déjà pris pour cet événement.");
        } else {
          setError(detail || "Cet email ou ce nom d'utilisateur est déjà utilisé pour cet événement.");
        }
      } else if (status === 400 && detail) {
        // Erreurs de validation agrégées renvoyées par le backend
        let mapped = false;
        if (lower.includes('mot de passe') || lower.includes('password')) {
          setPasswordError(detail);
          mapped = true;
        }
        if (detail.includes("Nom d'utilisateur") || lower.includes('utilisateur')) {
          setUsernameError(detail);
          mapped = true;
        }
        if (lower.includes('email')) {
          setEmailError(detail);
          mapped = true;
        }
        if (lower.includes('code')) {
          setEventCodeError(detail);
          mapped = true;
        }
        if (!mapped) setError(detail);
      } else {
        // Erreur 500, réseau ou autre erreur inattendue
        setError("Une erreur technique s'est produite. Merci de réessayer dans quelques instants.");
      }
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
              error={Boolean(usernameError)}
              helperText={usernameError || undefined}
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
              error={Boolean(emailError)}
              helperText={emailError || undefined}
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
              error={Boolean(passwordError)}
              helperText={passwordError || undefined}
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
              error={Boolean(confirmPasswordError)}
              helperText={confirmPasswordError || undefined}
            />
            
            <TextField
              fullWidth
              label="Code événement"
              value={formData.eventCode}
              onChange={handleInputChange('eventCode')}
              margin="normal"
              required
              disabled={loading || Boolean(eventCode || params.eventCode || new URLSearchParams(location.search).get('event_code'))}
              error={Boolean(eventCodeError)}
              helperText={eventCodeError || "Le code vous a été fourni par l'organisateur de l'événement"}
              placeholder="Ex: ABC12345"
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