from locust import HttpUser, task, between
from uuid import uuid4
import os
import time
import random
from pathlib import Path
import json
from urllib.parse import urlparse
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

# Charger la séquence HAR (ordre exact des appels /api/photo et event-expiration)
HAR_FILE = Path(__file__).parent / "session-utilisateur.har"
HAR_PHOTO_SEQUENCE = []

def load_har_photo_sequence():
    if not HAR_FILE.exists():
        print(f"[Locust] HAR introuvable: {HAR_FILE}")
        return []
    try:
        with open(HAR_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("log", {}).get("entries", [])
        seq = []
        seen_all_photos = False
        for e in entries:
            req = e.get("request", {})
            url = req.get("url", "") or ""
            if "/api/" not in url:
                continue
            path = urlparse(url).path
            if path == "/api/all-photos":
                seen_all_photos = True
                continue
            if not seen_all_photos:
                continue
            if path.startswith("/api/photo/"):
                seq.append("photo")
            elif path == "/api/user/event-expiration":
                seq.append("event-expiration")
        print(f"[Locust] HAR photo sequence loaded: {len(seq)} steps")
        return seq
    except Exception as e:
        print(f"[Locust] Erreur lecture HAR: {e}")
        return []

HAR_PHOTO_SEQUENCE = load_har_photo_sequence()

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

        # Step 3: validate selfie (pre-check, comme le front)
        try:
            with open(selected_photo, 'rb') as photo_file:
                files = {
                    'file': (selected_photo.name, photo_file, 'image/jpeg')
                }
                self.client.post(
                    "/api/validate-selfie",
                    files=files,
                    name="/api/validate-selfie"
                )
        except Exception as e:
            print(f"[Locust] Erreur validate-selfie pour {username}: {e}")

        # Step 4: re-check event code (second call in HAR)
        self.client.post(
            "/api/check-event-code",
            json={"event_code": "M01"},
            name="/api/check-event-code"
        )

        # Step 5: re-check availability (second call in HAR)
        self.client.post(
            "/api/check-user-availability",
            json={"username": username, "email": email, "event_code": "M01"},
            name="/api/check-user-availability"
        )

        # Step 6: register user
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

        # Step 7: login
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

        # Step 8: upload selfie avec la photo sélectionnée
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

        # Step 9: Simuler le comportement d'un utilisateur qui consulte ses photos
        # (comme s'il scrollait sur la page du dashboard)
        
        headers_auth = {'Authorization': f'Bearer {token}'}
        
        # 9.1 : Récupérer les photos matchées (Mes photos)
        try:
            my_photos_response = self.client.get(
                "/api/my-photos",
                headers=headers_auth,
                name="/api/my-photos"
            )
            if my_photos_response.status_code == 200:
                my_photos = my_photos_response.json()
                print(f"[Locust] {username} - {len(my_photos)} photos matchées récupérées")
        except Exception as e:
            print(f"[Locust] Erreur my-photos pour {username}: {e}")

        # 9.2 : Deuxième chargement Mes photos (comme dans le HAR)
        gevent.sleep(2.0)
        try:
            self.client.get(
                "/api/my-photos",
                headers=headers_auth,
                name="/api/my-photos"
            )
        except Exception as e:
            print(f"[Locust] Erreur my-photos (2) pour {username}: {e}")

        # 9.3 : provider + me
        try:
            self.client.get(
                "/api/admin/provider",
                headers=headers_auth,
                name="/api/admin/provider"
            )
        except Exception as e:
            print(f"[Locust] Erreur admin/provider pour {username}: {e}")

        try:
            self.client.get(
                "/api/me",
                headers=headers_auth,
                name="/api/me"
            )
        except Exception as e:
            print(f"[Locust] Erreur /api/me pour {username}: {e}")

        # 9.4 : Mes photos avec cache busting
        try:
            cb = int(time.time() * 1000)
            self.client.get(
                f"/api/my-photos?cb={cb}",
                headers=headers_auth,
                name="/api/my-photos?cb"
            )
        except Exception as e:
            print(f"[Locust] Erreur my-photos cb pour {username}: {e}")

        # 9.5 : Toutes les photos
        all_photos = []
        try:
            all_photos_response = self.client.get(
                "/api/all-photos",
                headers=headers_auth,
                name="/api/all-photos"
            )
            if all_photos_response.status_code == 200:
                all_photos = all_photos_response.json()
                print(f"[Locust] {username} - {len(all_photos)} photos totales récupérées")
        except Exception as e:
            print(f"[Locust] Erreur all-photos pour {username}: {e}")

        # 9.6 : Rejouer exactement l'ordre HAR pour /api/photo + event-expiration
        try:
            photo_pool_ids = []
            if isinstance(my_photos, list):
                for p in my_photos:
                    pid = p.get('id')
                    if pid:
                        photo_pool_ids.append(pid)
            if isinstance(all_photos, list):
                for p in all_photos:
                    pid = p.get('id')
                    if pid and pid not in photo_pool_ids:
                        photo_pool_ids.append(pid)

            if not HAR_PHOTO_SEQUENCE:
                print("[Locust] HAR photo sequence vide, skip replay")
            else:
                idx = 0
                for step in HAR_PHOTO_SEQUENCE:
                    if step == "event-expiration":
                        try:
                            self.client.get(
                                "/api/user/event-expiration",
                                headers=headers_auth,
                                name="/api/user/event-expiration"
                            )
                        except Exception as e:
                            print(f"[Locust] Erreur event-expiration pour {username}: {e}")
                        gevent.sleep(random.uniform(0.01, 0.05))
                        continue

                    if not photo_pool_ids:
                        break
                    pid = photo_pool_ids[idx % len(photo_pool_ids)]
                    idx += 1
                    try:
                        self.client.get(
                            f"/api/photo/{pid}",
                            headers=headers_auth,
                            name="/api/photo/[har]"
                        )
                    except Exception:
                        pass
                    gevent.sleep(random.uniform(0.01, 0.05))
        except Exception as e:
            print(f"[Locust] Erreur replay HAR photos pour {username}: {e}")
        
        # 👉 User a fini son scénario complet (création + consultation), on le "gèle"
        self.has_run = True
        gevent.sleep(999999)
