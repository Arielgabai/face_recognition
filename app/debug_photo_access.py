#!/usr/bin/env python3
"""
Script de débogage pour vérifier l'accès aux photos et selfies
"""

from sqlalchemy.orm import Session
from database import get_db, engine
from models import User, Photo, UserEvent
from sqlalchemy import text
import os

def debug_photo_access():
    """Vérifier l'état des photos et selfies dans la base de données"""
    
    print("🔍 Débogage de l'accès aux photos et selfies...")
    print("=" * 60)
    
    # Créer une session de base de données
    db = next(get_db())
    
    try:
        # 1. Vérifier les utilisateurs et leurs selfies
        print("\n📸 1. Vérification des utilisateurs et selfies:")
        users = db.query(User).all()
        print(f"   Total utilisateurs: {len(users)}")
        
        for user in users:
            has_selfie_data = user.selfie_data is not None
            has_selfie_path = user.selfie_path is not None
            print(f"   - User {user.id} ({user.username}): selfie_data={has_selfie_data}, selfie_path={has_selfie_path}")
        
        # 2. Vérifier les photos
        print("\n📷 2. Vérification des photos:")
        photos = db.query(Photo).all()
        print(f"   Total photos: {len(photos)}")
        
        photos_with_data = 0
        photos_with_path = 0
        
        for photo in photos:
            if photo.photo_data is not None:
                photos_with_data += 1
            if photo.file_path is not None:
                photos_with_path += 1
        
        print(f"   - Photos avec photo_data: {photos_with_data}")
        print(f"   - Photos avec file_path: {photos_with_path}")
        
        # 3. Vérifier les événements utilisateur
        print("\n🎯 3. Vérification des événements utilisateur:")
        user_events = db.query(UserEvent).all()
        print(f"   Total associations utilisateur-événement: {len(user_events)}")
        
        for user_event in user_events:
            user = db.query(User).filter(User.id == user_event.user_id).first()
            print(f"   - User {user_event.user_id} ({user.username if user else 'N/A'}) -> Event {user_event.event_id}")
        
        # 4. Vérifier les photos par événement
        print("\n📊 4. Vérification des photos par événement:")
        from sqlalchemy import func
        event_photos = db.query(Photo.event_id, func.count(Photo.id)).group_by(Photo.event_id).all()
        
        for event_id, count in event_photos:
            photos_with_data = db.query(Photo).filter(
                Photo.event_id == event_id,
                Photo.photo_data.isnot(None)
            ).count()
            print(f"   - Event {event_id}: {count} photos total, {photos_with_data} avec données binaires")
        
        # 5. Suggestions de résolution
        print("\n💡 5. Suggestions de résolution:")
        
        users_without_selfie = db.query(User).filter(User.selfie_data.is_(None)).count()
        if users_without_selfie > 0:
            print(f"   ⚠️  {users_without_selfie} utilisateur(s) sans selfie - ils doivent uploader une selfie")
        
        photos_without_data = db.query(Photo).filter(Photo.photo_data.is_(None)).count()
        if photos_without_data > 0:
            print(f"   ⚠️  {photos_without_data} photo(s) sans données binaires - migration nécessaire")
            print("   💡 Solution: Exécuter le script de migration des photos")
        
        if len(user_events) == 0:
            print("   ⚠️  Aucun utilisateur n'est associé à un événement")
            print("   💡 Solution: Les utilisateurs doivent rejoindre un événement")
        
        print("\n✅ Débogage terminé!")
        
    except Exception as e:
        print(f"❌ Erreur lors du débogage: {e}")
    finally:
        db.close()

def check_specific_user(user_id: int):
    """Vérifier un utilisateur spécifique"""
    print(f"\n🔍 Vérification détaillée pour l'utilisateur {user_id}:")
    
    db = next(get_db())
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"   ❌ Utilisateur {user_id} non trouvé")
            return
        
        print(f"   👤 Utilisateur: {user.username} ({user.email})")
        print(f"   📸 Selfie data: {'✅ Présent' if user.selfie_data else '❌ Absent'}")
        print(f"   📁 Selfie path: {user.selfie_path or 'Aucun'}")
        
        # Vérifier les événements de l'utilisateur
        user_events = db.query(UserEvent).filter(UserEvent.user_id == user_id).all()
        print(f"   🎯 Événements associés: {len(user_events)}")
        
        for user_event in user_events:
            photos = db.query(Photo).filter(Photo.event_id == user_event.event_id).all()
            photos_with_data = [p for p in photos if p.photo_data is not None]
            print(f"     - Event {user_event.event_id}: {len(photos)} photos total, {len(photos_with_data)} avec données")
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_photo_access()
    
    # Optionnel: vérifier un utilisateur spécifique
    # check_specific_user(1)  # Décommentez et changez l'ID si nécessaire 