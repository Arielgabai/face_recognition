Local Directory Watcher (FTP Drop → API Upload)

This small client watches a local folder and uploads any new image file to the server using the existing event upload endpoint.

It now includes a **pre-upload filtering layer** to reduce upload costs:
- **Quality gate**: reject images that are too small, too blurry, or badly exposed.
- **Near-duplicate gate**: reject images that are too similar to already accepted/uploaded images using a **perceptual hash** (dHash) + **Hamming distance** against a persistent local manifest.

Important behavior:
- The decision is made immediately when a file arrives (no "hold" queue).
- The **first acceptable photo of a scene wins**; later similar photos are rejected and never uploaded.

Requirements
- Python 3.11+
- requests (already in requirements)
- watchdog (optional but recommended for real-time watching)
- Pillow (already in requirements)
- OpenCV (opencv-python / opencv-python-headless)

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

Filtering (optional overrides)
- MIN_WIDTH / MIN_HEIGHT: Minimum resolution (defaults 800x600)
- MIN_SHARPNESS: Minimum variance of Laplacian (default 100.0)
- MIN_BRIGHTNESS / MAX_BRIGHTNESS: Brightness range (default 30..220)
- SIMILARITY_THRESHOLD: Max Hamming distance between dHashes to be considered "too similar" (default 6)
- REJECTED_LOW_QUALITY_DIR: Optional folder to move rejected low-quality files into
- REJECTED_DUPLICATE_DIR: Optional folder to move rejected near-duplicate files into
- REJECTED_LOW_FACE_QUALITY_DIR: Optional folder to move rejected face-quality files into

Face-aware filtering (only when faces are detected)
- FACE_SCORE_MIN: Minimum acceptable face_score when faces exist (default 0.45)
- FACE_MIN_RELATIVE_SIZE: Minimum face box area / image area (default 0.03)
- MAX_FACE_ROLL_DEG: Max eye-line tilt before penalty (default 15)
- MIN_EYE_DISTANCE_RATIO / MAX_EYE_DISTANCE_RATIO: Expected eye distance / face width range (yaw proxy)
- MIN_EYE_Y_RATIO / MAX_EYE_Y_RATIO: Expected eye y-position / face height range (pitch proxy)

Debug (optional)
- WATCHER_DEBUG=1: writes a per-photo JSON report (decision + scores)
- WATCHER_DEBUG_DIR: directory to write reports (default: `<watch_dir>/.watcher_reports`)
- CLI alternative: `python face_recognition/app/local_watcher.py --debug --debug-dir C:\path\to\reports`

Notes:
- Rejected folders can be absolute paths or relative to the watched directory.
- The script stores accepted uploads in `.uploaded_manifest.json` (sha256 + dHash + metrics). Older manifests are automatically backfilled with dHash when possible.

Run
Windows PowerShell example:
```powershell
$env:API_BASE_URL = "https://facerecognition-d0r8.onrender.com"
$env:EVENT_ID = "123"
$env:PHOTOGRAPHER_TOKEN = "<your_token>"  # or set USERNAME/PASSWORD
$env:WATCH_DIR = "C:\\ftp_drop"
$env:MOVE_UPLOADED_DIR = "C:\\ftp_drop\\uploaded"
$env:REJECTED_LOW_QUALITY_DIR = "C:\\ftp_drop\\rejected_low_quality"
$env:REJECTED_DUPLICATE_DIR = "C:\\ftp_drop\\rejected_duplicate"
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



