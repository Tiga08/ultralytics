# tvp/utils/metrics.py
import threading
from collections import defaultdict


class MetricsRegistry:
    _lock = threading.Lock()
    _gauges: dict[str, float] = {}
    _counters: dict[str, float] = defaultdict(float)

    @classmethod
    def set_gauge(cls, name: str, value: float, labels: dict | None = None) -> None:
        with cls._lock:
            cls._gauges[cls._key(name, labels)] = value

    @classmethod
    def inc_counter(cls, name: str, value: float = 1.0,
                    labels: dict | None = None) -> None:
        with cls._lock:
            cls._counters[cls._key(name, labels)] += value

    @classmethod
    def render(cls) -> str:
        lines = []
        with cls._lock:
            for k, v in cls._gauges.items():
                lines.append(f"{k} {v}")
            for k, v in cls._counters.items():
                lines.append(f"{k} {v}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _key(name: str, labels: dict | None) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
