import axios from 'axios';
import { User, Photo, UserProfile, LoginCredentials, RegisterData } from '../types';

const API_BASE_URL = '/api';

// Configuration d'axios
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour ajouter le token d'authentification
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Intercepteur pour gérer les erreurs d'authentification
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Services d'authentification
export const authService = {
  register: (userData: any) => api.post('/register', userData),
  login: (credentials: any) => api.post('/login', credentials),
  getCurrentUser: () => api.get('/me'),
};

// Services pour les photos
export const photoService = {
  uploadSelfie: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload-selfie', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  uploadPhoto: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/upload-photo', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  getMyPhotos: () => api.get('/my-photos'),
  getAllPhotos: () => api.get('/all-photos'),
  getProfile: () => api.get('/profile'),
  getImage: (filename: string) => `${API_BASE_URL}/image/${filename}`,
};

// Service admin
export const adminService = {
  getAllUsers: async (): Promise<User[]> => {
    const response = await api.get('/admin/users');
    return response.data;
  },

  getAllPhotos: async (): Promise<Photo[]> => {
    const response = await api.get('/admin/photos');
    return response.data;
  },
};

export default api; 