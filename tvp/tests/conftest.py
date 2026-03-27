import pytest
import numpy as np

from detector.base import DetectorBase
from pipeline.events import ViolationEvent
from pipeline.frame import Frame
from model.base import InferResult


class MockDetector(DetectorBase):
    def __init__(self, task_id, output_adapters):
        super().__init__(task_id, output_adapters)
        self.process_call_count = 0

    def setup(self, config) -> None:
        pass

    def process(self, frame, infer_result) -> list[ViolationEvent]:
        self.process_call_count += 1
        return []


@pytest.fixture
def mock_detector():
    return MockDetector(task_id="test_task", output_adapters=[])


@pytest.fixture
def sample_frame():
    return Frame(
        image=np.zeros((1080, 1920, 3), dtype=np.uint8),
        timestamp=1.0,
        camera_id="CAM_TEST",
    )


@pytest.fixture
def empty_infer_result():
    return InferResult(boxes=np.empty((0, 6)))
