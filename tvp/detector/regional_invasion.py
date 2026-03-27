from pydantic import BaseModel
from core.registry import PluginRegistry
from detector.base import DetectorBase
from pipeline.frame import Frame
from pipeline.events import ViolationEvent
from pipeline.bytetrack_wrapper import ByteTrackWrapper
from model.base import InferResult
from utils.logger import logger


class RegionalInvasionConfig(BaseModel):
    send_interval: int = 60
    conf_threshold: float = 0.5
    forbidden_zone: list[list[int]] = []
    target_classes: list[str] = ["person"]


@PluginRegistry.detector("regional_invasion")
class RegionalInvasionDetector(DetectorBase):
    CONFIG_CLASS = RegionalInvasionConfig

    def __init__(self, task_id: str, output_adapters: list):
        super().__init__(task_id, output_adapters)
        self._tracker = ByteTrackWrapper()

    def setup(self, config) -> None:
        if isinstance(config, dict):
            config = RegionalInvasionConfig.model_validate(config)
        self.conf_threshold = config.conf_threshold
        self.send_interval = config.send_interval
        self.forbidden_zone = config.forbidden_zone

    def process(self, frame: Frame, infer_result: InferResult) -> list[ViolationEvent]:
        violations = []
        try:
            for box in infer_result.boxes:
                if box[4] > self.conf_threshold:
                    violations.append(ViolationEvent(
                        task_id=self._task_id,
                        detector_name="regional_invasion",
                        violation_type="regional_invasion",
                        timestamp=frame.timestamp,
                        frame_snapshot=frame.image,
                        bounding_boxes=[box[:4].tolist()],
                    ))
        except Exception as e:
            logger.error("regional_invasion_process_error", error=str(e))
        return violations

    def cleanup(self) -> None:
        self._tracker.reset()
