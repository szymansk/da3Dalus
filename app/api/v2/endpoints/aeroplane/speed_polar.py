"""Speed polar endpoint — GET /aeroplanes/{id}/speed-polar (gh-841).

Returns the closed-form aircraft speed polar (sink vs V) from the aeroplane's
assumption_computation_context.  All math lives in speed_polar_service; this
module only handles HTTP plumbing and context extraction.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, NoReturn, cast

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import UUID4, BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ServiceException
from app.db.session import get_db
from app.models.aeroplanemodel import AeroplaneModel
from app.services.speed_polar_service import (
    SpeedPolarResult,
    _MissingInputs,
    compute_speed_polar,
    is_missing,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------


class SpeedPolarPoint(BaseModel):
    v_mps: float
    sink_mps: float
    cl: float


class SpeedPolarResponse(BaseModel):
    """Aircraft speed polar — sink rate [m/s] vs airspeed [m/s].

    All values use SI units. ``sink_mps`` is positive downward.
    """

    v_mps: list[float]
    sink_mps: list[float]
    cl: list[float]
    best_glide: SpeedPolarPoint
    min_sink: SpeedPolarPoint
    inputs: dict[str, Any]


class SpeedPolarMissingResponse(BaseModel):
    """Returned with HTTP 422 when required inputs are absent from the aeroplane context."""

    error: str
    missing_inputs: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_http_from_domain(exc: ServiceException) -> NoReturn:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


def _get_aeroplane(db: Session, aeroplane_id: UUID4) -> AeroplaneModel:
    plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == str(aeroplane_id)).first()
    if plane is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aeroplane not found")
    return plane


def _extract_polar_inputs(plane: AeroplaneModel) -> dict[str, Any]:
    """Pull the parabolic-polar parameters from the computation context.

    Beyond the legacy fixed cd0/e, also pulls the Reynolds cd0/e table, MAC,
    and CL_max so the polar uses the SAME model as the characteristic-speed
    chips (gh-924): the curve and the V_md / V_min_sink markers then match the
    chips instead of diverging.
    """
    ctx: dict[str, Any] = cast(dict[str, Any], plane.assumption_computation_context or {})
    return {
        "mass_kg": _safe_float(ctx.get("mass_kg")),
        "s_ref_m2": _safe_float(ctx.get("s_ref_m2")),
        "ar": _safe_float(ctx.get("aspect_ratio")),
        "e_oswald": _safe_float(ctx.get("e_oswald")),
        "cd0": _safe_float(ctx.get("cd0")),
        "polar_re_table": ctx.get("polar_re_table") or None,
        "mac_m": _safe_float(ctx.get("mac_m")),
        "cl_max": _extract_cl_max(ctx),
    }


def _extract_cl_max(ctx: dict[str, Any]) -> float | None:
    """Clean-config CL_max (stall) — clamps the sweep + markers at V_stall.

    Prefers the clean polar config, falling back to the first Reynolds-table
    row, then a top-level ``cl_max`` field.
    """
    clean = (ctx.get("polar_by_config") or {}).get("clean") or {}
    candidate = clean.get("cl_max")
    if candidate is None:
        table = ctx.get("polar_re_table") or []
        candidate = table[0].get("cl_max") if table else None
    if candidate is None:
        candidate = ctx.get("cl_max")
    return _safe_float(candidate)


def _safe_float(value: Any) -> float | None:
    """Return a float from *value*, or None if absent/non-numeric/non-positive."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/aeroplanes/{aeroplane_id}/speed-polar",
    operation_id="get_speed_polar",
    tags=["speed-polar"],
    summary="Aircraft speed polar (sink vs V, closed-form parabolic polar)",
    response_model=SpeedPolarResponse,
    responses={
        404: {"description": "Aeroplane not found"},
        422: {
            "description": "Missing inputs in assumption_computation_context",
            "model": SpeedPolarMissingResponse,
        },
    },
)
async def get_speed_polar(
    aeroplane_id: Annotated[UUID4, Path(..., description="Aeroplane UUID")],
    db: Annotated[Session, Depends(get_db)],
) -> SpeedPolarResponse:
    """Return the closed-form aircraft speed polar from polar parameters.

    Reads **mass_kg**, **s_ref_m2**, **aspect_ratio**, **e_oswald**, and **cd0**
    from the aeroplane's ``assumption_computation_context`` (written by the
    assumption-compute job). Returns HTTP 422 with a ``missing_inputs`` list
    when any of these fields is absent or non-positive.

    Formula references (ISA sea-level, parabolic drag polar):
    - V(CL) = sqrt(2W / (ρ·S·CL))
    - CD = CD0 + CL² / (π·AR·e)
    - sink = V · CD / CL
    - Best-glide: CL_bg = sqrt(CD0 / k)
    - Min-sink:   CL_ms = sqrt(3·CD0 / k) = √3 · CL_bg
    """
    plane = _get_aeroplane(db, aeroplane_id)
    polar_inputs = _extract_polar_inputs(plane)

    result: SpeedPolarResult | _MissingInputs = compute_speed_polar(**polar_inputs)

    if is_missing(result):
        missing_result = cast(_MissingInputs, result)
        logger.info(
            "Speed polar: missing inputs %s for aeroplane %s",
            missing_result.missing,
            aeroplane_id,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": "Insufficient aircraft parameters for speed polar. "
                "Run assumption recompute first.",
                "missing_inputs": missing_result.missing,
            },
        )

    polar = cast(SpeedPolarResult, result)
    return SpeedPolarResponse(
        v_mps=polar.v_mps,
        sink_mps=polar.sink_mps,
        cl=polar.cl,
        best_glide=SpeedPolarPoint(
            v_mps=polar.best_glide.v_mps,
            sink_mps=polar.best_glide.sink_mps,
            cl=polar.best_glide.cl,
        ),
        min_sink=SpeedPolarPoint(
            v_mps=polar.min_sink.v_mps,
            sink_mps=polar.min_sink.sink_mps,
            cl=polar.min_sink.cl,
        ),
        inputs=polar.inputs,
    )
