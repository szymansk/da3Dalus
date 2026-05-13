"""Matching chart endpoint — T/W vs W/S constraint diagram (gh-492)."""

from __future__ import annotations

import logging
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError, ServiceException
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.schemas.matching_chart import AircraftMode, MatchingChartResponse, ConstraintLine, DesignPoint
from app.services.design_assumptions_service import get_effective_assumption

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


def _resolve_aircraft_params(
    db: Session,
    plane: AeroplaneModel,
    v_cruise_override: float | None,
) -> dict[str, Any]:
    """Build the aircraft parameter dict consumed by compute_chart.

    Reads design assumptions and the assumption_computation_context stored on
    the aeroplane model, then merges them into a flat dict.  The caller may
    supply an explicit cruise-speed override which takes precedence over both
    the context value and the polar estimate.

    Parameters
    ----------
    db              : open SQLAlchemy session
    plane           : resolved AeroplaneModel row
    v_cruise_override : explicit v_cruise_mps from query params, or None

    Returns
    -------
    dict ready to pass to ``compute_chart`` as the *aircraft* argument.
    """
    ctx: dict[str, Any] = plane.assumption_computation_context or {}

    mass_kg = float(
        get_effective_assumption(db, plane.id, "mass") or PARAMETER_DEFAULTS["mass"]
    )
    cl_max = float(
        get_effective_assumption(db, plane.id, "cl_max") or PARAMETER_DEFAULTS["cl_max"]
    )
    cd0 = float(
        get_effective_assumption(db, plane.id, "cd0") or PARAMETER_DEFAULTS.get("cd0", 0.03)
    )
    t_static_raw = get_effective_assumption(db, plane.id, "t_static_N")
    t_static_n = float(t_static_raw) if t_static_raw and float(t_static_raw) > 0 else 0.0

    s_ref_m2: float | None = ctx.get("s_ref_m2")
    e_oswald: float | None = ctx.get("e_oswald")
    ar: float | None = ctx.get("aspect_ratio")
    v_md_ctx: float | None = ctx.get("v_md_mps")
    v_stall_ctx: float | None = ctx.get("v_stall_mps")
    b_ref_m: float | None = ctx.get("b_ref_m")

    aircraft: dict[str, Any] = {
        "mass_kg": mass_kg,
        "t_static_N": t_static_n,
        "cd0": cd0,
        "e_oswald": e_oswald if e_oswald else 0.8,
        "ar": ar if ar else 7.0,
        "cl_max_clean": cl_max,
        "cl_max_takeoff": cl_max,        # clean CL_max for TO (conservative)
        "cl_max_landing": cl_max * 1.3,  # rough flaps factor for landing
    }
    if s_ref_m2 is not None and s_ref_m2 > 0:
        aircraft["s_ref_m2"] = s_ref_m2
    if b_ref_m is not None:
        aircraft["b_ref_m"] = b_ref_m
    if v_md_ctx is not None:
        aircraft["v_md_mps"] = v_md_ctx
    if v_stall_ctx is not None:
        aircraft["v_stall_mps"] = v_stall_ctx

    # Cruise speed: explicit override wins; otherwise fall back to v_md from context.
    # When neither is present the service estimates v_cruise from polar parameters.
    v_cruise_resolved = v_cruise_override if v_cruise_override is not None else v_md_ctx
    if v_cruise_resolved is not None:
        aircraft["v_cruise_mps"] = v_cruise_resolved

    return aircraft


@router.get(
    "/aeroplanes/{aeroplane_id}/matching-chart",
    operation_id="get_matching_chart",
    tags=["matching-chart"],
    summary="Compute T/W vs W/S matching chart with constraint lines",
    responses={
        404: {"description": "Aeroplane not found"},
        422: {"description": "Missing required assumption (e.g. mass, polar parameters)"},
    },
)
async def get_matching_chart(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
    mode: Annotated[
        AircraftMode,
        Query(
            description=(
                "Aircraft mode: rc_runway | rc_hand_launch | uav_runway | uav_belly_land. "
                "Sets default field length, climb-gradient, and stall-speed targets."
            )
        ),
    ] = "rc_runway",
    s_runway: Annotated[
        float | None,
        Query(
            gt=0,
            description="[Override] Field length target [m] (to 50 ft for TO; from 50 ft for LDG). "
            "Defaults: rc_runway=50 m, uav_runway=200 m.",
        ),
    ] = None,
    v_s_target: Annotated[
        float | None,
        Query(
            gt=0,
            description="[Override] Maximum acceptable stall speed [m/s] (clean). "
            "Defaults: rc=7 m/s, uav=12 m/s.",
        ),
    ] = None,
    gamma_climb_deg: Annotated[
        float | None,
        Query(
            gt=0,
            le=30,
            description="[Override] Target climb gradient [°]. "
            "Defaults: rc=5°, uav=4°.",
        ),
    ] = None,
    v_cruise_mps: Annotated[
        float | None,
        Query(
            gt=0,
            description="[Override] Cruise speed [m/s] for the cruise constraint. "
            "Defaults to v_md_mps from assumption context or polar estimate.",
        ),
    ] = None,
) -> MatchingChartResponse:
    """Compute the T/W vs W/S matching chart for an aeroplane.

    Generates five constraint lines (takeoff, landing, cruise, climb, stall)
    as functions of wing loading W/S.  Each constraint defines the **minimum**
    T/W (or maximum W/S) required to satisfy that flight-phase requirement.

    The design point is derived from the aircraft's current mass, static thrust,
    and wing reference area stored in design assumptions + computation context.

    **Convention**: T/W = T_static_SL / W_MTOW (static thrust at sea level over
    maximum take-off weight). AR is held constant — when the design point is
    dragged, S = W / (W/S) and b = √(AR · S) vary accordingly.

    **Takeoff/Landing constants** (Loftin/Roskam §3.4): k_TO = 1.66, k_LDG = 2.73 —
    identical to the field-length service to prevent constant drift.

    **Stall constraint** uses CL_max_clean (not landing-configuration CL_max) per spec.

    Required design assumptions (via /design-assumptions endpoint):
    - ``mass``          — aircraft mass [kg]
    - ``cl_max``        — base CL_max (clean configuration)
    - ``cd0``           — zero-lift drag coefficient
    - ``t_static_N``    — zero-velocity static thrust [N]

    Required in assumption computation context (auto-populated by recompute):
    - ``s_ref_m2``      — wing reference area [m²]
    - ``e_oswald``      — Oswald efficiency factor
    - ``aspect_ratio``  — wing AR (or from geometry)
    """
    from app.services.matching_chart_service import compute_chart

    try:
        plane = _get_aeroplane(db, aeroplane_id)
        aircraft = _resolve_aircraft_params(db, plane, v_cruise_override=v_cruise_mps)

        result = compute_chart(
            aircraft,
            mode=mode,
            s_runway=s_runway,
            v_s_target=v_s_target,
            gamma_climb_deg=gamma_climb_deg,
            v_cruise_mps=v_cruise_mps,
        )

        # --- Map result to Pydantic schema -----------------------------------
        constraint_objs: list[ConstraintLine] = []
        for c in result["constraints"]:
            constraint_objs.append(
                ConstraintLine(
                    name=c["name"],
                    t_w_points=c.get("t_w_points"),
                    ws_max=c.get("ws_max"),
                    color=c["color"],
                    binding=c["binding"],
                    hover_text=c.get("hover_text"),
                )
            )

        dp_raw = result["design_point"]
        return MatchingChartResponse(
            ws_range_n_m2=result["ws_range_n_m2"],
            constraints=constraint_objs,
            design_point=DesignPoint(
                ws_n_m2=dp_raw["ws_n_m2"],
                t_w=dp_raw["t_w"],
            ),
            feasibility=result["feasibility"],
            warnings=result["warnings"],
        )

    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover — defensive fallback
        logger.exception("Unexpected error in get_matching_chart: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc
