# 测试策略

## 测试原则

- 单元测试随各开发阶段**同步编写**，不延后到集成测试阶段
- 集成测试阶段仅补全端到端管道验证
- 外部依赖（Kafka、MinIO、MQTT）在单元测试中使用 `unittest.mock.patch` 隔离

---

## 测试目录结构

```
tests/
├── unit/
│   ├── test_regional_invasion.py
│   ├── test_kafka_output.py
│   └── ...
├── integration/
│   ├── test_camera_worker.py
│   └── test_api.py
├── fixtures/
│   └── sample.mp4              # 集成测试用本地视频
└── conftest.py                 # 公共 fixtures（MockDetector 等）
```

---

## 单元测试

### 检测器单元测试示例

```python
# tests/unit/test_regional_invasion.py
import numpy as np
from detector.regional_invasion import RegionalInvasionDetector
from model.base import InferResult
from pipeline.frame import Frame

def test_regional_invasion_detected():
    # 两阶段初始化：先构造，再调用 setup()
    detector = RegionalInvasionDetector(task_id="test_task", output_adapters=[])
    detector.setup({"conf_threshold": 0.5, "send_interval": 60, "forbidden_zone": []})

    # 构造模拟推理结果（置信度 0.9，高于阈值）
    infer_result = InferResult(boxes=np.array([[100, 100, 200, 200, 0.9, 0]]))
    frame = Frame(image=np.zeros((1080, 1920, 3), dtype=np.uint8), timestamp=0.0)

    events = detector.process(frame, infer_result)
    assert len(events) > 0
    assert events[0].violation_type == "regional_invasion"
    assert events[0].task_id == "test_task"

def test_no_detection_below_threshold():
    detector = RegionalInvasionDetector(task_id="test_task", output_adapters=[])
    detector.setup({"conf_threshold": 0.8, "send_interval": 60, "forbidden_zone": []})

    # 置信度 0.3，低于阈值
    infer_result = InferResult(boxes=np.array([[100, 100, 200, 200, 0.3, 0]]))
    frame = Frame(image=np.zeros((1080, 1920, 3), dtype=np.uint8), timestamp=0.0)

    events = detector.process(frame, infer_result)
    assert len(events) == 0
```

---

## conftest.py — 公共 Fixtures

```python
# tests/conftest.py
import pytest
from detector.base import DetectorBase
from pipeline.events import ViolationEvent

class MockDetector(DetectorBase):
    """用于集成测试的 mock 检测器，记录 process() 调用次数"""
    process_call_count = 0

    def setup(self, config) -> None:
        pass

    def process(self, frame, infer_result) -> list[ViolationEvent]:
        self.process_call_count += 1
        return []

@pytest.fixture
def mock_detector():
    detector = MockDetector(task_id="test_task", output_adapters=[])
    detector.process_call_count = 0
    return detector
```

---

## 集成测试

### CameraWorker 集成测试（本地 MP4 替换 RTSP）

```python
# tests/integration/test_camera_worker.py
import threading
import time
import pytest
from pipeline.camera_worker import CameraWorker
from pipeline.inference_pipeline import InferencePipeline
from config.models import CameraConfig

@pytest.fixture
def local_camera_config():
    """用本地 MP4 文件替换 RTSP URL，验证完整采集→推理管道"""
    return CameraConfig(
        id="test_cam",
        rtsp_url="tests/fixtures/sample.mp4",
        rtsp_interval=1.0,
    )

def test_camera_worker_processes_frames(local_camera_config, mock_detector):
    worker = CameraWorker(
        camera_config=local_camera_config,
        detectors=[mock_detector],
        infer_pipeline=InferencePipeline("yolo_detection"),
    )
    stop = threading.Event()
    worker._stop_event = stop
    worker.start()
    time.sleep(3)
    stop.set()
    worker.join(timeout=5)
    assert mock_detector.process_call_count > 0
```

### API 集成测试

```python
# tests/integration/test_api.py
from fastapi.testclient import TestClient
from api.app import create_app

def test_create_task():
    client = TestClient(create_app())
    resp = client.post("/api/v1/tasks", json={
        "task_id": "test_task_001",
        "camera": {"id": "CAM_001", "rtsp_url": "rtsp://localhost/test"},
        "detectors": [{"name": "regional_invasion", "config": {}}],
    })
    assert resp.status_code == 201
    assert resp.json()["success"] is True

def test_health_endpoint():
    client = TestClient(create_app())
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "healthy" in resp.json()
```

---

## 外部依赖 Mock 策略

使用 `unittest.mock.patch` 在单元测试中隔离外部依赖：

```python
# tests/unit/test_kafka_output.py
from unittest.mock import patch, MagicMock
from output.kafka_output import KafkaOutputAdapter
from pipeline.events import ViolationEvent
import numpy as np

def test_kafka_adapter_send():
    adapter = KafkaOutputAdapter()
    with patch("confluent_kafka.Producer") as MockProducer:
        mock_producer = MagicMock()
        MockProducer.return_value = mock_producer

        adapter.setup(MagicMock(bootstrap_servers="localhost:9092",
                                topic_violation="test"))

        event = ViolationEvent(
            task_id="t1", detector_name="d1", violation_type="test",
            timestamp=0.0, frame_snapshot=None, bounding_boxes=[]
        )
        adapter.send(event)
        mock_producer.produce.assert_called_once()
        mock_producer.poll.assert_called_once_with(0)
```

集成测试中使用 Docker 启动临时服务（Kafka、MinIO、MQTT）。

---

## 覆盖率要求

| 模块 | 最低覆盖率 |
|------|-----------|
| `detector/` | ≥ 80% |
| `model/` | ≥ 80% |
| `config/` | ≥ 90% |
| `output/` | ≥ 70% |
| `pipeline/` | ≥ 70% |

---

## 运行命令

```bash
# 仅单元测试
pytest tests/unit/ -v

# 带覆盖率报告
pytest --cov=. --cov-report=html --cov-fail-under=80

# 指定单个测试
pytest tests/unit/test_regional_invasion.py::test_regional_invasion_detected -v
```
