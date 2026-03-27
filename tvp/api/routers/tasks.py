# tvp/api/routers/tasks.py
from fastapi import APIRouter, Depends, HTTPException, Response
from config.models import TaskConfig
from api.deps import get_engine
from api.schemas.responses import CommonResponse
from core.engine import TvpEngine

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.post("", status_code=201, response_model=CommonResponse)
async def create_task(req: TaskConfig, engine: TvpEngine = Depends(get_engine)):
    try:
        engine.create_task(req)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CommonResponse.ok(message="Task created successfully")


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, engine: TvpEngine = Depends(get_engine)):
    try:
        engine.delete_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return Response(status_code=204)


@router.get("/{task_id}", response_model=CommonResponse)
async def get_task(task_id: str, engine: TvpEngine = Depends(get_engine)):
    try:
        return CommonResponse.ok(data=engine.get_task_status(task_id))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")


@router.get("", response_model=CommonResponse)
async def list_tasks(engine: TvpEngine = Depends(get_engine)):
    return CommonResponse.ok(data=engine.list_tasks())


@router.post("/{task_id}/pause", response_model=CommonResponse)
async def pause_task(task_id: str, engine: TvpEngine = Depends(get_engine)):
    try:
        engine.pause_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return CommonResponse.ok(message="Task paused")


@router.post("/{task_id}/resume", response_model=CommonResponse)
async def resume_task(task_id: str, engine: TvpEngine = Depends(get_engine)):
    try:
        engine.resume_task(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return CommonResponse.ok(message="Task resumed")
