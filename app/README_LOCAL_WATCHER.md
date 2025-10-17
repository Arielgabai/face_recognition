Local Directory Watcher (FTP Drop → API Upload)

This small client watches a local folder and uploads any new image file to the server using the existing event upload endpoint.

Requirements
- Python 3.11+
- requests (already in requirements)
- watchdog (optional but recommended for real-time watching)

Install watchdog (optional):
```bash
pip install watchdog
```

Configuration (environment variables)
- API_BASE_URL: Server base URL (default `http://localhost:8000`)
- EVENT_ID: Target event ID (required)
- PHOTOGRAPHER_TOKEN: Bearer token (optional, preferred if you have it)
- PHOTOGRAPHER_USERNAME / PHOTOGRAPHER_PASSWORD: Credentials to obtain token (used if no token provided)
- WATCH_DIR: Directory to watch (required)
- MOVE_UPLOADED_DIR: Optional directory to move files after successful upload
- WATCHER_STABLE_SECONDS: Seconds to wait for file size to stabilize (default 2)

Run
Windows PowerShell example:
```powershell
$env:API_BASE_URL = "https://facerecognition-d0r8.onrender.com"
$env:EVENT_ID = "123"
$env:PHOTOGRAPHER_TOKEN = "<your_token>"  # or set USERNAME/PASSWORD
$env:WATCH_DIR = "C:\\ftp_drop"
$env:MOVE_UPLOADED_DIR = "C:\\ftp_drop\\uploaded"
python face_recognition/app/local_watcher.py
```

Linux/macOS example:
```bash
export API_BASE_URL="https://facerecognition-d0r8.onrender.com"
export EVENT_ID=123
export PHOTOGRAPHER_USERNAME="p1"
export PHOTOGRAPHER_PASSWORD="mdp1"
export WATCH_DIR="/srv/ftp_drop"
python face_recognition/app/local_watcher.py
```

The script maintains a `.uploaded_manifest.json` in the watch directory to avoid re-uploading the same files.



