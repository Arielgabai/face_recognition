import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"

def fix_photos_event():
    print("=== Correction Association Photos-Événement ===")
    
    # Connexion avec le photographe
    photog_credentials = {
        "username": "p1",
        "password": "mdp1"
    }
    
    try:
        # Connexion photographe
        response = requests.post(f"{BASE_URL}/api/login", json=photog_credentials)
        if response.status_code == 200:
            photog_data = response.json()
            photog_token = photog_data['access_token']
            photog_headers = {"Authorization": f"Bearer {photog_token}"}
            
            print("✅ Connexion photographe réussie")
            
            # Récupérer l'événement du photographe
            event_response = requests.get(f"{BASE_URL}/api/photographer/my-event", headers=photog_headers)
            if event_response.status_code == 200:
                event_info = event_response.json()
                event_id = event_info.get('id')
                event_name = event_info.get('name')
                print(f"Événement: {event_name} (ID: {event_id})")
                
                # Récupérer les photos du photographe
                photos_response = requests.get(f"{BASE_URL}/api/my-uploaded-photos", headers=photog_headers)
                if photos_response.status_code == 200:
                    photos = photos_response.json()
                    print(f"Photos trouvées: {len(photos)}")
                    
                    # Identifier les photos sans event_id
                    photos_without_event = [p for p in photos if p.get('event_id') is None]
                    print(f"Photos sans événement: {len(photos_without_event)}")
                    
                    if photos_without_event:
                        print("🔧 Correction nécessaire...")
                        print("Les photos suivantes n'ont pas d'événement associé:")
                        for photo in photos_without_event:
                            print(f"  - {photo['original_filename']} (ID: {photo['id']})")
                        
                        print("\n⚠️  Pour corriger cela, il faut:")
                        print("1. Mettre à jour la base de données directement")
                        print("2. Ou recréer les photos avec la bonne association")
                        print("3. Ou ajouter une route admin pour corriger les associations")
                        
                        return photos_without_event
                    else:
                        print("✅ Toutes les photos sont correctement associées à l'événement")
                else:
                    print(f"❌ Erreur pour récupérer les photos: {photos_response.status_code}")
            else:
                print(f"❌ Erreur pour récupérer l'événement: {event_response.status_code}")
            
        else:
            print("❌ Connexion photographe échouée")
            print(f"Réponse: {response.text}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    fix_photos_event() 