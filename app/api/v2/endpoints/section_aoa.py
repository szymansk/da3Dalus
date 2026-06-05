"""Endpoint: GET /aeroplanes/{uuid}/wings/{name}/section-aoa (gh-840).

Returns per-section world angle of attack for a named wing, computed via
``asb.LiftingLine`` at the specified (or resolved) trimmed operating point.

Platform guard: this module is only imported when ``aerosandbox_available()``
returns True.  ``main.py`` wraps the import in a try/except behind that guard.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi import status
from pydantic import UUID4, BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ServiceException, ValidationDomainError
from app.core.platform import require_aerosandbox
from app.db.session import get_db

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class SectionAoaPoint(BaseModel):
    """One spanwise sample point."""

    y_m: float
    chord_m: float
    cl: float
    alpha_geometric_deg: float
    alpha_effective_deg: float
    induced_angle_deg: float


class SectionAoaResponse(BaseModel):
    """Response for GET …/section-aoa."""

    aeroplane_id: str
    wing_name: str
    operating_point_id: int | None
    sections: list[SectionAoaPoint]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _raise_http(exc: ServiceException) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, ValidationDomainError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
    ) from exc


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/aeroplanes/{aeroplane_id}/wings/{wing_name}/section-aoa",
    response_model=SectionAoaResponse,
    status_code=status.HTTP_200_OK,
    tags=["wings", "aerodynamics"],
    operation_id="get_wing_section_aoa",
    dependencies=[Depends(require_aerosandbox)],
    summary="Per-section world AoA via LiftingLine (gh-840)",
    description=(
        "Returns the as-built world angle of attack (trim α + incidence + twist − induced) "
        "for every spanwise panel of the specified wing. "
        "Uses asb.LiftingLine for the per-section induced-downwash decomposition.\n\n"
        "**Operating-point resolution order:**\n"
        "1. `operating_point_id` query param (stored TRIMMED OP).\n"
        "2. First TRIMMED OP found for the aircraft.\n"
        "3. Level-flight AeroBuildup solve (fallback if no stored OP exists)."
    ),
)
async def get_wing_section_aoa(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    wing_name: Annotated[str, Path(..., description="Wing name (e.g. 'main_wing')")],
    db: Annotated[Session, Depends(get_db)],
    operating_point_id: Annotated[
        int | None,
        Query(
            description=(
                "ID of a stored TRIMMED OperatingPoint to use. "
                "When omitted, the first TRIMMED OP on the aircraft is used, "
                "or a level-flight solve is performed as fallback."
            )
        ),
    ] = None,
) -> SectionAoaResponse:
    """Compute per-section world AoA via LiftingLine."""
    from app.services.section_aoa_service import get_section_aoa

    try:
        entries = await get_section_aoa(
            db,
            aeroplane_id,
            wing_name,
            operating_point_id=operating_point_id,
        )
    except ServiceException as exc:
        _raise_http(exc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc

    return SectionAoaResponse(
        aeroplane_id=str(aeroplane_id),
        wing_name=wing_name,
        operating_point_id=operating_point_id,
        sections=[SectionAoaPoint(**e.to_dict()) for e in entries],
    )
