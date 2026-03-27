import sys
import types
from unittest.mock import patch, MagicMock

# paho 是可选依赖，未安装时用真正的 ModuleType 占位，确保 patch 能正确替换属性
if "paho" not in sys.modules:
    fake_paho = types.ModuleType("paho")
    fake_paho_mqtt = types.ModuleType("paho.mqtt")
    fake_paho_mqtt_client = types.ModuleType("paho.mqtt.client")
    fake_paho_mqtt_client.Client = None  # patch 目标占位
    sys.modules["paho"] = fake_paho
    sys.modules["paho.mqtt"] = fake_paho_mqtt
    sys.modules["paho.mqtt.client"] = fake_paho_mqtt_client

from output.mqtt_output import MqttOutputAdapter  # noqa: E402
from pipeline.events import ViolationEvent  # noqa: E402


def make_event():
    return ViolationEvent(task_id="t1", detector_name="d", violation_type="v",
                          timestamp=0.0, frame_snapshot=None, bounding_boxes=[])


def test_mqtt_setup_connects():
    adapter = MqttOutputAdapter()
    with patch("paho.mqtt.client.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        adapter.setup(MagicMock(host="mqtt-host", port=1883, topic_violation="tvp/v"))
        mock_client.connect.assert_called_once_with("mqtt-host", 1883)
        mock_client.loop_start.assert_called_once()


def test_mqtt_send_publishes():
    adapter = MqttOutputAdapter()
    with patch("paho.mqtt.client.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        adapter.setup(MagicMock(host="h", port=1883, topic_violation="tvp/v"))
        adapter.send(make_event())
        mock_client.publish.assert_called_once()


def test_mqtt_close_stops_loop():
    adapter = MqttOutputAdapter()
    with patch("paho.mqtt.client.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        adapter.setup(MagicMock(host="h", port=1883, topic_violation="tvp/v"))
        adapter.close()
        mock_client.loop_stop.assert_called_once()
        mock_client.disconnect.assert_called_once()
