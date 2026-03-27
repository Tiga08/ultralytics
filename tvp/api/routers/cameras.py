# tvp/api/routers/cameras.py
from fastapi import APIRouter, Depends, HTTPException
from api.deps import get_engine
from api.schemas.responses import CommonResponse
from core.engine import TvpEngine

router = APIRouter(prefix="/api/v1/cameras", tags=["cameras"])


@router.get("", response_model=CommonResponse)
async def list_cameras(engine: TvpEngine = Depends(get_engine)):
    tasks = engine.list_tasks()
    cameras: dict[str, dict] = {}
    for t in tasks:
        cid = t.get("camera_id", "")
        if cid not in cameras:
            cameras[cid] = {"camera_id": cid, "task_count": 0, "is_healthy": True}
        cameras[cid]["task_count"] += 1
        if not t.get("is_healthy", True):
            cameras[cid]["is_healthy"] = False
    return CommonResponse.ok(data=list(cameras.values()))


@router.get("/{camera_id}/status", response_model=CommonResponse)
async def camera_status(camera_id: str, engine: TvpEngine = Depends(get_engine)):
    tasks = [t for t in engine.list_tasks() if t.get("camera_id") == camera_id]
    if not tasks:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    is_healthy = all(t.get("is_healthy", False) for t in tasks)
    return CommonResponse.ok(data={"camera_id": camera_id, "is_healthy": is_healthy})
