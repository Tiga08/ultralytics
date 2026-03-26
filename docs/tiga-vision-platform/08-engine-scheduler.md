# 主引擎与调度

> **已知限制**：`TaskPriority` 字段当前仅作信息记录，**不影响任务调度顺序**，不做排队和抢占。
> 基于优先级的调度（引入 `PriorityQueue`）计划在 Phase 5 实现。详见 [11-deployment.md](11-deployment.md) 路线图。

## TvpEngine — 主引擎

**文件**：`core/engine.py`

### 职责

系统的唯一协调入口，负责：
- 从 `TaskConfig` 创建运行时任务（CameraWorker + Detector + OutputAdapter）
- 管理任务状态（running / paused / stopped / failed）
- 提供供 API 路由调用的操作接口

通过 `SingletonMeta` 保证全局唯一实例。

### 核心接口

```python
class TvpEngine(metaclass=SingletonMeta):

    def start(self, config: TvpConfig) -> None:
        """引擎启动：初始化模型、输出适配器、调度器、健康监控"""
        # 1. ModelManager().init(config.model_weights)
        # 2. _init_output_adapters(config)
        # 3. TaskScheduler 初始化
        # 4. HealthMonitor.start()

    def stop(self) -> None:
        """引擎停止：关闭所有任务和适配器"""

    def create_task(self, task_config: TaskConfig) -> None: ...
    def delete_task(self, task_id: str) -> None: ...
    def pause_task(self, task_id: str) -> None: ...
    def resume_task(self, task_id: str) -> None: ...
    def get_task_status(self, task_id: str) -> dict: ...
    def list_tasks(self) -> list[dict]: ...
```

### create_task 内部流程

```
1. 检查 task_id 是否重复
2. 遍历 task_config.detectors：
   a. PluginRegistry.get_detector(name) 获取插件类
   b. 实例化检测器（__init__）
   c. 若声明了 CONFIG_CLASS，validate 配置字典
   d. 调用 detector.setup(config)
      ↑ 若此处抛出异常，需回滚：对已初始化的所有检测器调用 cleanup()，中止 create_task()
3. 创建 InferencePipeline("yolo_detection")
4. 定义 worker_factory（无参闭包，每次返回新 CameraWorker 实例）
5. TaskScheduler.submit(task_id, worker, priority, worker_factory)
6. _task_status[task_id] = "running"
```

**worker_factory 模式**：Python `Thread` 对象不可重启，`worker_factory` 每次返回全新实例，供 `HealthMonitor` 触发重启时使用。

---

## TaskScheduler — 任务调度器

**文件**：`core/scheduler.py`

### TaskPriority 枚举

```python
class TaskPriority(IntEnum):
    CRITICAL = 1   # 安全关键任务
    HIGH = 2
    NORMAL = 3
    LOW = 4
```

当前 `priority` 仅作信息记录，不做排队调度（不排序、不抢占）。基于优先级的调度（引入 `PriorityQueue`、实现任务抢占）计划在 Phase 5 实现。

### 核心接口

```python
class TaskScheduler:

    def submit(self, task_id: str, worker,
               priority: TaskPriority,
               worker_factory: Callable[[], Any] | None = None) -> None:
        """注册并启动任务。worker_factory 为 None 时不支持 restart()"""

    def remove(self, task_id: str) -> None:
        """停止并移除任务"""

    def restart(self, task_id: str) -> None:
        """停止旧 worker，通过 worker_factory 重建并启动新 worker。
        未提供 worker_factory 时抛出 RuntimeError"""

    def check_health(self) -> list[str]:
        """返回不健康的 task_id 列表"""
```

---

## HealthMonitor — 健康监控

**文件**：`core/health.py`

### 工作原理

定期（`check_interval` 秒）调用 `TaskScheduler.check_health()`，对不健康任务执行自动重启：

```
for task_id in unhealthy_tasks:
    if fail_count >= max_restart_count:
        log.error("task_exceeded_max_restarts")  # 需人工介入
        continue
    if restart_on_failure:
        scheduler.restart(task_id)
        fail_count += 1
```

### 状态转移

```
running ──worker 崩溃──► failed   （HealthMonitor 检测到）
failed  ──自动重启──► running     （重启次数未超限）
failed  ──超限──► failed          （保持 failed，需人工介入）
```

`HealthMonitor` 是 `daemon=True` 的后台线程，引擎启动时随之启动，引擎停止时通过 `stop_event` 退出。

---

## HealthMonitor 默认配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `check_interval` | 30 秒 | 两次健康检查的间隔 |
| `restart_on_failure` | `true` | 检测到不健康时是否自动重启 |
| `max_restart_count` | 3 次 | 超过此次数后标记为 `failed`，需人工介入 |

## 线程安全

- `TvpEngine._lock`：`threading.RLock()`，保护 `_task_status` 字典
- `TaskScheduler._lock`：`threading.RLock()`，保护 `_tasks` 字典
- 二者均在同一 `_lock` 作用域内修改，保证 `_task_status` 与 `_tasks` 的一致性
- `OutputAdapter.send()`：各适配器客户端（confluent-kafka Producer、MinIO、paho-mqtt）自身线程安全
