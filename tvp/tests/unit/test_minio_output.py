import sys
import types

import numpy as np

# minio 是可选依赖，未安装时用假模块占位，让 patch 能正常工作
if "minio" not in sys.modules:
    fake_minio = types.ModuleType("minio")
    fake_minio.Minio = None  # patch 目标占位
    sys.modules["minio"] = fake_minio

from unittest.mock import patch, MagicMock  # noqa: E402
from output.minio_output import MinioOutputAdapter  # noqa: E402
from pipeline.events import ViolationEvent  # noqa: E402


def make_event_with_snapshot():
    return ViolationEvent(task_id="t1", detector_name="d1", violation_type="test",
                          timestamp=1000.5,
                          frame_snapshot=np.zeros((100, 100, 3), dtype=np.uint8),
                          bounding_boxes=[])


def test_minio_send_uploads_jpeg():
    adapter = MinioOutputAdapter()
    with patch("minio.Minio") as MockMinio, patch("cv2.imencode") as mock_enc:
        mock_client = MagicMock()
        MockMinio.return_value = mock_client
        mock_client.bucket_exists.return_value = True
        mock_enc.return_value = (True, np.array([0xFF, 0xD8], dtype=np.uint8))
        cfg = MagicMock(endpoint="x:9000", access_key="a", secret_key="s",
                        bucket="b", secure=False, jpeg_quality=85)
        adapter.setup(cfg)
        adapter.send(make_event_with_snapshot())
        mock_client.put_object.assert_called_once()
        obj_name = mock_client.put_object.call_args[0][1]
        assert "t1/test/" in obj_name and obj_name.endswith(".jpg")


def test_minio_send_skips_none_snapshot():
    adapter = MinioOutputAdapter()
    with patch("minio.Minio") as MockMinio:
        mock_client = MagicMock()
        MockMinio.return_value = mock_client
        mock_client.bucket_exists.return_value = True
        cfg = MagicMock(endpoint="x:9000", access_key="a", secret_key="s",
                        bucket="b", secure=False, jpeg_quality=85)
        adapter.setup(cfg)
        event = ViolationEvent(task_id="t1", detector_name="d", violation_type="v",
                               timestamp=0.0, frame_snapshot=None, bounding_boxes=[])
        adapter.send(event)
        mock_client.put_object.assert_not_called()


def test_minio_creates_bucket_if_not_exists():
    adapter = MinioOutputAdapter()
    with patch("minio.Minio") as MockMinio:
        mock_client = MagicMock()
        MockMinio.return_value = mock_client
        mock_client.bucket_exists.return_value = False
        cfg = MagicMock(endpoint="x:9000", access_key="a", secret_key="s",
                        bucket="new-bucket", secure=False, jpeg_quality=85)
        adapter.setup(cfg)
        mock_client.make_bucket.assert_called_once_with("new-bucket")
