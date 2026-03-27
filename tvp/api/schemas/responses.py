from datetime import datetime, timezone
from pydantic import BaseModel, model_validator


class CommonResponse(BaseModel):
    success: bool
    data: dict | list | None = None
    message: str = ""
    timestamp: str = ""

    @model_validator(mode="before")
    @classmethod
    def set_timestamp(cls, values):
        if not values.get("timestamp"):
            values["timestamp"] = datetime.now(timezone.utc).isoformat()
        return values

    @classmethod
    def ok(cls, data=None, message: str = "") -> "CommonResponse":
        return cls(success=True, data=data, message=message)

    @classmethod
    def error(cls, message: str) -> "CommonResponse":
        return cls(success=False, message=message)


class TaskHealthInfo(BaseModel):
    task_id: str
    status: str
    is_healthy: bool
    fail_count: int
    camera_id: str


class TaskResponse(BaseModel):
    task_id: str
    task_name: str
    priority: str
    status: str
    camera_id: str
    fail_count: int
    is_healthy: bool


class HealthResponse(BaseModel):
    healthy: bool
    task_count: int
    unhealthy_count: int
    tasks: list[TaskHealthInfo]


class PluginsResponse(BaseModel):
    detectors: list[str]
    outputs: list[str]
