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
import { photoService, validationService } from '../services/api';

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
  const [usernameError, setUsernameError] = useState('');
  const [emailError, setEmailError] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [confirmPasswordError, setConfirmPasswordError] = useState('');
  const [eventCodeError, setEventCodeError] = useState('');
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
    setUsernameError('');
    setEmailError('');
    setPasswordError('');
    setConfirmPasswordError('');
    setEventCodeError('');

    setIsLoading(true);

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
      setEventCodeError('Le code événement est obligatoire');
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

    // Vérifier validité du code événement
    try {
      const { valid } = await validationService.checkEventCode(formData.eventCode);
      if (!valid) {
        setEventCodeError('Code événement invalide');
        hasError = true;
      }
    } catch {}

    // Vérifier disponibilité username/email même si d'autres erreurs existent, pour tout afficher d'un coup
    try {
      const availability = await validationService.checkUserAvailability({
        username: formData.username,
        email: formData.email,
        event_code: formData.eventCode, // Vérifier pour cet événement spécifique
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
      // Ignore l'erreur réseau ici; l'API d'inscription confirmera au pire
    }

    if (hasError) {
      setIsLoading(false);
      return;
    }

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
      const msg: string = err?.response?.data?.detail || 'Erreur lors de l\'inscription';
      const lower = msg.toLowerCase();
      let mapped = false;
      if (lower.includes('mot de passe') || lower.includes('password')) {
        setPasswordError(msg);
        mapped = true;
      }
      if (msg.includes("Nom d'utilisateur") || lower.includes('utilisateur')) {
        setUsernameError(msg);
        mapped = true;
      }
      if (lower.includes('email')) {
        setEmailError(msg);
        mapped = true;
      }
      if (lower.includes('code')) {
        setEventCodeError(msg);
        mapped = true;
      }
      if (!mapped) {
        setError(msg);
      }
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
              error={Boolean(usernameError)}
              helperText={usernameError || undefined}
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
              error={Boolean(emailError)}
              helperText={emailError || undefined}
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
              error={Boolean(passwordError)}
              helperText={passwordError || undefined}
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
              error={Boolean(confirmPasswordError)}
              helperText={confirmPasswordError || undefined}
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
              error={Boolean(eventCodeError)}
              FormHelperTextProps={{ sx: { color: eventCodeError ? 'error.main' : undefined } }}
              placeholder="Ex: ABC12345"
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