# tvp/api/routers/health.py
from fastapi import APIRouter, Depends
from api.deps import get_engine
from api.schemas.responses import HealthResponse, TaskHealthInfo
from core.engine import TvpEngine

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(engine: TvpEngine = Depends(get_engine)):
    tasks = engine.list_tasks()
    task_infos = [
        TaskHealthInfo(
            task_id=t["task_id"],
            status=t["status"],
            is_healthy=t.get("is_healthy", False),
            fail_count=t.get("fail_count", 0),
            camera_id=t.get("camera_id", ""),
        )
        for t in tasks
    ]
    unhealthy = [t for t in task_infos if not t.is_healthy]
    return HealthResponse(
        healthy=len(unhealthy) == 0,
        task_count=len(tasks),
        unhealthy_count=len(unhealthy),
        tasks=task_infos,
    )
