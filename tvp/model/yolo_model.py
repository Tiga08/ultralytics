# tvp/model/yolo_model.py
import time
import numpy as np
import torch
from ultralytics import YOLO
from model.base import ModelBase, InferResult


class YoloModel(ModelBase):
    def __init__(self):
        self._model = None
        self._imgsz = 640
        self._conf = 0.3
        self._device = "cpu"

    def load(self, weight_path: str, imgsz: int = 640,
             conf: float = 0.3, device: str = "auto") -> None:
        self._model = YOLO(weight_path)
        self._imgsz = imgsz
        self._conf = conf
        self._device = self._resolve_device(device)

    def infer(self, frame: np.ndarray) -> InferResult:
        t0 = time.monotonic()
        results = self._model(
            frame, imgsz=self._imgsz, conf=self._conf,
            device=self._device, verbose=False
        )
        latency = (time.monotonic() - t0) * 1000
        r = results[0]
        boxes = r.boxes.data.cpu().numpy() if r.boxes is not None else np.empty((0, 6))
        kps = r.keypoints.data.cpu().numpy() if r.keypoints is not None else None
        masks = r.masks.data.cpu().numpy() if r.masks is not None else None
        return InferResult(boxes=boxes, keypoints=kps, masks=masks, latency_ms=latency)

    @property
    def class_names(self) -> dict[int, str]:
        return self._model.names if self._model else {}

    def _resolve_device(self, device: str) -> str:
        if device != "auto":
            return device
        if torch.cuda.is_available():
            return "cuda:0"
        try:
            import torch_npu
            if torch_npu.npu.is_available():
                return "npu:0"
        except ImportError:
            pass
        try:
            import torch_mlu
            if torch.mlu.is_available():
                return "mlu:0"
        except ImportError:
            pass
        return "cpu"
