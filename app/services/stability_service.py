"""Stability Summary Service — extract static stability data from an analysis result."""

import logging
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.AeroplaneRequest import AnalysisToolUrlType
from app.schemas.stability import StabilitySummaryResponse
from app.services.analysis_service import get_aeroplane_schema_or_raise

logger = logging.getLogger(__name__)


def _scalar(val) -> Optional[float]:
    """Extract a scalar float from a value that may be a list, numpy array, or None."""
    if val is None:
        return None
    if isinstance(val, np.ndarray):
        if val.ndim == 0:
            return float(val)
        if val.size > 1:
            logger.warning("_scalar received %s with %d elements; using first", type(val).__name__, val.size)
        return float(val[0]) if val.size > 0 else None
    if isinstance(val, list):
        if len(val) > 1:
            logger.warning("_scalar received %s with %d elements; using first", type(val).__name__, len(val))
        return float(val[0]) if len(val) > 0 else None
    return float(val)


def _compute_static_margin(xnp: Optional[float], xcg: Optional[float], cref_val) -> Optional[float]:
    """Compute static margin: (Xnp - Xcg) / MAC."""
    if xnp is None or xcg is None:
        return None
    mac = _scalar(cref_val)
    if not mac or mac <= 0:
        return None
    return (xnp - xcg) / mac


def _find_trim_elevator(control_surfaces) -> Optional[float]:
    """Extract trim elevator deflection from control surface data."""
    if not hasattr(control_surfaces, "deflections") or not control_surfaces.deflections:
        return None
    for name, defl in control_surfaces.deflections.items():
        if "elevator" in name.lower():
            return _scalar(defl)
    return None


async def get_stability_summary(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType,
) -> StabilitySummaryResponse:
    """Run an analysis and extract stability summary from the result."""
    # Lazy imports to avoid module-level import errors on platforms
    # where aerosandbox is not available.
    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.api.utils import analyse_aerodynamics

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
        result, _ = analyse_aerodynamics(analysis_tool, operating_point, asb_airplane)
    except Exception as e:
        logger.error("Error computing stability: %s", e)
        raise InternalError(message=f"Stability analysis error: {e}")

    xnp = _scalar(result.reference.Xnp)
    xcg = float(operating_point.xyz_ref[0]) if operating_point.xyz_ref else None
    cma = _scalar(result.derivatives.Cma)
    cnb = _scalar(result.derivatives.Cnb)
    clb = _scalar(result.derivatives.Clb)

    return StabilitySummaryResponse(
        static_margin=_compute_static_margin(xnp, xcg, result.reference.Cref),
        neutral_point_x=xnp,
        cg_x=xcg,
        trim_alpha_deg=_scalar(result.flight_condition.alpha),
        trim_elevator_deg=_find_trim_elevator(result.control_surfaces),
        Cma=cma,
        Cnb=cnb,
        Clb=clb,
        is_statically_stable=(cma is not None and cma < 0),
        is_directionally_stable=(cnb is not None and cnb > 0),
        is_laterally_stable=(clb is not None and clb < 0),
        analysis_method=result.method,
    )
