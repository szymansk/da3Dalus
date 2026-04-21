"""Health check endpoint.

Intentionally lightweight: performs a cheap SELECT 1 against the
configured database and returns a small JSON body. Must not import
CadQuery, Aerosandbox or any other heavy library — the endpoint is
expected to stay importable on every supported platform, including
linux/aarch64 where the CAD stack is excluded.
"""

from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.settings import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Simple liveness + database reachability payload."""

    status: str = Field(..., description="'ok' when the service is up.")
    version: str = Field(..., description="Application version from settings.")
    database: str = Field(
        ...,
        description="'reachable' if a trivial SELECT 1 succeeded, 'unreachable' otherwise.",
    )


@router.get(
    "/health",
    tags=["health"],
    summary="Liveness + database ping"
)
def get_health(db: Annotated[Session, Depends(get_db)]) -> HealthResponse:
    """Return service status and a DB reachability flag.

    A non-reachable database still returns HTTP 200 with
    ``database = "unreachable"`` so that a load balancer can tell the
    difference between "service is down" (HTTP error) and "service is
    up but degraded" (200 with payload).
    """
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        database_status = "reachable"
    except SQLAlchemyError:
        database_status = "unreachable"

    return HealthResponse(
        status="ok",
        version=settings.version,
        database=database_status,
    )
