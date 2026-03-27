from dataclasses import dataclass
import numpy as np
from utils.logger import logger


@dataclass
class TrackResult:
    track_id: int
    box: np.ndarray   # shape (4,): x1,y1,x2,y2
    score: float
    cls: int


class ByteTrackWrapper:
    def __init__(self, high_thresh: float = 0.6,
                 low_thresh: float = 0.1, buffer: int = 30):
        self._high_thresh = high_thresh
        self._low_thresh = low_thresh
        self._buffer = buffer
        self._frame_id = 0
        self._tracker = None
        self._init_tracker()

    def _init_tracker(self):
        try:
            from ultralytics.trackers.byte_tracker import BYTETracker
            class _Args:
                track_high_thresh = self._high_thresh
                track_low_thresh = self._low_thresh
                track_buffer = self._buffer
                match_thresh = 0.8
                mot20 = False
            self._tracker = BYTETracker(_Args(), frame_rate=30)
        except Exception as e:
            logger.warning("bytetrack_init_failed", error=str(e))
            self._tracker = None

    def update(self, boxes: np.ndarray) -> list[TrackResult]:
        if self._tracker is None or len(boxes) == 0:
            return []
        self._frame_id += 1
        try:
            tracks = self._tracker.update(boxes, (640, 640), (640, 640))
            return [
                TrackResult(
                    track_id=int(t.track_id),
                    box=t.tlbr,
                    score=float(t.score),
                    cls=int(t.cls) if hasattr(t, "cls") else 0,
                )
                for t in tracks
            ]
        except Exception as e:
            logger.warning("bytetrack_update_failed", error=str(e))
            return []

    def reset(self) -> None:
        self._frame_id = 0
        self._init_tracker()
