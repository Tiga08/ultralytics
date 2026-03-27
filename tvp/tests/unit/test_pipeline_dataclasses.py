import numpy as np

from pipeline.frame import Frame
from pipeline.events import ViolationEvent


def test_frame_default_camera_id():
    f = Frame(image=np.zeros((100, 100, 3), dtype=np.uint8), timestamp=1.0)
    assert f.camera_id == ""


def test_violation_event_extra_default_factory():
    e1 = ViolationEvent(task_id="t1", detector_name="d", violation_type="v",
                        timestamp=0.0, frame_snapshot=None, bounding_boxes=[])
    e2 = ViolationEvent(task_id="t2", detector_name="d", violation_type="v",
                        timestamp=0.0, frame_snapshot=None, bounding_boxes=[])
    e1.extra["key"] = "val"
    assert "key" not in e2.extra  # 确保 default_factory 不共享实例


def test_violation_event_fields():
    e = ViolationEvent(task_id="t1", detector_name="d1", violation_type="invasion",
                       timestamp=1000.0, frame_snapshot=None,
                       bounding_boxes=[[1, 2, 3, 4]])
    assert e.task_id == "t1"
    assert len(e.bounding_boxes) == 1
