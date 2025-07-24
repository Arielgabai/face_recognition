import requests
import json

# Configuration
BASE_URL = "https://facerecognition-d0r8.onrender.com"

def test_user_synchronization():
    print("=== Test Synchronisation Utilisateur ===")
    
    # 1. Se connecter en admin pour lister les utilisateurs et événements
    print("\n1. Connexion admin et liste des données")
    admin_credentials = {
        "username": "admin",  # Remplacer par vos identifiants admin
        "password": "admin123"  # Remplacer par votre mot de passe admin
    }
    
    try:
        # Connexion admin
        response = requests.post(f"{BASE_URL}/api/login", json=admin_credentials)
        if response.status_code == 200:
            admin_data = response.json()
            admin_token = admin_data['access_token']
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            
            print("✅ Connexion admin réussie")
            
            # Lister les événements
            events_response = requests.get(f"{BASE_URL}/api/admin/events", headers=admin_headers)
            if events_response.status_code == 200:
                events = events_response.json()
                print(f"\n🎉 Événements ({len(events)}):")
                for event in events:
                    print(f"  - {event['name']} (Code: {event['event_code']}) - ID: {event['id']} - Photographe ID: {event['photographer_id']}")
                    
                    # Lister les photos de cet événement
                    photos_response = requests.get(f"{BASE_URL}/api/all-photos", headers=admin_headers)
                    if photos_response.status_code == 200:
                        all_photos = photos_response.json()
                        event_photos = [p for p in all_photos if p.get('event_id') == event['id']]
                        print(f"    📸 Photos de l'événement: {len(event_photos)}")
                        for photo in event_photos:
                            print(f"      - {photo['original_filename']} (ID: {photo['id']})")
            else:
                print(f"❌ Erreur pour récupérer les événements: {events_response.status_code}")
            
        else:
            print("❌ Connexion admin échouée")
            print(f"Réponse: {response.text}")
            print("Continuing with user test...")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        print("Continuing with user test...")
    
    # 2. Tester avec un utilisateur créé via QR code
    print("\n2. Test avec un utilisateur créé via QR code")
    
    # Essayer de se connecter avec un utilisateur existant
    user_credentials = {
        "username": "test",  # Utiliser l'utilisateur test
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
                
                # Tester les routes photos
                print("\n📸 Test des routes photos:")
                
                # Test /api/my-photos
                my_photos_response = requests.get(f"{BASE_URL}/api/my-photos", headers=user_headers)
                print(f"  /api/my-photos: {my_photos_response.status_code}")
                if my_photos_response.ok:
                    my_photos = my_photos_response.json()
                    print(f"    Photos où l'utilisateur est reconnu: {len(my_photos)}")
                    for photo in my_photos:
                        print(f"      - {photo['original_filename']} (ID: {photo['id']}) - Event ID: {photo.get('event_id')}")
                else:
                    print(f"    Erreur: {my_photos_response.text}")
                
                # Test /api/all-photos
                all_photos_response = requests.get(f"{BASE_URL}/api/all-photos", headers=user_headers)
                print(f"  /api/all-photos: {all_photos_response.status_code}")
                if all_photos_response.ok:
                    all_photos = all_photos_response.json()
                    print(f"    Toutes les photos de l'événement: {len(all_photos)}")
                    for photo in all_photos:
                        print(f"      - {photo['original_filename']} (ID: {photo['id']}) - Event ID: {photo.get('event_id')}")
                else:
                    print(f"    Erreur: {all_photos_response.text}")
                
                # Test /api/my-selfie
                selfie_response = requests.get(f"{BASE_URL}/api/my-selfie", headers=user_headers)
                print(f"  /api/my-selfie: {selfie_response.status_code}")
                if selfie_response.ok:
                    selfie_info = selfie_response.json()
                    print(f"    Selfie: {selfie_info.get('filename')}")
                else:
                    print(f"    Erreur: {selfie_response.text}")
                
            else:
                print(f"❌ Erreur pour récupérer les infos utilisateur: {me_response.status_code}")
            
        else:
            print("❌ Connexion utilisateur échouée")
            print(f"Réponse: {response.text}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    test_user_synchronization() 