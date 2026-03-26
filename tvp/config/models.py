from pydantic import BaseModel, RootModel


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8555


class VideoConfig(BaseModel):
    capture_backend: str = "ffmpeg"
    reconnect_interval: int = 5
    frame_queue_size: int = 30


class InferenceConfig(BaseModel):
    backend: str = "auto"
    thread_count: int = 4


class TrackingConfig(BaseModel):
    high_thresh: float = 0.6
    low_thresh: float = 0.1
    buffer: int = 30


class HealthConfig(BaseModel):
    check_interval: int = 30
    restart_on_failure: bool = True
    max_restart_count: int = 3
    camera_timeout: int = 60


class LoggingConfig(BaseModel):
    level: str = "INFO"
    format: str = "json"
    file_path: str = "logs/"


class ModelWeightEntry(BaseModel):
    path: str
    imgsz: int = 640
    conf: float = 0.3


class ModelWeightsConfig(RootModel[dict[str, ModelWeightEntry]]):
    pass


class KafkaConfig(BaseModel):
    bootstrap_servers: str
    topic_violation: str = "tvp_violation_events"


class MinioConfig(BaseModel):
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str = "tvp-evidence"
    secure: bool = False
    jpeg_quality: int = 85


class MqttConfig(BaseModel):
    host: str
    port: int = 1883
    topic_violation: str = "tvp/violation"


class TvpConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    video: VideoConfig = VideoConfig()
    inference: InferenceConfig = InferenceConfig()
    model_weights: ModelWeightsConfig
    tracking: TrackingConfig = TrackingConfig()
    kafka: KafkaConfig | None = None
    minio: MinioConfig | None = None
    mqtt: MqttConfig | None = None
    health: HealthConfig = HealthConfig()
    logging: LoggingConfig = LoggingConfig()


class CameraConfig(BaseModel):
    id: str
    name: str = ""
    rtsp_url: str
    rtsp_interval: float = 0.5


class ScheduleConfig(BaseModel):
    enabled_days: list[int] = [1, 2, 3, 4, 5, 6, 7]
    start_time: str = "00:00:00"
    end_time: str = "23:59:59"


class DetectorTaskConfig(BaseModel):
    name: str
    config: dict = {}


class TaskConfig(BaseModel):
    task_id: str
    task_name: str = ""
    stand_id: str = ""
    priority: str = "NORMAL"
    camera: CameraConfig
    schedule: ScheduleConfig = ScheduleConfig()
    detectors: list[DetectorTaskConfig]
