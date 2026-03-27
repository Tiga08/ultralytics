import threading
from enum import IntEnum
from typing import Callable, Any
from utils.logger import logger


class TaskPriority(IntEnum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


class TaskScheduler:
    def __init__(self):
        self._tasks: dict[str, dict] = {}
        self._lock = threading.RLock()

    def submit(self, task_id: str, worker, priority: TaskPriority,
               worker_factory: Callable[[], Any] | None = None) -> None:
        with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"Task '{task_id}' already exists")
            worker.start()
            self._tasks[task_id] = {
                "worker": worker, "priority": priority,
                "factory": worker_factory, "fail_count": 0,
            }
            logger.info("task_submitted", task_id=task_id, priority=priority.name)

    def remove(self, task_id: str) -> None:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task '{task_id}' not found")
            self._tasks[task_id]["worker"].stop()
            del self._tasks[task_id]

    def restart(self, task_id: str) -> None:
        with self._lock:
            if task_id not in self._tasks:
                raise KeyError(f"Task '{task_id}' not found")
            entry = self._tasks[task_id]
            if entry["factory"] is None:
                raise RuntimeError(f"Task '{task_id}' has no worker_factory")
            entry["worker"].stop()
            new_worker = entry["factory"]()
            new_worker.start()
            entry["worker"] = new_worker
            entry["fail_count"] += 1

    def check_health(self) -> list[str]:
        with self._lock:
            return [tid for tid, e in self._tasks.items() if not e["worker"].is_healthy]

    def get_entry(self, task_id: str) -> dict | None:
        with self._lock:
            e = self._tasks.get(task_id)
            return dict(e) if e else None
