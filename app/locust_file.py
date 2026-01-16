from locust import HttpUser, task, between
from uuid import uuid4
import os
import random
from pathlib import Path
import gevent  # 👈 ajouté pour pouvoir endormir le user très longtemps

# Charger les photos au démarrage du module
SELFIE_DIR = Path(__file__).parent / "photos_selfies_exemple"
SELFIE_PHOTOS = []

def load_selfie_photos(): 
    """Charge toutes les photos de selfie au démarrage"""
    global SELFIE_PHOTOS
    if SELFIE_DIR.exists():
        SELFIE_PHOTOS = [
            photo for photo in SELFIE_DIR.iterdir() 
            if photo.is_file() and photo.suffix.lower() in ['.jpg', '.jpeg', '.png']
        ]
        print(f"[Locust] {len(SELFIE_PHOTOS)} photos de selfie chargées depuis {SELFIE_DIR}")
    else:
        print(f"[Locust] ATTENTION: Le dossier {SELFIE_DIR} n'existe pas!")

# Charger les photos au démarrage
load_selfie_photos()

class RegisterUser(HttpUser):
    # wait_time ne sert plus vraiment, mais on le laisse
    wait_time = between(1, 2)

    def on_start(self):
        """
        Appelé au démarrage du user.
        On ajoute un flag pour savoir si ce user a déjà fait son scénario.
        """
        self.has_run = False

    @task
    def create_account(self):
        # 👉 IMPORTANT : si ce user a déjà fait le scénario, on le "parque"
        if self.has_run:
            # On endort ce user très longtemps pour qu'il ne refasse plus rien
            gevent.sleep(999999)
            return

        # Vérifier qu'on a des photos disponibles
        if not SELFIE_PHOTOS:
            print("[Locust] ERREUR: Aucune photo de selfie disponible!")
            # On considère que ce user a terminé, pour éviter de boucler en erreur
            self.has_run = True
            gevent.sleep(999999)
            return

        # Generate unique identifiers
        rand = uuid4().hex[:8]
        username = f"user_{rand}"
        email = f"{username}@test.com"
        password = "Secret.000"

        # Sélectionner une photo aléatoire
        selected_photo = random.choice(SELFIE_PHOTOS)
        print(f"[Locust] Utilisateur {username} utilisera la photo: {selected_photo.name}")

        # Step 1: check event code
        self.client.post(
            "/api/check-event-code",
            json={"event_code": "M01"},
            name="/api/check-event-code"
        )

        # Step 2: availability check
        self.client.post(
            "/api/check-user-availability",
            json={"username": username, "email": email, "event_code": "M01"},
            name="/api/check-user-availability"
        )

        # Step 3: register user
        response = self.client.post(
            "/api/register-with-event-code",
            json={
                "user_data": {
                    "username": username,
                    "email": email,
                    "password": password,
                    "user_type": "user"
                },
                "event_code": "M01"
            },
            name="/api/register-with-event-code"
        )

        # Vérifier que l'inscription a réussi
        if response.status_code != 200:
            print(f"[Locust] Inscription échouée pour {username}: {response.status_code}")
            self.has_run = True
            gevent.sleep(999999)
            return

        # Step 4: login
        login_response = self.client.post(
            "/api/login",
            json={"username": username, "password": password},
            name="/api/login"
        )

        # Vérifier que le login a réussi et récupérer le token
        if login_response.status_code != 200:
            print(f"[Locust] Login échoué pour {username}: {login_response.status_code}")
            self.has_run = True
            gevent.sleep(999999)
            return

        try:
            token = login_response.json().get("access_token")
            if not token:
                print(f"[Locust] Pas de token reçu pour {username}")
                self.has_run = True
                gevent.sleep(999999)
                return
        except Exception:
            print(f"[Locust] Erreur lors de la lecture du token pour {username}")
            self.has_run = True
            gevent.sleep(999999)
            return

        # Step 5: upload selfie avec la photo sélectionnée
        try:
            with open(selected_photo, 'rb') as photo_file:
                files = {
                    'file': (selected_photo.name, photo_file, 'image/jpeg')
                }
                headers = {
                    'Authorization': f'Bearer {token}'
                }
                
                upload_response = self.client.post(
                    "/api/upload-selfie",
                    files=files,
                    headers=headers,
                    name="/api/upload-selfie"
                )

                if upload_response.status_code == 200:
                    print(f"[Locust] ✓ Selfie uploadé avec succès pour {username}")
                else:
                    print(f"[Locust] ✗ Upload selfie échoué pour {username}: {upload_response.status_code}")
        except Exception as e:
            print(f"[Locust] Erreur lors de l'upload du selfie pour {username}: {e}")

        # 👉 A PARTIR D’ICI : ce user a fini son scénario, on le "gèle"
        self.has_run = True
        gevent.sleep(999999)
