import os
import time
import json
import threading
import hashlib
import math
import sys
import argparse
from typing import Optional, Dict, Any, Tuple

from PIL import Image, ImageStat, ImageFilter
import numpy as np
import cv2

import requests
import mimetypes

# Charger les variables d'environnement depuis .env.local
try:
    from dotenv import load_dotenv, dotenv_values
    
    # Fonction pour trouver .env.local intelligemment
    def find_env_file(filename):
        """Cherche le fichier .env dans plusieurs emplacements."""
        # 1. Répertoire courant
        if os.path.exists(filename):
            return filename
        
        # 2. Répertoire du script (face_recognition/app/)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(script_dir, filename)
        if os.path.exists(candidate):
            return candidate
        
        # 3. Deux niveaux au-dessus (racine du projet face_reco/)
        project_root = os.path.dirname(os.path.dirname(script_dir))
        candidate = os.path.join(project_root, filename)
        if os.path.exists(candidate):
            return candidate
        
        # 4. Un niveau au-dessus du script
        parent_dir = os.path.dirname(script_dir)
        candidate = os.path.join(parent_dir, filename)
        if os.path.exists(candidate):
            return candidate
        
        return None
    
    # Chercher .env.local puis .env
    env_file = find_env_file('.env.local') or find_env_file('.env')
    
    if env_file:
        # Charger et forcer l'override de TOUTES les variables du fichier
        env_vars = dotenv_values(env_file)
        for key, value in env_vars.items():
            if value is not None:  # Ne pas écraser avec des valeurs None
                os.environ[key] = value
        print(f"[config] ✓ Loaded configuration from {os.path.basename(env_file)} (path: {env_file})")
    else:
        print("[config] ⚠ No .env.local or .env file found, using system environment variables")
        
except ImportError:
    # python-dotenv pas installé, on continue avec les variables système
    print("[config] ⚠ python-dotenv not installed, using system environment variables")
    pass

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except Exception:
    # Fallback sans watchdog: simple boucle de scan
    WATCHDOG_AVAILABLE = False


DEFAULT_STABLE_SECONDS = int(os.environ.get("WATCHER_STABLE_SECONDS", "2") or "2")
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# -----------------------------
# Photo Selection Algorithm Toggle
# -----------------------------
# Set ENABLE_PHOTO_SELECTION=0 to disable the automatic photo selection algorithm
# and upload ALL photos without quality/duplicate filtering
ENABLE_PHOTO_SELECTION = (os.environ.get("ENABLE_PHOTO_SELECTION", "1").strip() or "1").lower() in {"1", "true", "yes", "y", "on"}

# Debug: afficher la valeur au démarrage pour vérification
if os.environ.get("WATCHER_DEBUG") or os.environ.get("WATCHER_AGENT_VERBOSE", "1") == "1":
    _raw_value = os.environ.get("ENABLE_PHOTO_SELECTION", "1")
    print(f"[config] ENABLE_PHOTO_SELECTION raw value: '{_raw_value}' → parsed as: {ENABLE_PHOTO_SELECTION}")

# -----------------------------
# Filtering configuration
# -----------------------------
# Quality thresholds (tweak as needed). You can also override via environment variables.
# Note: decision is made immediately when the file arrives (first acceptable photo "wins";
# later similar ones are rejected and never uploaded).
MIN_WIDTH = int(os.environ.get("MIN_WIDTH", "640"))  # Réduit de 800 à 640
MIN_HEIGHT = int(os.environ.get("MIN_HEIGHT", "480"))  # Réduit de 600 à 480
MIN_SHARPNESS = float(os.environ.get("MIN_SHARPNESS", "30.0"))  # Réduit de 100 à 30 (variance of Laplacian)
MIN_BRIGHTNESS = float(os.environ.get("MIN_BRIGHTNESS", "20.0"))  # Réduit de 30 à 20 (0..255 grayscale mean)
MAX_BRIGHTNESS = float(os.environ.get("MAX_BRIGHTNESS", "235.0"))  # Augmenté de 220 à 235 (0..255 grayscale mean)

# Similarity threshold: Hamming distance between perceptual hashes (dHash here).
# If distance <= SIMILARITY_THRESHOLD, the new image is considered a near-duplicate and is rejected.
SIMILARITY_THRESHOLD = int(os.environ.get("SIMILARITY_THRESHOLD", "8"))  # Augmenté de 6 à 8 (plus tolérant)

# Face-aware thresholds (applied only when a photo contains faces).
# Heuristic-based scoring using OpenCV Haar cascades (offline, lightweight).
FACE_SCORE_MIN = float(os.environ.get("FACE_SCORE_MIN", "0.35"))  # Réduit de 0.45 à 0.35 (plus tolérant)
FACE_MIN_RELATIVE_SIZE = float(os.environ.get("FACE_MIN_RELATIVE_SIZE", "0.02"))  # Réduit de 0.03 à 0.02
MAX_FACE_ROLL_DEG = float(os.environ.get("MAX_FACE_ROLL_DEG", "20.0"))  # Augmenté de 15 à 20 (proxy via eye line tilt)
MIN_EYE_DISTANCE_RATIO = float(os.environ.get("MIN_EYE_DISTANCE_RATIO", "0.20"))  # Réduit de 0.25 à 0.20 (eye_dist / face_width)
MAX_EYE_DISTANCE_RATIO = float(os.environ.get("MAX_EYE_DISTANCE_RATIO", "0.70"))  # Augmenté de 0.65 à 0.70 (eye_dist / face_width)
MIN_EYE_Y_RATIO = float(os.environ.get("MIN_EYE_Y_RATIO", "0.10"))  # Réduit de 0.15 à 0.10 (avg_eye_y / face_height)
MAX_EYE_Y_RATIO = float(os.environ.get("MAX_EYE_Y_RATIO", "0.60"))  # Augmenté de 0.55 à 0.60

# Debug (optional): set WATCHER_DEBUG=1 and optionally WATCHER_DEBUG_DIR.
WATCHER_DEBUG = (os.environ.get("WATCHER_DEBUG", "").strip() or "").lower() in {"1", "true", "yes", "y", "on"}
WATCHER_DEBUG_DIR = os.environ.get("WATCHER_DEBUG_DIR", "").strip() or None

# Agent diagnostics / logging behavior (verbose by default for easier debugging)
WATCHER_AGENT_VERBOSE = (os.environ.get("WATCHER_AGENT_VERBOSE", "1").strip() or "1").lower() in {"1", "true", "yes", "y", "on"}
WATCHER_LOG_ERRORS = (os.environ.get("WATCHER_LOG_ERRORS", "1").strip() or "1").lower() in {"1", "true", "yes", "y", "on"}

# Dossiers locaux pour déplacer les fichiers rejetés (créés automatiquement).
# Si un chemin relatif est fourni, il est relatif au répertoire surveillé.
# Vous pouvez désactiver en définissant la variable d'environnement à une chaîne vide.
REJECTED_DUPLICATE_DIR = os.environ.get("REJECTED_DUPLICATE_DIR", "").strip() or ".rejected_duplicates"
REJECTED_LOW_QUALITY_DIR = os.environ.get("REJECTED_LOW_QUALITY_DIR", "").strip() or ".rejected_low_quality"
REJECTED_LOW_FACE_QUALITY_DIR = os.environ.get("REJECTED_LOW_FACE_QUALITY_DIR", "").strip() or ".rejected_low_face_quality"


def is_image_file(path: str) -> bool:
    _, ext = os.path.splitext(path.lower())
    return ext in SUPPORTED_EXTENSIONS


def file_is_stable(path: str, stable_seconds: int = DEFAULT_STABLE_SECONDS) -> bool:
    try:
        size1 = os.path.getsize(path)
    except Exception:
        return False
    time.sleep(stable_seconds)
    try:
        size2 = os.path.getsize(path)
    except Exception:
        return False
    return size1 == size2


def compute_file_hash(path: str) -> Optional[str]:
    """Calcule le hash SHA256 du contenu du fichier."""
    try:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            # Lire par blocs pour économiser la mémoire sur gros fichiers
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        return sha256.hexdigest()
    except Exception:
        return None


def _resolve_target_dir(base_dir: str, maybe_dir: Optional[str]) -> Optional[str]:
    """Resolve a user-provided directory.

    - None/empty => None
    - Relative => relative to base_dir
    - Absolute => as-is
    """
    if not maybe_dir:
        return None
    d = maybe_dir.strip()
    if not d:
        return None
    return d if os.path.isabs(d) else os.path.join(base_dir, d)


def _safe_move(src: str, dest_dir: str, reason_tag: str) -> Optional[str]:
    """Move a file into dest_dir, de-conflicting name if needed. Returns dest path if moved."""
    try:
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, os.path.basename(src))
        base, ext = os.path.splitext(dest)
        i = 1
        while os.path.exists(dest):
            dest = f"{base}_{i}{ext}"
            i += 1
        os.replace(src, dest)
        print(f"[moved:{reason_tag}] {src} -> {dest}")
        return dest
    except Exception as e:
        print(f"[warn] move failed ({reason_tag}) for {src}: {e}")
        return None


def _dhash_hex(img: Image.Image, hash_size: int = 8) -> str:
    """Compute dHash (difference hash) as a hex string.

    dHash compares adjacent pixels after resizing to (hash_size+1, hash_size).
    For hash_size=8 => 64-bit hash => 16 hex chars.
    """
    # Convert to grayscale and resize
    try:
        resample = Image.Resampling.LANCZOS  # Pillow >= 9
    except Exception:
        resample = Image.LANCZOS  # type: ignore[attr-defined]

    g = img.convert("L").resize((hash_size + 1, hash_size), resample=resample)
    pixels = list(g.getdata())

    # Build bitstring row by row: left pixel > right pixel
    bits = 0
    bit_index = 0
    for row in range(hash_size):
        row_start = row * (hash_size + 1)
        for col in range(hash_size):
            left = pixels[row_start + col]
            right = pixels[row_start + col + 1]
            if left > right:
                bits |= (1 << (hash_size * hash_size - 1 - bit_index))
            bit_index += 1

    width_bits = hash_size * hash_size
    hex_len = (width_bits + 3) // 4
    return f"{bits:0{hex_len}x}"


def _hamming_distance_hex(a_hex: str, b_hex: str) -> Optional[int]:
    """Hamming distance between two hex-encoded bitstrings (same bit-width)."""
    try:
        ai = int(a_hex, 16)
        bi = int(b_hex, 16)
    except Exception:
        return None
    x = ai ^ bi
    try:
        return x.bit_count()  # Python 3.8+
    except Exception:
        # Fallback
        return bin(x).count("1")


def compute_image_features(path: str) -> Optional[Dict[str, Any]]:
    """Compute perceptual hash + basic quality metrics for an image file.

    Returns dict containing:
    - dhash: hex string (perceptual hash)
    - width, height
    - sharpness: variance of Laplacian (via PIL kernel)
    - brightness: grayscale mean
    """
    try:
        with Image.open(path) as im:
            im.load()
            width, height = im.size

            dhash = _dhash_hex(im)

            gray = im.convert("L")
            brightness = float(ImageStat.Stat(gray).mean[0])

            # Variance of Laplacian (sharpness proxy). Equivalent to OpenCV's var(Laplacian).
            lap_kernel = ImageFilter.Kernel(
                size=(3, 3),
                kernel=[0, 1, 0, 1, -4, 1, 0, 1, 0],
                scale=1,
                offset=0,
            )
            lap = gray.filter(lap_kernel)
            sharpness = float(ImageStat.Stat(lap).var[0])

            return {
                "dhash": dhash,
                "width": int(width),
                "height": int(height),
                "sharpness": sharpness,
                "brightness": brightness,
            }
    except Exception as e:
        print(f"[skip] cannot read image / compute features: {path} ({e})")
        return None


def quality_ok(features: Dict[str, Any]) -> Tuple[bool, str]:
    """Return (ok, reason)."""
    w = int(features.get("width", 0) or 0)
    h = int(features.get("height", 0) or 0)
    sharp = float(features.get("sharpness", 0.0) or 0.0)
    bright = float(features.get("brightness", 0.0) or 0.0)

    if w < MIN_WIDTH or h < MIN_HEIGHT:
        return False, f"resolution too low ({w}x{h} < {MIN_WIDTH}x{MIN_HEIGHT})"
    if sharp < MIN_SHARPNESS:
        return False, f"too blurry (sharpness={sharp:.2f} < {MIN_SHARPNESS})"
    if bright < MIN_BRIGHTNESS or bright > MAX_BRIGHTNESS:
        return False, f"bad exposure (brightness={bright:.1f} not in [{MIN_BRIGHTNESS}, {MAX_BRIGHTNESS}])"
    return True, "ok"


def technical_quality_score(features: Dict[str, Any]) -> Dict[str, Any]:
    """Compute a numeric technical quality score (0..1) + pass/fail using the existing thresholds.

    - This does NOT include face quality. Face logic is applied separately if faces exist.
    """
    w = int(features.get("width", 0) or 0)
    h = int(features.get("height", 0) or 0)
    sharp = float(features.get("sharpness", 0.0) or 0.0)
    bright = float(features.get("brightness", 0.0) or 0.0)

    ok, reason = quality_ok(features)

    # Resolution score: ratio vs minimum (cap at 1.0)
    res_ratio = 0.0
    if MIN_WIDTH > 0 and MIN_HEIGHT > 0:
        res_ratio = min(w / float(MIN_WIDTH), h / float(MIN_HEIGHT))
    res_score = max(0.0, min(1.0, res_ratio))

    # Sharpness score: scaled vs threshold (cap at 1.0)
    sharp_score = 0.0 if MIN_SHARPNESS <= 0 else max(0.0, min(1.0, sharp / float(MIN_SHARPNESS)))

    # Brightness score: 1.0 within range; otherwise degrade linearly by distance to range
    if MIN_BRIGHTNESS <= bright <= MAX_BRIGHTNESS:
        bright_score = 1.0
    else:
        if bright < MIN_BRIGHTNESS:
            dist = MIN_BRIGHTNESS - bright
        else:
            dist = bright - MAX_BRIGHTNESS
        # 40 is an arbitrary "full penalty" span; tweak if needed
        bright_score = max(0.0, 1.0 - (dist / 40.0))

    score = max(0.0, min(1.0, 0.35 * res_score + 0.45 * sharp_score + 0.20 * bright_score))
    return {
        "ok": bool(ok),
        "reason": reason,
        "score": float(score),
        "width": w,
        "height": h,
        "sharpness": sharp,
        "brightness": bright,
        "res_score": float(res_score),
        "sharp_score": float(sharp_score),
        "bright_score": float(bright_score),
    }


_FACE_CASCADE: Optional[cv2.CascadeClassifier] = None
_EYE_CASCADE: Optional[cv2.CascadeClassifier] = None


def _get_cascades() -> Tuple[cv2.CascadeClassifier, cv2.CascadeClassifier]:
    """Load Haar cascades (offline) once and reuse."""
    global _FACE_CASCADE, _EYE_CASCADE
    if _FACE_CASCADE is None:
        _FACE_CASCADE = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    if _EYE_CASCADE is None:
        _EYE_CASCADE = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_eye.xml"))
    return _FACE_CASCADE, _EYE_CASCADE


def _cv2_imread_unicode(path: str) -> Optional[np.ndarray]:
    """Robust cv2 image load for Windows/unicode paths."""
    try:
        data = np.fromfile(path, dtype=np.uint8)
        if data.size == 0:
            return None
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return img
    except Exception:
        # fallback to cv2.imread
        try:
            return cv2.imread(path, cv2.IMREAD_COLOR)
        except Exception:
            return None


def _range_score(x: float, lo: float, hi: float) -> float:
    """Score 1.0 inside [lo, hi], else decrease linearly to 0 as it moves away."""
    if lo <= x <= hi:
        return 1.0
    # scale by distance relative to interval size (avoid div by zero)
    span = max(1e-9, (hi - lo))
    if x < lo:
        d = (lo - x) / span
    else:
        d = (x - hi) / span
    return max(0.0, 1.0 - d)


def compute_face_metrics(path: str) -> Dict[str, Any]:
    """Face-aware evaluation (offline).

    Method (heuristic):
    - Detect faces with OpenCV Haar cascade (frontalface).
    - For each face ROI, detect eyes (haarcascade_eye).
    - Score each face by:
      - face size ratio (face_area / image_area) vs FACE_MIN_RELATIVE_SIZE
      - eye detection (2 eyes preferred)
      - roll proxy: eye-line tilt angle (prefer near 0, max MAX_FACE_ROLL_DEG)
      - crude yaw/pitch proxies via eye distance ratio and eye y-position ratio within the face ROI

    Output:
    - face_present: bool
    - num_faces: int
    - face_score: float (0..1) (best face wins)
    - faces: list of per-face details (for debug)
    """
    img = _cv2_imread_unicode(path)
    if img is None:
        return {"face_present": False, "num_faces": 0, "face_score": 0.0, "faces": [], "error": "cv2_imread_failed"}

    h_img, w_img = img.shape[:2]
    if w_img <= 0 or h_img <= 0:
        return {"face_present": False, "num_faces": 0, "face_score": 0.0, "faces": [], "error": "bad_dimensions"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade, eye_cascade = _get_cascades()

    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
    faces_list: list[Dict[str, Any]] = []
    best_score = 0.0

    # Gestion robuste du résultat de detectMultiScale (peut retourner None ou array vide)
    if faces is None or len(faces) == 0:
        faces_iter = []
    else:
        faces_iter = faces

    img_area = float(w_img * h_img)
    for (x, y, w, h) in faces_iter:
        face_area = float(w * h)
        rel = face_area / img_area if img_area > 0 else 0.0
        size_score = max(0.0, min(1.0, rel / max(1e-9, FACE_MIN_RELATIVE_SIZE)))

        roi_gray = gray[y : y + h, x : x + w]
        # Eyes are usually in the upper half; restrict ROI a bit to reduce false positives.
        roi_gray_eyes = roi_gray[0 : int(h * 0.65), :]

        # Eye minSize relative to face; helps for large images.
        eye_min = max(10, int(min(w, h) * 0.12))
        eyes = eye_cascade.detectMultiScale(roi_gray_eyes, scaleFactor=1.1, minNeighbors=8, minSize=(eye_min, eye_min))

        # Gestion robuste du résultat de detectMultiScale pour les yeux
        if eyes is None or len(eyes) == 0:
            eyes_iter = []
        else:
            eyes_iter = eyes

        # Pick up to 2 largest eyes (by area)
        eyes_sorted = sorted([(ex, ey, ew, eh) for (ex, ey, ew, eh) in eyes_iter], key=lambda t: t[2] * t[3], reverse=True)
        eyes_top = eyes_sorted[:2]
        eye_count = len(eyes_top)
        eye_count_score = 1.0 if eye_count >= 2 else (0.6 if eye_count == 1 else 0.0)

        roll_score = 0.0
        yaw_proxy_score = 0.0
        pitch_proxy_score = 0.0
        angle_deg: Optional[float] = None
        eye_dist_ratio: Optional[float] = None
        eye_y_ratio: Optional[float] = None

        if eye_count >= 2:
            # Eye centers in ROI coordinates
            (ex1, ey1, ew1, eh1), (ex2, ey2, ew2, eh2) = eyes_top[0], eyes_top[1]
            c1 = (ex1 + ew1 / 2.0, ey1 + eh1 / 2.0)
            c2 = (ex2 + ew2 / 2.0, ey2 + eh2 / 2.0)
            # Ensure left/right ordering for consistency
            if c2[0] < c1[0]:
                c1, c2 = c2, c1

            dx = c2[0] - c1[0]
            dy = c2[1] - c1[1]
            angle_deg = float(abs(math.degrees(math.atan2(dy, dx)))) if dx != 0 else 90.0
            roll_score = max(0.0, 1.0 - (angle_deg / max(1e-9, MAX_FACE_ROLL_DEG)))

            dist = math.sqrt(dx * dx + dy * dy)
            eye_dist_ratio = float(dist / max(1e-9, float(w)))
            yaw_proxy_score = _range_score(eye_dist_ratio, MIN_EYE_DISTANCE_RATIO, MAX_EYE_DISTANCE_RATIO)

            avg_eye_y = (c1[1] + c2[1]) / 2.0
            # Note: eyes ROI is clipped to 0..0.65*h, but we normalize by full face height for interpretability.
            eye_y_ratio = float(avg_eye_y / max(1e-9, float(h)))
            pitch_proxy_score = _range_score(eye_y_ratio, MIN_EYE_Y_RATIO, MAX_EYE_Y_RATIO)

        # Combine: emphasize eye evidence (frontal usability), but always require some size.
        face_score = float(
            max(0.0, min(1.0, math.sqrt(max(0.0, size_score))))
            * (0.40 * eye_count_score + 0.20 * roll_score + 0.20 * yaw_proxy_score + 0.20 * pitch_proxy_score)
        )

        faces_list.append(
            {
                "box": [int(x), int(y), int(w), int(h)],
                "relative_area": float(rel),
                "size_score": float(size_score),
                "eye_count": int(eye_count),
                "eye_count_score": float(eye_count_score),
                "roll_deg": angle_deg,
                "roll_score": float(roll_score),
                "eye_dist_ratio": eye_dist_ratio,
                "yaw_proxy_score": float(yaw_proxy_score),
                "eye_y_ratio": eye_y_ratio,
                "pitch_proxy_score": float(pitch_proxy_score),
                "face_score": float(face_score),
            }
        )
        best_score = max(best_score, face_score)

    return {
        "face_present": bool(len(faces_list) > 0),
        "num_faces": int(len(faces_list)),
        "face_score": float(best_score),
        "faces": faces_list,
    }


def _write_debug_report(report_dir: str, report: Dict[str, Any]) -> None:
    try:
        os.makedirs(report_dir, exist_ok=True)
    except Exception:
        return
    try:
        base = os.path.basename(str(report.get("path") or "photo"))
        safe = "".join([c if c.isalnum() or c in "._-" else "_" for c in base])
        sha = str(report.get("sha256") or "")
        suffix = sha[:8] if sha else str(int(time.time()))
        out = os.path.join(report_dir, f"{safe}.{suffix}.watcher_report.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception:
        return


class UploadClient:
    def __init__(self, base_url: str, username: Optional[str], password: Optional[str], token: Optional[str]) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self._username = username
        self._password = password
        self._token = token
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def login_if_needed(self) -> None:
        if "Authorization" in self.session.headers:
            return
        if not (self._username and self._password):
            raise RuntimeError("No token or credentials provided for authentication")
        # POST /api/login expects JSON { username, password }
        url = f"{self.base_url}/api/login"
        resp = self.session.post(url, json={"username": self._username, "password": self._password}, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"Login failed: {resp.status_code} {resp.text}")
        data = resp.json()
        tok = data.get("access_token")
        if not tok:
            raise RuntimeError("Login ok but access_token missing in response")
        self.session.headers.update({"Authorization": f"Bearer {tok}"})

    def upload_file_to_event(self, event_id: int, file_path: str, watcher_id: Optional[int] = None) -> None:
        self.login_if_needed()
        url = f"{self.base_url}/api/photographer/events/{event_id}/upload-photos"
        with open(file_path, "rb") as f:
            guessed, _ = mimetypes.guess_type(file_path)
            content_type = guessed if (guessed and guessed.startswith("image/")) else "image/jpeg"
            files = [("files", (os.path.basename(file_path), f, content_type))]
            data = {"watcher_id": watcher_id} if watcher_id is not None else None
            print(f"[upload] -> {os.path.basename(file_path)} ct={content_type} watcher_id={watcher_id}")
            resp = self.session.post(url, files=files, data=data, timeout=300)
        if not resp.ok:
            raise RuntimeError(f"Upload failed {os.path.basename(file_path)}: {resp.status_code} {resp.text}")
        try:
            data = resp.json()
            print(f"[upload] <- ok: {data}")
        except Exception:
            print(f"[upload] <- ok: status={resp.status_code}")


class Manifest:
    def __init__(self, manifest_path: str) -> None:
        self.path = manifest_path
        self._lock = threading.Lock()
        # Stocke sha256 -> metadata (includes perceptual hash used for similarity checks)
        self._seen: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Support ancien format (list de paths) et nouveau format (dict de hashs)
            uploaded = data.get("uploaded", [])
            if isinstance(uploaded, list):
                # Ancien format: convertir en dict vide (va se reconstruire au fur et à mesure)
                self._seen = {}
            else:
                # Nouveau format: dict {hash: {path, timestamp}}
                self._seen = uploaded
        except Exception:
            self._seen = {}

    def add(self, file_hash: str, absolute_path: str) -> None:
        with self._lock:
            self._seen[file_hash] = {
                "path": absolute_path,
                "timestamp": time.time(),
            }
            self._save()

    def add_with_features(self, file_hash: str, absolute_path: str, features: Dict[str, Any]) -> None:
        """Register an uploaded/accepted image with its perceptual hash + quality metadata."""
        with self._lock:
            self._seen[file_hash] = {
                "path": absolute_path,
                "timestamp": time.time(),
                "dhash": features.get("dhash"),
                "width": features.get("width"),
                "height": features.get("height"),
                "sharpness": features.get("sharpness"),
                "brightness": features.get("brightness"),
            }
            self._save()

    def contains(self, file_hash: str) -> bool:
        return file_hash in self._seen

    def find_similar(self, dhash_hex: str, threshold: int = SIMILARITY_THRESHOLD) -> Optional[Dict[str, Any]]:
        """Return the closest match (with distance) if within threshold, else None."""
        # Snapshot to avoid iterating while another thread writes.
        with self._lock:
            items = list((self._seen or {}).items())
        best: Optional[Dict[str, Any]] = None
        best_dist: Optional[int] = None
        for sha, meta in items:
            existing = meta.get("dhash")
            # Backfill perceptual hash for older manifest entries (sha256-only) when possible.
            if (not isinstance(existing, str) or not existing) and isinstance(meta.get("path"), str):
                p = str(meta.get("path"))
                if p and os.path.isfile(p):
                    feats = compute_image_features(p)
                    if feats and isinstance(feats.get("dhash"), str):
                        existing = str(feats.get("dhash"))
                        # Persist the backfill to speed up future checks.
                        try:
                            with self._lock:
                                cur = self._seen.get(sha, {})
                                if isinstance(cur, dict):
                                    cur.update(
                                        {
                                            "dhash": feats.get("dhash"),
                                            "width": feats.get("width"),
                                            "height": feats.get("height"),
                                            "sharpness": feats.get("sharpness"),
                                            "brightness": feats.get("brightness"),
                                        }
                                    )
                                    self._seen[sha] = cur
                                    self._save()
                        except Exception:
                            pass
            if not isinstance(existing, str) or not existing:
                continue
            d = _hamming_distance_hex(dhash_hex, existing)
            if d is None:
                continue
            if best_dist is None or d < best_dist:
                best_dist = d
                best = {
                    "sha256": sha,
                    "path": meta.get("path"),
                    "dhash": existing,
                    "distance": d,
                }
                # Can't do better than exact match
                if best_dist == 0:
                    break
        if best is not None and best_dist is not None and best_dist <= threshold:
            return best
        return None

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except Exception:
            pass
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"uploaded": self._seen}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def process_path(client: UploadClient, event_id: int, path: str, manifest: Manifest, move_uploaded_dir: Optional[str], watcher_id: Optional[int]) -> None:
    if not os.path.isfile(path) or not is_image_file(path):
        return
    abspath = os.path.abspath(path)
    base_dir = os.path.dirname(abspath)

    rejected_dup_dir = _resolve_target_dir(base_dir, REJECTED_DUPLICATE_DIR)
    rejected_lowq_dir = _resolve_target_dir(base_dir, REJECTED_LOW_QUALITY_DIR)
    rejected_lowface_dir = _resolve_target_dir(base_dir, REJECTED_LOW_FACE_QUALITY_DIR)
    debug_dir = _resolve_target_dir(base_dir, WATCHER_DEBUG_DIR) if WATCHER_DEBUG_DIR else None
    
    # Vérifier la stabilité du fichier avant de calculer le hash
    if not file_is_stable(abspath):
        print(f"[skip] not stable yet: {abspath}")
        return
    
    # Calculer le hash du contenu
    file_hash = compute_file_hash(abspath)
    if not file_hash:
        print(f"[skip] cannot compute hash: {abspath}")
        return
    
    # Vérifier si ce contenu a déjà été uploadé
    if manifest.contains(file_hash):
        print(f"[skip] already uploaded (hash={file_hash[:8]}...): {abspath}")
        return

    # --- Photo Selection Algorithm: can be disabled via ENABLE_PHOTO_SELECTION=0 ---
    if not ENABLE_PHOTO_SELECTION:
        # Selection algorithm disabled: upload all photos without filtering
        print(f"[accept:no-filter] {abspath} | selection algorithm disabled (ENABLE_PHOTO_SELECTION=0)")
        client.upload_file_to_event(event_id, abspath, watcher_id=watcher_id)
        manifest.add(file_hash, abspath)
        if move_uploaded_dir:
            try:
                os.makedirs(move_uploaded_dir, exist_ok=True)
                dest = os.path.join(move_uploaded_dir, os.path.basename(abspath))
                # If exists, add suffix
                base, ext = os.path.splitext(dest)
                i = 1
                while os.path.exists(dest):
                    dest = f"{base}_{i}{ext}"
                    i += 1
                os.replace(abspath, dest)
                print(f"[moved] {abspath} -> {dest}")
            except Exception:
                # keep file if move fails
                print(f"[warn] move failed for {abspath}")
        return

    # --- Filtering layer (quality + similarity) BEFORE uploading ---
    features = compute_image_features(abspath)
    if not features:
        # Can't evaluate -> treat as reject (avoid paying for uploads of unreadable images)
        print(f"[reject:low_quality] cannot compute features: {abspath}")
        if rejected_lowq_dir:
            _safe_move(abspath, rejected_lowq_dir, "low_quality")
        return

    tech = technical_quality_score(features)
    if not tech.get("ok"):
        print(
            f"[reject:technical] {abspath} | {tech.get('reason')} | "
            f"tech_score={float(tech.get('score') or 0.0):.2f} "
            f"sharpness={float(tech.get('sharpness') or 0.0):.2f} brightness={float(tech.get('brightness') or 0.0):.1f} "
            f"res={tech.get('width')}x{tech.get('height')} dhash={features.get('dhash')}"
        )
        if WATCHER_DEBUG and (debug_dir or True):
            _write_debug_report(debug_dir or os.path.join(base_dir, ".watcher_reports"), {
                "path": abspath,
                "sha256": file_hash,
                "dhash": features.get("dhash"),
                "decision": "rejected_low_quality_technical",
                "technical": tech,
            })
        if rejected_lowq_dir:
            _safe_move(abspath, rejected_lowq_dir, "technical")
        return

    similar = manifest.find_similar(str(features.get("dhash") or ""), threshold=SIMILARITY_THRESHOLD)
    if similar:
        print(
            f"[reject:duplicate] {abspath} | dist={similar.get('distance')} <= {SIMILARITY_THRESHOLD} "
            f"vs {similar.get('path')} (sha={str(similar.get('sha256'))[:8]}...) | "
            f"tech_score={float(tech.get('score') or 0.0):.2f}"
        )
        if WATCHER_DEBUG and (debug_dir or True):
            _write_debug_report(debug_dir or os.path.join(base_dir, ".watcher_reports"), {
                "path": abspath,
                "sha256": file_hash,
                "dhash": features.get("dhash"),
                "decision": "rejected_duplicate",
                "technical": tech,
                "duplicate": similar,
            })
        if rejected_dup_dir:
            _safe_move(abspath, rejected_dup_dir, "duplicate")
        return

    # Face-aware scoring (only for unique + technical OK images)
    face = compute_face_metrics(abspath)
    face_present = bool(face.get("face_present"))
    num_faces = int(face.get("num_faces") or 0)
    face_score = float(face.get("face_score") or 0.0)

    if face_present and face_score < FACE_SCORE_MIN:
        print(
            f"[reject:faces] {abspath} | face_score too low ({face_score:.2f} < {FACE_SCORE_MIN}) | "
            f"faces={num_faces} | tech_score={float(tech.get('score') or 0.0):.2f}"
        )
        if WATCHER_DEBUG and (debug_dir or True):
            _write_debug_report(debug_dir or os.path.join(base_dir, ".watcher_reports"), {
                "path": abspath,
                "sha256": file_hash,
                "dhash": features.get("dhash"),
                "decision": "rejected_low_quality_faces",
                "technical": tech,
                "face": {
                    "face_present": face_present,
                    "num_faces": num_faces,
                    "face_score": face_score,
                    "threshold": FACE_SCORE_MIN,
                    "details": face.get("faces") if WATCHER_DEBUG else None,
                },
            })
        if rejected_lowface_dir:
            _safe_move(abspath, rejected_lowface_dir, "faces")
        return

    # Accepted: upload immediately. First acceptable photo of a scene "wins";
    # later similar ones will be rejected against the manifest and never uploaded.
    print(
        f"[accept] {abspath} | not duplicate, technical OK"
        f"{', faces=' + str(num_faces) + ', face_score=' + format(face_score, '.2f') if face_present else ', faces=0'} | "
        f"tech_score={float(tech.get('score') or 0.0):.2f} dhash={features.get('dhash')}"
    )
    client.upload_file_to_event(event_id, abspath, watcher_id=watcher_id)
    manifest.add_with_features(file_hash, abspath, features)
    if WATCHER_DEBUG and (debug_dir or True):
        _write_debug_report(debug_dir or os.path.join(base_dir, ".watcher_reports"), {
            "path": abspath,
            "sha256": file_hash,
            "dhash": features.get("dhash"),
            "decision": "accepted_uploaded",
            "technical": tech,
            "face": {
                "face_present": face_present,
                "num_faces": num_faces,
                "face_score": face_score,
                "threshold": FACE_SCORE_MIN if face_present else None,
                "details": face.get("faces") if WATCHER_DEBUG else None,
            },
        })
    if move_uploaded_dir:
        try:
            os.makedirs(move_uploaded_dir, exist_ok=True)
            dest = os.path.join(move_uploaded_dir, os.path.basename(abspath))
            # If exists, add suffix
            base, ext = os.path.splitext(dest)
            i = 1
            while os.path.exists(dest):
                dest = f"{base}_{i}{ext}"
                i += 1
            os.replace(abspath, dest)
            print(f"[moved] {abspath} -> {dest}")
        except Exception:
            # keep file if move fails
            print(f"[warn] move failed for {abspath}")


class CreatedHandler(FileSystemEventHandler):
    def __init__(self, client: UploadClient, event_id: int, manifest: Manifest, move_uploaded_dir: Optional[str], watcher_id: Optional[int]) -> None:
        super().__init__()
        self.client = client
        self.event_id = event_id
        self.manifest = manifest
        self.move_uploaded_dir = move_uploaded_dir
        self.watcher_id = watcher_id

    def on_created(self, event):  # type: ignore[no-untyped-def]
        if getattr(event, "is_directory", False):
            return
        try:
            process_path(self.client, self.event_id, event.src_path, self.manifest, self.move_uploaded_dir, self.watcher_id)
        except Exception:
            pass

    def on_modified(self, event):  # type: ignore[no-untyped-def]
        if getattr(event, "is_directory", False):
            return
        try:
            process_path(self.client, self.event_id, event.src_path, self.manifest, self.move_uploaded_dir, self.watcher_id)
        except Exception as e:
            if WATCHER_LOG_ERRORS or WATCHER_DEBUG:
                print(f"[warn] on_modified failed: {e}")

    def on_moved(self, event):  # type: ignore[no-untyped-def]
        """Important for FTP drops: many clients upload to a temp name then rename/move into place."""
        if getattr(event, "is_directory", False):
            return
        try:
            dest = getattr(event, "dest_path", None)
            if dest:
                process_path(self.client, self.event_id, dest, self.manifest, self.move_uploaded_dir, self.watcher_id)
        except Exception as e:
            if WATCHER_LOG_ERRORS or WATCHER_DEBUG:
                print(f"[warn] on_moved failed: {e}")


def scan_existing_once(watch_dir: str, client: UploadClient, event_id: int, manifest: Manifest, move_uploaded_dir: Optional[str], watcher_id: Optional[int]) -> None:
    try:
        for name in os.listdir(watch_dir):
            p = os.path.join(watch_dir, name)
            if os.path.isfile(p) and is_image_file(p):
                try:
                    process_path(client, event_id, p, manifest, move_uploaded_dir, watcher_id)
                except Exception:
                    pass
    except Exception:
        pass


def main() -> None:
    # Optional CLI flags (keeps env-var behavior intact)
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--debug", action="store_true", help="Enable per-photo JSON debug report (also via WATCHER_DEBUG=1).")
    parser.add_argument("--debug-dir", default=None, help="Directory to write JSON reports (also via WATCHER_DEBUG_DIR).")
    args, _unknown = parser.parse_known_args(sys.argv[1:])
    global WATCHER_DEBUG, WATCHER_DEBUG_DIR
    if args.debug:
        WATCHER_DEBUG = True
    if args.debug_dir:
        WATCHER_DEBUG_DIR = args.debug_dir

    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000").strip()
    event_id_str = os.environ.get("EVENT_ID", "").strip()
    username = os.environ.get("PHOTOGRAPHER_USERNAME", "").strip() or None
    password = os.environ.get("PHOTOGRAPHER_PASSWORD", "").strip() or None
    token = os.environ.get("PHOTOGRAPHER_TOKEN", "").strip() or None
    watch_dir = os.environ.get("WATCH_DIR", "").strip()
    move_uploaded_dir = os.environ.get("MOVE_UPLOADED_DIR", "").strip() or None
    watcher_id_env = os.environ.get("WATCHER_ID", "").strip()
    watcher_id = int(watcher_id_env) if watcher_id_env.isdigit() else None
    machine_label = os.environ.get("MACHINE_LABEL", "").strip() or None

    client = UploadClient(base_url=base_url, username=username, password=password, token=token)

    # Agent mode: if MACHINE_LABEL present, poll server to get watchers
    if machine_label:
        print(f"\n{'='*60}")
        print(f"[agent] LOCAL WATCHER STARTED in AGENT MODE")
        print(f"[agent] machine_label={machine_label}")
        print(f"[agent] API base URL: {base_url}")
        print(f"[agent] Photo Selection Algorithm: {'ENABLED ✓' if ENABLE_PHOTO_SELECTION else 'DISABLED ✗'}")
        if not ENABLE_PHOTO_SELECTION:
            print(f"[agent] ⚠ All photos will be uploaded without quality filtering")
        print(f"[agent] Polling server every 3 seconds for watchers...")
        print(f"{'='*60}\n")
        try:
            client.login_if_needed()
            print(f"[agent] ✓ Authentication successful")
        except Exception as e:
            print(f"[agent] ✗ Login failed: {e}")
            raise SystemExit(1)

        active: dict[int, dict] = {}
        observers: dict[int, Observer] = {}
        manifests: dict[int, Manifest] = {}
        try:
            while True:
                # Fetch watchers for this machine (with 401 re-login)
                ws = []
                try:
                    resp = client.session.get(f"{base_url}/api/admin/local-watchers", params={"machine_label": machine_label}, timeout=30)
                    if resp.status_code == 401:
                        # token expired or missing → re-login then retry once
                        try:
                            # drop old header and login again
                            try:
                                client.session.headers.pop("Authorization", None)
                            except Exception:
                                pass
                            client.login_if_needed()
                            resp = client.session.get(f"{base_url}/api/admin/local-watchers", params={"machine_label": machine_label}, timeout=30)
                        except Exception:
                            pass
                    if resp.ok:
                        ws = resp.json()
                except Exception:
                    ws = []
                ids = set()
                # Always log fetch count for visibility
                try:
                    print(f"[agent] Fetched {len(ws or [])} watcher(s) for machine_label={machine_label}")
                except Exception:
                    pass
                for w in (ws or []):
                    wid = int(w.get("id"))
                    ids.add(wid)
                    listen = bool(w.get("listening"))
                    wdir = w.get("expected_path") or ""
                    move_dir = w.get("move_uploaded_dir") or None
                    ev_id = int(w.get("event_id"))
                    # Always log watcher details for visibility
                    try:
                        path_exists = os.path.isdir(wdir) if wdir else False
                        status = "✓ EXISTS" if path_exists else "✗ NOT FOUND"
                        print(f"[agent] Watcher #{wid}: event={ev_id}, listening={listen}, path={status}")
                        if WATCHER_AGENT_VERBOSE:
                            print(f"        └─ expected_path: {wdir}")
                    except Exception:
                        pass
                    if not wdir or not os.path.isdir(wdir):
                        # Don't auto-disable server-side listening; just report locally.
                        # (Auto-disabling here can hide configuration mistakes and requires manual re-enable.)
                        print(f"[agent] skip watcher {wid}: path not found or not accessible: {wdir}")
                        # stop if running
                        if wid in observers:
                            try:
                                observers[wid].stop(); observers[wid].join(); del observers[wid]
                            except Exception:
                                pass
                        continue
                    if not listen:
                        # stop if running
                        if wid in observers:
                            try:
                                observers[wid].stop(); observers[wid].join(); del observers[wid]
                                print(f"[agent] stopped watcher {wid}")
                            except Exception:
                                pass
                        continue
                    # ensure running
                    if wid not in observers:
                        man = Manifest(os.path.join(wdir, ".uploaded_manifest.json"))
                        manifests[wid] = man
                        # initial scan
                        scan_existing_once(wdir, client, ev_id, man, move_dir, wid)
                        if WATCHDOG_AVAILABLE:
                            handler = CreatedHandler(client, ev_id, man, move_dir, wid)
                            obs = Observer(); obs.schedule(handler, wdir, recursive=False); obs.start()
                            observers[wid] = obs
                            print(f"[agent] ✓ STARTED watcher #{wid} watching: {wdir}")
                            print(f"        └─ Monitoring event_id={ev_id} for new photos...")
                        else:
                            print(f"[agent] ⚠ Fallback scan mode for watcher #{wid} (watchdog not available)")
                    # In fallback (no watchdog), rescan every loop for active watchers
                    if not WATCHDOG_AVAILABLE:
                        man = manifests.get(wid) or Manifest(os.path.join(wdir, ".uploaded_manifest.json"))
                        manifests[wid] = man
                        scan_existing_once(wdir, client, ev_id, man, move_dir, wid)
                # stop removed watchers
                for wid, obs in list(observers.items()):
                    if wid not in ids:
                        try:
                            obs.stop(); obs.join(); del observers[wid]
                            print(f"[agent] removed watcher {wid}")
                        except Exception:
                            pass
                time.sleep(3)
        except KeyboardInterrupt:
            for obs in observers.values():
                try:
                    obs.stop(); obs.join()
                except Exception:
                    pass
        return

    # Single watcher mode (legacy)
    if not event_id_str.isdigit():
        raise SystemExit("EVENT_ID is required and must be an integer (or set MACHINE_LABEL for agent mode)")
    event_id = int(event_id_str)
    if not watch_dir or not os.path.isdir(watch_dir):
        raise SystemExit("WATCH_DIR must point to an existing directory")

    print(f"\n{'='*60}")
    print(f"[start] LOCAL WATCHER STARTED in LEGACY MODE")
    print(f"[start] Watching directory: {watch_dir}")
    print(f"[start] Event ID: {event_id}")
    print(f"[start] API base URL: {base_url}")
    print(f"[start] Photo Selection Algorithm: {'ENABLED ✓' if ENABLE_PHOTO_SELECTION else 'DISABLED ✗'}")
    if not ENABLE_PHOTO_SELECTION:
        print(f"[start] ⚠ All photos will be uploaded without quality filtering")
    print(f"{'='*60}\n")

    manifest = Manifest(os.path.join(watch_dir, ".uploaded_manifest.json"))
    scan_existing_once(watch_dir, client, event_id, manifest, move_uploaded_dir, watcher_id)
    if WATCHDOG_AVAILABLE:
        handler = CreatedHandler(client, event_id, manifest, move_uploaded_dir, watcher_id)
        observer = Observer(); observer.schedule(handler, watch_dir, recursive=False); observer.start()
        print(f"[start] ✓ Watcher active. Monitoring for new photos... (Press Ctrl+C to quit)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop(); observer.join()
    else:
        print("[info] watchdog not installed; falling back to periodic scan.")
        try:
            while True:
                scan_existing_once(watch_dir, client, event_id, manifest, move_uploaded_dir, watcher_id)
                time.sleep(2)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()



