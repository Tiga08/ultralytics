# CLAUDE.md

本文件为 Claude Code 在此仓库工作时提供上下文。

## 项目背景

本仓库为 **ultralytics YOLO 框架**的定制工作区，同时用于开发 **Tiga Vision Platform (TVP)**——一个基于 `ultralytics`、`FastAPI`、`Pydantic v2` 构建的插件化视觉 AI 监控平台，用于多摄像头 RTSP 流的实时目标检测与违规事件分发。

---

## TVP 项目文档

TVP 设计文档位于 `docs/tiga-vision-platform/`：

| 文件 | 内容 |
|------|------|
| `README.md` | 总览与导航索引 |
| `01-architecture.md` | 架构概述：目录结构、技术选型、数据流 |
| `02-config-system.md` | 配置系统：Pydantic v2、YAML、环境变量覆盖 |
| `03-plugin-registry.md` | 插件注册表：装饰器注册、开发约定 |
| `04-model-layer.md` | 模型推理层：ModelBase、YoloModel、ModelManager |
| `05-pipeline.md` | 视频处理管道：Frame、VideoCapture、CameraWorker |
| `06-detector.md` | 检测器插件：DetectorBase、ByteTrack、开发快速指南 |
| `07-output-adapters.md` | 输出适配器：Kafka、MinIO、MQTT、Local |
| `08-engine-scheduler.md` | 主引擎与调度：TvpEngine、TaskScheduler、HealthMonitor |
| `09-api.md` | REST API：状态机、路由表、Schema |
| `10-testing.md` | 测试策略：单元测试、集成测试、覆盖率 |
| `11-deployment.md` | 部署与路线图：启动流程、验证方法、实施阶段 |

---

## TVP 开发规范

### 代码组织

- 所有新 TVP 代码放在独立的 `tvp/` 目录下，**不修改** ultralytics 核心代码
- 参考原始设计文档：`2026-03-25-tiga-vision-platform-design.md`

### 检测器插件开发

1. 在 `detector/` 创建新文件，继承 `DetectorBase`
2. 用 `@PluginRegistry.detector("name")` 注册
3. 声明 `CONFIG_CLASS` 指向 Pydantic 配置模型
4. 在 `detector/__init__.py` 中添加导入行

### 输出适配器开发

1. 在 `output/` 创建新文件，继承 `OutputAdapterBase`
2. 用 `@PluginRegistry.output("name")` 注册
3. 在 `output/__init__.py` 中添加导入行

### 关键约定

- 可选依赖（kafka、minio、mqtt、paho 等）在 `setup()` 内按需导入，**不在模块顶部导入**
- 所有配置使用 Pydantic v2 模型，支持 YAML + 环境变量覆盖（`TVP__X__Y` 格式）
- 新增检测器时须同步编写单元测试（`tests/unit/`）
- `ViolationEvent` 定义在 `pipeline/events.py`（不在 `detector/`），避免循环依赖

---

## Git 规范

- 分支名使用英文（如 `tiga-vision-platform-threading`、`feat/xxx`）
- `git commit` 提交信息使用中文
