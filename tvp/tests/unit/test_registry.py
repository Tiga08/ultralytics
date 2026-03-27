import pytest
from core.registry import PluginRegistry


def test_register_and_get_detector():
    from detector.base import DetectorBase

    @PluginRegistry.detector("__test_det__")
    class _TD(DetectorBase):
        def setup(self, config): pass
        def process(self, frame, infer_result): return []

    assert PluginRegistry.get_detector("__test_det__") is _TD
    del PluginRegistry._detectors["__test_det__"]


def test_get_unknown_detector_raises():
    with pytest.raises(KeyError, match="not registered"):
        PluginRegistry.get_detector("__no_such__")


def test_register_and_get_output():
    from output.base import OutputAdapterBase

    @PluginRegistry.output("__test_out__")
    class _TO(OutputAdapterBase):
        def setup(self, config): pass
        def send(self, event): pass
        def close(self): pass

    assert PluginRegistry.get_output("__test_out__") is _TO
    del PluginRegistry._outputs["__test_out__"]


def test_list_detectors():
    assert isinstance(PluginRegistry.list_detectors(), list)


def test_list_outputs():
    assert isinstance(PluginRegistry.list_outputs(), list)
