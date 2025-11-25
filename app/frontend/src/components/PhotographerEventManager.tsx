import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Chip,
  Grid,
  CardMedia,
} from '@mui/material';
import { useAuth } from '../contexts/AuthContext';
import { photoService, gdriveService } from '../services/api';
import { Photo } from '../types';
import PhotoUpload from './PhotoUpload';

interface Event {
  id: number;
  name: string;
  event_code: string;
  date: string;
  photographer_id: number;
}

interface PhotographerEventManagerProps {
  onEventChange: (eventId: number) => void;
  currentEventId?: number;
}

const PhotographerEventManager: React.FC<PhotographerEventManagerProps> = ({ 
  onEventChange, 
  currentEventId 
}) => {
  const { user } = useAuth();
  const [events, setEvents] = useState<Event[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<number | ''>('');
  const [eventPhotos, setEventPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [gConnectBusy, setGConnectBusy] = useState(false);
  const [gIntegrationId, setGIntegrationId] = useState<number | null>(null);
  const [gFolderId, setGFolderId] = useState<string>('');
  const [gSyncJob, setGSyncJob] = useState<{ id: string; status: string; processed: number; total: number; failed: number } | null>(null);

  useEffect(() => {
    loadEvents();
  }, []);

  useEffect(() => {
    if (currentEventId) {
      setSelectedEventId(currentEventId);
      loadEventPhotos(currentEventId);
    } else if (events.length > 0) {
      setSelectedEventId(events[0].id);
      onEventChange(events[0].id);
      loadEventPhotos(events[0].id);
    }
  }, [events, currentEventId, onEventChange]);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const response = await photoService.getPhotographerEvents();
      setEvents(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement des événements');
    } finally {
      setLoading(false);
    }
  };

  const loadEventPhotos = async (eventId: number) => {
    try {
      const response = await photoService.getEventPhotos(eventId);
      setEventPhotos(response.data);
      setSelectedIds([]);
    } catch (err: any) {
      console.error('Erreur lors du chargement des photos:', err);
    }
  };

  const handleEventChange = (eventId: number) => {
    setSelectedEventId(eventId);
    onEventChange(eventId);
    loadEventPhotos(eventId);
  };

  const handlePhotoUploadSuccess = () => {
    if (selectedEventId) {
      loadEventPhotos(selectedEventId);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={2}>
        <CircularProgress />
      </Box>
    );
  }

  if (events.length === 0) {
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Aucun événement assigné
          </Typography>
          <Typography color="text.secondary">
            Vous n'avez aucun événement assigné. Contactez l'administrateur.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Gérer vos événements
          </Typography>
          
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel>Événement</InputLabel>
            <Select
              value={selectedEventId}
              label="Événement"
              onChange={(e) => handleEventChange(e.target.value as number)}
            >
              {events.map((event) => (
                <MenuItem key={event.id} value={event.id}>
                  <Box>
                    <Typography variant="body1">{event.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      Code: {event.event_code} • {new Date(event.date).toLocaleDateString()}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {selectedEventId && (
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Événement sélectionné:
              </Typography>
              {events
                .filter((event) => event.id === selectedEventId)
                .map((event) => (
                  <Box key={event.id} display="flex" alignItems="center" gap={1}>
                    <Chip label={event.name} color="primary" />
                    <Typography variant="body2" color="text.secondary">
                      Code: {event.event_code}
                    </Typography>
                  </Box>
                ))}
            </Box>
          )}
        </CardContent>
      </Card>

      {selectedEventId && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Photos de l'événement ({eventPhotos.length})
            </Typography>
            {/* Google Drive */}
            <Box display="flex" gap={1} mb={2} alignItems="center" flexWrap="wrap">
              <Button
                variant="outlined"
                disabled={gConnectBusy}
                onClick={async () => {
                  try {
                    setGConnectBusy(true);
                    const r = await gdriveService.getConnectUrl();
                    const url = r.data?.auth_url;
                    if (url) {
                      window.open(url, '_blank');
                    }
                  } catch (e) {
                  } finally {
                    setGConnectBusy(false);
                  }
                }}
              >
                Connecter Google Drive
              </Button>
              <Button
                variant="outlined"
                onClick={async () => {
                  const code = prompt('Collez le code ?code=xxxx reçu en fin d’URL après consentement Google');
                  if (!code) return;
                  try {
                    const resp = await gdriveService.callback(code);
                    const integId = resp.data?.integration_id;
                    if (integId) setGIntegrationId(integId);
                  } catch (e) {}
                }}
              >
                Renseigner le code de callback
              </Button>
              <input
                placeholder="ID du dossier Google Drive"
                value={gFolderId}
                onChange={(e) => setGFolderId(e.target.value)}
                style={{ padding: 8, border: '1px solid #ccc', borderRadius: 4 }}
              />
              <Button
                variant="contained"
                disabled={!gIntegrationId || !gFolderId}
                onClick={async () => {
                  if (!gIntegrationId || !selectedEventId || !gFolderId) return;
                  try {
                    await gdriveService.linkFolder(gIntegrationId, selectedEventId, gFolderId);
                    alert('Dossier lié à l’événement.');
                  } catch (e) {}
                }}
              >
                Lier le dossier à l’événement
              </Button>
              <Button
                variant="contained"
                color="secondary"
                disabled={!gIntegrationId}
                onClick={async () => {
                  if (!gIntegrationId) return;
                  try {
                    const r = await gdriveService.syncNow(gIntegrationId);
                    const jobId = r.data?.job_id;
                    if (!jobId) return;
                    const poll = async () => {
                      try {
                        const st = await gdriveService.getJobStatus(jobId);
                        const d = st.data;
                        setGSyncJob({ id: jobId, status: d.status, processed: d.processed, total: d.total, failed: d.failed });
                        if (d.status === 'done' || d.status === 'error') {
                          await loadEventPhotos(selectedEventId);
                          return;
                        }
                      } catch {}
                      setTimeout(poll, 1500);
                    };
                    setTimeout(poll, 1500);
                  } catch (e) {}
                }}
              >
                Synchroniser maintenant
              </Button>
            </Box>
            {gSyncJob && (
              <Alert severity={gSyncJob.status === 'error' ? 'error' : 'info'} sx={{ mb: 2 }}>
                Drive job {gSyncJob.id}: {gSyncJob.processed}/{gSyncJob.total} • échecs: {gSyncJob.failed} • statut: {gSyncJob.status}
              </Alert>
            )}
            {eventPhotos.length > 0 && (
              <Box display="flex" gap={1} mb={2} flexWrap="wrap">
                <Button variant="outlined" onClick={() => setSelectedIds([])} disabled={bulkBusy}>Désélectionner</Button>
                <Button variant="outlined" onClick={() => setSelectedIds(eventPhotos.map(p => p.id))} disabled={bulkBusy}>Tout sélectionner</Button>
                
                <Button 
                  variant="contained" 
                  color="success"
                  disabled={bulkBusy || selectedIds.length === 0}
                  onClick={async () => {
                    if (!selectedEventId || selectedIds.length === 0) return;
                    if (!confirm(`Afficher ${selectedIds.length} photo(s) dans l'onglet "Général" ?`)) return;
                    try {
                      setBulkBusy(true);
                      await photoService.bulkTogglePhotosShowInGeneral(selectedIds, true);
                      await loadEventPhotos(selectedEventId);
                    } catch (e) {
                      console.error(e);
                    } finally {
                      setBulkBusy(false);
                    }
                  }}
                >
                  ✓ Afficher dans Général ({selectedIds.length})
                </Button>
                
                <Button 
                  variant="contained" 
                  color="warning"
                  disabled={bulkBusy || selectedIds.length === 0}
                  onClick={async () => {
                    if (!selectedEventId || selectedIds.length === 0) return;
                    if (!confirm(`Masquer ${selectedIds.length} photo(s) de l'onglet "Général" ?`)) return;
                    try {
                      setBulkBusy(true);
                      await photoService.bulkTogglePhotosShowInGeneral(selectedIds, false);
                      await loadEventPhotos(selectedEventId);
                    } catch (e) {
                      console.error(e);
                    } finally {
                      setBulkBusy(false);
                    }
                  }}
                >
                  ✗ Masquer de Général ({selectedIds.length})
                </Button>
                
                <Button 
                  variant="contained" 
                  color="error" 
                  disabled={bulkBusy || selectedIds.length === 0}
                  onClick={async () => {
                    if (!selectedEventId || selectedIds.length === 0) return;
                    if (!confirm(`Supprimer ${selectedIds.length} photo(s) ?`)) return;
                    try {
                      setBulkBusy(true);
                      await photoService.deletePhotosBulk(selectedIds);
                      await loadEventPhotos(selectedEventId);
                    } catch (e) {
                      console.error(e);
                    } finally {
                      setBulkBusy(false);
                    }
                  }}
                >
                  🗑 Supprimer ({selectedIds.length})
                </Button>
                
                <Button
                  variant="outlined"
                  size="small"
                  onClick={async () => {
                    if (!currentEventId) return;
                    try {
                      await photoService.rematchEventAsPhotographer(currentEventId);
                    } catch {}
                  }}
                >
                  Relancer le matching de l'événement
                </Button>
              </Box>
            )}
            
            {eventPhotos.length === 0 ? (
              <Typography color="text.secondary">
                Aucune photo uploadée pour cet événement.
              </Typography>
            ) : (
              <Grid container spacing={2}>
                {eventPhotos.map((photo) => {
                  const checked = selectedIds.includes(photo.id);
                  const showInGeneral = photo.show_in_general;
                  
                  return (
                    <Grid item xs={12} sm={6} md={4} key={photo.id}>
                      <Card sx={{ 
                        position: 'relative', 
                        outline: checked ? '3px solid #d32f2f' : 'none',
                        border: showInGeneral === true ? '2px solid #4caf50' : 
                                showInGeneral === false ? '2px solid #ff9800' : 'none'
                      }}>
                        {/* Badge pour indiquer si la photo est dans "Général" */}
                        {showInGeneral === true && (
                          <Chip
                            label="Visible dans Général"
                            size="small"
                            color="success"
                            sx={{
                              position: 'absolute',
                              top: 8,
                              right: 8,
                              zIndex: 1,
                              fontWeight: 'bold'
                            }}
                          />
                        )}
                        {showInGeneral === false && (
                          <Chip
                            label="Masqué de Général"
                            size="small"
                            color="warning"
                            sx={{
                              position: 'absolute',
                              top: 8,
                              right: 8,
                              zIndex: 1,
                              fontWeight: 'bold'
                            }}
                          />
                        )}
                        <CardMedia
                          component="img"
                          height="200"
                          image={photoService.getImage(photo.filename)}
                          alt={photo.original_filename}
                          onClick={() => {
                            setSelectedIds(prev => checked ? prev.filter(id => id !== photo.id) : [...prev, photo.id]);
                          }}
                          style={{ cursor: 'pointer' }}
                        />
                        <CardContent>
                          <Box display="flex" justifyContent="space-between" alignItems="center" flexDirection="column" gap={1}>
                            <Typography variant="body2" color="text.secondary" sx={{ width: '100%', textAlign: 'center' }}>
                              {photo.original_filename}
                            </Typography>
                            <Box display="flex" gap={1} width="100%">
                              <Button 
                                size="small" 
                                variant={checked ? "contained" : "outlined"}
                                onClick={() => {
                                  setSelectedIds(prev => checked ? prev.filter(id => id !== photo.id) : [...prev, photo.id]);
                                }}
                                fullWidth
                              >
                                {checked ? '✓ Sélectionné' : 'Sélectionner'}
                              </Button>
                            </Box>
                          </Box>
                        </CardContent>
                      </Card>
                    </Grid>
                  );
                })}
              </Grid>
            )}
          </CardContent>
        </Card>
      )}

      {selectedEventId && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Uploader des photos pour cet événement
            </Typography>
            <PhotoUpload onSuccess={handlePhotoUploadSuccess} eventId={selectedEventId} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              L’upload est traité en arrière-plan par sous-lots; les photos apparaissent au fur et à mesure.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default PhotographerEventManager; 