"""Turbulator optimizer endpoint — gh-935 Part C.

POST /aeroplanes/{aeroplane_id}/turbulator/optimize
  → run the turbulator optimizer and return per-section optima + 3D summary.

This is a compute-only endpoint (Slice 2): results are returned but not
persisted. Persisting the optimal position to the turbulator is Slice 3.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, status
from pydantic import UUID4
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ServiceException, ValidationDomainError
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.turbulator_optimizer import (
    TurbulatorOptimizeRequest,
    TurbulatorOptimizerResponse,
    TurbulatorOptimizerSummarySchema,
    TurbulatorSectionResult,
)
from app.services.turbulator_optimizer_service import TurbulatorOptimizerResult

logger = logging.getLogger(__name__)

router = APIRouter()


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


def _call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ServiceException as exc:
        _raise_http(exc)
    except Exception as exc:
        logger.error("Unexpected error in turbulator optimizer: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


def _call_optimizer(
    db: Session,
    aeroplane_id: UUID4,
    scope: str,
) -> TurbulatorOptimizerResult:
    """Resolve section data and run the turbulator optimizer.

    Operating-point resolution:
    1. Read design_speed_mps assumption (defaults to 15 m/s).
    2. Run LiftingLine via section_aoa_service to get per-section (y, chord, cl, Re, airfoil).
    3. Pass to build_wing_section_data (shared helper, MINOR 4/5) → WingSectionData list.
    4. Pass to turbulator_optimizer_service.run_turbulator_optimizer.
    """
    import aerosandbox as asb

    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.services.analysis_service import get_aeroplane_schema_or_raise
    from app.services.design_assumptions_service import get_effective_assumption
    from app.services.section_aoa_service import compute_section_aoa
    from app.services.turbulator_optimizer_service import (
        build_wing_section_data,
        run_turbulator_optimizer,
    )

    # --- Resolve aeroplane --------------------------------------------------
    aircraft = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == str(aeroplane_id)).first()
    if aircraft is None:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_id)

    # --- Operating speed ----------------------------------------------------
    design_speed = get_effective_assumption(db, aircraft.id, "design_speed_mps") or 15.0

    # --- Build ASB airplane -------------------------------------------------
    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_id)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)

    if not asb_airplane.wings:
        raise ValidationDomainError(
            message="Cannot optimize turbulator: aircraft has no wings."
        )

    # --- Pick main wing (largest planform area) ------------------------------
    main_wing = max(asb_airplane.wings, key=lambda w: float(w.area()))
    wing_name = getattr(main_wing, "name", None) or "main_wing"
    s_ref = float(main_wing.area())
    wing_symmetric = getattr(main_wing, "symmetric", False)

    # --- Build operating point ----------------------------------------------
    # alpha=3.0 is a representative cruise value; LiftingLine re-solves the
    # circulation at the true condition, so only the CL-distribution shape
    # depends on this seed alpha.
    asb_op = asb.OperatingPoint(
        velocity=design_speed,
        alpha=3.0,
    )

    # --- Get per-section data from LiftingLine ------------------------------
    try:
        section_entries = compute_section_aoa(asb_airplane, asb_op, wing_name=wing_name)
    except Exception as exc:
        raise ValidationDomainError(
            message=f"Could not compute section AoA for wing '{wing_name}': {exc}"
        ) from exc

    if not section_entries:
        raise ValidationDomainError(
            message="No spanwise sections could be computed for this wing."
        )

    # --- Build WingSectionData list (shared helper, MINOR 4/5) --------------
    wing_data = build_wing_section_data(
        asb_airplane=asb_airplane,
        section_entries=section_entries,
        velocity=design_speed,
        s_ref=s_ref,
    )

    # --- Run optimizer ------------------------------------------------------
    return run_turbulator_optimizer(
        sections=wing_data,
        s_ref=s_ref,
        scope=scope,
        wing_symmetric=wing_symmetric,
    )


def _result_to_response(result: TurbulatorOptimizerResult) -> TurbulatorOptimizerResponse:
    """Convert the service result to the Pydantic response schema."""
    sections = [
        TurbulatorSectionResult(
            y_m=sec.y_m,
            chord_m=sec.chord_m,
            re_local=sec.re_local,
            cl=sec.cl,
            xtr_opt=sec.xtr_opt,
            cd_clean=sec.cd_clean,
            cd_tripped=sec.cd_tripped,
            delta_cd=sec.delta_cd,
            warnings=sec.warnings,
        )
        for sec in result.sections
    ]
    summary = TurbulatorOptimizerSummarySchema(
        delta_cd0=result.summary.delta_cd0,
        l_d_clean=result.summary.l_d_clean,
        l_d_tripped=result.summary.l_d_tripped,
        delta_l_d=result.summary.delta_l_d,
    )
    return TurbulatorOptimizerResponse(
        sections=sections,
        summary=summary,
        scope=result.scope,
    )


@router.post(
    "/aeroplanes/{aeroplane_id}/turbulator/optimize",
    status_code=status.HTTP_200_OK,
    tags=["turbulator"],
    operation_id="optimize_turbulator",
    summary="Optimize turbulator trip position for minimum section drag",
    responses={
        404: {"description": "Aeroplane not found"},
        422: {"description": "Validation error (no wings, invalid scope)"},
        500: {"description": "Internal server error"},
    },
)
async def optimize_turbulator(
    aeroplane_id: Annotated[UUID4, Path(..., description="The ID of the aeroplane")],
    body: Annotated[TurbulatorOptimizeRequest, Body(...)],
    db: Annotated[Session, Depends(get_db)],
) -> TurbulatorOptimizerResponse:
    """Run the turbulator x/c position optimizer for the aircraft's main wing.

    For each spanwise section at the design operating point (design_speed_mps),
    sweeps the trip position (xtr_upper) over a 15-point grid (0.2→0.9) and
    returns the position that minimises 2D drag (cd).

    Returns per-section optima and a 3D summary (ΔCD0, L/D with/without turbulator).

    This endpoint is COMPUTE-ONLY (Slice 2). The results are not persisted
    back to the turbulator position — that is Slice 3.
    """
    result = _call(_call_optimizer, db, aeroplane_id, body.scope)
    return _result_to_response(result)
