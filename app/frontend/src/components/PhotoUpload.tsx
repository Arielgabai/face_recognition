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

interface PhotoUploadProps {
  onSuccess: () => void;
  eventId?: number; // Nouveau prop pour spécifier l'événement
}

const PhotoUpload: React.FC<PhotoUploadProps> = ({ onSuccess, eventId }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    
    if (imageFiles.length !== files.length) {
      setError('Certains fichiers ne sont pas des images et ont été ignorés');
    }
    
    if (imageFiles.length === 0) {
      setError('Veuillez sélectionner au moins une image');
      return;
    }
    
    setSelectedFiles(imageFiles);
    setError('');
    setSuccess('');
    
    // Créer des aperçus
    const newPreviews: string[] = [];
    imageFiles.forEach(file => {
      const reader = new FileReader();
      reader.onload = (e) => {
        newPreviews.push(e.target?.result as string);
        if (newPreviews.length === imageFiles.length) {
          setPreviews(newPreviews);
        }
      };
      reader.readAsDataURL(file);
    });
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError('Veuillez sélectionner au moins une image');
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    try {
      if (eventId) {
        // Upload vers un événement spécifique
        await photoService.uploadPhotoToEvent(selectedFiles, eventId);
      } else {
        // Upload normal (une seule photo)
        await photoService.uploadPhoto(selectedFiles[0]);
      }
      
      setSuccess(`${selectedFiles.length} photo(s) uploadée(s) et traitée(s) avec succès !`);
      setSelectedFiles([]);
      setPreviews([]);
      onSuccess();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'upload');
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Upload de photos
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {eventId 
          ? `Uploadez des photos pour cet événement qui seront analysées pour détecter les visages des utilisateurs`
          : 'Uploadez des photos qui seront analysées pour détecter les visages des utilisateurs'
        }
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
          id="photo-file"
          type="file"
          multiple={!!eventId} // Multiple files seulement pour les événements
          onChange={handleFileSelect}
        />
        <label htmlFor="photo-file">
          <Button
            variant="outlined"
            component="span"
            startIcon={<CloudUpload />}
            disabled={uploading}
          >
            {eventId ? 'Sélectionner des images' : 'Sélectionner une image'}
          </Button>
        </label>

        {previews.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" gutterBottom>
              {selectedFiles.length} image(s) sélectionnée(s):
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, justifyContent: 'center' }}>
              {previews.map((preview, index) => (
                <Box key={index} sx={{ textAlign: 'center' }}>
                  <img
                    src={preview}
                    alt={`Aperçu ${index + 1}`}
                    style={{
                      width: '100px',
                      height: '100px',
                      objectFit: 'cover',
                      borderRadius: '4px',
                    }}
                  />
                  <Typography variant="caption" display="block">
                    {selectedFiles[index]?.name}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Box>
        )}
      </Paper>

      {selectedFiles.length > 0 && (
        <Button
          variant="contained"
          onClick={handleUpload}
          disabled={uploading}
          fullWidth
        >
          {uploading ? (
            <>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              Upload et traitement en cours...
            </>
          ) : (
            `Uploader ${selectedFiles.length} photo(s)`
          )}
        </Button>
      )}
    </Box>
  );
};

export default PhotoUpload; 