# tvp/core/health.py
import threading
from utils.logger import logger


class HealthMonitor:
    def __init__(self, scheduler, config):
        self._scheduler = scheduler
        self._config = config
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="health-monitor", daemon=True
        )
        self._fail_counts: dict[str, int] = {}

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop_event.wait(self._config.check_interval):
            try:
                for task_id in self._scheduler.check_health():
                    self._handle_unhealthy(task_id)
            except Exception as e:
                logger.error("health_monitor_error", error=str(e))

    def _handle_unhealthy(self, task_id: str) -> None:
        count = self._fail_counts.get(task_id, 0)
        if count >= self._config.max_restart_count:
            logger.error("task_exceeded_max_restarts", task_id=task_id, fail_count=count)
            return
        if self._config.restart_on_failure:
            logger.warning("task_unhealthy_restarting", task_id=task_id)
            try:
                self._scheduler.restart(task_id)
                self._fail_counts[task_id] = count + 1
            except Exception as e:
                logger.error("task_restart_failed", task_id=task_id, error=str(e))
