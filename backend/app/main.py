"""Application factory and ASGI entry point.

The scanner is an *authorized* tool: every scan will later require proof of
target ownership and explicit authorization (see Phase 1 of the roadmap). This
module just wires up the HTTP surface; the guardrails live in their own modules.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.health import router as health_router
from app.api.targets import router as targets_router
from app.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger("webhawk")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(debug=settings.debug)

    app = FastAPI(
        title="WebHawk API",
        version=__version__,
        summary="Authorized web-application vulnerability scanner.",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(targets_router)

    logger.info("WebHawk API initialised (env=%s)", settings.environment)
    return app


# Uvicorn entry point: `uvicorn app.main:app`.
app = create_app()
