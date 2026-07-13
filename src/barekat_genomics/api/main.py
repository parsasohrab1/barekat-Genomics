"""FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from barekat_genomics import __version__
from barekat_genomics.api.middleware.metrics import PrometheusMiddleware
from barekat_genomics.api.routes import patients, samples, pipeline, reports, ehr, health, dashboard, variants, auth, audit, ai
from barekat_genomics.core.config import get_settings
from barekat_genomics.core.observability import setup_observability
from barekat_genomics.core.observability.metrics import init_app_info

logger = structlog.get_logger(__name__)

DASHBOARD_DIST = Path(__file__).resolve().parents[3] / "dashboard" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_observability()
    init_app_info(__version__, settings.app_env)
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

    if settings.metrics_enabled:
        app.add_middleware(PrometheusMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(health.router, prefix=prefix, tags=["Health"])
    app.include_router(auth.router, prefix=prefix, tags=["Auth"])
    app.include_router(patients.router, prefix=prefix, tags=["Patients"])
    app.include_router(samples.router, prefix=prefix, tags=["Samples"])
    app.include_router(pipeline.router, prefix=prefix, tags=["Pipeline"])
    app.include_router(reports.router, prefix=prefix, tags=["Reports"])
    app.include_router(ehr.router, prefix=prefix, tags=["EHR Integration"])
    app.include_router(dashboard.router, prefix=prefix, tags=["Dashboard"])
    app.include_router(variants.router, prefix=prefix, tags=["Variants"])
    app.include_router(audit.router, prefix=prefix, tags=["Audit"])
    app.include_router(ai.router, prefix=prefix, tags=["AI Decision Support"])

    if settings.metrics_enabled:
        from barekat_genomics.api.routes.health import prometheus_metrics

        app.add_api_route("/metrics", prometheus_metrics, methods=["GET"], include_in_schema=False)

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
