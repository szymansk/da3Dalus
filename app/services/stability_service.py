"""Stability Summary Service — extract static stability data from an analysis result."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.exceptions import InternalError
from app.schemas.aeroanalysisschema import OperatingPointSchema
from app.schemas.AeroplaneRequest import AnalysisToolUrlType
from app.schemas.stability import StabilitySummaryResponse
from app.services.analysis_service import get_aeroplane_schema_or_raise

logger = logging.getLogger(__name__)


def _scalar(val) -> Optional[float]:
    """Extract a scalar float from a value that may be a list or None."""
    if val is None:
        return None
    if isinstance(val, list):
        return float(val[0]) if len(val) > 0 else None
    return float(val)


async def get_stability_summary(
    db: Session,
    aeroplane_uuid,
    operating_point: OperatingPointSchema,
    analysis_tool: AnalysisToolUrlType,
) -> StabilitySummaryResponse:
    """Run an analysis and extract stability summary from the result."""
    # Lazy imports to avoid module-level import errors on platforms
    # where aerosandbox is not available.
    from app.converters.model_schema_converters import aeroplaneSchemaToAsbAirplane_async
    from app.api.utils import analyse_aerodynamics

    plane_schema = await get_aeroplane_schema_or_raise(db, aeroplane_uuid)

    try:
        asb_airplane = await aeroplaneSchemaToAsbAirplane_async(plane_schema=plane_schema)
        result, _ = await analyse_aerodynamics(
            analysis_tool, operating_point, asb_airplane
        )
    except Exception as e:
        logger.error("Error computing stability: %s", e)
        raise InternalError(message=f"Stability analysis error: {e}")

    # Extract data from AnalysisModel
    xnp = _scalar(result.reference.Xnp)
    xcg = float(operating_point.xyz_ref[0]) if operating_point.xyz_ref else None

    # Derivatives
    cma = _scalar(result.derivatives.Cma)
    cnb = _scalar(result.derivatives.Cnb)
    clb = _scalar(result.derivatives.Clb)

    # Static margin: (Xnp - Xcg) / MAC
    static_margin = None
    if xnp is not None and xcg is not None:
        mac = _scalar(result.reference.Cref)
        if mac and mac > 0:
            static_margin = (xnp - xcg) / mac

    # Flight condition
    alpha = _scalar(result.flight_condition.alpha)

    # Trim elevator (from control surface deflections if available)
    trim_elevator = None
    if hasattr(result.control_surfaces, "deflections") and result.control_surfaces.deflections:
        for name, defl in result.control_surfaces.deflections.items():
            if "elevator" in name.lower():
                trim_elevator = _scalar(defl)
                break

    return StabilitySummaryResponse(
        static_margin=static_margin,
        neutral_point_x=xnp,
        cg_x=xcg,
        trim_alpha_deg=alpha,
        trim_elevator_deg=trim_elevator,
        Cma=cma,
        Cnb=cnb,
        Clb=clb,
        is_statically_stable=(cma is not None and cma < 0),
        is_directionally_stable=(cnb is not None and cnb > 0),
        is_laterally_stable=(clb is not None and clb < 0),
        analysis_method=result.method,
    )
