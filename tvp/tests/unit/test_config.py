import pytest
import yaml
from config.models import (
    TvpConfig, TaskConfig, ModelWeightsConfig,
)
from config.loader import ConfigLoader


def test_tvp_config_requires_model_weights():
    with pytest.raises(Exception):
        TvpConfig.model_validate({})


def test_tvp_config_defaults():
    config = TvpConfig.model_validate({
        "model_weights": {"yolo_detection": {"path": "weights/yolo.pt"}}
    })
    assert config.server.port == 8555
    assert config.video.reconnect_interval == 5
    assert config.kafka is None


def test_model_weights_root_model():
    mwc = ModelWeightsConfig.model_validate({
        "yolo_detection": {"path": "weights/yolo.pt", "imgsz": 960}
    })
    assert "yolo_detection" in mwc.root
    assert mwc.root["yolo_detection"].conf == 0.3


def test_task_config_full():
    data = {
        "task_id": "task_001",
        "camera": {"id": "CAM_001", "rtsp_url": "rtsp://localhost/test"},
        "detectors": [{"name": "regional_invasion", "config": {}}],
    }
    tc = TaskConfig.model_validate(data)
    assert tc.priority == "NORMAL"


def test_task_config_camera_required():
    with pytest.raises(Exception):
        TaskConfig.model_validate({"task_id": "t1", "detectors": []})


def test_config_loader_from_yaml(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({
        "model_weights": {"det": {"path": "w.pt"}},
        "server": {"port": 9000},
    }))
    config = ConfigLoader.load(str(cfg_file))
    assert config.server.port == 9000


def test_config_loader_env_override(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml.dump({"model_weights": {"det": {"path": "w.pt"}}}))
    monkeypatch.setenv("TVP__SERVER__PORT", "7777")
    config = ConfigLoader.load(str(cfg_file))
    assert config.server.port == 7777


def test_config_loader_load_task(tmp_path):
    task_file = tmp_path / "task.yaml"
    task_file.write_text(yaml.dump({
        "task_id": "t_yaml",
        "camera": {"id": "C1", "rtsp_url": "rtsp://x/s"},
        "detectors": [{"name": "regional_invasion"}],
    }))
    tc = ConfigLoader.load_task(str(task_file))
    assert tc.task_id == "t_yaml"
