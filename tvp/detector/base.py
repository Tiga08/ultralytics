from abc import ABC, abstractmethod
from typing import Any

from utils.logger import logger
from pipeline.frame import Frame
from pipeline.events import ViolationEvent
from model.base import InferResult


class DetectorBase(ABC):
    CONFIG_CLASS: type | None = None

    def __init__(self, task_id: str, output_adapters: list) -> None:
        self._task_id = task_id
        self._output_adapters = output_adapters
        self._active = True

    @abstractmethod
    def setup(self, config: Any) -> None: ...

    @abstractmethod
    def process(self, frame: Frame, infer_result: InferResult) -> list[ViolationEvent]: ...

    def emit_violation(self, event: ViolationEvent) -> None:
        for adapter in self._output_adapters:
            try:
                adapter.send(event)
            except Exception as e:
                logger.error("adapter_send_failed",
                             adapter=type(adapter).__name__, error=str(e))

    def cleanup(self) -> None:
        pass

    def is_active(self) -> bool:
        return self._active

    def pause(self) -> None:
        self._active = False

    def resume(self) -> None:
        self._active = True
