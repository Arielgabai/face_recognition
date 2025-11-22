import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User, LoginCredentials, RegisterData, AuthContextType } from '../types';
import { authService } from '../services/api';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initializeAuth = async () => {
      const savedToken = localStorage.getItem('token');
      const savedUser = localStorage.getItem('user');

      if (savedToken && savedUser) {
        try {
          // Restauration optimiste de la session
          setToken(savedToken);
          const parsedUser = JSON.parse(savedUser);
          setUser(parsedUser);
          
          // On considère l'utilisateur connecté immédiatement pour éviter la redirection
          setIsLoading(false);
          
          // Vérification du token en arrière-plan
          try {
            await authService.getCurrentUser();
          } catch (error) {
            // Si le token n'est plus valide côté serveur, on déconnecte proprement
            console.error("Session expirée ou invalide", error);
            logout();
          }
          return;
        } catch (error) {
          // Erreur de parsing des données locales
          console.error("Erreur de lecture du localStorage", error);
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        }
      }
      // Si pas de données sauvegardées ou erreur de parsing
      setIsLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (credentials: LoginCredentials) => {
    try {
      const response = await authService.login(credentials);
      const access_token: string = response.data.access_token;

      // Récupérer les informations de l'utilisateur
      const userResponse = await authService.getCurrentUser();
      const userData: User = userResponse.data;

      setToken(access_token);
      setUser(userData);

      localStorage.setItem('token', access_token);
      localStorage.setItem('user', JSON.stringify(userData));
    } catch (error) {
      throw error;
    }
  };

  const register = async (data: RegisterData) => {
    try {
      const response = await authService.register(data);
      // Certaines implémentations renvoient un Token, d'autres un User. On tente de récupérer l'utilisateur ensuite si besoin.
      const maybeUser = response.data as any;
      if (maybeUser && (maybeUser.username || maybeUser.email)) {
        setUser(maybeUser as User);
      }
    } catch (error) {
      throw error;
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    register,
    logout,
    isLoading,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}; 