# Guide de démarrage rapide du Local Watcher

## ⚠️ IMPORTANT : Le watcher doit tourner EN LOCAL sur ton PC

Le **local watcher** est un script Python qui doit **tourner sur le PC qui a accès aux dossiers photos locaux**.  
Il ne tourne **PAS** dans le serveur Docker (backend) - c'est un client séparé.

## Pourquoi ça ne marche pas ?

Si tu crées des watchers dans l'admin mais que "rien ne se passe" quand tu ajoutes des photos :
- ➡️ C'est parce que le script `local_watcher.py` **n'est pas lancé** sur ton PC
- ➡️ Le serveur backend (Docker) ne peut pas accéder aux dossiers locaux de ton PC Windows

## Comment démarrer le watcher

### Méthode 1 : Script PowerShell (recommandé)

1. **Édite** `start_watcher.ps1` et configure :
   - `API_BASE_URL` : URL de ton serveur (ex: `https://facerecognition-d0r8.onrender.com`)
   - `MACHINE_LABEL` : doit **correspondre exactement** à celui configuré dans l'admin (ex: `ADMIN-PC-P1`)
   - `PHOTOGRAPHER_USERNAME` et `PHOTOGRAPHER_PASSWORD` : tes identifiants admin

2. **Lance** le script dans PowerShell :
   ```powershell
   cd C:\Users\agabai\Desktop\face_reco\face_recognition\app
   .\start_watcher.ps1
   ```

3. **Vérifie** que tu vois :
   ```
   [agent] LOCAL WATCHER STARTED in AGENT MODE
   [agent] machine_label=ADMIN-PC-P1
   [agent] ✓ Authentication successful
   [agent] Fetched X watcher(s)...
   [agent] ✓ STARTED watcher #... watching: C:\...
   ```

### Méthode 2 : Ligne de commande directe

```powershell
cd C:\Users\agabai\Desktop\face_reco\face_recognition\app

$env:API_BASE_URL="https://facerecognition-d0r8.onrender.com"
$env:MACHINE_LABEL="ADMIN-PC-P1"
$env:PHOTOGRAPHER_USERNAME="admin"
$env:PHOTOGRAPHER_PASSWORD="ton_mot_de_passe"

python local_watcher.py
```

## Vérification que ça fonctionne

Une fois lancé, tu dois voir dans la console :
- `[agent] Fetched X watcher(s)` toutes les 3 secondes
- `[agent] Watcher #XX: event=YY, listening=True, path=✓ EXISTS`
- `[agent] ✓ STARTED watcher #XX watching: C:\ton\dossier`

Quand tu ajoutes une photo dans un dossier surveillé, tu dois voir :
- `[detected] C:\...\photo.jpg`
- `[accept] ... | not duplicate, technical OK, faces=X ...`
- `[upload] -> photo.jpg ...`
- `[upload] <- ok: ...`

## Problèmes courants

### ❌ "Fetched 0 watcher(s)"
- Vérifie que `MACHINE_LABEL` est **exactement identique** à celui dans l'admin
- Vérifie que tu es bien authentifié (token valide)

### ❌ "path=✗ NOT FOUND"
- Le chemin `expected_path` configuré dans l'admin n'existe pas sur ce PC
- Vérifie l'orthographe exacte du chemin Windows (ex: `C:\ftp_drop\event2`)
- Vérifie les permissions d'accès au dossier

### ❌ Watcher démarre puis s'arrête immédiatement
- Regarde les logs pour voir `[agent] skip watcher #XX: path not found...`
- Corrige le `expected_path` dans l'admin pour qu'il corresponde au chemin réel sur ton PC

### ❌ Photo ajoutée mais rien ne se passe
- Vérifie que le fichier est bien `.jpg`, `.jpeg`, `.png` ou `.webp`
- Attends 2 secondes (stabilité du fichier)
- Si tu utilises FTP, le fichier peut être "déplacé" au lieu de "créé" → le patch `on_moved` devrait gérer ça maintenant
- Active le debug : `$env:WATCHER_DEBUG="1"` pour voir les rapports JSON détaillés

## Arrêter le watcher

Appuie sur **Ctrl+C** dans la console PowerShell.

## Lancer en arrière-plan (service)

Pour que le watcher tourne en permanence, tu peux :
- Utiliser **Task Scheduler** Windows (tâche au démarrage)
- Utiliser **NSSM** (Non-Sucking Service Manager) pour créer un service Windows
- Laisser la console PowerShell ouverte en permanence

