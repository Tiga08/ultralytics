import json
import numpy as np
from unittest.mock import MagicMock
from output.local_output import LocalOutputAdapter
from pipeline.events import ViolationEvent


def test_local_output_creates_json_file(tmp_path):
    adapter = LocalOutputAdapter()
    adapter.setup(MagicMock(output_dir=str(tmp_path)))
    event = ViolationEvent(
        task_id="t1", detector_name="d1", violation_type="invasion",
        timestamp=1000.123,
        frame_snapshot=np.zeros((100, 100, 3), dtype=np.uint8),
        bounding_boxes=[[1, 2, 3, 4]],
    )
    adapter.send(event)
    json_files = list(tmp_path.glob("*.json"))
    assert len(json_files) == 1
    data = json.loads(json_files[0].read_text())
    assert data["task_id"] == "t1"
    assert data["violation_type"] == "invasion"
