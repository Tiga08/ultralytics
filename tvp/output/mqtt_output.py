import json
from core.registry import PluginRegistry
from output.base import OutputAdapterBase
from pipeline.events import ViolationEvent
from utils.logger import logger


@PluginRegistry.output("mqtt")
class MqttOutputAdapter(OutputAdapterBase):
    def setup(self, config) -> None:
        import paho.mqtt.client as mqtt
        self._client = mqtt.Client()
        self._client.connect(config.host, config.port)
        self._client.loop_start()
        self._topic = config.topic_violation

    def send(self, event: ViolationEvent) -> None:
        try:
            payload = json.dumps({
                "task_id": event.task_id,
                "detector": event.detector_name,
                "violation_type": event.violation_type,
                "timestamp": event.timestamp,
            })
            self._client.publish(self._topic, payload)
        except Exception as e:
            logger.error("mqtt_send_failed", error=str(e))

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()
