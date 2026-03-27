# tvp/model/model_manager.py
from utils.singleton import SingletonMeta
from utils.logger import logger
from model.base import ModelBase
from model.yolo_model import YoloModel


class ModelManager(metaclass=SingletonMeta):
    def __init__(self):
        self._models: dict[str, ModelBase] = {}

    def init(self, config, device: str = "auto") -> None:
        for name, entry in config.root.items():
            model = YoloModel()
            try:
                model.load(entry.path, entry.imgsz, entry.conf, device)
                self._models[name] = model
                logger.info("model_loaded", name=name, path=entry.path, device=device)
            except Exception as e:
                raise RuntimeError(f"Failed to load model '{name}': {e}") from e

    def get(self, name: str) -> ModelBase:
        if name not in self._models:
            raise KeyError(f"Model '{name}' not found. Available: {list(self._models)}")
        return self._models[name]
