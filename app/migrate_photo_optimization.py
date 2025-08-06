#!/usr/bin/env python3
"""
Script de migration pour ajouter les colonnes d'optimisation photos
"""

import sqlite3
import os
from datetime import datetime, timedelta

DATABASE_PATH = 'app.db'

def migrate_photo_optimization():
    """Ajoute les nouvelles colonnes d'optimisation à la table photos"""
    
    print("🔄 Début de la migration pour l'optimisation photos...")
    
    if not os.path.exists(DATABASE_PATH):
        print(f"❌ Base de données {DATABASE_PATH} non trouvée")
        return False
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Vérifier si les colonnes existent déjà
        cursor.execute("PRAGMA table_info(photos)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            'original_size',
            'compressed_size', 
            'compression_ratio',
            'retention_days',
            'expires_at',
            'quality_level'
        ]
        
        # Ajouter les colonnes manquantes
        for column in new_columns:
            if column not in columns:
                print(f"📝 Ajout de la colonne '{column}'...")
                
                if column == 'original_size':
                    cursor.execute("ALTER TABLE photos ADD COLUMN original_size INTEGER")
                elif column == 'compressed_size':
                    cursor.execute("ALTER TABLE photos ADD COLUMN compressed_size INTEGER")
                elif column == 'compression_ratio':
                    cursor.execute("ALTER TABLE photos ADD COLUMN compression_ratio REAL")
                elif column == 'retention_days':
                    cursor.execute("ALTER TABLE photos ADD COLUMN retention_days INTEGER DEFAULT 30")
                elif column == 'expires_at':
                    cursor.execute("ALTER TABLE photos ADD COLUMN expires_at DATETIME")
                elif column == 'quality_level':
                    cursor.execute("ALTER TABLE photos ADD COLUMN quality_level VARCHAR(20) DEFAULT 'medium'")
                    
                print(f"✅ Colonne '{column}' ajoutée avec succès")
            else:
                print(f"⏭️ Colonne '{column}' existe déjà")
        
        # Mettre à jour les photos existantes avec des valeurs par défaut
        print("🔄 Mise à jour des photos existantes...")
        
        # Obtenir toutes les photos existantes
        cursor.execute("SELECT id, photo_data FROM photos WHERE original_size IS NULL")
        photos_to_update = cursor.fetchall()
        
        print(f"📊 {len(photos_to_update)} photos à mettre à jour")
        
        for photo_id, data in photos_to_update:
            if data:
                # Calculer la taille originale (taille des données binaires)
                original_size = len(data)
                
                # Calculer la date d'expiration (30 jours par défaut)
                expires_at = datetime.now() + timedelta(days=30)
                
                cursor.execute("""
                    UPDATE photos 
                    SET original_size = ?,
                        compressed_size = ?,
                        compression_ratio = 1.0,
                        retention_days = 30,
                        expires_at = ?,
                        quality_level = 'medium'
                    WHERE id = ?
                """, (original_size, original_size, expires_at, photo_id))
        
        conn.commit()
        print(f"✅ {len(photos_to_update)} photos mises à jour")
        
        # Vérifier le résultat
        cursor.execute("SELECT COUNT(*) FROM photos WHERE original_size IS NOT NULL")
        updated_count = cursor.fetchone()[0]
        
        print(f"📈 Total photos avec métadonnées d'optimisation : {updated_count}")
        
        conn.close()
        
        print("🎉 Migration terminée avec succès !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la migration : {e}")
        return False

if __name__ == "__main__":
    migrate_photo_optimization()