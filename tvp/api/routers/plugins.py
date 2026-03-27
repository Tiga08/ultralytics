# tvp/api/routers/plugins.py
from fastapi import APIRouter
from api.schemas.responses import PluginsResponse
from core.registry import PluginRegistry

router = APIRouter(prefix="/api/v1", tags=["plugins"])


@router.get("/plugins", response_model=PluginsResponse)
async def list_plugins():
    return PluginsResponse(
        detectors=PluginRegistry.list_detectors(),
        outputs=PluginRegistry.list_outputs(),
    )
