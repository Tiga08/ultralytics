import subprocess
import threading
import time
import numpy as np
from utils.logger import logger
from pipeline.frame import Frame


class VideoCapture:
    def __init__(self, rtsp_url: str, reconnect_interval: int = 5,
                 rtsp_interval: float = 0.5):
        self._url = rtsp_url
        self._reconnect_interval = reconnect_interval
        self._interval = rtsp_interval

    def _probe_resolution(self) -> tuple[int, int]:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0", self._url,
        ]
        try:
            out = subprocess.check_output(cmd, timeout=10).decode().strip()
            w, h = map(int, out.split(","))
            return w, h
        except Exception as e:
            logger.warning("ffprobe_failed", url=self._url, error=str(e))
            return 1920, 1080

    def stream(self, stop_event: threading.Event, camera_id: str = ""):
        while not stop_event.is_set():
            process = None
            try:
                w, h = self._probe_resolution()
                fps = 1.0 / self._interval if self._interval > 0 else 2.0
                cmd = [
                    "ffmpeg", "-rtsp_transport", "tcp",
                    "-i", self._url,
                    "-vf", f"fps={fps:.4f}",
                    "-f", "rawvideo", "-pix_fmt", "bgr24", "pipe:1",
                ]
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
                )
                frame_size = w * h * 3
                while not stop_event.is_set():
                    raw = process.stdout.read(frame_size)
                    if len(raw) < frame_size:
                        break
                    yield Frame(
                        image=np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3)).copy(),
                        timestamp=time.time(),
                        camera_id=camera_id,
                    )
            except Exception as e:
                logger.warning("capture_error", url=self._url, error=str(e))
            finally:
                if process is not None:
                    process.kill()
                    process.wait()
            if not stop_event.is_set():
                time.sleep(self._reconnect_interval)
