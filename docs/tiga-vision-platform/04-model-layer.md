# 模型推理层

## 设计原则

`ultralytics.YOLO` 作为统一推理后端，`ModelBase` ABC 屏蔽差异，`ModelManager` 单例避免重复加载。

---

## InferResult — 推理结果数据结构

```python
@dataclass
class InferResult:
    boxes: np.ndarray           # shape (N, 6): x1,y1,x2,y2,conf,cls
    keypoints: np.ndarray | None = None
    masks: np.ndarray | None = None
    latency_ms: float = 0.0
```

---

## ModelBase — 抽象接口

```python
class ModelBase(ABC):
    @abstractmethod
    def load(self, weight_path: str, imgsz: int, **kwargs) -> None: ...

    @abstractmethod
    def infer(self, frame: np.ndarray) -> InferResult: ...

    @property
    @abstractmethod
    def class_names(self) -> dict[int, str]: ...
```

---

## YoloModel — ultralytics 封装

**文件**：`model/yolo_model.py`

### 核心实现

```python
class YoloModel(ModelBase):

    def load(self, weight_path: str, imgsz: int = 640,
             conf: float = 0.3, device: str = "auto") -> None:
        self._model = YOLO(weight_path)
        self._imgsz = imgsz
        self._conf = conf
        self._device = self._resolve_device(device)

    def infer(self, frame: np.ndarray) -> InferResult:
        results = self._model(frame, imgsz=self._imgsz,
                              conf=self._conf, device=self._device, verbose=False)
        r = results[0]
        return InferResult(
            boxes=r.boxes.data.cpu().numpy() if r.boxes else np.empty((0, 6)),
            keypoints=r.keypoints.data.cpu().numpy() if r.keypoints else None,
            masks=r.masks.data.cpu().numpy() if r.masks else None,
            latency_ms=...
        )
```

### 设备自动检测逻辑（`_resolve_device`）

优先级：`CUDA` → `NPU（Ascend/torch_npu）` → `MLU（寒武纪/torch_mlu）` → `CPU`

最终选定的设备在启动时记录到日志：`logger.info("model_device_selected", device=...)`。

```python
def _resolve_device(self, device: str) -> str:
    if device != "auto":
        return device
    if torch.cuda.is_available():
        return "cuda:0"
    try:
        import torch_npu
        if torch_npu.npu.is_available():
            return "npu:0"
    except ImportError:
        pass
    try:
        import torch_mlu
        if torch.mlu.is_available():
            return "mlu:0"
    except ImportError:
        pass
    return "cpu"
```

---

## ModelManager — 单例管理器

**文件**：`model/model_manager.py`

### 职责

- 按配置预加载所有模型权重，避免多任务共享同一推理后端时重复加载
- 按模型名称缓存已加载的模型实例
- 通过 `SingletonMeta` 保证全局唯一实例

### 接口

```python
class ModelManager(metaclass=SingletonMeta):

    def init(self, config: ModelWeightsConfig, device: str = "auto") -> None:
        """按配置预加载所有模型权重，在 TvpEngine.start() 中调用"""
        for name, entry in config.root.items():
            self._load_model(name, entry.path, entry.imgsz, entry.conf, device)

    def get(self, name: str) -> ModelBase:
        """按名称获取已加载的模型，未找到时抛出 KeyError"""
        # init() 中任意模型加载失败（路径不存在、显存不足等）会抛出 RuntimeError，
        # 导致 TvpEngine.start() 中断，不会静默跳过
```

### 使用方式

`TvpEngine.start()` 时初始化：

```python
ModelManager().init(config.model_weights)
```

`InferencePipeline` 中使用：

```python
model = ModelManager().get("yolo_detection")
result = model.infer(frame.image)
```

---

## 扩展：支持其他模型后端

通过实现 `ModelBase` ABC 并注册到 `ModelManager` 即可接入非 YOLO 模型：

```python
class OnnxModel(ModelBase):
    def load(self, weight_path: str, imgsz: int = 640, **kwargs) -> None:
        import onnxruntime as ort
        self._session = ort.InferenceSession(weight_path,
                                             providers=["CUDAExecutionProvider",
                                                        "CPUExecutionProvider"])
        self._imgsz = imgsz
        self._input_name = self._session.get_inputs()[0].name

    def infer(self, frame: np.ndarray) -> InferResult:
        # 预处理：resize → normalize → NCHW
        blob = self._preprocess(frame)
        outputs = self._session.run(None, {self._input_name: blob})
        boxes = self._postprocess(outputs)
        return InferResult(boxes=boxes)

    @property
    def class_names(self) -> dict[int, str]:
        return {}  # 按实际模型填写
```
