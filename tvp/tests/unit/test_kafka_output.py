import json
import sys
import types
from unittest.mock import patch, MagicMock

# confluent_kafka 是可选依赖，未安装时用假模块占位，让 patch 能正常工作
if "confluent_kafka" not in sys.modules:
    fake_ck = types.ModuleType("confluent_kafka")
    fake_ck.Producer = None  # patch 目标占位
    sys.modules["confluent_kafka"] = fake_ck

from output.kafka_output import KafkaOutputAdapter  # noqa: E402
from pipeline.events import ViolationEvent  # noqa: E402


def make_event():
    return ViolationEvent(task_id="t1", detector_name="d1", violation_type="test",
                          timestamp=1000.0, frame_snapshot=None,
                          bounding_boxes=[[1, 2, 3, 4]])


def test_kafka_send_produces_to_topic():
    adapter = KafkaOutputAdapter()
    with patch("confluent_kafka.Producer") as MockProducer:
        mock_prod = MagicMock()
        MockProducer.return_value = mock_prod
        cfg = MagicMock(bootstrap_servers="localhost:9092", topic_violation="test_topic")
        adapter.setup(cfg)
        adapter.send(make_event())
        assert mock_prod.produce.call_args[0][0] == "test_topic"
        mock_prod.poll.assert_called_once_with(0)


def test_kafka_send_payload_fields():
    adapter = KafkaOutputAdapter()
    with patch("confluent_kafka.Producer") as MockProducer:
        mock_prod = MagicMock()
        MockProducer.return_value = mock_prod
        adapter.setup(MagicMock(bootstrap_servers="x", topic_violation="t"))
        adapter.send(make_event())
        payload = json.loads(mock_prod.produce.call_args[0][1])
        assert payload["task_id"] == "t1"
        assert payload["violation_type"] == "test"


def test_kafka_send_exception_does_not_propagate():
    adapter = KafkaOutputAdapter()
    with patch("confluent_kafka.Producer") as MockProducer:
        mock_prod = MagicMock()
        mock_prod.produce.side_effect = Exception("Network error")
        MockProducer.return_value = mock_prod
        adapter.setup(MagicMock(bootstrap_servers="x", topic_violation="t"))
        adapter.send(make_event())  # 不应抛出


def test_kafka_close_flushes():
    adapter = KafkaOutputAdapter()
    with patch("confluent_kafka.Producer") as MockProducer:
        mock_prod = MagicMock()
        MockProducer.return_value = mock_prod
        adapter.setup(MagicMock(bootstrap_servers="x", topic_violation="t"))
        adapter.close()
        mock_prod.flush.assert_called_once()
