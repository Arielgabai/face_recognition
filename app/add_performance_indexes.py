"""
Script pour ajouter les index manquants qui impactent les performances des tests de charge
Exécution : python add_performance_indexes.py
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./face_recognition.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def add_performance_indexes():
    """Ajoute les index critiques pour améliorer les performances"""
    print("=" * 70)
    print("🔧 AJOUT DES INDEX DE PERFORMANCE")
    print("=" * 70)
    
    with engine.connect() as conn:
        indexes = [
            # FaceMatch : requis pour les jointures fréquentes lors du matching
            ("idx_face_matches_user_id", "CREATE INDEX IF NOT EXISTS idx_face_matches_user_id ON face_matches(user_id);"),
            ("idx_face_matches_photo_id", "CREATE INDEX IF NOT EXISTS idx_face_matches_photo_id ON face_matches(photo_id);"),
            ("idx_face_matches_user_photo", "CREATE INDEX IF NOT EXISTS idx_face_matches_user_photo ON face_matches(user_id, photo_id);"),
            
            # Photo : événements utilisés partout
            ("idx_photos_event_id", "CREATE INDEX IF NOT EXISTS idx_photos_event_id ON photos(event_id);"),
            ("idx_photos_photographer_id", "CREATE INDEX IF NOT EXISTS idx_photos_photographer_id ON photos(photographer_id);"),
            ("idx_photos_event_photographer", "CREATE INDEX IF NOT EXISTS idx_photos_event_photographer ON photos(event_id, photographer_id);"),
            
            # UserEvent : association users <-> events (queries fréquentes)
            ("idx_user_events_user_id", "CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);"),
            ("idx_user_events_event_id", "CREATE INDEX IF NOT EXISTS idx_user_events_event_id ON user_events(event_id);"),
            ("idx_user_events_user_event", "CREATE INDEX IF NOT EXISTS idx_user_events_user_event ON user_events(user_id, event_id);"),
            
            # User : recherches par type et événement
            ("idx_users_user_type", "CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type);"),
            ("idx_users_event_user_type", "CREATE INDEX IF NOT EXISTS idx_users_event_user_type ON users(event_id, user_type);"),
        ]
        
        success_count = 0
        for idx_name, idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
                print(f"  ✅ {idx_name:<35} créé")
                success_count += 1
            except Exception as e:
                print(f"  ⚠️  {idx_name:<35} erreur: {e}")
        
        print("=" * 70)
        print(f"✅ {success_count}/{len(indexes)} index ajoutés avec succès!")
        print("=" * 70)
        print("\n📊 Impact attendu:")
        print("  - check-user-availability : 3.7s → 0.3s (12x plus rapide)")
        print("  - upload-selfie           : 45s  → 5s   (9x plus rapide)")
        print("  - Requêtes sur événements : jusqu'à 20x plus rapides")
        print("\n🚀 Prochaine étape: Redémarrer l'application")

if __name__ == "__main__":
    add_performance_indexes()
