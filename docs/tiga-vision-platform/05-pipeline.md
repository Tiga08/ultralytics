# 视频处理管道

## 组件概览

| 组件 | 文件 | 职责 |
|------|------|------|
| `Frame` | `pipeline/frame.py` | 单帧数据载体 |
| `VideoCapture` | `pipeline/capture.py` | FFmpeg RTSP 采集，断线重连 |
| `InferencePipeline` | `pipeline/inference_pipeline.py` | 从 ModelManager 取模型执行推理 |
| `CameraWorker` | `pipeline/camera_worker.py` | 每摄像头一个线程，串联采集→推理→检测 |

---

## Frame — 帧数据模型

```python
@dataclass
class Frame:
    image: np.ndarray    # BGR 格式，shape (H, W, 3)
    timestamp: float     # Unix 时间戳（秒）
    camera_id: str = ""  # 来源摄像头 ID，由 CameraWorker 填充
```

`Frame` 是管道中流转的基础数据单元，在 `VideoCapture`、`InferencePipeline`、`DetectorBase` 之间传递。

---

## VideoCapture — RTSP 采集

**文件**：`pipeline/capture.py`

### 设计要点

- 使用 **FFmpeg 子进程**拉取 RTSP 流，通过 stdout 管道读取原始 BGR 帧
- 每次（重）连接前用 `ffprobe` 获取流分辨率，无需硬编码宽高
- 检测到断流时自动等待 `reconnect_interval` 秒后重连
- `stream()` 是生成器方法，`stop_event` 置位时退出

### FFmpeg 命令参数

```bash
ffmpeg -rtsp_transport tcp \
       -i <rtsp_url> \
       -vf "fps=<1/interval>" \      # interval=0.5 → fps=2.0
       -f rawvideo -pix_fmt bgr24 pipe:1
```

### ffprobe 分辨率探测

```bash
ffprobe -v error -select_streams v:0 \
        -show_entries stream=width,height \
        -of csv=p=0 <rtsp_url>
```

输出格式：`1920,1080`

### 关键接口

```python
class VideoCapture:
    def stream(self, stop_event: threading.Event):
        """生成器：持续产出 Frame，stop_event 置位时退出"""
        while not stop_event.is_set():
            # ffprobe 探测分辨率 → 启动 ffmpeg → 读帧循环
            # 任何异常 → kill ffmpeg → sleep → 重连
```

---

## InferencePipeline — 推理管道

**文件**：`pipeline/inference_pipeline.py`

```python
class InferencePipeline:
    def __init__(self, model_name: str,
                 model_manager: ModelManager | None = None) -> None:
        self._model_name = model_name
        self._mm = model_manager or ModelManager()

    def run(self, frame: Frame) -> InferResult:
        model = self._mm.get(self._model_name)
        return model.infer(frame.image)
```

`model_name` 对应 `config.yaml` 中 `model_weights` 的 key（如 `"yolo_detection"`）。

---

## CameraWorker — 摄像头工作线程

**文件**：`pipeline/camera_worker.py`

### 生命周期

```
start() → run() → VideoCapture.stream() → 每帧循环：
    infer_pipeline.run(frame)
    for detector in detectors:
        if detector.is_active():
            violations = detector.process(frame, infer_result)
            for v in violations:
                detector.emit_violation(v)
stop() → stop_event.set() → 等待 VideoCapture 生成器退出
```

### 健康检查

```python
@property
def is_healthy(self) -> bool:
    """超过 60 秒没有新帧，认为不健康"""
    return (time.time() - self._health_last_frame_ts) < 60
```

`HealthMonitor` 定期调用此属性，不健康时触发重启。

### 构造参数

```python
CameraWorker(
    camera_config: CameraConfig,
    detectors: list[DetectorBase],
    infer_pipeline: InferencePipeline,
)
```

每个 `CameraWorker` 是一个 `daemon=True` 的线程，线程名为 `cam-{camera_id}`。

---

## 暂停行为说明

`pause_task()` 调用后，`CameraWorker` 线程**继续运行**（继续采帧推理），但每个 `DetectorBase.is_active()` 返回 `False`，因此检测器的 `process()` 不会被调用，不产生违规事件。

这样设计的好处：恢复时无需重启线程，响应更快。
