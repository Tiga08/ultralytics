from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import numpy as np


@dataclass
class InferResult:
    boxes: np.ndarray          # shape (N, 6): x1,y1,x2,y2,conf,cls
    keypoints: np.ndarray | None = None
    masks: np.ndarray | None = None
    latency_ms: float = 0.0


class ModelBase(ABC):
    @abstractmethod
    def load(self, weight_path: str, imgsz: int, **kwargs) -> None: ...

    @abstractmethod
    def infer(self, frame: np.ndarray) -> InferResult: ...

    @property
    @abstractmethod
    def class_names(self) -> dict[int, str]: ...
