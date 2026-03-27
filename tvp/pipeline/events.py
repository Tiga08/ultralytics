from dataclasses import dataclass, field

import numpy as np


@dataclass
class ViolationEvent:
    task_id: str
    detector_name: str
    violation_type: str
    timestamp: float
    frame_snapshot: np.ndarray | None
    bounding_boxes: list[list[float]]
    extra: dict = field(default_factory=dict)
