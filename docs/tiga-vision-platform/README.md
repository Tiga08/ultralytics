# Tiga Vision Platform (TVP) 文档库

Tiga Vision Platform 是基于 `ultralytics`、`FastAPI`、`Pydantic v2` 构建的插件化视觉 AI 监控平台，用于多摄像头 RTSP 流的实时目标检测、违规事件识别与分发。

---

## 核心目标

| 目标 | 说明 |
|------|------|
| 插件化架构 | 检测器、模型、输出适配器均可热注册，无需修改框架代码 |
| 配置系统重设计 | Pydantic v2 类型安全配置，支持 YAML/JSON，运行时校验 |
| 任务调度与资源管理 | 任务优先级、健康检查、自动恢复 |
| 开发友好性 | 清晰抽象层、完整类型注解、单测覆盖、FastAPI 自动文档 |

---

## 技术选型

| 层次 | 技术 |
|------|------|
| Web 框架 | FastAPI + Uvicorn |
| 配置系统 | Pydantic v2 + PyYAML |
| 模型推理 | `ultralytics.YOLO` |
| 目标跟踪 | ByteTrack（`ByteTrackWrapper` 封装） |
| 视频采集 | FFmpeg（RTSP/RTMP，断线重连） |
| 消息队列 | Kafka（`confluent-kafka`） |
| 消息推送 | MQTT（`paho-mqtt`） |
| 对象存储 | MinIO |
| 日志 | structlog |
| 测试 | pytest + pytest-asyncio |

---

## 文档导航

| 文件 | 内容 |
|------|------|
| [01-architecture.md](01-architecture.md) | 架构概述：目录结构、设计目标、数据流总览 |
| [02-config-system.md](02-config-system.md) | 配置系统：Pydantic v2 模型、YAML 格式、环境变量覆盖 |
| [03-plugin-registry.md](03-plugin-registry.md) | 插件注册表：装饰器注册、自动发现、开发约定 |
| [04-model-layer.md](04-model-layer.md) | 模型推理层：ModelBase、YoloModel、ModelManager |
| [05-pipeline.md](05-pipeline.md) | 视频处理管道：Frame、VideoCapture、CameraWorker |
| [06-detector.md](06-detector.md) | 检测器插件：DetectorBase、ByteTrack、开发快速指南 |
| [07-output-adapters.md](07-output-adapters.md) | 输出适配器：Kafka、MinIO、MQTT、Local |
| [08-engine-scheduler.md](08-engine-scheduler.md) | 主引擎与调度：TvpEngine、TaskScheduler、HealthMonitor |
| [09-api.md](09-api.md) | REST API：任务状态机、路由表、Schema |
| [10-testing.md](10-testing.md) | 测试策略：单元测试、集成测试、覆盖率要求 |
| [11-deployment.md](11-deployment.md) | 部署与路线图：启动流程、验证方法、实施阶段 |
