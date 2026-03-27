import numpy as np
import pytest
from unittest.mock import patch, MagicMock
from model.base import InferResult, ModelBase
from model.yolo_model import YoloModel
from model.model_manager import ModelManager
from utils.singleton import SingletonMeta


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


def test_yolo_model_infer():
    with patch("model.yolo_model.YOLO") as MockYOLO:
        mock_yolo = MagicMock()
        MockYOLO.return_value = mock_yolo
        mock_result = MagicMock()
        mock_result.boxes.data.cpu().numpy.return_value = np.array([[10, 20, 100, 200, 0.9, 0]])
        mock_result.keypoints = None
        mock_result.masks = None
        mock_yolo.return_value = [mock_result]

        model = YoloModel()
        model.load("fake.pt", imgsz=640, conf=0.3, device="cpu")
        result = model.infer(np.zeros((640, 640, 3), dtype=np.uint8))
        assert result.boxes.shape == (1, 6)
        assert result.boxes[0, 4] == pytest.approx(0.9)

def test_yolo_model_empty_boxes():
    with patch("model.yolo_model.YOLO") as MockYOLO:
        mock_yolo = MagicMock()
        MockYOLO.return_value = mock_yolo
        mock_result = MagicMock()
        mock_result.boxes = None
        mock_result.keypoints = None
        mock_result.masks = None
        mock_yolo.return_value = [mock_result]
        model = YoloModel()
        model.load("fake.pt", imgsz=640, device="cpu")
        result = model.infer(np.zeros((640, 640, 3), dtype=np.uint8))
        assert result.boxes.shape == (0, 6)

def test_yolo_resolve_device_cpu():
    model = YoloModel()
    with patch("torch.cuda.is_available", return_value=False):
        assert model._resolve_device("auto") == "cpu"

def test_yolo_resolve_device_explicit():
    model = YoloModel()
    assert model._resolve_device("cpu") == "cpu"

def test_model_manager_singleton():
    SingletonMeta._instances.pop(ModelManager, None)
    assert ModelManager() is ModelManager()

def test_model_manager_get_unknown_raises():
    SingletonMeta._instances.pop(ModelManager, None)
    with pytest.raises(KeyError):
        ModelManager().get("nonexistent_model")


def test_model_manager_get_success():
    SingletonMeta._instances.pop(ModelManager, None)
    with patch("model.model_manager.YoloModel") as MockYoloModel:
        mock_model_instance = MagicMock()
        MockYoloModel.return_value = mock_model_instance

        mock_config = MagicMock()
        mock_config.root.items.return_value = [("det", MagicMock(path="w.pt", imgsz=640, conf=0.3))]

        manager = ModelManager()
        manager.init(mock_config, device="cpu")
        result = manager.get("det")
        assert result is mock_model_instance
