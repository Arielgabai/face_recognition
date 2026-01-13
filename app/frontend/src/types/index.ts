export interface User {
  id: number;
  username: string;
  email: string;
  user_type: 'user' | 'photographer';
  selfie_path?: string;
  is_active: boolean;
  created_at: string;
}

export interface Photo {
  id: number;
  filename: string;
  original_filename: string;
  file_path: string;
  photo_type: string;
  user_id?: number;
  photographer_id?: number;
  uploaded_at: string;
  has_face_match?: boolean;
  show_in_general?: boolean | null;
}

export interface FaceMatch {
  id: number;
  photo_id: number;
  user_id: number;
  confidence_score: number;
  detected_at: string;
}

export interface UserProfile {
  user: User;
  total_photos: number;
  photos_with_face: number;
}

export interface LoginCredentials {
  username: string;
  password: string;
  user_id?: number; // Pour se connecter à un compte spécifique quand plusieurs existent
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  user_type: 'user' | 'photographer';
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (credentials: LoginCredentials) => Promise<any>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
} 