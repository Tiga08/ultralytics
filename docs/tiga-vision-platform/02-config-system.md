# 配置系统

## 设计原则

层级化 Pydantic v2 模型，YAML 主配置 + 任务级 YAML 覆盖，运行时类型检查。

**加载优先级（高 → 低）：**
1. 环境变量（前缀 `TVP__`）
2. 命令行参数（`--config path/to/config.yaml`）
3. 项目 `config.yaml`
4. Pydantic 默认值

---

## 全局配置模型（`config/models.py`）

### TvpConfig — 根模型

```python
class TvpConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    video: VideoConfig = VideoConfig()
    inference: InferenceConfig = InferenceConfig()
    model_weights: ModelWeightsConfig      # 必填
    tracking: TrackingConfig = TrackingConfig()
    kafka: KafkaConfig | None = None       # None 表示禁用
    minio: MinioConfig | None = None
    mqtt: MqttConfig | None = None
    health: HealthConfig = HealthConfig()
    logging: LoggingConfig = LoggingConfig()
```

### 各子配置说明

| 模型 | 关键字段 | 默认值 | 单位/说明 |
|------|---------|--------|----------|
| `ServerConfig` | `host`, `port` | `0.0.0.0`, `8555` | — |
| `VideoConfig` | `capture_backend`, `reconnect_interval`, `frame_queue_size` | `ffmpeg`, `5`, `30` | `reconnect_interval` 单位：秒；`frame_queue_size` 单位：帧数 |
| `InferenceConfig` | `backend`, `thread_count` | `auto`, `4` | `backend`：`auto \| pytorch \| tensorrt \| cpu` |
| `TrackingConfig` | `high_thresh`, `low_thresh`, `buffer` | `0.6`, `0.1`, `30` | `buffer` 单位：帧数（遮挡容忍帧数） |
| `HealthConfig` | `check_interval`, `restart_on_failure`, `max_restart_count` | `30`, `true`, `3` | `check_interval` 单位：秒 |
| `LoggingConfig` | `level`, `format`, `file_path` | `INFO`, `json`, `logs/` | `format`：`json \| text` |

### ModelWeightsConfig — RootModel 设计

```python
class ModelWeightEntry(BaseModel):
    path: str        # 相对于项目根目录（run.py 所在目录），或使用绝对路径
    imgsz: int = 640
    conf: float = 0.3

class ModelWeightsConfig(RootModel[dict[str, ModelWeightEntry]]):
    """key 为模型名称，value 为权重配置。
    使用 RootModel 避免每新增一个模型都要修改类定义。

    用法：
        entry = config.root["yolo_detection"]   # 访问指定模型
        for name, entry in config.root.items(): # 遍历所有模型
    """
```

**设计意图**：新增模型只需在 `config.yaml` 中追加一项，无需修改任何 Python 代码。

---

## 任务级配置模型

```python
class CameraConfig(BaseModel):
    id: str
    name: str = ""
    rtsp_url: str
    rtsp_interval: float = 0.5    # 采帧间隔（秒）

class ScheduleConfig(BaseModel):
    enabled_days: list[int] = [1,2,3,4,5,6,7]  # 1=周一 … 7=周日
    start_time: str = "00:00:00"
    end_time: str = "23:59:59"

class DetectorTaskConfig(BaseModel):
    name: str           # 对应 PluginRegistry 中注册的检测器名称
    config: dict = {}   # 透传给检测器 setup() 的参数字典

class TaskConfig(BaseModel):
    task_id: str
    task_name: str = ""
    stand_id: str = ""
    priority: str = "NORMAL"      # CRITICAL | HIGH | NORMAL | LOW
    camera: CameraConfig
    schedule: ScheduleConfig = ScheduleConfig()
    detectors: list[DetectorTaskConfig]
```

---

## config.yaml 示例

```yaml
server:
  host: "0.0.0.0"
  port: 8555

video:
  capture_backend: "ffmpeg"
  reconnect_interval: 5
  frame_queue_size: 30

inference:
  backend: "auto"       # auto | pytorch | tensorrt | cpu
  thread_count: 4

model_weights:
  yolo_detection:
    path: "weights/yolov8m_det.pt"
    imgsz: 960
    conf: 0.3
  person_det:             # 新增模型只需在此追加
    path: "weights/yolo11x.pt"
    imgsz: 640
    conf: 0.25

tracking:
  high_thresh: 0.6
  low_thresh: 0.1
  buffer: 30

kafka:
  bootstrap_servers: "tiga-kafka:9092"
  topic_violation: "tvp_violation_events"

minio:
  endpoint: "tiga-minio:9000"
  access_key: "..."
  secret_key: "..."
  bucket: "tvp-evidence"

mqtt:
  host: "tiga-mqtt"
  port: 1883
  topic_violation: "tvp/violation"

logging:
  level: "INFO"
  format: "json"         # json | text
  file_path: "logs/"

health:
  check_interval: 30
  restart_on_failure: true
  max_restart_count: 3
```

---

## 完整 config.yaml 模板

以下为包含所有字段的完整配置模板（可选项标有注释）：

```yaml
server:
  host: "0.0.0.0"
  port: 8555

video:
  capture_backend: "ffmpeg"
  reconnect_interval: 5     # 断线重连间隔（秒）
  frame_queue_size: 30      # 内部帧缓冲大小（帧数）

inference:
  backend: "auto"           # auto | pytorch | tensorrt | cpu
  thread_count: 4

model_weights:
  yolo_detection:
    path: "weights/yolov8m_det.pt"    # 相对于项目根目录，或绝对路径
    imgsz: 960
    conf: 0.3
  # person_det:                       # 新增模型只需在此追加，无需修改代码
  #   path: "weights/yolo11x.pt"
  #   imgsz: 640
  #   conf: 0.25

tracking:
  high_thresh: 0.6
  low_thresh: 0.1
  buffer: 30                # 遮挡容忍帧数

# kafka:                    # 可选，注释掉或设为 null 表示禁用
#   bootstrap_servers: "tiga-kafka:9092"
#   topic_violation: "tvp_violation_events"

# minio:                    # 可选
#   endpoint: "tiga-minio:9000"
#   access_key: "..."       # 建议通过环境变量 TVP__MINIO__ACCESS_KEY 注入
#   secret_key: "..."       # 建议通过环境变量 TVP__MINIO__SECRET_KEY 注入
#   bucket: "tvp-evidence"
#   secure: false

# mqtt:                     # 可选
#   host: "tiga-mqtt"
#   port: 1883
#   topic_violation: "tvp/violation"

logging:
  level: "INFO"             # DEBUG | INFO | WARNING | ERROR
  format: "json"            # json | text
  file_path: "logs/"

health:
  check_interval: 30        # 健康检查间隔（秒）
  restart_on_failure: true
  max_restart_count: 3
  # camera_timeout: 60      # 摄像头无新帧超时（秒），建议新增字段
```

---

## 安全实践

敏感字段（密钥、密码）**不应**明文写入版本控制的 `config.yaml`。推荐做法：

```bash
# 通过环境变量注入敏感值
export TVP__MINIO__ACCESS_KEY=minioadmin
export TVP__MINIO__SECRET_KEY=your_secret
export TVP__KAFKA__BOOTSTRAP_SERVERS=kafka.internal:9092
```

或使用 `.env` 文件（加入 `.gitignore`）配合 `python-dotenv` 在启动前加载。

---

## 任务级 YAML 示例

```yaml
# tasks/regional_invasion.yaml
task_id: "regional_invasion_stand_a1_cam1"
task_name: "A1 机位区域入侵检测"
stand_id: "STAND_A1"
camera:
  id: "CAM_A1_001"
  name: "A1_北侧相机"
  rtsp_url: "rtsp://tiga-camera:8554/stream1"
  rtsp_interval: 0.5

schedule:
  enabled_days: [1, 2, 3, 4, 5, 6, 7]
  start_time: "00:00:00"
  end_time: "23:59:59"

detectors:
  - name: "regional_invasion"
    config:
      send_interval: 60
      conf_threshold: 0.5
      target_classes: ["person"]
      forbidden_zone: [[100, 200], [500, 200], [500, 600], [100, 600]]
```

---

## 环境变量覆盖规则

命名格式：`TVP__` + 层级路径，双下划线分隔（不区分大小写）：

```bash
TVP__SERVER__PORT=9000
TVP__KAFKA__BOOTSTRAP_SERVERS=kafka:9092
TVP__MINIO__ACCESS_KEY=minioadmin
TVP__INFERENCE__BACKEND=tensorrt
```

列表类型环境变量使用 JSON 格式：

```bash
TVP__SCHEDULE__ENABLED_DAYS=[1,2,3,4,5]
```

---

## ConfigLoader

```python
class ConfigLoader:

    @staticmethod
    def load(config_path: str) -> TvpConfig:
        """加载全局配置：YAML → 环境变量覆盖 → Pydantic 校验"""
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        ConfigLoader._apply_env_overrides(data, prefix="TVP")
        return TvpConfig.model_validate(data)

    @staticmethod
    def load_task(task_path: str) -> TaskConfig:
        """加载任务级 YAML 配置"""
        with open(task_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return TaskConfig.model_validate(data)
```

`_apply_env_overrides` 递归将 `TVP__A__B=val` 写入 `data["a"]["b"] = val`，赋值后由 Pydantic JSON coercion 解析类型。
