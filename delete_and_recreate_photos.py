import requests
import json
import os

# Configuration
BASE_URL = "http://localhost:8000"

def delete_and_recreate_photos():
    print("=== Suppression et Recréation des Photos ===")
    
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
                    print(f"Photos existantes: {len(photos)}")
                    
                    if photos:
                        print("\n🗑️  Suppression des photos existantes...")
                        
                        # Supprimer chaque photo
                        for photo in photos:
                            photo_id = photo['id']
                            delete_response = requests.delete(f"{BASE_URL}/api/photos/{photo_id}", headers=photog_headers)
                            if delete_response.status_code == 200:
                                print(f"  ✅ Photo {photo['original_filename']} supprimée")
                            else:
                                print(f"  ❌ Erreur suppression {photo['original_filename']}: {delete_response.status_code}")
                        
                        print("\n✅ Toutes les photos ont été supprimées")
                        print("\n📸 Maintenant, vous pouvez uploader de nouvelles photos via l'interface photographe")
                        print("   Les nouvelles photos seront automatiquement associées à l'événement")
                        
                        # Vérifier que les photos ont bien été supprimées
                        photos_after_response = requests.get(f"{BASE_URL}/api/my-uploaded-photos", headers=photog_headers)
                        if photos_after_response.status_code == 200:
                            photos_after = photos_after_response.json()
                            print(f"Photos restantes: {len(photos_after)}")
                            
                            if len(photos_after) == 0:
                                print("✅ Confirmation : Toutes les photos ont été supprimées")
                            else:
                                print("⚠️  Attention : Il reste des photos")
                    else:
                        print("✅ Aucune photo à supprimer")
                        print("📸 Vous pouvez directement uploader de nouvelles photos")
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
    delete_and_recreate_photos() 