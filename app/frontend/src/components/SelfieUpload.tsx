import React, { useState } from 'react';
import {
  Box,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Paper,
} from '@mui/material';
import { CloudUpload } from '@mui/icons-material';
import { photoService } from '../services/api';

interface SelfieUploadProps {
  onSuccess: () => Promise<void>;
}

const SelfieUpload: React.FC<SelfieUploadProps> = ({ onSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        setError('Veuillez sélectionner une image');
        return;
      }
      
      setSelectedFile(file);
      setError('');
      setSuccess('');
      
      // Créer un aperçu
      const reader = new FileReader();
      reader.onload = (e) => {
        setPreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Veuillez sélectionner une image');
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    try {
      await photoService.uploadSelfie(selectedFile);
      setSuccess('Selfie et photos mis à jour avec succès !');
      setSelectedFile(null);
      setPreview(null);
      // Attendre que le parent recharge les photos (Vos photos) avant d'arrêter le spinner
      await onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'upload');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Upload de votre selfie
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Uploadez une photo de votre visage pour que nous puissions vous reconnaître dans les photos
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

      <Paper
        sx={{
          p: 3,
          border: '2px dashed #ccc',
          textAlign: 'center',
          mb: 2,
        }}
      >
        <input
          accept="image/*"
          style={{ display: 'none' }}
          id="selfie-file"
          type="file"
          onChange={handleFileSelect}
        />
        <label htmlFor="selfie-file">
          <Button
            variant="outlined"
            component="span"
            startIcon={<CloudUpload />}
            disabled={uploading}
          >
            Sélectionner une image
          </Button>
        </label>

        {preview && (
          <Box sx={{ mt: 2 }}>
            <img
              src={preview}
              alt="Aperçu"
              style={{
                maxWidth: '200px',
                maxHeight: '200px',
                objectFit: 'cover',
              }}
            />
            <Typography variant="body2" sx={{ mt: 1 }}>
              {selectedFile?.name}
            </Typography>
          </Box>
        )}
      </Paper>

      {selectedFile && (
        <Button
          variant="contained"
          onClick={handleUpload}
          disabled={uploading}
          fullWidth
        >
          {uploading ? (
            <>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              Upload en cours...
            </>
          ) : (
            'Uploader le selfie'
          )}
        </Button>
      )}
    </Box>
  );
};

export default SelfieUpload; 