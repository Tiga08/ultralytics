import json
import os
import cv2
from core.registry import PluginRegistry
from output.base import OutputAdapterBase
from pipeline.events import ViolationEvent
from utils.logger import logger


@PluginRegistry.output("local")
class LocalOutputAdapter(OutputAdapterBase):
    def setup(self, config) -> None:
        self._output_dir = config.output_dir
        os.makedirs(self._output_dir, exist_ok=True)

    def send(self, event: ViolationEvent) -> None:
        try:
            base = os.path.join(
                self._output_dir,
                f"{event.task_id}_{event.violation_type}_{int(event.timestamp * 1000)}"
            )
            meta = {
                "task_id": event.task_id,
                "detector_name": event.detector_name,
                "violation_type": event.violation_type,
                "timestamp": event.timestamp,
                "bounding_boxes": event.bounding_boxes,
                **event.extra,
            }
            with open(f"{base}.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            if event.frame_snapshot is not None:
                cv2.imwrite(f"{base}.jpg", event.frame_snapshot)
        except Exception as e:
            logger.error("local_output_failed", error=str(e))

    def close(self) -> None:
        pass
