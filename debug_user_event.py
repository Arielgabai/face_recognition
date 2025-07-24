import requests
import json

# Configuration
BASE_URL = "https://facerecognition-d0r8.onrender.com"

def debug_user_event():
    print("=== Debug Association Utilisateur-Événement ===")
    
    # Connexion avec l'utilisateur test
    user_credentials = {
        "username": "test",
        "password": "mdptest"
    }
    
    try:
        # Connexion utilisateur
        response = requests.post(f"{BASE_URL}/api/login", json=user_credentials)
        if response.status_code == 200:
            user_data = response.json()
            user_token = user_data['access_token']
            user_headers = {"Authorization": f"Bearer {user_token}"}
            
            print("✅ Connexion utilisateur réussie")
            
            # Récupérer les informations utilisateur
            me_response = requests.get(f"{BASE_URL}/api/me", headers=user_headers)
            if me_response.status_code == 200:
                user_info = me_response.json()
                print(f"User ID: {user_info.get('id')}")
                print(f"Username: {user_info.get('username')}")
                print(f"Email: {user_info.get('email')}")
                print(f"Type: {user_info.get('user_type')}")
                
                # Test direct de l'association UserEvent
                print("\n🔍 Test de l'association UserEvent:")
                
                # Essayer d'accéder aux photos pour voir l'erreur exacte
                print("\n📸 Test /api/my-photos:")
                my_photos_response = requests.get(f"{BASE_URL}/api/my-photos", headers=user_headers)
                print(f"  Status: {my_photos_response.status_code}")
                if my_photos_response.status_code == 404:
                    print(f"  Erreur: {my_photos_response.json().get('detail')}")
                elif my_photos_response.status_code == 200:
                    my_photos = my_photos_response.json()
                    print(f"  Photos trouvées: {len(my_photos)}")
                
                print("\n📸 Test /api/all-photos:")
                all_photos_response = requests.get(f"{BASE_URL}/api/all-photos", headers=user_headers)
                print(f"  Status: {all_photos_response.status_code}")
                if all_photos_response.status_code == 404:
                    print(f"  Erreur: {all_photos_response.json().get('detail')}")
                elif all_photos_response.status_code == 200:
                    all_photos = all_photos_response.json()
                    print(f"  Photos trouvées: {len(all_photos)}")
                
                # Test avec le photographe pour voir ses photos
                print("\n📸 Test avec le photographe:")
                photog_credentials = {
                    "username": "p1",
                    "password": "mdp1"
                }
                
                photog_response = requests.post(f"{BASE_URL}/api/login", json=photog_credentials)
                if photog_response.status_code == 200:
                    photog_data = photog_response.json()
                    photog_token = photog_data['access_token']
                    photog_headers = {"Authorization": f"Bearer {photog_token}"}
                    
                    # Test /api/my-uploaded-photos
                    photog_photos_response = requests.get(f"{BASE_URL}/api/my-uploaded-photos", headers=photog_headers)
                    print(f"  Photos du photographe: {photog_photos_response.status_code}")
                    if photog_photos_response.status_code == 200:
                        photog_photos = photog_photos_response.json()
                        print(f"    Nombre de photos: {len(photog_photos)}")
                        for photo in photog_photos:
                            print(f"      - {photo['original_filename']} (ID: {photo['id']}) - Event ID: {photo.get('event_id')}")
                    
                    # Test /api/photographer/my-event
                    event_response = requests.get(f"{BASE_URL}/api/photographer/my-event", headers=photog_headers)
                    print(f"  Événement du photographe: {event_response.status_code}")
                    if event_response.status_code == 200:
                        event_info = event_response.json()
                        print(f"    Événement: {event_info.get('name')} (ID: {event_info.get('id')})")
                
            else:
                print(f"❌ Erreur pour récupérer les infos utilisateur: {me_response.status_code}")
            
        else:
            print("❌ Connexion utilisateur échouée")
            print(f"Réponse: {response.text}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    debug_user_event() 