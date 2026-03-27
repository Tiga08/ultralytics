from dataclasses import dataclass

import numpy as np


@dataclass
class Frame:
    image: np.ndarray  # BGR (H, W, 3)
    timestamp: float
    camera_id: str = ""
