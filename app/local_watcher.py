import os
import time
import json
import threading
from typing import Optional, Set

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
        self._seen: Set[str] = set()
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._seen = set(map(str, data.get("uploaded", [])))
        except Exception:
            self._seen = set()

    def add(self, absolute_path: str) -> None:
        with self._lock:
            self._seen.add(os.path.abspath(absolute_path))
            self._save()

    def contains(self, absolute_path: str) -> bool:
        return os.path.abspath(absolute_path) in self._seen

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
        except Exception:
            pass
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump({"uploaded": sorted(self._seen)}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def process_path(client: UploadClient, event_id: int, path: str, manifest: Manifest, move_uploaded_dir: Optional[str], watcher_id: Optional[int]) -> None:
    if not os.path.isfile(path) or not is_image_file(path):
        return
    abspath = os.path.abspath(path)
    if manifest.contains(abspath):
        return
    if not file_is_stable(abspath):
        print(f"[skip] not stable yet: {abspath}")
        return
    print(f"[detected] {abspath}")
    client.upload_file_to_event(event_id, abspath, watcher_id=watcher_id)
    manifest.add(abspath)
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
                            # fallback simple: rescan every loop via scan_existing_once
                            pass
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



