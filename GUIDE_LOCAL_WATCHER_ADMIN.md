# 🖥️ Guide d'utilisation - Local Watcher

## Qu'est-ce que le Local Watcher ?

Le `local_watcher.py` permet d'uploader automatiquement des photos vers un événement en surveillant un dossier local. Dès qu'une photo est ajoutée dans le dossier surveillé, elle est automatiquement uploadée.

## Modes d'utilisation

### Mode 1 : Agent (Multi-Watchers) - Recommandé

Dans ce mode, le script interroge régulièrement le serveur pour récupérer la liste des watchers actifs à surveiller.

**Avantages** :
- Gestion centralisée depuis l'interface admin
- Peut surveiller plusieurs dossiers simultanément
- Configuration dynamique (pas besoin de redémarrer le script)

**Configuration** :
```bash
export API_BASE_URL="https://votre-url.com"
export PHOTOGRAPHER_USERNAME="votre-username"
export PHOTOGRAPHER_PASSWORD="votre-password"
export MACHINE_LABEL="ADMIN-PC-P1"  # Identifiant unique de cette machine

python face_recognition/app/local_watcher.py
```

**Ce qui se passe** :
1. Le script se connecte au serveur
2. Il interroge `/api/admin/local-watchers?machine_label=ADMIN-PC-P1`
3. Le serveur renvoie la liste des watchers configurés pour cette machine
4. Le script surveille automatiquement ces dossiers

**Si vous voyez** :
```
INFO: GET /api/admin/local-watchers?machine_label=ADMIN-PC-P1 200 OK
```
...puis plus rien → **C'est normal !** Ça signifie qu'aucun watcher n'est configuré.

### Comment créer un watcher (Interface Admin)

1. **Connectez-vous à l'interface admin** : `https://votre-url.com/static/admin.html`
2. **Allez dans l'onglet "Local Watchers"**
3. **Remplissez le formulaire** :
   - **Événement** : Sélectionnez l'événement cible
   - **Label** : Nom descriptif (ex: "PC Bureau 1")
   - **Machine Label** : `ADMIN-PC-P1` (doit correspondre à ce que le script utilise)
   - **Expected Path** : `C:\Users\...\mon_dossier_photos` (chemin absolu)
   - **Move Uploaded Dir** (optionnel) : Dossier où déplacer les photos après upload
   - **Listening** : ✅ Coché (actif)
4. **Cliquez sur "Créer le watcher"**

Une fois créé, le script devrait afficher :
```
[agent] started watcher <id> on C:\Users\...\mon_dossier_photos
```

Et chaque fois qu'une photo est ajoutée dans ce dossier :
```
[detected] C:\Users\...\mon_dossier_photos\photo123.jpg (hash=abc12345...)
[upload] -> photo123.jpg ct=image/jpeg watcher_id=1
[upload] <- ok: {...}
```

### Mode 2 : Standalone (Single Watcher)

Pour surveiller un seul dossier sans passer par l'interface admin.

**Configuration** :
```bash
export API_BASE_URL="https://votre-url.com"
export PHOTOGRAPHER_USERNAME="votre-username"
export PHOTOGRAPHER_PASSWORD="votre-password"
export EVENT_ID="4"  # ID de l'événement
export WATCH_DIR="C:\Users\...\mon_dossier_photos"
export MOVE_UPLOADED_DIR="C:\Users\...\photos_uploadées"  # Optionnel

python face_recognition/app/local_watcher.py
```

**Ce qui se passe** :
1. Le script surveille immédiatement le dossier `WATCH_DIR`
2. Toute nouvelle photo est uploadée vers l'événement `EVENT_ID`
3. Si `MOVE_UPLOADED_DIR` est défini, les photos sont déplacées après upload

---

## 🔍 Dépannage

### Problème : "plus rien dans mon serveur"

**Cause** : Mode agent sans watcher configuré.

**Solution** : Créez un watcher via l'interface admin (voir ci-dessus).

### Problème : "watcher_id not found"

**Cause** : Le watcher a été supprimé ou désactivé.

**Solution** : Vérifiez dans l'interface admin que le watcher existe et est actif (`listening = true`).

### Problème : "path not found"

**Cause** : Le chemin `expected_path` n'existe pas sur la machine où tourne le script.

**Solution** : Vérifiez que le chemin est correct et que le dossier existe.

### Problème : "Upload failed: 403"

**Cause** : Le compte photographe n'a pas les droits sur cet événement.

**Solution** : Vérifiez que l'événement est bien assigné à ce photographe.

---

## 📊 Vérification

### Vérifier les watchers actifs (API)

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://votre-url.com/api/admin/local-watchers?machine_label=ADMIN-PC-P1"
```

Réponse attendue si aucun watcher :
```json
[]
```

Réponse avec watchers :
```json
[
  {
    "id": 1,
    "event_id": 4,
    "event_name": "Mon Mariage",
    "label": "PC Bureau 1",
    "machine_label": "ADMIN-PC-P1",
    "expected_path": "C:\\Users\\...\\photos",
    "listening": true,
    ...
  }
]
```

### Logs du script

Le script affiche des logs pour chaque action :
```
[agent] machine_label=ADMIN-PC-P1
[agent] started watcher 1 on C:\Users\...\photos
[detected] C:\Users\...\photos\IMG_001.jpg (hash=abc12345...)
[upload] -> IMG_001.jpg ct=image/jpeg watcher_id=1
[upload] <- ok: {"enqueued_jobs": [...]}
[moved] C:\Users\...\photos\IMG_001.jpg -> C:\Users\...\uploaded\IMG_001.jpg
```

---

## 💡 Cas d'usage

### Cas 1 : Studio photo avec dossier Dropbox

1. Configurer Dropbox pour synchroniser un dossier local
2. Créer un watcher pointant vers ce dossier
3. Le photographe exporte ses photos dans le dossier Dropbox
4. Le script upload automatiquement vers l'événement
5. Les photos sont déplacées vers un sous-dossier "uploaded"

### Cas 2 : Événement en direct avec carte SD

1. Brancher une carte SD
2. Configurer un watcher pointant vers la carte SD
3. Copier les photos depuis l'appareil photo vers la carte
4. Upload automatique pendant que le photographe continue de shooter

### Cas 3 : Multi-événements

1. Créer plusieurs watchers (un par événement)
2. Chaque watcher surveille un dossier différent
3. Un seul script surveille tous les dossiers
4. Les photos vont automatiquement vers le bon événement

---

## 🎯 Bonnes pratiques

1. **Utilisez des chemins absolus** : Évite les problèmes de working directory
2. **Définissez MOVE_UPLOADED_DIR** : Évite de réuploader les mêmes photos
3. **Un machine_label par machine** : Pour identifier facilement où tourne chaque script
4. **Testez d'abord en standalone** : Plus simple pour débugger
5. **Vérifiez les permissions** : Le script doit pouvoir lire le dossier surveillé

---

## 📝 Notes importantes

- Le script utilise un **manifest** (`.uploaded_manifest.json`) pour éviter les doublons basé sur le hash du fichier
- Même si vous renommez une photo, elle ne sera **pas** réuploadée (détection par contenu)
- Le script attend que le fichier soit **stable** (taille inchangée pendant 2 secondes) avant d'uploader
- Supporte **watchdog** pour la détection en temps réel, sinon scan périodique toutes les 2 secondes

---

## 🆘 Support

Si vous avez des problèmes :
1. Vérifiez les logs du script
2. Vérifiez les logs du serveur
3. Testez d'abord en mode standalone
4. Vérifiez que le compte a les droits sur l'événement
5. Vérifiez que le dossier existe et est accessible

