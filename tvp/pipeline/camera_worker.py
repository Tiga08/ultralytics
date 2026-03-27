import threading
import time
from utils.logger import logger
from pipeline.capture import VideoCapture
from pipeline.frame import Frame


class CameraWorker(threading.Thread):
    def __init__(self, camera_config, detectors, infer_pipeline):
        super().__init__(name=f"cam-{camera_config.id}", daemon=True)
        self._config = camera_config
        self._detectors = detectors
        self._infer_pipeline = infer_pipeline
        self._stop_event = threading.Event()
        self._health_last_frame_ts = time.time()

    @property
    def is_healthy(self) -> bool:
        # camera_timeout 默认 60 秒（可通过 HealthConfig.camera_timeout 配置）
        return (time.time() - self._health_last_frame_ts) < 60

    def stop(self) -> None:
        self._stop_event.set()

    def _process_frame(self, frame: Frame) -> None:
        try:
            infer_result = self._infer_pipeline.run(frame)
        except Exception as e:
            logger.error("inference_failed", camera_id=self._config.id, error=str(e))
            return
        for detector in self._detectors:
            if not detector.is_active():
                continue
            try:
                events = detector.process(frame, infer_result)
                for event in events:
                    detector.emit_violation(event)
            except Exception as e:
                logger.error("detector_failed",
                             detector=type(detector).__name__, error=str(e))

    def run(self) -> None:
        capture = VideoCapture(
            self._config.rtsp_url,
            reconnect_interval=5,
            rtsp_interval=self._config.rtsp_interval,
        )
        for frame in capture.stream(self._stop_event, camera_id=self._config.id):
            self._health_last_frame_ts = time.time()
            self._process_frame(frame)
