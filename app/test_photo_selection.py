import os
import time
import json
import hashlib
import math
import sys
import argparse
from typing import Optional, Dict, Any, Tuple

from PIL import Image, ImageStat, ImageFilter
import numpy as np
import cv2

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


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# -----------------------------
# Photo Selection Algorithm Toggle
# -----------------------------
ENABLE_PHOTO_SELECTION = (os.environ.get("ENABLE_PHOTO_SELECTION", "1").strip() or "1").lower() in {"1", "true", "yes", "y", "on"}
print(ENABLE_PHOTO_SELECTION)
# -----------------------------
# Filtering configuration
# -----------------------------
MIN_WIDTH = int(os.environ.get("MIN_WIDTH", "640"))
MIN_HEIGHT = int(os.environ.get("MIN_HEIGHT", "480"))
MIN_SHARPNESS = float(os.environ.get("MIN_SHARPNESS", "30.0"))
MIN_BRIGHTNESS = float(os.environ.get("MIN_BRIGHTNESS", "20.0"))
MAX_BRIGHTNESS = float(os.environ.get("MAX_BRIGHTNESS", "235.0"))
SIMILARITY_THRESHOLD = int(os.environ.get("SIMILARITY_THRESHOLD", "8"))

# Face-aware thresholds
FACE_SCORE_MIN = float(os.environ.get("FACE_SCORE_MIN", "0.35"))
FACE_MIN_RELATIVE_SIZE = float(os.environ.get("FACE_MIN_RELATIVE_SIZE", "0.02"))
MAX_FACE_ROLL_DEG = float(os.environ.get("MAX_FACE_ROLL_DEG", "20.0"))
MIN_EYE_DISTANCE_RATIO = float(os.environ.get("MIN_EYE_DISTANCE_RATIO", "0.20"))
MAX_EYE_DISTANCE_RATIO = float(os.environ.get("MAX_EYE_DISTANCE_RATIO", "0.70"))
MIN_EYE_Y_RATIO = float(os.environ.get("MIN_EYE_Y_RATIO", "0.10"))
MAX_EYE_Y_RATIO = float(os.environ.get("MAX_EYE_Y_RATIO", "0.60"))

# Dossiers pour les fichiers rejetés
REJECTED_DUPLICATE_DIR = os.environ.get("REJECTED_DUPLICATE_DIR", "").strip() or ".rejected_duplicates"
REJECTED_LOW_QUALITY_DIR = os.environ.get("REJECTED_LOW_QUALITY_DIR", "").strip() or ".rejected_low_quality"
REJECTED_LOW_FACE_QUALITY_DIR = os.environ.get("REJECTED_LOW_FACE_QUALITY_DIR", "").strip() or ".rejected_low_face_quality"
ACCEPTED_DIR = ".accepted_photos"


def is_image_file(path: str) -> bool:
    _, ext = os.path.splitext(path.lower())
    return ext in SUPPORTED_EXTENSIONS


def compute_file_hash(path: str) -> Optional[str]:
    """Calcule le hash SHA256 du contenu du fichier."""
    try:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(4096), b""):
                sha256.update(block)
        return sha256.hexdigest()
    except Exception:
        return None


def _resolve_target_dir(base_dir: str, maybe_dir: Optional[str]) -> Optional[str]:
    """Resolve a user-provided directory."""
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


def _safe_copy(src: str, dest_dir: str, reason_tag: str) -> Optional[str]:
    """Copy a file into dest_dir (for testing without moving originals)."""
    import shutil
    try:
        os.makedirs(dest_dir, exist_ok=True)
        dest = os.path.join(dest_dir, os.path.basename(src))
        base, ext = os.path.splitext(dest)
        i = 1
        while os.path.exists(dest):
            dest = f"{base}_{i}{ext}"
            i += 1
        shutil.copy2(src, dest)
        print(f"[copied:{reason_tag}] {src} -> {dest}")
        return dest
    except Exception as e:
        print(f"[warn] copy failed ({reason_tag}) for {src}: {e}")
        return None


def _dhash_hex(img: Image.Image, hash_size: int = 8) -> str:
    """Compute dHash (difference hash) as a hex string."""
    try:
        resample = Image.Resampling.LANCZOS
    except Exception:
        resample = Image.LANCZOS  # type: ignore[attr-defined]

    g = img.convert("L").resize((hash_size + 1, hash_size), resample=resample)
    pixels = list(g.getdata())

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
    """Hamming distance between two hex-encoded bitstrings."""
    try:
        ai = int(a_hex, 16)
        bi = int(b_hex, 16)
    except Exception:
        return None
    x = ai ^ bi
    try:
        return x.bit_count()
    except Exception:
        return bin(x).count("1")


def compute_image_features(path: str) -> Optional[Dict[str, Any]]:
    """Compute perceptual hash + basic quality metrics for an image file."""
    try:
        with Image.open(path) as im:
            im.load()
            width, height = im.size

            dhash = _dhash_hex(im)

            gray = im.convert("L")
            brightness = float(ImageStat.Stat(gray).mean[0])

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
    """Compute a numeric technical quality score (0..1) + pass/fail using the existing thresholds."""
    w = int(features.get("width", 0) or 0)
    h = int(features.get("height", 0) or 0)
    sharp = float(features.get("sharpness", 0.0) or 0.0)
    bright = float(features.get("brightness", 0.0) or 0.0)

    ok, reason = quality_ok(features)

    # Resolution score
    res_ratio = 0.0
    if MIN_WIDTH > 0 and MIN_HEIGHT > 0:
        res_ratio = min(w / float(MIN_WIDTH), h / float(MIN_HEIGHT))
    res_score = max(0.0, min(1.0, res_ratio))

    # Sharpness score
    sharp_score = 0.0 if MIN_SHARPNESS <= 0 else max(0.0, min(1.0, sharp / float(MIN_SHARPNESS)))

    # Brightness score
    if MIN_BRIGHTNESS <= bright <= MAX_BRIGHTNESS:
        bright_score = 1.0
    else:
        if bright < MIN_BRIGHTNESS:
            dist = MIN_BRIGHTNESS - bright
        else:
            dist = bright - MAX_BRIGHTNESS
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
        try:
            return cv2.imread(path, cv2.IMREAD_COLOR)
        except Exception:
            return None


def _range_score(x: float, lo: float, hi: float) -> float:
    """Score 1.0 inside [lo, hi], else decrease linearly to 0 as it moves away."""
    if lo <= x <= hi:
        return 1.0
    span = max(1e-9, (hi - lo))
    if x < lo:
        d = (lo - x) / span
    else:
        d = (x - hi) / span
    return max(0.0, 1.0 - d)


def compute_face_metrics(path: str) -> Dict[str, Any]:
    """Face-aware evaluation (offline)."""
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
        roi_gray_eyes = roi_gray[0 : int(h * 0.65), :]

        eye_min = max(10, int(min(w, h) * 0.12))
        eyes = eye_cascade.detectMultiScale(roi_gray_eyes, scaleFactor=1.1, minNeighbors=8, minSize=(eye_min, eye_min))

        if eyes is None or len(eyes) == 0:
            eyes_iter = []
        else:
            eyes_iter = eyes

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
            (ex1, ey1, ew1, eh1), (ex2, ey2, ew2, eh2) = eyes_top[0], eyes_top[1]
            c1 = (ex1 + ew1 / 2.0, ey1 + eh1 / 2.0)
            c2 = (ex2 + ew2 / 2.0, ey2 + eh2 / 2.0)
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
            eye_y_ratio = float(avg_eye_y / max(1e-9, float(h)))
            pitch_proxy_score = _range_score(eye_y_ratio, MIN_EYE_Y_RATIO, MAX_EYE_Y_RATIO)

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


class TestManifest:
    """Simple manifest to track processed images during testing."""
    def __init__(self) -> None:
        self._seen: Dict[str, Dict[str, Any]] = {}

    def add_with_features(self, file_hash: str, absolute_path: str, features: Dict[str, Any]) -> None:
        """Register an accepted image with its features."""
        self._seen[file_hash] = {
            "path": absolute_path,
            "timestamp": time.time(),
            "dhash": features.get("dhash"),
            "width": features.get("width"),
            "height": features.get("height"),
            "sharpness": features.get("sharpness"),
            "brightness": features.get("brightness"),
        }

    def contains(self, file_hash: str) -> bool:
        return file_hash in self._seen

    def find_similar(self, dhash_hex: str, threshold: int = SIMILARITY_THRESHOLD) -> Optional[Dict[str, Any]]:
        """Return the closest match (with distance) if within threshold, else None."""
        best: Optional[Dict[str, Any]] = None
        best_dist: Optional[int] = None
        for sha, meta in self._seen.items():
            existing = meta.get("dhash")
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
                if best_dist == 0:
                    break
        if best is not None and best_dist is not None and best_dist <= threshold:
            return best
        return None


def process_photo(path: str, manifest: TestManifest, base_dir: str, move_files: bool = False) -> Dict[str, Any]:
    """Test photo selection on a single image. Returns decision report."""
    abspath = os.path.abspath(path)
    
    rejected_dup_dir = _resolve_target_dir(base_dir, REJECTED_DUPLICATE_DIR)
    rejected_lowq_dir = _resolve_target_dir(base_dir, REJECTED_LOW_QUALITY_DIR)
    rejected_lowface_dir = _resolve_target_dir(base_dir, REJECTED_LOW_FACE_QUALITY_DIR)
    accepted_dir = _resolve_target_dir(base_dir, ACCEPTED_DIR)
    
    # Calculer le hash du contenu
    file_hash = compute_file_hash(abspath)
    if not file_hash:
        return {"path": abspath, "decision": "error", "reason": "cannot compute hash"}
    
    # Vérifier si déjà traité
    if manifest.contains(file_hash):
        return {"path": abspath, "decision": "skip", "reason": "already processed"}

    # Si algorithme de sélection désactivé
    if not ENABLE_PHOTO_SELECTION:
        print(f"[accept:no-filter] {os.path.basename(abspath)} | selection algorithm disabled")
        manifest.add_with_features(file_hash, abspath, {})
        if move_files:
            _safe_copy(abspath, accepted_dir, "accepted")
        return {
            "path": abspath,
            "decision": "accepted",
            "reason": "selection algorithm disabled",
            "sha256": file_hash,
        }

    # Calculer les features
    features = compute_image_features(abspath)
    if not features:
        print(f"[reject:low_quality] {os.path.basename(abspath)} | cannot compute features")
        if move_files and rejected_lowq_dir:
            _safe_copy(abspath, rejected_lowq_dir, "low_quality")
        return {
            "path": abspath,
            "decision": "rejected",
            "reason": "cannot compute features",
            "sha256": file_hash,
        }

    # Test qualité technique
    tech = technical_quality_score(features)
    if not tech.get("ok"):
        print(
            f"[reject:technical] {os.path.basename(abspath)} | {tech.get('reason')} | "
            f"tech_score={float(tech.get('score') or 0.0):.2f} "
            f"sharpness={float(tech.get('sharpness') or 0.0):.2f} brightness={float(tech.get('brightness') or 0.0):.1f} "
            f"res={tech.get('width')}x{tech.get('height')}"
        )
        if move_files and rejected_lowq_dir:
            _safe_copy(abspath, rejected_lowq_dir, "technical")
        return {
            "path": abspath,
            "decision": "rejected",
            "reason": "low_quality_technical",
            "sha256": file_hash,
            "dhash": features.get("dhash"),
            "technical": tech,
        }

    # Test similarité
    similar = manifest.find_similar(str(features.get("dhash") or ""), threshold=SIMILARITY_THRESHOLD)
    if similar:
        print(
            f"[reject:duplicate] {os.path.basename(abspath)} | dist={similar.get('distance')} <= {SIMILARITY_THRESHOLD} "
            f"vs {os.path.basename(similar.get('path', ''))} | "
            f"tech_score={float(tech.get('score') or 0.0):.2f}"
        )
        if move_files and rejected_dup_dir:
            _safe_copy(abspath, rejected_dup_dir, "duplicate")
        return {
            "path": abspath,
            "decision": "rejected",
            "reason": "duplicate",
            "sha256": file_hash,
            "dhash": features.get("dhash"),
            "technical": tech,
            "duplicate": similar,
        }

    # Test qualité des visages
    face = compute_face_metrics(abspath)
    face_present = bool(face.get("face_present"))
    num_faces = int(face.get("num_faces") or 0)
    face_score = float(face.get("face_score") or 0.0)

    if face_present and face_score < FACE_SCORE_MIN:
        print(
            f"[reject:faces] {os.path.basename(abspath)} | face_score too low ({face_score:.2f} < {FACE_SCORE_MIN}) | "
            f"faces={num_faces} | tech_score={float(tech.get('score') or 0.0):.2f}"
        )
        if move_files and rejected_lowface_dir:
            _safe_copy(abspath, rejected_lowface_dir, "faces")
        return {
            "path": abspath,
            "decision": "rejected",
            "reason": "low_quality_faces",
            "sha256": file_hash,
            "dhash": features.get("dhash"),
            "technical": tech,
            "face": {
                "face_present": face_present,
                "num_faces": num_faces,
                "face_score": face_score,
                "threshold": FACE_SCORE_MIN,
                "details": face.get("faces"),
            },
        }

    # Accepté!
    print(
        f"[accept] {os.path.basename(abspath)} | not duplicate, technical OK"
        f"{', faces=' + str(num_faces) + ', face_score=' + format(face_score, '.2f') if face_present else ', faces=0'} | "
        f"tech_score={float(tech.get('score') or 0.0):.2f}"
    )
    manifest.add_with_features(file_hash, abspath, features)
    if move_files:
        _safe_copy(abspath, accepted_dir, "accepted")
    
    return {
        "path": abspath,
        "decision": "accepted",
        "reason": "passed all filters",
        "sha256": file_hash,
        "dhash": features.get("dhash"),
        "technical": tech,
        "face": {
            "face_present": face_present,
            "num_faces": num_faces,
            "face_score": face_score,
            "threshold": FACE_SCORE_MIN if face_present else None,
            "details": face.get("faces"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test photo selection algorithm locally (no upload)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test on a single directory
  python test_photo_selection.py /path/to/photos

  # Test and copy files to categorized folders
  python test_photo_selection.py /path/to/photos --move

  # Generate detailed JSON report
  python test_photo_selection.py /path/to/photos --report output.json

  # Test and move + report
  python test_photo_selection.py /path/to/photos --move --report output.json
        """
    )
    parser.add_argument("directory", help="Directory containing photos to test")
    parser.add_argument("--move", action="store_true", help="Copy files to categorized folders (.accepted_photos, .rejected_*)")
    parser.add_argument("--report", default=None, help="Generate JSON report with detailed results")
    parser.add_argument("--recursive", "-r", action="store_true", help="Scan directory recursively")
    
    args = parser.parse_args()
    
    test_dir = args.directory
    if not os.path.isdir(test_dir):
        print(f"Error: Directory not found: {test_dir}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"[test] PHOTO SELECTION TEST")
    print(f"[test] Directory: {test_dir}")
    print(f"[test] Photo Selection Algorithm: {'ENABLED ✓' if ENABLE_PHOTO_SELECTION else 'DISABLED ✗'}")
    if ENABLE_PHOTO_SELECTION:
        print(f"[test] Quality thresholds:")
        print(f"       - Min resolution: {MIN_WIDTH}x{MIN_HEIGHT}")
        print(f"       - Min sharpness: {MIN_SHARPNESS}")
        print(f"       - Brightness range: [{MIN_BRIGHTNESS}, {MAX_BRIGHTNESS}]")
        print(f"       - Similarity threshold: {SIMILARITY_THRESHOLD}")
        print(f"       - Face score min: {FACE_SCORE_MIN}")
    print(f"[test] Move files: {'YES ✓' if args.move else 'NO ✗'}")
    print(f"[test] Generate report: {'YES ✓' if args.report else 'NO ✗'}")
    print(f"{'='*60}\n")
    
    manifest = TestManifest()
    results = []
    stats = {
        "total": 0,
        "accepted": 0,
        "rejected": 0,
        "rejected_technical": 0,
        "rejected_duplicate": 0,
        "rejected_faces": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    # Collecter tous les fichiers image
    image_files = []
    if args.recursive:
        for root, dirs, files in os.walk(test_dir):
            for f in files:
                path = os.path.join(root, f)
                if is_image_file(path):
                    image_files.append(path)
    else:
        for f in os.listdir(test_dir):
            path = os.path.join(test_dir, f)
            if os.path.isfile(path) and is_image_file(path):
                image_files.append(path)
    
    print(f"[test] Found {len(image_files)} image(s) to process\n")
    
    # Traiter chaque image
    for i, path in enumerate(image_files, 1):
        print(f"[{i}/{len(image_files)}] Processing: {os.path.basename(path)}")
        result = process_photo(path, manifest, test_dir, move_files=args.move)
        results.append(result)
        
        stats["total"] += 1
        decision = result.get("decision")
        if decision == "accepted":
            stats["accepted"] += 1
        elif decision == "rejected":
            stats["rejected"] += 1
            reason = result.get("reason")
            if "technical" in reason:
                stats["rejected_technical"] += 1
            elif "duplicate" in reason:
                stats["rejected_duplicate"] += 1
            elif "faces" in reason:
                stats["rejected_faces"] += 1
        elif decision == "skip":
            stats["skipped"] += 1
        elif decision == "error":
            stats["errors"] += 1
        print()
    
    # Résumé
    print(f"\n{'='*60}")
    print(f"[summary] RESULTS")
    print(f"{'='*60}")
    print(f"Total processed:       {stats['total']}")
    print(f"✓ Accepted:            {stats['accepted']} ({stats['accepted']*100/max(1,stats['total']):.1f}%)")
    print(f"✗ Rejected:            {stats['rejected']} ({stats['rejected']*100/max(1,stats['total']):.1f}%)")
    print(f"  - Low quality:       {stats['rejected_technical']}")
    print(f"  - Duplicates:        {stats['rejected_duplicate']}")
    print(f"  - Face quality:      {stats['rejected_faces']}")
    print(f"⊘ Skipped:             {stats['skipped']}")
    print(f"⚠ Errors:              {stats['errors']}")
    print(f"{'='*60}\n")
    
    # Générer rapport JSON si demandé
    if args.report:
        report_data = {
            "test_info": {
                "directory": test_dir,
                "timestamp": time.time(),
                "enable_photo_selection": ENABLE_PHOTO_SELECTION,
                "thresholds": {
                    "min_width": MIN_WIDTH,
                    "min_height": MIN_HEIGHT,
                    "min_sharpness": MIN_SHARPNESS,
                    "min_brightness": MIN_BRIGHTNESS,
                    "max_brightness": MAX_BRIGHTNESS,
                    "similarity_threshold": SIMILARITY_THRESHOLD,
                    "face_score_min": FACE_SCORE_MIN,
                } if ENABLE_PHOTO_SELECTION else None,
            },
            "statistics": stats,
            "results": results,
        }
        try:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            print(f"[report] Saved detailed report to: {args.report}")
        except Exception as e:
            print(f"[error] Failed to save report: {e}")
    
    if args.move:
        print(f"\n[info] Files have been copied to categorized folders:")
        print(f"       - Accepted: {os.path.join(test_dir, ACCEPTED_DIR)}")
        print(f"       - Rejected (technical): {os.path.join(test_dir, REJECTED_LOW_QUALITY_DIR)}")
        print(f"       - Rejected (duplicates): {os.path.join(test_dir, REJECTED_DUPLICATE_DIR)}")
        print(f"       - Rejected (face quality): {os.path.join(test_dir, REJECTED_LOW_FACE_QUALITY_DIR)}")


if __name__ == "__main__":
    main()

