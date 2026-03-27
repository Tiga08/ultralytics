import io

import cv2

from core.registry import PluginRegistry
from output.base import OutputAdapterBase
from pipeline.events import ViolationEvent
from utils.logger import logger


@PluginRegistry.output("minio")
class MinioOutputAdapter(OutputAdapterBase):
    def setup(self, config) -> None:
        from minio import Minio
        self._client = Minio(
            config.endpoint, access_key=config.access_key,
            secret_key=config.secret_key, secure=config.secure
        )
        self._bucket = config.bucket
        self._jpeg_quality = config.jpeg_quality
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def send(self, event: ViolationEvent) -> None:
        if event.frame_snapshot is None:
            return
        try:
            ok, buf = cv2.imencode(
                ".jpg", event.frame_snapshot,
                [cv2.IMWRITE_JPEG_QUALITY, self._jpeg_quality]
            )
            if not ok:
                return
            data = buf.tobytes()
            obj_name = f"{event.task_id}/{event.violation_type}/{int(event.timestamp * 1000)}.jpg"
            self._client.put_object(
                self._bucket, obj_name, io.BytesIO(data),
                length=len(data), content_type="image/jpeg"
            )
        except Exception as e:
            logger.error("minio_send_failed", error=str(e))

    def close(self) -> None:
        pass
