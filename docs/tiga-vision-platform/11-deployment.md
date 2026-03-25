# 部署与路线图

## 依赖清单（pyproject.toml）

```toml
[project]
name = "tvp"
version = "1.0.0"
requires-python = ">=3.10"

dependencies = [
    "torch>=2.0.0",
    "ultralytics>=8.3.0",
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "pyyaml>=6.0",
    "structlog>=24.4.0",
    "confluent-kafka>=2.5.0",
    "minio>=7.2.0",
    "paho-mqtt>=2.1.0",
    "numpy>=1.26.0",
    "opencv-python-headless>=4.10.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "httpx>=0.27.0",
    "ruff>=0.7.0",
    "mypy>=1.13.0",
]
```

---

## 启动流程

```
run.py: main()
  ↓
ConfigLoader.load("config.yaml")
  ↓ YAML + 环境变量 → TvpConfig（Pydantic 校验）
  ↓
import detector   # 触发 detector/__init__.py，完成检测器插件注册
import output     # 触发 output/__init__.py，完成输出适配器插件注册
  ↓
engine = TvpEngine()
engine.start(config)
  ├─ ModelManager.init(config.model_weights)     # 预加载所有模型权重
  ├─ OutputAdapter 初始化（kafka/minio/mqtt 按需）
  ├─ TaskScheduler 初始化
  ├─ HealthMonitor.start()
  └─ 加载初始任务
     ├─ 扫描 tasks/*.yaml → ConfigLoader.load_task() → engine.create_task()
     └─ API 动态创建：POST /api/v1/tasks → engine.create_task()
  ↓
FastAPI 应用启动（Uvicorn）
  └─ http://0.0.0.0:8555
```

---

## 验证方法

1. **启动验证**：`python run.py --config config.yaml`，访问 `http://localhost:8555/docs`

2. **任务创建**：POST `/api/v1/tasks` 提交测试任务配置，确认响应 `success: true`

3. **插件加载**：GET `/api/v1/plugins` 确认所有检测器与输出适配器已注册

4. **健康检查**：GET `/api/v1/health` 查看所有任务状态

5. **推理验证**：使用本地 MP4 视频文件，确认检测器输出 `ViolationEvent`，日志中出现 `violation_detected`

6. **Kafka 投递验证**：使用 `kafka-console-consumer` 订阅 `tvp_violation_events`，触发违规后确认消息到达

7. **MinIO 截图验证**：登录 MinIO Console（默认 `http://localhost:9001`），确认 `tvp-evidence` bucket 中出现 JPEG 截图

8. **HealthMonitor 重启验证**：手动断开摄像头 RTSP 流 60 秒以上，观察日志出现 `task_unhealthy_restarting`，恢复流后确认任务自动恢复

9. **GPU 推理验证**：启动时日志确认 `device=cuda:0`，使用 `nvidia-smi` 确认 GPU 利用率上升

10. **单元测试**：`pytest tests/unit/ -v --cov=. --cov-fail-under=80`

---

## 实施路线图

| 阶段 | 内容 | 优先级 |
|------|------|--------|
| **Phase 1** | 框架骨架：core + pipeline + config + FastAPI | 必须 |
| **Phase 2** | 模型层：YoloModel（ultralytics 封装）+ ModelManager | 必须 |
| **Phase 3** | 迁移核心检测器（示例：区域入侵）+ 同步编写单元测试 | 必须 |
| **Phase 4** | 输出适配器：Kafka + MinIO + MQTT + Local + 适配器单元测试 | 必须 |
| **Phase 5** | 健康检查 + 任务优先级调度 | 高 |
| **Phase 6** | 扩展业务检测器（随各检测器同步补充测试） | 中 |
| **Phase 7** | 集成测试套件（端到端管道验证） | 中 |
| **Phase 8** | Prometheus 指标 + 日志优化 | 低 |

> **测试原则**：单元测试随各 Phase 同步编写，不延后到 Phase 7；Phase 7 仅负责端到端集成测试的补全。
