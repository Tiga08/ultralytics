# 输出适配器

## 设计原则

- Kafka、MinIO、MQTT 均为可选插件，通过配置启用/禁用，可独立测试
- 所有适配器全局共享（多个检测器复用同一实例），`send()` 须保证线程安全
- 可选依赖在 `setup()` 内按需导入，未安装时仅在任务创建阶段报错，不影响启动
- **`send()` 中必须捕获所有异常并记录日志，不得向上抛出**——任何适配器的网络/IO 错误不应中断 `CameraWorker` 线程

## 线程安全说明

| 适配器 | 线程安全依据 |
|--------|------------|
| `KafkaOutputAdapter` | `confluent-kafka` 的 `Producer` 是 C 扩展，自身线程安全 |
| `MinioOutputAdapter` | MinIO 官方客户端无全局状态，线程安全 |
| `MqttOutputAdapter` | `paho-mqtt` 使用后台线程处理 I/O，`publish()` 线程安全 |
| `LocalOutputAdapter` | 文件写入无共享状态，天然线程安全 |
| `WebhookOutputAdapter` | `httpx.Client` 支持并发请求，连接池线程安全 |

---

## OutputAdapterBase — 抽象接口

```python
class OutputAdapterBase(ABC):
    @abstractmethod
    def setup(self, config) -> None: ...

    @abstractmethod
    def send(self, event: ViolationEvent) -> None: ...

    @abstractmethod
    def close(self) -> None: ...
```

---

## 生命周期规范

由 `TvpEngine` 统一管理：

```
创建：TvpEngine.start() 时，根据 config.kafka/minio/mqtt 是否启用，创建全局共享适配器实例
初始化：TvpEngine.start() 中调用 adapter.setup(config)
使用：每个 DetectorBase 接收已初始化的适配器列表引用（共享，非独占）
关闭：TvpEngine.stop() 中调用所有 adapter.close()
```

---

## KafkaOutputAdapter

**文件**：`output/kafka_output.py`

- 使用 `confluent-kafka`（替代已停止维护的 kafka-python）
- `Producer` 对象自身线程安全
- 每次 `send()` 后调用 `poll(0)` 处理回调

```python
@PluginRegistry.output("kafka")
class KafkaOutputAdapter(OutputAdapterBase):
    def setup(self, config) -> None:
        from confluent_kafka import Producer   # 可选依赖，延迟导入
        self._producer = Producer({"bootstrap.servers": config.bootstrap_servers})
        self._topic = config.topic_violation

    def send(self, event: ViolationEvent) -> None:
        payload = json.dumps({
            "task_id": event.task_id,
            "detector": event.detector_name,
            "violation_type": event.violation_type,
            "timestamp": event.timestamp,
            "bounding_boxes": event.bounding_boxes,
            **event.extra
        }).encode()
        self._producer.produce(self._topic, payload)
        self._producer.poll(0)

    def close(self) -> None:
        self._producer.flush()
```

---

## MinioOutputAdapter

**文件**：`output/minio_output.py`

- 将 `frame_snapshot`（numpy BGR 数组）编码为 JPEG 后上传
- 对象命名规则：`{task_id}/{violation_type}/{timestamp_ms}.jpg`
- MinIO 客户端线程安全

```python
@PluginRegistry.output("minio")
class MinioOutputAdapter(OutputAdapterBase):
    def setup(self, config) -> None:
        from minio import Minio   # 可选依赖，延迟导入
        self._client = Minio(config.endpoint,
                             access_key=config.access_key,
                             secret_key=config.secret_key,
                             secure=getattr(config, "secure", False))
        self._jpeg_quality = getattr(config, "jpeg_quality", 85)  # 建议在 MinioConfig 中添加 jpeg_quality: int = 85
        self._bucket = config.bucket
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def send(self, event: ViolationEvent) -> None:
        if event.frame_snapshot is None:
            return
        ok, buf = cv2.imencode(".jpg", event.frame_snapshot,
                               [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality])
        if not ok:
            return
        data = buf.tobytes()
        obj_name = f"{event.task_id}/{event.violation_type}/{int(event.timestamp * 1000)}.jpg"
        self._client.put_object(self._bucket, obj_name,
                                io.BytesIO(data), length=len(data),
                                content_type="image/jpeg")

    def close(self) -> None:
        pass  # Minio 客户端无需显式关闭
```

---

## MqttOutputAdapter

**文件**：`output/mqtt_output.py`

- 使用 `paho-mqtt`，`loop_start()` 后台线程处理网络 I/O
- 适合边缘设备轻量级推送

```python
@PluginRegistry.output("mqtt")
class MqttOutputAdapter(OutputAdapterBase):
    def setup(self, config) -> None:
        import paho.mqtt.client as mqtt   # 可选依赖，延迟导入
        self._client = mqtt.Client()
        self._client.connect(config.host, config.port)
        self._client.loop_start()
        self._topic = config.topic_violation

    def send(self, event: ViolationEvent) -> None:
        payload = json.dumps({...})
        self._client.publish(self._topic, payload)

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
```

---

## LocalOutputAdapter

**文件**：`output/local_output.py`

用于本地调试，每个违规事件落地为一个 JPEG 截图 + JSON 元数据：

- `{base}.jpg`：违规帧截图
- `{base}.json`：事件元数据

文件命名：`{output_dir}/{task_id}_{violation_type}_{timestamp_ms}`

---

## 输出适配器开发快速指南（4 步）

### 第 1 步：创建文件 `output/webhook_output.py`

### 第 2 步：定义配置模型

```python
class WebhookConfig(BaseModel):
    url: str
    timeout: int = 5
```

### 第 3 步：注册并实现

```python
@PluginRegistry.output("webhook")
class WebhookOutputAdapter(OutputAdapterBase):
    def setup(self, config: WebhookConfig) -> None:
        import httpx   # 可选依赖，延迟导入
        self._client = httpx.Client(timeout=config.timeout)
        self._url = config.url

    def send(self, event: ViolationEvent) -> None:
        self._client.post(self._url, json={
            "task_id": event.task_id,
            "violation_type": event.violation_type,
            "timestamp": event.timestamp,
        })

    def close(self) -> None:
        self._client.close()
```

### 第 4 步：在 `output/__init__.py` 中添加导入

```python
from .webhook_output import WebhookOutputAdapter   # noqa: F401
```

---

## 多适配器联合配置示例

同时启用 Kafka、MinIO、MQTT（在 `config.yaml` 中）：

```yaml
kafka:
  bootstrap_servers: "tiga-kafka:9092"
  topic_violation: "tvp_violation_events"

minio:
  endpoint: "tiga-minio:9000"
  access_key: "minioadmin"      # 建议通过环境变量注入
  secret_key: "minioadmin"
  bucket: "tvp-evidence"
  secure: false

mqtt:
  host: "tiga-mqtt"
  port: 1883
  topic_violation: "tvp/violation"
```

三者同时启用时，每个 `ViolationEvent` 会依次调用三个适配器的 `send()`，各适配器独立处理，互不影响。

---

## 导入规范

| 类型 | 导入位置 | 示例 |
|------|---------|------|
| 必选依赖 | 模块顶部 | `import json`, `import cv2` |
| 可选依赖 | `setup()` 内 | `confluent_kafka`, `minio`, `paho.mqtt`, `httpx` |

可选依赖延迟导入的好处：未安装时只在任务创建阶段报错（调用 `setup()`），不影响系统启动和其他适配器的正常工作。
