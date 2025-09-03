from typing import Dict
from threading import Lock
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
        self._since_ts = time.time()

    def inc(self, op: str, n: int = 1) -> None:
        with self._lock:
            self._counts[op] = self._counts.get(op, 0) + n

    def reset(self) -> None:
        with self._lock:
            self._counts = {}
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
            }


aws_metrics = AwsMetrics()

