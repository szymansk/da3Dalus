"""Powertrain solution-space endpoint (gh-975).

GET /aeroplanes/{aeroplane_id}/powertrain/solution-space

Thin endpoint — delegates entirely to
``app.services.powertrain_solution_space_service.compute_solution_space``.

All tunable assumptions are exposed as query parameters with spec defaults.
cell_counts is a multi-value Query param (e.g. ?cell_counts=2&cell_counts=4).
"""

from __future__ import annotations

import logging
from typing import Annotated, NoReturn, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError, ServiceException
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.powertrain_solution_space import (
    PowertrainSolutionSpaceResponse,
    SolutionSpaceAssumptions,
)
from app.services.powertrain_solution_space_service import compute_solution_space

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
    # ValidationError / ValidationDomainError → 422
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


def _get_aeroplane(db: Session, aeroplane_id: UUID4) -> AeroplaneModel:
    """Resolve aeroplane by UUID or raise HTTP 404."""
    plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == str(aeroplane_id)).first()
    if plane is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aeroplane not found")
    return plane


@router.get(
    "/aeroplanes/{aeroplane_id}/powertrain/solution-space",
    operation_id="get_powertrain_solution_space",
    tags=["powertrain"],
    summary="Compute powertrain required-spec solution space from mission + aero",
    responses={
        404: {"description": "Aeroplane not found"},
        422: {"description": "Invalid assumptions (e.g. V_top ≤ V_cruise, t_target ≤ 0)"},
    },
)
async def get_powertrain_solution_space(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
    # ----- Tunable assumption query params (all optional — spec defaults apply) -----
    cell_counts: Annotated[
        list[int] | None,
        Query(description="LiPo cell counts to evaluate, e.g. ?cell_counts=2&cell_counts=4"),
    ] = None,
    eta_prop_lo: Annotated[
        float | None,
        Query(ge=0.01, le=0.99, description="Lower bound of propeller efficiency band"),
    ] = None,
    eta_prop_hi: Annotated[
        float | None,
        Query(ge=0.01, le=0.99, description="Upper bound of propeller efficiency band"),
    ] = None,
    eta_motor: Annotated[
        float | None,
        Query(ge=0.01, le=0.99, description="Motor efficiency"),
    ] = None,
    eta_esc: Annotated[
        float | None,
        Query(ge=0.01, le=0.99, description="ESC efficiency"),
    ] = None,
    dod: Annotated[
        float | None,
        Query(ge=0.01, le=1.0, description="Depth of discharge (usable fraction)"),
    ] = None,
    esc_margin: Annotated[
        float | None,
        Query(ge=1.0, description="ESC current rating margin multiplier"),
    ] = None,
    c_margin: Annotated[
        float | None,
        Query(ge=1.0, description="Battery C-rate margin multiplier"),
    ] = None,
    load_rpm_factor: Annotated[
        float | None,
        Query(ge=0.5, le=1.0, description="Motor shaft RPM under load vs. no-load"),
    ] = None,
    prop_pd: Annotated[
        float | None,
        Query(ge=0.3, le=1.5, description="Prop pitch/diameter ratio"),
    ] = None,
    t_target_min: Annotated[
        float | None,
        Query(gt=0, description="Target flight time [minutes]"),
    ] = None,
    v_top_mps: Annotated[
        float | None,
        Query(
            gt=0,
            description=(
                "Top speed [m/s] for peak-power sizing. "
                "Defaults to 1.4 × V_cruise when not supplied."
            ),
        ),
    ] = None,
    rho: Annotated[
        float | None,
        Query(gt=0, description="Air density [kg/m³] (ISA sea-level default 1.225)"),
    ] = None,
    g: Annotated[
        float | None,
        Query(gt=0, description="Gravitational acceleration [m/s²]"),
    ] = None,
) -> PowertrainSolutionSpaceResponse:
    """Compute the powertrain solution space for an aeroplane.

    Returns the *required* component-spec envelope (per LiPo cell count, across
    an η_prop band) derived from mission + aero in the gh-924 computation context.

    **Data sources (single source of truth — gh-924):**
    - Aero invariants (cd0, e_oswald, AR, S_ref, V_cruise) come from
      ``assumption_computation_context`` (populated by the recompute endpoint).
    - Mass comes from the design assumption ``mass``.
    - Tunable assumptions (η bands, DoD, cell counts, t_target, V_top) are
      query parameters with spec defaults.

    **Design warnings** are emitted (not errors) when aero context is missing
    or uncomputed — consistent with gh-956.

    **Validation errors (422):**
    - V_top ≤ V_cruise
    - t_target ≤ 0
    """
    try:
        plane = _get_aeroplane(db, aeroplane_id)

        # Build assumptions: start with defaults, apply any provided overrides.
        assumptions_kwargs: dict = {}
        if cell_counts is not None:
            assumptions_kwargs["cell_counts"] = cell_counts
        if eta_prop_lo is not None:
            assumptions_kwargs["eta_prop_lo"] = eta_prop_lo
        if eta_prop_hi is not None:
            assumptions_kwargs["eta_prop_hi"] = eta_prop_hi
        if eta_motor is not None:
            assumptions_kwargs["eta_motor"] = eta_motor
        if eta_esc is not None:
            assumptions_kwargs["eta_esc"] = eta_esc
        if dod is not None:
            assumptions_kwargs["dod"] = dod
        if esc_margin is not None:
            assumptions_kwargs["esc_margin"] = esc_margin
        if c_margin is not None:
            assumptions_kwargs["c_margin"] = c_margin
        if load_rpm_factor is not None:
            assumptions_kwargs["load_rpm_factor"] = load_rpm_factor
        if prop_pd is not None:
            assumptions_kwargs["prop_pd"] = prop_pd
        if t_target_min is not None:
            assumptions_kwargs["t_target_min"] = t_target_min
        if v_top_mps is not None:
            assumptions_kwargs["v_top_mps"] = v_top_mps
        if rho is not None:
            assumptions_kwargs["rho"] = rho
        if g is not None:
            assumptions_kwargs["g"] = g

        assumptions = SolutionSpaceAssumptions(**assumptions_kwargs)

        return compute_solution_space(db, plane, assumptions)

    except ServiceException as exc:
        _raise_http_from_domain(exc)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover — defensive fallback
        logger.exception("Unexpected error in get_powertrain_solution_space: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {exc}",
        ) from exc
