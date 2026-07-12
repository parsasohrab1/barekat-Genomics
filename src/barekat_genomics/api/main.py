"""FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from barekat_genomics import __version__
from barekat_genomics.api.routes import patients, samples, pipeline, reports, ehr, health
from barekat_genomics.core.config import get_settings

logger = structlog.get_logger(__name__)

DASHBOARD_DIST = Path(__file__).resolve().parents[3] / "dashboard" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("starting_app", env=settings.app_env, version=__version__)
    yield
    logger.info("shutting_down_app")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="barekat-Genomics",
        description="پلتفرم تحلیل داده‌های ژنومی و فارماکوژنومیک",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix, tags=["Health"])
    app.include_router(patients.router, prefix=prefix, tags=["Patients"])
    app.include_router(samples.router, prefix=prefix, tags=["Samples"])
    app.include_router(pipeline.router, prefix=prefix, tags=["Pipeline"])
    app.include_router(reports.router, prefix=prefix, tags=["Reports"])
    app.include_router(ehr.router, prefix=prefix, tags=["EHR Integration"])

    _mount_dashboard(app)

    return app


def _mount_dashboard(app: FastAPI) -> None:
    """Serve built React dashboard at root when dist/ exists."""
    if not DASHBOARD_DIST.is_dir():
        return

    assets_dir = DASHBOARD_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="dashboard-assets")

    @app.get("/", include_in_schema=False)
    async def dashboard_index():
        return FileResponse(DASHBOARD_DIST / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def dashboard_spa(full_path: str):
        file_path = DASHBOARD_DIST / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(DASHBOARD_DIST / "index.html")


app = create_app()
