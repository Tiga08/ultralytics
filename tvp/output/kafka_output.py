import json
from core.registry import PluginRegistry
from output.base import OutputAdapterBase
from pipeline.events import ViolationEvent
from utils.logger import logger


@PluginRegistry.output("kafka")
class KafkaOutputAdapter(OutputAdapterBase):
    def setup(self, config) -> None:
        from confluent_kafka import Producer
        self._producer = Producer({"bootstrap.servers": config.bootstrap_servers})
        self._topic = config.topic_violation

    def send(self, event: ViolationEvent) -> None:
        try:
            payload = json.dumps({
                "task_id": event.task_id,
                "detector": event.detector_name,
                "violation_type": event.violation_type,
                "timestamp": event.timestamp,
                "bounding_boxes": event.bounding_boxes,
                **event.extra,
            }).encode()
            self._producer.produce(self._topic, payload)
            self._producer.poll(0)
        except Exception as e:
            logger.error("kafka_send_failed", error=str(e))

    def close(self) -> None:
        self._producer.flush()
