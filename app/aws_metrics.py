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

    def inc_action(self, action: str, op: str, n: int = 1) -> None:
        with self._lock:
            a = self._actions.setdefault(action, {})
            a[op] = a.get(op, 0) + n

    def end_action(self, action: str) -> None:
        # No-op placeholder for future timing if needed
        return

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

