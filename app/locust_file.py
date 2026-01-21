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

                # 👉 catch_response=True pour pouvoir marquer success/failure avec un message détaillé
                with self.client.post(
                    "/api/upload-selfie",
                    files=files,
                    headers=headers,
                    name="/api/upload-selfie",
                    catch_response=True
                ) as upload_response:

                    if upload_response.status_code == 200:
                        # Facultatif : tu peux aussi regarder upload_response.json() ici
                        print(f"[Locust] ✓ Selfie uploadé avec succès pour {username}")
                        upload_response.success()
                    else:
                        # On log le body pour comprendre ce qui cloche
                        try:
                            body = upload_response.text
                        except Exception:
                            body = "<no body>"

                        msg = (f"[Locust] ✗ Upload selfie échoué pour {username}: "
                               f"status={upload_response.status_code}, body={body}")
                        print(msg)
                        upload_response.failure(msg)
                        self.has_run = True
                        gevent.sleep(999999)
                        return

        except Exception as e:
            # Si on a une vraie exception côté client (timeout, connexion, etc.)
            print(f"[Locust] Erreur lors de l'upload du selfie pour {username}: {e}")
            # Ici aussi, Locust marquera ce task en fail
            self.has_run = True
            gevent.sleep(999999)
            return

        # Step 6: Simuler le comportement d'un utilisateur qui consulte ses photos
        # (comme s'il scrollait sur la page du dashboard)
        
        # Attendre un peu (comme si l'utilisateur attendait le matching)
        gevent.sleep(random.uniform(2, 5))
        
        headers_auth = {'Authorization': f'Bearer {token}'}
        
        # 6.1 : Récupérer le profil utilisateur
        try:
            profile_response = self.client.get(
                "/api/profile",
                headers=headers_auth,
                name="/api/profile"
            )
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                photos_with_face = profile_data.get('photos_with_face', 0)
                print(f"[Locust] {username} - Profil chargé : {photos_with_face} photos matchées")
        except Exception as e:
            print(f"[Locust] Erreur profile pour {username}: {e}")
        
        # Attendre un peu (scroll)
        gevent.sleep(random.uniform(0.5, 1.5))
        
        # 6.2 : Récupérer les photos matchées (onglet "Mes photos")
        try:
            my_photos_response = self.client.get(
                "/api/my-photos",
                headers=headers_auth,
                name="/api/my-photos"
            )
            if my_photos_response.status_code == 200:
                my_photos = my_photos_response.json()
                print(f"[Locust] {username} - {len(my_photos)} photos matchées récupérées")
                
                # Charger quelques miniatures (simuler scroll/affichage)
                images_to_load = min(5, len(my_photos))  # Charger max 5 premières photos
                for i in range(images_to_load):
                    if my_photos[i].get('filename'):
                        try:
                            self.client.get(
                                f"/api/image/{my_photos[i]['filename']}",
                                headers=headers_auth,
                                name="/api/image/[matched]"
                            )
                        except Exception:
                            pass
                        # Petit délai entre chaque image (scroll naturel)
                        gevent.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            print(f"[Locust] Erreur my-photos pour {username}: {e}")
        
        # Attendre un peu (changement d'onglet)
        gevent.sleep(random.uniform(1, 2))
        
        # 6.3 : Récupérer toutes les photos de l'événement (onglet "Toutes les photos")
        try:
            all_photos_response = self.client.get(
                "/api/all-photos",
                headers=headers_auth,
                name="/api/all-photos"
            )
            if all_photos_response.status_code == 200:
                all_photos = all_photos_response.json()
                print(f"[Locust] {username} - {len(all_photos)} photos totales récupérées")
                
                # Charger quelques miniatures (simuler scroll)
                images_to_load = min(10, len(all_photos))  # Charger max 10 premières photos
                for i in range(images_to_load):
                    if all_photos[i].get('filename'):
                        try:
                            self.client.get(
                                f"/api/image/{all_photos[i]['filename']}",
                                headers=headers_auth,
                                name="/api/image/[all]"
                            )
                        except Exception:
                            pass
                        # Petit délai entre chaque image
                        gevent.sleep(random.uniform(0.1, 0.3))
        except Exception as e:
            print(f"[Locust] Erreur all-photos pour {username}: {e}")
        
        # 6.4 : Vérifier le statut du matching (polling comme ferait le frontend)
        for _ in range(3):  # 3 tentatives de polling
            gevent.sleep(random.uniform(2, 4))
            try:
                status_response = self.client.get(
                    "/api/rematch-status",
                    headers=headers_auth,
                    name="/api/rematch-status"
                )
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get('status') == 'done':
                        print(f"[Locust] ✓ Matching terminé pour {username} : {status_data.get('matched', 0)} matches")
                        break
            except Exception:
                pass

        # 👉 User a fini son scénario complet (création + consultation), on le "gèle"
        self.has_run = True
        gevent.sleep(999999)
