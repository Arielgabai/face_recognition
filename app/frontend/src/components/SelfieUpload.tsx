import React, { useState, useRef } from 'react';
import {
  Box,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Paper,
  Stack,
} from '@mui/material';
import { CameraAlt, PhotoLibrary } from '@mui/icons-material';
import { photoService } from '../services/api';

interface SelfieUploadProps {
  onSuccess: () => Promise<void>;
}

const MAX_DIM = 1920;
const JPEG_QUALITY = 0.8;
const COMPRESS_THRESHOLD = 3 * 1024 * 1024;
const MAX_RAW_SIZE = 20 * 1024 * 1024;

async function compressImage(file: File): Promise<File> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      try {
        let w = img.naturalWidth;
        let h = img.naturalHeight;
        if (w > MAX_DIM || h > MAX_DIM) {
          const ratio = Math.min(MAX_DIM / w, MAX_DIM / h);
          w = Math.round(w * ratio);
          h = Math.round(h * ratio);
        }
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        canvas.getContext('2d')!.drawImage(img, 0, 0, w, h);
        canvas.toBlob(
          (blob) => {
            if (!blob) { reject(new Error('Compression échouée')); return; }
            resolve(new File([blob], file.name.replace(/\.\w+$/, '.jpg'), {
              type: 'image/jpeg',
              lastModified: Date.now(),
            }));
          },
          'image/jpeg',
          JPEG_QUALITY,
        );
      } catch (e) { reject(e); }
    };
    img.onerror = () => reject(new Error('Impossible de lire l\'image'));
    img.src = URL.createObjectURL(file);
  });
}

const SelfieUpload: React.FC<SelfieUploadProps> = ({ onSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [info, setInfo] = useState('');
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setError('Veuillez sélectionner une image');
      return;
    }

    if (file.size > MAX_RAW_SIZE) {
      setError('Le fichier est trop volumineux (maximum 20 MB)');
      return;
    }

    setError('');
    setSuccess('');
    setInfo('');

    let fileToUse = file;
    if (file.size > COMPRESS_THRESHOLD) {
      try {
        setInfo('Compression de l\'image en cours...');
        fileToUse = await compressImage(file);
        const savedPct = Math.round((1 - fileToUse.size / file.size) * 100);
        setInfo(`Image compressée (${(fileToUse.size / 1024 / 1024).toFixed(1)} MB, -${savedPct}%)`);
      } catch {
        fileToUse = file;
        setInfo('');
      }
    }

    setSelectedFile(fileToUse);

    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target?.result as string);
    };
    reader.readAsDataURL(fileToUse);
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
      setInfo('');
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

      {info && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {info}
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
          capture="user"
          style={{ display: 'none' }}
          ref={cameraRef}
          type="file"
          onChange={handleFileSelect}
        />
        <input
          accept="image/*"
          style={{ display: 'none' }}
          ref={galleryRef}
          type="file"
          onChange={handleFileSelect}
        />
        <Stack direction="column" spacing={1} alignItems="center">
          <Button
            variant="contained"
            startIcon={<CameraAlt />}
            disabled={uploading}
            onClick={() => cameraRef.current?.click()}
          >
            Prendre une photo
          </Button>
          <Button
            variant="outlined"
            startIcon={<PhotoLibrary />}
            disabled={uploading}
            onClick={() => galleryRef.current?.click()}
          >
            Choisir depuis la galerie
          </Button>
        </Stack>

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