import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Container,
  Alert,
  Link,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import AccountSelector from './AccountSelector';

interface AccountInfo {
  user_id: number;
  username: string;
  user_type: string;
  event_id?: number;
  event_name?: string;
  event_code?: string;
  event_date?: string;
}

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showAccountSelector, setShowAccountSelector] = useState(false);
  const [availableAccounts, setAvailableAccounts] = useState<AccountInfo[]>([]);
  
  const { login, user, isLoading } = useAuth();
  const navigate = useNavigate();

  // Redirection automatique si déjà connecté
  useEffect(() => {
    if (user) {
      navigate('/dashboard', { replace: true });
    }
  }, [user, navigate]);

  // Si l'authentification est en cours de chargement ou si l'utilisateur est déjà connecté,
  // on n'affiche rien pour éviter le "flash" du formulaire de connexion.
  if (isLoading || user) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const result = await login({ username, password });
      
      // Si plusieurs comptes existent, afficher le sélecteur
      if (result && result.multiple_accounts && result.accounts) {
        setAvailableAccounts(result.accounts);
        setShowAccountSelector(true);
        setIsSubmitting(false);
        return;
      }
      
      // Connexion réussie avec un seul compte
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur de connexion');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleAccountSelection = async (account: AccountInfo) => {
    setShowAccountSelector(false);
    setIsSubmitting(true);
    setError('');

    try {
      // Se connecter avec l'user_id spécifique
      await login({ username, password, user_id: account.user_id });
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur de connexion');
    } finally {
      setIsSubmitting(false);
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
            Connexion
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
              label="Nom d'utilisateur ou email"
              name="username"
              autoComplete="username"
              autoFocus
              placeholder="Nom d'utilisateur ou email"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Mot de passe"
              type="password"
              id="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Connexion...' : 'Se connecter'}
            </Button>
            <Box sx={{ textAlign: 'center' }}>
              <Link href="/register" variant="body2">
                {"Pas encore de compte ? S'inscrire"}
              </Link>
              <br />
              <Link href="/register-with-code" variant="body2">
                Première connexion avec un code événement
              </Link>
              <br />
              <Link href="/forgot-password" variant="body2" sx={{ mt: 1 }}>
                🔑 Mot de passe oublié ?
              </Link>
            </Box>
          </Box>
        </Paper>
      </Box>
      
      {/* Sélecteur de compte pour emails utilisés sur plusieurs événements */}
      <AccountSelector
        open={showAccountSelector}
        accounts={availableAccounts}
        onSelectAccount={handleAccountSelection}
        onClose={() => setShowAccountSelector(false)}
      />
    </Container>
  );
};

export default Login; 