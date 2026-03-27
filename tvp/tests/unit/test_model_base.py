import numpy as np
import pytest
from model.base import InferResult, ModelBase


def test_infer_result_defaults():
    boxes = np.array([[10, 20, 100, 200, 0.9, 0]])
    r = InferResult(boxes=boxes)
    assert r.keypoints is None
    assert r.masks is None
    assert r.latency_ms == 0.0


def test_infer_result_empty_boxes():
    r = InferResult(boxes=np.empty((0, 6)))
    assert r.boxes.shape == (0, 6)


def test_model_base_is_abstract():
    with pytest.raises(TypeError):
        ModelBase()


def test_concrete_model_must_implement_all():
    class PartialModel(ModelBase):
        def load(self, weight_path, imgsz, **kwargs): pass
        # 缺少 infer 和 class_names
    with pytest.raises(TypeError):
        PartialModel()
