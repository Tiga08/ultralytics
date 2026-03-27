# tvp/api/app.py
from fastapi import FastAPI
from api.routers import tasks, cameras, health, plugins


def create_app() -> FastAPI:
    import detector  # noqa: F401 — 触发插件注册
    import output    # noqa: F401

    app = FastAPI(title="Tiga Vision Platform", version="1.0.0")
    app.include_router(tasks.router)
    app.include_router(cameras.router)
    app.include_router(health.router)
    app.include_router(plugins.router)
    return app
