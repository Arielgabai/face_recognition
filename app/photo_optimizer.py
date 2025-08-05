"""
Module d'optimisation des photos pour une gestion efficace du stockage.

Ce module fournit des fonctionnalités pour :
- Compression intelligente des images
- Gestion de la rétention des photos
- Calcul des statistiques d'optimisation
- Nettoyage automatique des photos expirées
"""

import io
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, BinaryIO
from PIL import Image, ImageOps
import logging

logger = logging.getLogger(__name__)

class PhotoOptimizer:
    """
    Gestionnaire d'optimisation des photos avec compression et rétention.
    """
    
    # Configuration par défaut
    DEFAULT_QUALITY = 85
    DEFAULT_RETENTION_DAYS = 365
    MAX_WIDTH = 1920
    MAX_HEIGHT = 1080
    
    # Profils de qualité
    QUALITY_PROFILES = {
        'low': {'quality': 60, 'max_size': (1280, 720)},
        'medium': {'quality': 75, 'max_size': (1600, 900)},
        'high': {'quality': 85, 'max_size': (1920, 1080)},
        'ultra': {'quality': 95, 'max_size': (2560, 1440)}
    }
    
    @classmethod
    def optimize_image(
        cls, 
        image_data: bytes, 
        photo_type: str = 'uploaded',
        quality_profile: str = 'high',
        retention_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Optimise une image en la compressant et en calculant les métadonnées.
        
        Args:
            image_data: Données binaires de l'image
            photo_type: Type de photo ('uploaded', 'selfie', etc.)
            quality_profile: Profil de qualité ('low', 'medium', 'high', 'ultra')
            retention_days: Durée de rétention personnalisée
            
        Returns:
            Dict contenant les données optimisées et métadonnées
        """
        try:
            # Charger l'image
            original_image = Image.open(io.BytesIO(image_data))
            original_size = len(image_data)
            
            # Corriger l'orientation EXIF
            original_image = ImageOps.exif_transpose(original_image)
            
            # Convertir en RGB si nécessaire
            if original_image.mode in ('RGBA', 'LA', 'P'):
                # Créer un fond blanc pour les images avec transparence
                background = Image.new('RGB', original_image.size, (255, 255, 255))
                if original_image.mode == 'P':
                    original_image = original_image.convert('RGBA')
                background.paste(original_image, mask=original_image.split()[-1] if original_image.mode in ('RGBA', 'LA') else None)
                original_image = background
            elif original_image.mode != 'RGB':
                original_image = original_image.convert('RGB')
            
            # Obtenir le profil de qualité
            profile = cls.QUALITY_PROFILES.get(quality_profile, cls.QUALITY_PROFILES['high'])
            quality = profile['quality']
            max_size = profile['max_size']
            
            # Redimensionner si nécessaire
            optimized_image = cls._resize_image(original_image, max_size)
            
            # Compresser l'image
            output_buffer = io.BytesIO()
            optimized_image.save(
                output_buffer,
                format='JPEG',
                quality=quality,
                optimize=True,
                progressive=True
            )
            
            compressed_data = output_buffer.getvalue()
            compressed_size = len(compressed_data)
            
            # Calculer le ratio de compression
            compression_ratio = round((1 - compressed_size / original_size) * 100, 2) if original_size > 0 else 0
            
            # Calculer la date d'expiration
            retention = retention_days or cls._get_retention_days(photo_type)
            expires_at = datetime.utcnow() + timedelta(days=retention)
            
            return {
                'compressed_data': compressed_data,
                'content_type': 'image/jpeg',
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': compression_ratio,
                'quality_level': quality,
                'retention_days': retention,
                'expires_at': expires_at,
                'profile_used': quality_profile
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de l'image: {e}")
            # En cas d'erreur, retourner l'image originale
            return {
                'compressed_data': image_data,
                'content_type': 'image/jpeg',
                'original_size': len(image_data),
                'compressed_size': len(image_data),
                'compression_ratio': 0,
                'quality_level': cls.DEFAULT_QUALITY,
                'retention_days': retention_days or cls.DEFAULT_RETENTION_DAYS,
                'expires_at': datetime.utcnow() + timedelta(days=retention_days or cls.DEFAULT_RETENTION_DAYS),
                'profile_used': 'fallback'
            }
    
    @classmethod
    def _resize_image(cls, image: Image.Image, max_size: tuple) -> Image.Image:
        """
        Redimensionne une image en préservant le ratio d'aspect.
        """
        original_width, original_height = image.size
        max_width, max_height = max_size
        
        # Calculer le ratio de redimensionnement
        width_ratio = max_width / original_width
        height_ratio = max_height / original_height
        resize_ratio = min(width_ratio, height_ratio, 1.0)  # Ne jamais agrandir
        
        if resize_ratio < 1.0:
            new_width = int(original_width * resize_ratio)
            new_height = int(original_height * resize_ratio)
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    @classmethod
    def _get_retention_days(cls, photo_type: str) -> int:
        """
        Détermine la durée de rétention selon le type de photo.
        """
        retention_mapping = {
            'uploaded': 365,    # 1 an pour les photos uploadées
            'selfie': 180,      # 6 mois pour les selfies
            'processed': 90,    # 3 mois pour les photos traitées
            'temporary': 7      # 1 semaine pour les temporaires
        }
        return retention_mapping.get(photo_type, cls.DEFAULT_RETENTION_DAYS)
    
    @classmethod
    def calculate_storage_savings(cls, photos_data: list) -> Dict[str, Any]:
        """
        Calcule les économies de stockage réalisées.
        """
        total_original = sum(photo.get('original_size', 0) for photo in photos_data)
        total_compressed = sum(photo.get('compressed_size', 0) for photo in photos_data)
        
        if total_original == 0:
            return {
                'total_photos': 0,
                'original_size_mb': 0,
                'compressed_size_mb': 0,
                'space_saved_mb': 0,
                'average_compression_ratio': 0
            }
        
        space_saved = total_original - total_compressed
        average_ratio = round((space_saved / total_original) * 100, 2)
        
        return {
            'total_photos': len(photos_data),
            'original_size_mb': round(total_original / (1024 * 1024), 2),
            'compressed_size_mb': round(total_compressed / (1024 * 1024), 2),
            'space_saved_mb': round(space_saved / (1024 * 1024), 2),
            'average_compression_ratio': average_ratio
        }
    
    @classmethod
    def get_expired_photos_count(cls, photos_data: list) -> int:
        """
        Compte le nombre de photos expirées.
        """
        now = datetime.utcnow()
        return sum(1 for photo in photos_data 
                  if photo.get('expires_at') and photo['expires_at'] < now)
    
    @classmethod
    def estimate_compression(cls, file_size: int, quality_profile: str = 'high') -> Dict[str, Any]:
        """
        Estime la compression pour une taille de fichier donnée.
        """
        profile = cls.QUALITY_PROFILES.get(quality_profile, cls.QUALITY_PROFILES['high'])
        
        # Estimation basée sur des moyennes observées
        estimated_ratios = {
            'low': 0.75,    # 75% de compression
            'medium': 0.65, # 65% de compression  
            'high': 0.55,   # 55% de compression
            'ultra': 0.35   # 35% de compression
        }
        
        ratio = estimated_ratios.get(quality_profile, 0.55)
        estimated_size = int(file_size * (1 - ratio))
        space_saved = file_size - estimated_size
        
        return {
            'original_size': file_size,
            'estimated_compressed_size': estimated_size,
            'estimated_space_saved': space_saved,
            'estimated_compression_ratio': round(ratio * 100, 2),
            'quality_profile': quality_profile
        }