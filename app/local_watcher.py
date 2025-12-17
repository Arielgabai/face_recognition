import os
import time
import json
import threading
import hashlib
from typing import Optional, Dict, Any, Tuple

from PIL import Image, ImageStat, ImageFilter

import requests
import mimetypes

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
# Filtering configuration
# -----------------------------
# Quality thresholds (tweak as needed). You can also override via environment variables.
# Note: decision is made immediately when the file arrives (first acceptable photo "wins";
# later similar ones are rejected and never uploaded).
MIN_WIDTH = int(os.environ.get("MIN_WIDTH", "800"))
MIN_HEIGHT = int(os.environ.get("MIN_HEIGHT", "600"))
MIN_SHARPNESS = float(os.environ.get("MIN_SHARPNESS", "100.0"))  # variance of Laplacian (higher = sharper)
MIN_BRIGHTNESS = float(os.environ.get("MIN_BRIGHTNESS", "30.0"))  # 0..255 grayscale mean
MAX_BRIGHTNESS = float(os.environ.get("MAX_BRIGHTNESS", "220.0"))  # 0..255 grayscale mean

# Similarity threshold: Hamming distance between perceptual hashes (dHash here).
# If distance <= SIMILARITY_THRESHOLD, the new image is considered a near-duplicate and is rejected.
SIMILARITY_THRESHOLD = int(os.environ.get("SIMILARITY_THRESHOLD", "6"))

# Optional local folders to move rejected files into (if unset, files are kept in place).
# If a relative path is provided, it's treated as relative to the watched directory.
REJECTED_DUPLICATE_DIR = os.environ.get("REJECTED_DUPLICATE_DIR", "").strip() or None
REJECTED_LOW_QUALITY_DIR = os.environ.get("REJECTED_LOW_QUALITY_DIR", "").strip() or None


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

    # --- Filtering layer (quality + similarity) BEFORE uploading ---
    features = compute_image_features(abspath)
    if not features:
        # Can't evaluate -> treat as reject (avoid paying for uploads of unreadable images)
        print(f"[reject:low_quality] cannot compute features: {abspath}")
        if rejected_lowq_dir:
            _safe_move(abspath, rejected_lowq_dir, "low_quality")
        return

    ok, reason = quality_ok(features)
    if not ok:
        sharp = float(features.get("sharpness", 0.0) or 0.0)
        bright = float(features.get("brightness", 0.0) or 0.0)
        print(
            f"[reject:low_quality] {abspath} | {reason} | "
            f"sharpness={sharp:.2f} brightness={bright:.1f} "
            f"res={features.get('width')}x{features.get('height')} dhash={features.get('dhash')}"
        )
        if rejected_lowq_dir:
            _safe_move(abspath, rejected_lowq_dir, "low_quality")
        return

    similar = manifest.find_similar(str(features.get("dhash") or ""), threshold=SIMILARITY_THRESHOLD)
    if similar:
        print(
            f"[reject:duplicate] {abspath} | dhash distance={similar.get('distance')} <= {SIMILARITY_THRESHOLD} "
            f"vs {similar.get('path')} (sha={str(similar.get('sha256'))[:8]}...)"
        )
        if rejected_dup_dir:
            _safe_move(abspath, rejected_dup_dir, "duplicate")
        return

    # Accepted: upload immediately. First acceptable photo of a scene "wins";
    # later similar ones will be rejected against the manifest and never uploaded.
    sharp = float(features.get("sharpness", 0.0) or 0.0)
    bright = float(features.get("brightness", 0.0) or 0.0)
    print(
        f"[accept] {abspath} | passes quality & uniqueness | "
        f"sharpness={sharp:.2f} brightness={bright:.1f} "
        f"res={features.get('width')}x{features.get('height')} dhash={features.get('dhash')}"
    )
    client.upload_file_to_event(event_id, abspath, watcher_id=watcher_id)
    manifest.add_with_features(file_hash, abspath, features)
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
        except Exception:
            pass


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
        print(f"[agent] machine_label={machine_label}")
        try:
            client.login_if_needed()
        except Exception as e:
            print(f"[agent] login failed: {e}")
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
                for w in (ws or []):
                    wid = int(w.get("id"))
                    ids.add(wid)
                    listen = bool(w.get("listening"))
                    wdir = w.get("expected_path") or ""
                    move_dir = w.get("move_uploaded_dir") or None
                    ev_id = int(w.get("event_id"))
                    if not wdir or not os.path.isdir(wdir):
                        # update last_error
                        try:
                            client.session.put(f"{base_url}/api/admin/local-watchers/{wid}", json={"listening": False}, timeout=15)
                        except Exception:
                            pass
                        print(f"[agent] skip watcher {wid}: path not found {wdir}")
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
                            print(f"[agent] started watcher {wid} on {wdir}")
                        else:
                            print(f"[agent] fallback scan mode for watcher {wid} on {wdir}")
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

    manifest = Manifest(os.path.join(watch_dir, ".uploaded_manifest.json"))
    scan_existing_once(watch_dir, client, event_id, manifest, move_uploaded_dir, watcher_id)
    if WATCHDOG_AVAILABLE:
        handler = CreatedHandler(client, event_id, manifest, move_uploaded_dir, watcher_id)
        observer = Observer(); observer.schedule(handler, watch_dir, recursive=False); observer.start()
        print(f"[start] watcher on {watch_dir}. Press Ctrl+C to quit.")
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



