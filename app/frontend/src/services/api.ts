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

  uploadPhotoToEvent: (files: File[], eventId: number) => {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    return api.post(`/photographer/events/${eventId}/upload-photos`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  
  getMyPhotos: () => api.get('/my-photos'),
  getAllPhotos: () => api.get('/all-photos'),
  getProfile: () => api.get('/profile'),
  getImage: (filename: string) => `${API_BASE_URL}/image/${filename}`,

  // Nouvelles méthodes pour la gestion des événements
  getUserEvents: () => api.get('/user/events'),
  getPhotographerEvents: () => api.get('/photographer/events'),
  getEventPhotos: (eventId: number) => api.get(`/photographer/events/${eventId}/photos`),
  getUserEventPhotos: (eventId: number) => api.get(`/user/events/${eventId}/photos`),
  getAllEventPhotos: (eventId: number) => api.get(`/user/events/${eventId}/all-photos`),
  joinEvent: (eventCode: string) => api.post('/join-event', { event_code: eventCode }),
  registerWithEventCode: (userData: any, eventCode: string) => 
    api.post('/register-with-event-code', { user_data: userData, event_code: eventCode }),
};

// Validation / helpers
export const validationService = {
  checkUserAvailability: (payload: { username?: string; email?: string }) =>
    api.post('/check-user-availability', payload).then(r => r.data as { username_taken: boolean; email_taken: boolean }),
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