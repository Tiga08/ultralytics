# REST API

## 基础路径

`/api/v1/`

---

## 路由表

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/tasks` | 创建并启动任务 |
| DELETE | `/api/v1/tasks/{task_id}` | 删除任务（→ stopped） |
| GET | `/api/v1/tasks/{task_id}` | 查询单个任务状态 |
| GET | `/api/v1/tasks` | 列出所有任务 |
| POST | `/api/v1/tasks/{task_id}/pause` | 暂停任务（→ paused） |
| POST | `/api/v1/tasks/{task_id}/resume` | 恢复任务（→ running） |
| GET | `/api/v1/cameras` | 列出所有摄像机 |
| GET | `/api/v1/cameras/{camera_id}/status` | 摄像机状态 |
| GET | `/api/v1/health` | 系统健康状态 |
| GET | `/api/v1/metrics` | Prometheus 指标 |
| GET | `/api/v1/plugins` | 列出已注册插件 |

---

## 任务状态机

```
状态值：running | paused | stopped | failed

转移规则：
  running ──pause──►  paused
  paused  ──resume──► running
  running ──delete──► stopped
  paused  ──delete──► stopped
  running ──worker 崩溃──► failed   （HealthMonitor 检测到）
  failed  ──HealthMonitor 重启──► running（重启次数未超限）
  failed  ──重启次数超限──► failed   （需人工介入）

注意：
  - stopped 是终态，不可再次启动（需重新 POST /tasks）
  - failed 由 HealthMonitor 自动管理，API 只读该状态
  - paused 状态下 CameraWorker 继续采帧推理，仅 is_active() 返回 False
```

---

## 请求 Schema

### TaskCreateRequest

```json
{
  "task_id": "regional_invasion_a1_cam1",
  "task_name": "A1 机位区域入侵检测",
  "priority": "HIGH",
  "stand_id": "STAND_A1",
  "camera": {
    "id": "CAM_A1_001",
    "rtsp_url": "rtsp://tiga-camera:8554/stream1",
    "rtsp_interval": 0.5
  },
  "schedule": {
    "enabled_days": [1, 2, 3, 4, 5, 6, 7],
    "start_time": "00:00:00",
    "end_time": "23:59:59"
  },
  "detectors": [
    {
      "name": "regional_invasion",
      "config": {
        "send_interval": 60,
        "conf_threshold": 0.5,
        "forbidden_zone": [[100,200],[500,200],[500,600],[100,600]]
      }
    }
  ]
}
```

---

## 响应 Schema

### CommonResponse — 标准响应格式

```python
class CommonResponse(BaseModel):
    success: bool
    data: dict | list | None = None
    message: str = ""
    timestamp: str = ""
```

示例：

```json
{
  "success": true,
  "data": { ... },
  "message": "Task created successfully",
  "timestamp": "2026-03-25T10:30:45Z"
}
```

### TaskResponse

```python
class TaskResponse(BaseModel):
    task_id: str
    task_name: str
    priority: str
    status: str        # running | paused | stopped | failed
    camera_id: str
    fail_count: int
    is_healthy: bool
```

### HealthResponse

```python
class TaskHealthInfo(BaseModel):
    task_id: str
    status: str
    is_healthy: bool
    fail_count: int
    camera_id: str

class HealthResponse(BaseModel):
    healthy: bool          # 所有任务均健康时为 True
    task_count: int
    unhealthy_count: int
    tasks: list[TaskHealthInfo]
```

示例：

```json
{
  "healthy": false,
  "task_count": 3,
  "unhealthy_count": 1,
  "tasks": [
    {"task_id": "task_001", "status": "running",  "is_healthy": true,  "fail_count": 0, "camera_id": "CAM_001"},
    {"task_id": "task_002", "status": "failed",   "is_healthy": false, "fail_count": 3, "camera_id": "CAM_002"},
    {"task_id": "task_003", "status": "running",  "is_healthy": true,  "fail_count": 0, "camera_id": "CAM_003"}
  ]
}
```

---

## 依赖注入

```python
# api/deps.py
from functools import lru_cache
from core.engine import TvpEngine

@lru_cache(maxsize=1)
def get_engine() -> TvpEngine:
    """返回 TvpEngine 单例，由 FastAPI 依赖注入系统管理"""
    return TvpEngine()
```

路由中使用：

```python
@router.post("/tasks", status_code=201)
async def create_task(req: TaskCreateRequest,
                      engine: TvpEngine = Depends(get_engine)):
    engine.create_task(req)
    return CommonResponse.ok(message="Task created")
```

---

## API Schema 设计说明

`api/schemas/task.py` 中的请求模型与 `config/models.py` 结构高度重合。为减少维护负担，原则上**直接复用** config models，仅在字段语义有差异时定义独立类型：

```python
# api/schemas/task.py
from config.models import TaskConfig

TaskCreateRequest = TaskConfig   # POST /tasks 的请求体就是 TaskConfig
```

---

## 访问入口

- API 服务：`http://0.0.0.0:8555`
- OpenAPI 文档：`http://0.0.0.0:8555/docs`
- ReDoc：`http://0.0.0.0:8555/redoc`
