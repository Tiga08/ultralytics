import numpy as np
from unittest.mock import MagicMock
from pipeline.camera_worker import CameraWorker
from pipeline.frame import Frame
from model.base import InferResult
from config.models import CameraConfig


def _make_worker(detectors=None):
    camera_config = CameraConfig(id="CAM_T", rtsp_url="rtsp://fake/s")
    mock_pipeline = MagicMock()
    mock_pipeline.run.return_value = InferResult(boxes=np.empty((0, 6)))
    return CameraWorker(
        camera_config=camera_config,
        detectors=detectors or [],
        infer_pipeline=mock_pipeline,
    )


def test_camera_worker_is_daemon():
    worker = _make_worker()
    assert worker.daemon is True


def test_camera_worker_is_healthy_initially():
    worker = _make_worker()
    assert worker.is_healthy is True


def test_process_frame_calls_active_detector():
    mock_detector = MagicMock()
    mock_detector.is_active.return_value = True
    mock_detector.process.return_value = []
    worker = _make_worker(detectors=[mock_detector])
    fake_frame = Frame(image=np.zeros((480, 640, 3), dtype=np.uint8),
                       timestamp=1.0, camera_id="CAM_T")
    worker._process_frame(fake_frame)
    mock_detector.process.assert_called_once()


def test_process_frame_skips_inactive_detector():
    mock_detector = MagicMock()
    mock_detector.is_active.return_value = False
    worker = _make_worker(detectors=[mock_detector])
    fake_frame = Frame(image=np.zeros((480, 640, 3), dtype=np.uint8),
                       timestamp=1.0, camera_id="CAM_T")
    worker._process_frame(fake_frame)
    mock_detector.process.assert_not_called()
