from typing import Dict
from threading import Lock, local
from contextlib import contextmanager
import time


class AwsMetrics:
    """In-memory counters for AWS Rekognition calls and estimated cost.

    NOTE: Process-local only. For multi-instance deployments, persist to DB or use Redis.
    """

    PRICES_USD = {
        # Approx public pricing (illustrative). Adjust to your negotiated prices.
        # IndexFaces and SearchFaces billed per image, SearchFacesByImage billed per image
        'IndexFaces': 0.001,            # $1.00 / 1000 images
        'SearchFaces': 0.001,           # $1.00 / 1000 searches
        'SearchFacesByImage': 0.001,    # $1.00 / 1000 images
        'DetectFaces': 0.001,           # $1.00 / 1000 images
        'ListFaces': 0.0,
        'DeleteFaces': 0.0,
        'CreateCollection': 0.0,
        'DescribeCollection': 0.0,
    }

    def __init__(self) -> None:
        self._lock = Lock()
        self._counts: Dict[str, int] = {}
        self._actions: Dict[str, Dict[str, int]] = {}
        self._since_ts = time.time()
        self._action_start: Dict[str, float] = {}
        self._action_log: list[dict] = []
        self._tls = local()

    def inc(self, op: str, n: int = 1) -> None:
        with self._lock:
            self._counts[op] = self._counts.get(op, 0) + n
            # Also increment per-action bucket if a current action is active
            cur = getattr(self._tls, 'action', None)
            if cur:
                a = self._actions.setdefault(cur, {})
                a[op] = a.get(op, 0) + n

    def reset(self) -> None:
        with self._lock:
            self._counts = {}
            self._actions = {}
            self._since_ts = time.time()
            self._action_start = {}
            self._action_log = []

    def snapshot(self) -> Dict:
        with self._lock:
            counts = dict(self._counts)
            total_cost = 0.0
            costs = {}
            for op, c in counts.items():
                unit = self.PRICES_USD.get(op, 0.0)
                cost = float(c) * float(unit)
                costs[op] = round(cost, 6)
                total_cost += cost
            return {
                'since': self._since_ts,
                'counts': counts,
                'costs': costs,
                'total_cost_usd': round(total_cost, 6),
                'actions': self._actions,
                'action_log': list(self._action_log),
            }

    # -------- Per-action helpers --------
    def begin_action(self, action: str) -> None:
        with self._lock:
            self._actions.setdefault(action, {
                'IndexFaces': 0,
                'SearchFaces': 0,
                'SearchFacesByImage': 0,
                'DetectFaces': 0,
            })
            self._action_start[action] = time.time()

    def inc_action(self, action: str, op: str, n: int = 1) -> None:
        with self._lock:
            a = self._actions.setdefault(action, {})
            a[op] = a.get(op, 0) + n

    def end_action(self, action: str) -> None:
        with self._lock:
            counts = dict(self._actions.get(action, {}))
            cost = 0.0
            for op, c in counts.items():
                cost += float(c) * float(self.PRICES_USD.get(op, 0.0))
            ts = self._action_start.get(action, time.time())
            desc = self._describe_action(action)
            entry = {
                'ts': ts,
                'action': action,
                'description': desc,
                'counts': counts,
                'cost_usd': round(cost, 6),
            }
            self._action_log.append(entry)
            # Optionally cap log length
            if len(self._action_log) > 500:
                self._action_log = self._action_log[-500:]

    def _describe_action(self, action: str) -> str:
        try:
            if action.startswith('upload_event:'):
                eid = action.split(':', 1)[1]
                return f"Upload de photos (événement {eid})"
            if action.startswith('selfie_update:event:'):
                parts = action.split(':')
                # selfie_update:event:{event_id}:user:{user_id}
                ev = parts[2] if len(parts) > 2 else '?'
                uid = parts[4] if len(parts) > 4 else '?'
                return f"Mise à jour du selfie (user {uid}, événement {ev})"
        except Exception:
            pass
        return action

    def current_action(self) -> str | None:
        try:
            return getattr(self._tls, 'action', None)
        except Exception:
            return None

    @contextmanager
    def action_context(self, action: str):
        prev = getattr(self._tls, 'action', None)
        try:
            self.begin_action(action)
            self._tls.action = action
            yield
        finally:
            try:
                self._tls.action = prev
            except Exception:
                pass


aws_metrics = AwsMetrics()

