# tvp/api/routers/metrics.py
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from utils.metrics import MetricsRegistry

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    return MetricsRegistry.render()
