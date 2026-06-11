"""Health and readiness endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__

router = APIRouter(tags=["health"])

# Process start time, used to report uptime.
_STARTED_AT = time.monotonic()


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
def health() -> HealthResponse:
    """Liveness check — the process is up and serving requests."""
    return HealthResponse(
        status="ok",
        version=__version__,
        uptime_seconds=round(time.monotonic() - _STARTED_AT, 3),
    )
