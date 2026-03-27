import numpy as np
from pipeline.bytetrack_wrapper import ByteTrackWrapper, TrackResult


def test_update_empty_boxes_returns_empty():
    tracker = ByteTrackWrapper()
    result = tracker.update(np.empty((0, 6)))
    assert result == []


def test_reset_clears_frame_id():
    tracker = ByteTrackWrapper()
    tracker._frame_id = 99
    tracker.reset()
    assert tracker._frame_id == 0


def test_track_result_fields():
    import numpy as np
    t = TrackResult(track_id=1, box=np.array([10, 20, 100, 200]), score=0.9, cls=0)
    assert t.track_id == 1
