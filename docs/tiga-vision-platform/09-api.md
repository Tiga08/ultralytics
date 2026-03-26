# REST API

## 基础路径

`/api/v1/`

---

## 路由表

| 方法 | 端点 | 状态码 | 说明 |
|------|------|--------|------|
| POST | `/api/v1/tasks` | 201 | 创建并启动任务 |
| DELETE | `/api/v1/tasks/{task_id}` | 204 / 404 | 删除任务（→ stopped）；任务不存在返回 404 |
| GET | `/api/v1/tasks/{task_id}` | 200 / 404 | 查询单个任务状态 |
| GET | `/api/v1/tasks` | 200 | 列出所有任务 |
| POST | `/api/v1/tasks/{task_id}/pause` | 200 / 404 | 暂停任务（→ paused） |
| POST | `/api/v1/tasks/{task_id}/resume` | 200 / 404 | 恢复任务（→ running） |
| GET | `/api/v1/cameras` | 200 | 列出所有摄像机 |
| GET | `/api/v1/cameras/{camera_id}/status` | 200 / 404 | 摄像机状态 |
| GET | `/api/v1/health` | 200 | 系统健康状态 |
| GET | `/api/v1/metrics` | 200 | Prometheus 指标（纯文本格式） |
| GET | `/api/v1/plugins` | 200 | 列出已注册插件 |

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

### CameraResponse

```python
class CameraResponse(BaseModel):
    camera_id: str
    rtsp_url: str
    task_count: int        # 当前绑定的任务数
    is_healthy: bool       # 是否在正常采帧

class CameraStatusResponse(BaseModel):
    camera_id: str
    is_healthy: bool
    last_frame_ts: float   # 最近一帧的 Unix 时间戳
    fps_actual: float      # 实际采帧速率（近 10 秒均值）
```

示例（`GET /api/v1/cameras/{camera_id}/status`）：

```json
{
  "camera_id": "CAM_A1_001",
  "is_healthy": true,
  "last_frame_ts": 1711360245.3,
  "fps_actual": 1.98
}
```

### PluginsResponse

```python
class PluginsResponse(BaseModel):
    detectors: list[str]   # 当前注册的检测器名称列表
    outputs: list[str]     # 当前注册的输出适配器名称列表
```

示例：

```json
{
  "detectors": ["regional_invasion", "helmet_detection"],
  "outputs": ["kafka", "minio", "mqtt", "local"]
}
```

> `GET /api/v1/plugins` 返回的是运行时动态注册列表，与代码中实际导入的插件同步。

### Prometheus 指标（`GET /api/v1/metrics`）

返回纯文本格式，供 Prometheus 抓取。主要指标：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `tvp_task_total` | Gauge | 当前任务总数 |
| `tvp_task_status{status="running"}` | Gauge | 各状态任务数 |
| `tvp_frame_processed_total` | Counter | 累计处理帧数 |
| `tvp_violation_total{detector="..."}` | Counter | 各检测器累计违规事件数 |
| `tvp_inference_latency_ms` | Histogram | 推理延迟分布 |

### 错误响应格式

所有错误均返回统一格式：

```python
class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    code: int
```

示例：

```json
{
  "success": false,
  "message": "Task 'task_001' not found",
  "code": 404
}
```

常见错误码：`400`（请求参数错误）、`404`（资源不存在）、`409`（task_id 已存在）、`500`（引擎内部错误）。

---

## 访问入口

- API 服务：`http://0.0.0.0:8555`
- OpenAPI 文档：`http://0.0.0.0:8555/docs`
- ReDoc：`http://0.0.0.0:8555/redoc`
- 当前版本不含认证（内网部署场景）；如需接入认证，可在 FastAPI 中添加 `HTTPBearer` 依赖。
