# 架构概述

## 设计目标与约束

### 核心目标

| 目标 | 说明 |
|------|------|
| 插件化架构 | 检测器、模型、输出适配器均可热注册，无需修改框架代码 |
| 配置系统重设计 | Pydantic v2 类型安全配置，支持 YAML/JSON，运行时校验 |
| 任务调度与资源管理 | 任务优先级、健康检查、自动恢复 |
| 开发友好性 | 清晰抽象层、完整类型注解、单测覆盖、FastAPI 自动文档 |

### 约束条件

- 单台服务器部署，多摄像头（RTSP/RTMP）
- 推理后端：NVIDIA GPU / NPU / CPU（自动检测）
- `ultralytics` 用于模型推理及目标跟踪接口封装
- API 风格：标准 RESTful

---

## 技术选型

| 层次 | 技术 | 理由 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | 原生 Pydantic、异步、自动生成 OpenAPI 文档 |
| 配置系统 | Pydantic v2 Settings + PyYAML | 类型安全、校验完善、层级继承 |
| 模型推理 | `ultralytics.YOLO` | 统一接口封装所有 YOLO 系列模型 |
| 目标跟踪 | ByteTrack | 独立 `ByteTrackWrapper` 封装，各检测器实例内部持有 |
| 视频采集 | FFmpeg | 稳定、支持 RTSP/RTMP、断线重连 |
| 消息队列 | Kafka（`confluent-kafka`） | 违规事件异步分发 |
| 消息推送 | MQTT | 轻量级事件推送，适合边缘设备 |
| 对象存储 | MinIO | 违规截图/视频片段存储 |
| 日志 | structlog + ELK 兼容输出 | 结构化日志 |
| 测试 | pytest + pytest-asyncio | 单元测试 + 集成测试 |

---

## 目录结构

```
tvp/
├── core/                        # 框架核心，不含业务逻辑
│   ├── engine.py                # TvpEngine 主引擎（单例）
│   ├── registry.py              # PluginRegistry 插件注册表
│   ├── scheduler.py             # TaskScheduler 任务调度器
│   └── health.py                # HealthMonitor 健康检查
│
├── pipeline/                    # 视频处理管道
│   ├── capture.py               # VideoCapture RTSP 采集（含 ffprobe 分辨率探测）
│   ├── frame.py                 # Frame 数据模型
│   ├── events.py                # ViolationEvent 违规事件模型
│   ├── inference_pipeline.py    # InferencePipeline 推理管道
│   ├── camera_worker.py         # CameraWorker 单摄像头线程
│   └── bytetrack_wrapper.py     # ByteTrackWrapper 跟踪封装
│
├── model/                       # AI 模型封装层
│   ├── base.py                  # ModelBase ABC
│   ├── yolo_model.py            # YoloModel (ultralytics 封装)
│   └── model_manager.py         # ModelManager 单例管理器
│
├── detector/                    # 检测器插件（业务逻辑层）
│   ├── __init__.py              # 显式 import 各检测器触发 PluginRegistry 注册
│   ├── base.py                  # DetectorBase ABC
│   └── regional_invasion.py     # 区域入侵检测（示例）
│
├── output/                      # 输出适配器插件
│   ├── __init__.py
│   ├── base.py                  # OutputAdapterBase ABC
│   ├── kafka_output.py          # Kafka 违规事件输出
│   ├── minio_output.py          # MinIO 截图/视频上传
│   ├── mqtt_output.py           # MQTT 轻量级事件推送
│   └── local_output.py          # 本地文件（调试用）
│
├── config/                      # 配置系统
│   ├── models.py                # 所有 Pydantic 配置模型
│   └── loader.py                # 配置加载与合并逻辑
│
├── api/                         # REST API 层
│   ├── app.py                   # FastAPI 应用工厂
│   ├── deps.py                  # 依赖注入
│   ├── routers/                 # 路由（tasks/cameras/health/metrics）
│   └── schemas/                 # 请求/响应 Schema
│
├── utils/                       # 公共工具
│   ├── logger.py                # structlog 配置
│   ├── singleton.py             # 单例 metaclass
│   ├── time_checker.py          # 时间区间检查
│   └── metrics.py               # Prometheus 指标
│
├── tasks/                       # 任务配置 YAML 示例
├── tests/                       # 测试套件
├── weights/                     # 模型权重
├── config.yaml                  # 主配置文件
├── run.py                       # 启动入口
└── pyproject.toml               # 依赖管理
```

---

## 数据流总览

```
RTSP 流
  ↓
VideoCapture.stream()          # FFmpeg 子进程采集，生成 Frame 对象；断流自动重连
  ↓                            # 断流策略：任何异常 → kill ffmpeg → sleep(reconnect_interval 秒) → 重启进程，无限重试
CameraWorker.run()             # 线程循环，从 capture 读帧
  ↓
InferencePipeline.run(frame)   # 封装 ModelManager.get(model_name).infer()，屏蔽推理细节 → InferResult
  ↓
DetectorBase.process(frame, infer_result)
  ├─ ByteTrackWrapper.update()  # 各检测器实例内部持有独立 tracker
  ├─ 违规逻辑判断
  └─ 返回 ViolationEvent 列表
      ↓
DetectorBase.emit_violation()
  ├─ KafkaOutputAdapter.send()  # JSON 序列化 → Kafka topic
  ├─ MinioOutputAdapter.send()  # frame_snapshot → JPEG → minio.put_object
  ├─ MqttOutputAdapter.send()   # MQTT 推送
  └─ LocalOutputAdapter.send()  # 本地 JPEG + JSON（调试用）
```

### ViolationEvent 数据结构

违规事件由检测器生成，在数据流中传递给所有输出适配器。定义于 `pipeline/events.py`（参见 [06-detector.md](06-detector.md)）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | `str` | 任务 ID |
| `detector_name` | `str` | 检测器注册名称 |
| `violation_type` | `str` | 违规类型标识 |
| `timestamp` | `float` | Unix 时间戳（秒） |
| `frame_snapshot` | `np.ndarray \| None` | 违规帧 BGR 图像 |
| `bounding_boxes` | `list[list[float]]` | 边界框列表，每项 `[x1, y1, x2, y2]` |
| `extra` | `dict` | 扩展字段，如 `{"zone_id": "zone_A", "duration_s": 3.5}` |

---

## 层次关系

```
API 层（FastAPI）
    ↓ Depends(get_engine)
TvpEngine（单例协调入口）
    ├─ ModelManager（模型缓存）
    ├─ TaskScheduler（任务生命周期）  ← 持有并管理 CameraWorker 线程，通过 worker_factory 支持重启
    ├─ HealthMonitor（心跳检测）      ← 定期调用 scheduler.check_health()，触发不健康任务重启
    ├─ OutputAdapters（全局共享）
    └─ CameraWorker × N（每摄像头一线程）
           └─ DetectorBase × M（每任务多检测器）
                  └─ ByteTrackWrapper（每检测器独立 tracker）
```

### 线程模型

| 线程 | 数量 | 类型 | 退出方式 |
|------|------|------|---------|
| `CameraWorker` | 每摄像头 1 个 | `daemon=True`，名为 `cam-{id}` | `stop_event.set()` |
| `HealthMonitor` | 全局 1 个 | `daemon=True` | `stop_event.set()` |
| paho-mqtt 后台线程 | 0 或 1 个 | `daemon`，由 paho 内部管理 | `loop_stop()` |

`CameraWorker` 线程由 `TaskScheduler` 持有和启动；`worker_factory` 是一个无参闭包，每次调用返回一个全新的 `CameraWorker` 实例，用于 `HealthMonitor` 触发重启场景（Python `Thread` 对象不可重启）。
