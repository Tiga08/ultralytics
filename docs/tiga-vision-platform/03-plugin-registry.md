# 插件注册表

## 设计原则

通过装饰器注册，按名称动态实例化，零框架侵入。

- 检测器和输出适配器均通过类装饰器注册到 `PluginRegistry`
- `TvpEngine` 在运行时通过名称字符串动态获取并实例化插件
- 框架代码无需感知具体插件的存在

---

## PluginRegistry 接口

```python
class PluginRegistry:

    # 注册检测器插件
    @classmethod
    def detector(cls, name: str):
        """装饰器：将检测器类注册为 name"""

    # 注册输出适配器插件
    @classmethod
    def output(cls, name: str):
        """装饰器：将输出适配器类注册为 name"""

    # 查询接口
    @classmethod
    def get_detector(cls, name: str) -> Type[DetectorBase]: ...
    @classmethod
    def list_detectors(cls) -> list[str]: ...
    @classmethod
    def get_output(cls, name: str) -> Type[OutputAdapterBase]: ...
    @classmethod
    def list_outputs(cls) -> list[str]: ...

    # 备选：自动扫描（见下文）
    @classmethod
    def autodiscover(cls, packages: list[str] | None = None) -> None: ...
```

---

## 注册方式

### 推荐方式：`__init__.py` 显式导入

在 `detector/__init__.py` 中显式导入每个检测器模块，Python 执行导入时触发装饰器完成注册：

```python
# detector/__init__.py
from .regional_invasion import RegionalInvasionDetector   # noqa: F401
from .helmet_detection import HelmetDetector               # noqa: F401
# 新增检测器时在此追加一行导入即可
```

同理，`output/__init__.py`：

```python
# output/__init__.py
from .kafka_output import KafkaOutputAdapter    # noqa: F401
from .minio_output import MinioOutputAdapter    # noqa: F401
from .mqtt_output import MqttOutputAdapter      # noqa: F401
from .local_output import LocalOutputAdapter    # noqa: F401
```

启动流程中显式触发：

```python
# run.py
import detector   # 触发 detector/__init__.py
import output     # 触发 output/__init__.py
```

### 备选方式：autodiscover 自动扫描

```python
PluginRegistry.autodiscover(["detector", "output"])
```

适用于**第三方扩展包**或**动态加载**场景。注意：与显式导入方式不应同时使用（重复注册幂等，但会产生警告）。

---

## 使用示例

### 注册检测器

```python
# detector/regional_invasion.py
from core.registry import PluginRegistry
from detector.base import DetectorBase

@PluginRegistry.detector("regional_invasion")
class RegionalInvasionDetector(DetectorBase):
    ...
```

### 注册输出适配器

```python
# output/kafka_output.py
from core.registry import PluginRegistry
from output.base import OutputAdapterBase

@PluginRegistry.output("kafka")
class KafkaOutputAdapter(OutputAdapterBase):
    ...
```

### TvpEngine 中动态实例化

```python
# core/engine.py（内部逻辑）
klass = PluginRegistry.get_detector("regional_invasion")
detector = klass(task_id=task_id, output_adapters=adapters)
```

### API 查询已注册插件

```
GET /api/v1/plugins
→ { "detectors": ["regional_invasion", ...], "outputs": ["kafka", "minio", ...] }
```

---

## 错误处理

`get_detector` / `get_output` 在名称未注册时抛出 `KeyError`，错误信息包含可用列表：

```
KeyError: "Detector plugin 'unknown_detector' not registered.
Available: ['regional_invasion', 'helmet_detection']"
```

---

## 注意事项

- 注册是**幂等**的（同名多次注册以最后一次为准，并产生警告）
- 装饰器在**模块被导入时**执行，因此插件模块必须被导入才能完成注册
- 推荐通过 `__init__.py` 统一管理导入，避免遗漏
