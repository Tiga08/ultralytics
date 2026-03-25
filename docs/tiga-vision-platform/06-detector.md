# 检测器插件

## ViolationEvent — 违规事件

**文件**：`pipeline/events.py`（注意：不在 `detector/` 下）

```python
@dataclass
class ViolationEvent:
    task_id: str
    detector_name: str
    violation_type: str
    timestamp: float
    frame_snapshot: Any          # numpy array，BGR 格式
    bounding_boxes: list[list[float]]
    extra: dict = field(default_factory=dict)
```

**为何放在 `pipeline/` 层？**

避免循环导入：
- `output/base.py` 需要 `ViolationEvent`（来自 detector）
- `detector/base.py` 需要 `OutputAdapterBase`（来自 output）

将 `ViolationEvent` 上移到两者共同依赖的 `pipeline` 层即可打破循环。

---

## DetectorBase — 检测器基类

**文件**：`detector/base.py`

### 生命周期

```
1. __init__(task_id, output_adapters)   # 仅保存基础引用
2. setup(config)                         # TvpEngine 构造后显式调用，完成参数初始化
3. process(frame, infer_result)          # 每帧调用（is_active() 为 True 时）
4. cleanup()                             # 任务停止时调用，释放资源
```

**两阶段初始化的意义**：避免父类构造器中调用抽象方法的反模式，使子类可在 `__init__` 中安全初始化自己的属性（如 `ByteTrackWrapper`），再由 `setup()` 使用它们。

### 核心接口

```python
class DetectorBase(ABC):

    # 子类可声明 CONFIG_CLASS，TvpEngine 会自动将裸字典 validate 为该类型
    CONFIG_CLASS: type | None = None

    @abstractmethod
    def setup(self, config: Any) -> None:
        """初始化检测器参数，config 已经过 Pydantic validate（若声明了 CONFIG_CLASS）"""

    @abstractmethod
    def process(self, frame: Frame, infer_result: InferResult) -> list[ViolationEvent]:
        """处理单帧，返回违规事件列表（可为空）"""

    def emit_violation(self, event: ViolationEvent) -> None:
        """向所有输出适配器发送违规事件"""

    def cleanup(self) -> None:
        """任务停止时调用，默认空实现，子类按需 override"""

    # 暂停/恢复控制
    def is_active(self) -> bool: ...
    def pause(self): ...
    def resume(self): ...
```

### CONFIG_CLASS 自动 Validate

```python
@PluginRegistry.detector("regional_invasion")
class RegionalInvasionDetector(DetectorBase):
    CONFIG_CLASS = RegionalInvasionConfig   # 声明配置类型

    def setup(self, config: RegionalInvasionConfig) -> None:
        # config 已是 Pydantic 对象，类型安全
        self.conf_threshold = config.conf_threshold
```

`TvpEngine.create_task()` 中自动处理：

```python
if klass.CONFIG_CLASS is not None:
    cfg_dict = klass.CONFIG_CLASS.model_validate(cfg_dict)
detector.setup(cfg_dict)
```

---

## ByteTrackWrapper — 目标跟踪

**文件**：`pipeline/bytetrack_wrapper.py`

每个检测器实例内部持有一个**独立的** `ByteTrackWrapper`，确保不同检测器的目标轨迹互不干扰。

```python
@dataclass
class TrackResult:
    track_id: int
    box: np.ndarray   # shape (4,): x1, y1, x2, y2
    score: float
    cls: int

class ByteTrackWrapper:
    def __init__(self, high_thresh=0.6, low_thresh=0.1, buffer=30): ...

    def update(self, boxes: np.ndarray) -> list[TrackResult]:
        """输入 shape (N,6) 检测框，返回活跃轨迹列表"""

    def reset(self) -> None:
        """重置 tracker 内部状态（任务重启时调用）"""
```

---

## 检测器开发快速指南（5 步）

### 第 1 步：创建文件 `detector/my_detector.py`

### 第 2 步：定义配置模型（Pydantic）

```python
from pydantic import BaseModel

class MyDetectorConfig(BaseModel):
    conf_threshold: float = 0.5
    send_interval: int = 60
    # ... 其他参数
```

### 第 3 步：注册插件并声明 CONFIG_CLASS

```python
from core.registry import PluginRegistry
from detector.base import DetectorBase

@PluginRegistry.detector("my_detector")
class MyDetector(DetectorBase):
    CONFIG_CLASS = MyDetectorConfig

    def __init__(self, task_id, output_adapters):
        super().__init__(task_id, output_adapters)
        self._tracker = ByteTrackWrapper()  # 安全：在 __init__ 中初始化
```

### 第 4 步：实现 setup 和 process

```python
    def setup(self, config: MyDetectorConfig) -> None:
        self.conf_threshold = config.conf_threshold
        self.send_interval = config.send_interval

    def process(self, frame: Frame, infer_result: InferResult) -> list[ViolationEvent]:
        tracks = self._tracker.update(infer_result.boxes)
        violations = []
        for track in tracks:
            if self._is_violation(track):
                violations.append(ViolationEvent(
                    task_id=self._task_id,
                    detector_name="my_detector",
                    violation_type="my_violation",
                    timestamp=frame.timestamp,
                    frame_snapshot=frame.image,
                    bounding_boxes=[track.box.tolist()],
                ))
        return violations

    def cleanup(self) -> None:
        self._tracker.reset()   # 任务重启时清空轨迹状态
```

### 第 5 步：在 `detector/__init__.py` 中添加导入

```python
# detector/__init__.py
from .my_detector import MyDetector   # noqa: F401
```

完成后即可在任务 YAML 中使用：

```yaml
detectors:
  - name: "my_detector"
    config:
      conf_threshold: 0.6
      send_interval: 30
```

---

## RegionalInvasionDetector 完整示例

```python
# detector/regional_invasion.py
from pydantic import BaseModel
from core.registry import PluginRegistry
from detector.base import DetectorBase
from pipeline.frame import Frame
from pipeline.events import ViolationEvent
from pipeline.bytetrack_wrapper import ByteTrackWrapper
from model.base import InferResult

class RegionalInvasionConfig(BaseModel):
    send_interval: int = 60
    conf_threshold: float = 0.5
    forbidden_zone: list[list[int]] = []

@PluginRegistry.detector("regional_invasion")
class RegionalInvasionDetector(DetectorBase):
    CONFIG_CLASS = RegionalInvasionConfig

    def __init__(self, task_id, output_adapters):
        super().__init__(task_id, output_adapters)
        self._tracker = ByteTrackWrapper()

    def setup(self, config: RegionalInvasionConfig) -> None:
        self.conf_threshold = config.conf_threshold
        self.send_interval = config.send_interval
        self.forbidden_zone = config.forbidden_zone

    def process(self, frame: Frame, infer_result: InferResult) -> list[ViolationEvent]:
        violations = []
        for box in infer_result.boxes:
            if box[4] > self.conf_threshold:
                violations.append(ViolationEvent(
                    task_id=self._task_id,
                    detector_name="regional_invasion",
                    violation_type="regional_invasion",
                    timestamp=frame.timestamp,
                    frame_snapshot=frame.image,
                    bounding_boxes=[box[:4].tolist()]
                ))
        return violations

    def cleanup(self) -> None:
        self._tracker.reset()
```
