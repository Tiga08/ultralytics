import threading
import numpy as np
from unittest.mock import patch, MagicMock
from pipeline.capture import VideoCapture


def test_stream_yields_one_frame():
    fake_frame = np.zeros((480, 640, 3), dtype=np.uint8).tobytes()
    mock_proc = MagicMock()
    # 第一次返回完整帧，第二次返回空触发断流
    mock_proc.stdout.read.side_effect = [fake_frame, b""]

    with patch("subprocess.Popen", return_value=mock_proc), \
         patch.object(VideoCapture, "_probe_resolution", return_value=(640, 480)):
        cap = VideoCapture("rtsp://fake/stream", reconnect_interval=0)
        stop = threading.Event()
        frames = []
        for frame in cap.stream(stop, camera_id="CAM_001"):
            frames.append(frame)
            stop.set()

    assert len(frames) == 1
    assert frames[0].image.shape == (480, 640, 3)
    assert frames[0].camera_id == "CAM_001"


def test_stream_sets_timestamp():
    fake_frame = np.zeros((480, 640, 3), dtype=np.uint8).tobytes()
    mock_proc = MagicMock()
    mock_proc.stdout.read.side_effect = [fake_frame, b""]

    with patch("subprocess.Popen", return_value=mock_proc), \
         patch.object(VideoCapture, "_probe_resolution", return_value=(640, 480)):
        cap = VideoCapture("rtsp://fake/stream", reconnect_interval=0)
        stop = threading.Event()
        for frame in cap.stream(stop):
            assert frame.timestamp > 0
            stop.set()
