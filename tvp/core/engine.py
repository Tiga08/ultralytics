# tvp/core/engine.py
import threading
from utils.singleton import SingletonMeta
from utils.logger import logger
from core.registry import PluginRegistry
from core.scheduler import TaskScheduler, TaskPriority
from core.health import HealthMonitor


class TvpEngine(metaclass=SingletonMeta):
    def __init__(self):
        self._config = None
        self._scheduler: TaskScheduler | None = None
        self._health_monitor: HealthMonitor | None = None
        self._output_adapters: list = []
        self._task_status: dict[str, str] = {}
        self._task_configs: dict = {}
        self._lock = threading.RLock()

    def start(self, config) -> None:
        self._config = config
        from model.model_manager import ModelManager
        ModelManager().init(config.model_weights, config.inference.backend)
        self._output_adapters = self._init_output_adapters(config)
        self._scheduler = TaskScheduler()
        self._health_monitor = HealthMonitor(self._scheduler, config.health)
        self._health_monitor.start()
        logger.info("engine_started")

    def stop(self) -> None:
        if self._health_monitor:
            self._health_monitor.stop()
        with self._lock:
            for task_id in list(self._task_status.keys()):
                try:
                    self._scheduler.remove(task_id)
                except Exception:
                    pass
        for adapter in self._output_adapters:
            try:
                adapter.close()
            except Exception as e:
                logger.error("adapter_close_failed", error=str(e))
        logger.info("engine_stopped")

    def _init_output_adapters(self, config) -> list:
        adapters = []
        for attr, name in [("kafka", "kafka"), ("minio", "minio"), ("mqtt", "mqtt")]:
            cfg = getattr(config, attr, None)
            if cfg is not None:
                klass = PluginRegistry.get_output(name)
                adapter = klass()
                adapter.setup(cfg)
                adapters.append(adapter)
        return adapters

    def create_task(self, task_config) -> None:
        with self._lock:
            task_id = task_config.task_id
            if task_id in self._task_status:
                raise ValueError(f"Task '{task_id}' already exists")
            detectors = []
            try:
                for det_cfg in task_config.detectors:
                    klass = PluginRegistry.get_detector(det_cfg.name)
                    detector = klass(task_id, self._output_adapters)
                    cfg = det_cfg.config
                    if klass.CONFIG_CLASS is not None:
                        cfg = klass.CONFIG_CLASS.model_validate(cfg)
                    detector.setup(cfg)
                    detectors.append(detector)
            except Exception:
                for d in detectors:
                    d.cleanup()
                raise

            first_model = list(self._config.model_weights.root.keys())[0]

            def worker_factory():
                from pipeline.camera_worker import CameraWorker
                from pipeline.inference_pipeline import InferencePipeline
                return CameraWorker(
                    camera_config=task_config.camera,
                    detectors=detectors,
                    infer_pipeline=InferencePipeline(first_model),
                )

            priority = TaskPriority[task_config.priority]
            self._scheduler.submit(task_id, worker_factory(), priority, worker_factory)
            self._task_status[task_id] = "running"
            self._task_configs[task_id] = task_config

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            if task_id not in self._task_status:
                raise KeyError(f"Task '{task_id}' not found")
            self._scheduler.remove(task_id)
            del self._task_status[task_id]
            del self._task_configs[task_id]

    def pause_task(self, task_id: str) -> None:
        with self._lock:
            if task_id not in self._task_status:
                raise KeyError(f"Task '{task_id}' not found")
            entry = self._scheduler.get_entry(task_id)
            if entry:
                worker = entry["worker"]
                for det in worker._detectors:
                    det.pause()
            self._task_status[task_id] = "paused"

    def resume_task(self, task_id: str) -> None:
        with self._lock:
            if task_id not in self._task_status:
                raise KeyError(f"Task '{task_id}' not found")
            entry = self._scheduler.get_entry(task_id)
            if entry:
                worker = entry["worker"]
                for det in worker._detectors:
                    det.resume()
            self._task_status[task_id] = "running"

    def get_task_status(self, task_id: str) -> dict:
        with self._lock:
            if task_id not in self._task_status:
                raise KeyError(f"Task '{task_id}' not found")
            entry = self._scheduler.get_entry(task_id)
            cfg = self._task_configs.get(task_id)
            fail_count = entry["fail_count"] if entry else 0
            is_healthy = entry["worker"].is_healthy if entry else False
            return {
                "task_id": task_id,
                "task_name": cfg.task_name if cfg else "",
                "priority": cfg.priority if cfg else "NORMAL",
                "status": self._task_status[task_id],
                "camera_id": cfg.camera.id if cfg else "",
                "fail_count": fail_count,
                "is_healthy": is_healthy,
            }

    def list_tasks(self) -> list[dict]:
        with self._lock:
            return [self.get_task_status(tid) for tid in self._task_status]
