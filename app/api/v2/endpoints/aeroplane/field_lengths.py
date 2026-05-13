"""Field length endpoints — takeoff and landing distance (gh-489)."""

from __future__ import annotations

import logging
from typing import Annotated, Literal, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError, ServiceException
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.schemas.field_length import FieldLengthRead, LandingMode, TakeoffMode

logger = logging.getLogger(__name__)

router = APIRouter()


def _raise_http_from_domain(exc: ServiceException) -> NoReturn:
    """Map domain exceptions to HTTP status codes."""
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    if isinstance(exc, InternalError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message
        ) from exc
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


def _get_aeroplane(db: Session, aeroplane_id: UUID4) -> AeroplaneModel:
    """Resolve aeroplane by UUID or raise HTTP 404."""
    plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == str(aeroplane_id)).first()
    if plane is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aeroplane not found")
    return plane


def _effective_assumption(
    db: Session, aeroplane_id: int, param_name: str
) -> float | None:
    """Return the effective (active-source) value of a design assumption, or None."""
    row = (
        db.query(DesignAssumptionModel)
        .filter(
            DesignAssumptionModel.aeroplane_id == aeroplane_id,
            DesignAssumptionModel.parameter_name == param_name,
        )
        .first()
    )
    if row is None:
        return PARAMETER_DEFAULTS.get(param_name)
    if row.active_source == "CALCULATED" and row.calculated_value is not None:
        return row.calculated_value
    return row.estimate_value


@router.get(
    "/aeroplanes/{aeroplane_id}/field-lengths",
    operation_id="get_field_lengths",
    tags=["field-lengths"],
    summary="Compute takeoff and landing field lengths",
    responses={
        404: {"description": "Aeroplane not found"},
        422: {"description": "Missing required assumption (e.g. t_static_N)"},
    },
)
async def get_field_lengths(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
    takeoff_mode: Annotated[
        TakeoffMode,
        Query(description="Takeoff mode: runway | hand_launch | bungee | catapult"),
    ] = "runway",
    landing_mode: Annotated[
        LandingMode,
        Query(description="Landing mode: runway | belly_land"),
    ] = "runway",
    v_throw_mps: Annotated[
        float | None,
        Query(gt=0, description="[hand_launch] throw speed in m/s (default 10 m/s)"),
    ] = None,
    v_release_mps: Annotated[
        float | None,
        Query(gt=0, description="[bungee/catapult] release speed in m/s"),
    ] = None,
    bungee_force_N: Annotated[
        float | None,
        Query(gt=0, description="[bungee] bungee tension force in N"),
    ] = None,
    stretch_m: Annotated[
        float | None,
        Query(gt=0, description="[bungee] bungee stretch distance in m"),
    ] = None,
) -> FieldLengthRead:
    """Compute takeoff and landing field lengths for an aeroplane.

    Uses the Roskam Vol I §3.4 simplified ground-roll (energy method) with
    RC-specific mode extensions. Reads aircraft parameters from the
    design-assumptions table and the assumption_computation_context cache.

    **Required assumptions** (set via Design Assumptions):
    - ``mass``         — aircraft mass [kg]
    - ``cl_max``       — maximum lift coefficient (base value)

    **Required in computation context** (populated by assumption recompute):
    - ``v_stall_mps``  — stall speed [m/s]
    - ``s_ref_m2``     — wing reference area [m²]

    **Required for runway/bungee takeoff**:
    - ``t_static_N``   — zero-velocity static thrust [N]
      (set via Design Assumptions; 0 = absent → 422 error)
    """
    from app.services.field_length_service import compute_field_lengths

    try:
        plane = _get_aeroplane(db, aeroplane_id)

        # Gather inputs from design assumptions + computation context
        ctx = plane.assumption_computation_context or {}

        mass_kg = _effective_assumption(db, plane.id, "mass") or PARAMETER_DEFAULTS["mass"]
        cl_max = _effective_assumption(db, plane.id, "cl_max") or PARAMETER_DEFAULTS["cl_max"]
        t_static_raw = _effective_assumption(db, plane.id, "t_static_N")
        s_ref_m2 = ctx.get("s_ref_m2")
        v_stall_mps = ctx.get("v_stall_mps")

        if s_ref_m2 is None or s_ref_m2 <= 0:
            raise ServiceException(
                message=(
                    "Wing reference area (s_ref_m2) is not available. "
                    "Trigger an assumption recompute first by saving the wing geometry."
                )
            )
        if v_stall_mps is None or v_stall_mps <= 0:
            raise ServiceException(
                message=(
                    "Stall speed (v_stall_mps) is not available. "
                    "Trigger an assumption recompute first."
                )
            )

        aircraft: dict = {
            "mass_kg": float(mass_kg),
            "s_ref_m2": float(s_ref_m2),
            "cl_max": float(cl_max),
            "v_stall_mps": float(v_stall_mps),
        }

        # Include thrust if present (and non-zero)
        if t_static_raw is not None and float(t_static_raw) > 0:
            aircraft["t_static_N"] = float(t_static_raw)
        # else: leave absent → service will raise if mode requires it

        # RC mode inputs
        if v_throw_mps is not None:
            aircraft["v_throw_mps"] = v_throw_mps
        if v_release_mps is not None:
            aircraft["v_release_mps"] = v_release_mps
        if bungee_force_N is not None:
            aircraft["bungee_force_N"] = bungee_force_N
        if stretch_m is not None:
            aircraft["stretch_m"] = stretch_m

        result = compute_field_lengths(aircraft, takeoff_mode=takeoff_mode, landing_mode=landing_mode)
        return FieldLengthRead(**result)

    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover — defensive fallback
        logger.exception("Unexpected error in get_field_lengths: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc
