from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.deps import get_automation_scheduler
from app.api.routes.automation import router as automation_router
from app.api.routes.projects import router as projects_router
from app.core.config import get_settings
from app.core.database import Database


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    Database(settings.database_path)
    settings.runtime_dir.mkdir(parents=True, exist_ok=True)
    scheduler = get_automation_scheduler()
    if settings.automation_scheduler_enabled:
        scheduler.start()
    yield
    scheduler.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    legacy_web_dir = settings.project_root / "app" / "web"
    dist_web_dir = legacy_web_dir / "dist"
    web_dir = dist_web_dir if dist_web_dir.exists() else legacy_web_dir

    app = FastAPI(
        title=settings.app_name,
        version="0.3.0",
        lifespan=lifespan,
        summary="Grid short-video production agent with provider-based orchestration and operator console.",
    )

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    @app.get("/health")
    def healthcheck() -> dict:
        return {"status": "ok", "app_env": settings.app_env, "runtime_dir": str(settings.runtime_dir)}

    app.mount("/web", StaticFiles(directory=web_dir), name="web")
    app.mount("/runtime", StaticFiles(directory=settings.runtime_dir), name="runtime")
    app.include_router(projects_router, prefix="/projects", tags=["projects"])
    app.include_router(automation_router, prefix="/automation", tags=["automation"])
    return app


app = create_app()
