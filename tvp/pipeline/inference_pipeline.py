from pipeline.frame import Frame
from model.base import InferResult


class InferencePipeline:
    def __init__(self, model_name: str, model_manager=None) -> None:
        self._model_name = model_name
        self._mm = model_manager

    def _get_mm(self):
        if self._mm is None:
            from model.model_manager import ModelManager
            self._mm = ModelManager()
        return self._mm

    def run(self, frame: Frame) -> InferResult:
        return self._get_mm().get(self._model_name).infer(frame.image)
