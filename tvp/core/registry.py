from __future__ import annotations


class PluginRegistry:
    _detectors: dict = {}
    _outputs: dict = {}

    @classmethod
    def detector(cls, name: str):
        def decorator(klass):
            if name in cls._detectors:
                import warnings
                warnings.warn(f"Detector '{name}' is being re-registered.", stacklevel=2)
            cls._detectors[name] = klass
            return klass
        return decorator

    @classmethod
    def output(cls, name: str):
        def decorator(klass):
            if name in cls._outputs:
                import warnings
                warnings.warn(f"Output '{name}' is being re-registered.", stacklevel=2)
            cls._outputs[name] = klass
            return klass
        return decorator

    @classmethod
    def get_detector(cls, name: str):
        if name not in cls._detectors:
            raise KeyError(
                f"Detector plugin '{name}' not registered. "
                f"Available: {list(cls._detectors)}"
            )
        return cls._detectors[name]

    @classmethod
    def get_output(cls, name: str):
        if name not in cls._outputs:
            raise KeyError(
                f"Output plugin '{name}' not registered. "
                f"Available: {list(cls._outputs)}"
            )
        return cls._outputs[name]

    @classmethod
    def list_detectors(cls) -> list[str]:
        return list(cls._detectors)

    @classmethod
    def list_outputs(cls) -> list[str]:
        return list(cls._outputs)
