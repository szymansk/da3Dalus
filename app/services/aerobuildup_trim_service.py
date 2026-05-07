"""AeroBuildup trim analysis — find control deflections via scipy root-finding."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import aerosandbox as asb
from pydantic import UUID4
from scipy.optimize import brentq

from app.schemas.aeroanalysisschema import (
    AeroBuildupTrimRequest,
    AeroBuildupTrimResult,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_AERO_COEFF_KEYS = {"CL", "CD", "CY", "Cm", "Cl", "Cn"}
_STABILITY_DERIV_KEYS = {
    "CL_a",
    "CL_b",
    "CY_a",
    "CY_b",
    "Cm_a",
    "Cn_b",
    "Cl_b",
    "Clb",
    "Cnr",
    "Clr",
    "Cnb",
}


def _run_single_aerobuildup(
    asb_airplane: asb.Airplane,
    op_point: asb.OperatingPoint,
    xyz_ref: list[float],
    trim_variable: str,
    deflection_deg: float,
) -> dict:
    """Run a single AeroBuildup analysis at a specific control deflection."""
    deflected = asb_airplane.with_control_deflections({trim_variable: deflection_deg})
    abu = asb.AeroBuildup(
        airplane=deflected,
        op_point=op_point,
        xyz_ref=xyz_ref,
    )
    return abu.run_with_stability_derivatives()


async def trim_with_aerobuildup(
    db: Session,
    aeroplane_uuid: UUID4,
    request: AeroBuildupTrimRequest,
) -> AeroBuildupTrimResult:
    """Run AeroBuildup trim: vary a control surface deflection to achieve target coefficient."""
    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.core.exceptions import ValidationDomainError
    from app.services.analysis_service import get_aeroplane_schema_or_raise

    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    op = request.operating_point

    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
    asb_airplane.xyz_ref = op.xyz_ref

    atmosphere = asb.Atmosphere(altitude=op.altitude)
    op_point = asb.OperatingPoint(
        velocity=op.velocity,
        alpha=op.alpha,
        beta=op.beta,
        p=op.p,
        q=op.q,
        r=op.r,
        atmosphere=atmosphere,
    )

    # Verify the trim variable (control surface) exists on the airplane
    control_names: set[str] = set()
    for wing in asb_airplane.wings:
        for xsec in wing.xsecs:
            for cs in xsec.control_surfaces:
                control_names.add(cs.name)
    if request.trim_variable not in control_names:
        raise ValidationDomainError(
            message=f"Control surface '{request.trim_variable}' not found on airplane. "
            f"Available: {sorted(control_names)}"
        )

    target_coeff = request.target_coefficient
    target_val = request.target_value

    def residual(deflection_deg: float) -> float:
        result = _run_single_aerobuildup(
            asb_airplane,
            op_point,
            op.xyz_ref,
            request.trim_variable,
            deflection_deg,
        )
        coeff_val = result.get(target_coeff)
        if coeff_val is None:
            raise ValidationDomainError(
                message=f"Coefficient '{target_coeff}' not found in AeroBuildup output. "
                f"Available: {sorted(k for k in result if isinstance(result[k], (int, float)))}"
            )
        return float(coeff_val) - target_val

    lower, upper = request.deflection_bounds

    # Check that the root is bracketed
    try:
        f_lower = residual(lower)
        f_upper = residual(upper)
    except ValidationDomainError:
        raise
    except Exception as e:
        raise ValidationDomainError(message=f"AeroBuildup evaluation failed at bounds: {e}") from e

    if f_lower * f_upper > 0:
        return AeroBuildupTrimResult(
            converged=False,
            trim_variable=request.trim_variable,
            trimmed_deflection=0.0,
            target_coefficient=target_coeff,
            achieved_value=float("nan"),
            aero_coefficients={},
            stability_derivatives={},
        )

    try:
        trimmed_deflection = brentq(residual, lower, upper, xtol=1e-6, maxiter=50)
    except ValueError:
        return AeroBuildupTrimResult(
            converged=False,
            trim_variable=request.trim_variable,
            trimmed_deflection=0.0,
            target_coefficient=target_coeff,
            achieved_value=float("nan"),
            aero_coefficients={},
            stability_derivatives={},
        )

    # Final run at trim to get full coefficients
    final_result = _run_single_aerobuildup(
        asb_airplane,
        op_point,
        op.xyz_ref,
        request.trim_variable,
        trimmed_deflection,
    )

    aero = {
        k: float(v)
        for k, v in final_result.items()
        if k in _AERO_COEFF_KEYS and isinstance(v, (int, float))
    }
    derivs = {
        k: float(v)
        for k, v in final_result.items()
        if k in _STABILITY_DERIV_KEYS and isinstance(v, (int, float))
    }
    achieved = float(final_result.get(target_coeff, float("nan")))

    return AeroBuildupTrimResult(
        converged=True,
        trim_variable=request.trim_variable,
        trimmed_deflection=round(trimmed_deflection, 6),
        target_coefficient=target_coeff,
        achieved_value=round(achieved, 8),
        aero_coefficients=aero,
        stability_derivatives=derivs,
    )
