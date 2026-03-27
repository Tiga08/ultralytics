import numpy as np
import pytest
from unittest.mock import MagicMock
from detector.regional_invasion import RegionalInvasionDetector
from model.base import InferResult
from pipeline.frame import Frame
from pipeline.events import ViolationEvent


def make_detector(conf_threshold=0.5):
    d = RegionalInvasionDetector(task_id="test_task", output_adapters=[])
    d.setup({"conf_threshold": conf_threshold, "send_interval": 60, "forbidden_zone": []})
    return d


def test_regional_invasion_detected():
    d = make_detector(conf_threshold=0.5)
    infer = InferResult(boxes=np.array([[100, 100, 200, 200, 0.9, 0]]))
    frame = Frame(image=np.zeros((1080, 1920, 3), dtype=np.uint8), timestamp=0.0)
    events = d.process(frame, infer)
    assert len(events) > 0
    assert events[0].violation_type == "regional_invasion"
    assert events[0].task_id == "test_task"


def test_no_detection_below_threshold():
    d = make_detector(conf_threshold=0.8)
    infer = InferResult(boxes=np.array([[100, 100, 200, 200, 0.3, 0]]))
    frame = Frame(image=np.zeros((1080, 1920, 3), dtype=np.uint8), timestamp=0.0)
    assert d.process(frame, infer) == []


def test_no_detection_empty_boxes():
    d = make_detector()
    infer = InferResult(boxes=np.empty((0, 6)))
    frame = Frame(image=np.zeros((1080, 1920, 3), dtype=np.uint8), timestamp=0.0)
    assert d.process(frame, infer) == []


def test_detector_pause_resume():
    d = make_detector()
    d.pause()
    assert d.is_active() is False
    d.resume()
    assert d.is_active() is True


def test_emit_violation_calls_adapter():
    mock_adapter = MagicMock()
    d = RegionalInvasionDetector(task_id="t1", output_adapters=[mock_adapter])
    d.setup({})
    event = ViolationEvent(task_id="t1", detector_name="regional_invasion",
                           violation_type="regional_invasion",
                           timestamp=0.0, frame_snapshot=None, bounding_boxes=[])
    d.emit_violation(event)
    mock_adapter.send.assert_called_once_with(event)


def test_cleanup_resets_tracker():
    d = make_detector()
    d._tracker._frame_id = 50
    d.cleanup()
    assert d._tracker._frame_id == 0
