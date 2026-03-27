from abc import ABC, abstractmethod

from pipeline.events import ViolationEvent


class OutputAdapterBase(ABC):
    @abstractmethod
    def setup(self, config) -> None: ...

    @abstractmethod
    def send(self, event: ViolationEvent) -> None: ...

    @abstractmethod
    def close(self) -> None: ...
