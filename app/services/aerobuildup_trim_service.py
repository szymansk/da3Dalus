"""AeroBuildup trim — find a single control deflection via scipy Brent root-finding."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import UUID4

from app.schemas.aeroanalysisschema import (
    AeroBuildupTrimRequest,
    AeroBuildupTrimResult,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Aerosandbox uses underscore notation (CL_a = dCL/dalpha);
# legacy AVL-style keys (Clb, Cnr) may also appear in output.
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
    asb_airplane,
    op_point,
    xyz_ref: list[float],
    trim_variable: str,
    deflection_deg: float,
) -> dict:
    """Run a single AeroBuildup analysis at a specific control deflection."""
    import aerosandbox as asb

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
    """Find the control deflection that achieves a target aero coefficient via Brent's method."""
    import aerosandbox as asb
    from scipy.optimize import brentq

    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.core.exceptions import InternalError, ValidationDomainError
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

    # Fail fast before expensive solver iterations if the surface doesn't exist
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

    try:
        f_lower = residual(lower)
        f_upper = residual(upper)
    except ValidationDomainError:
        raise
    except (ValueError, TypeError) as e:
        raise ValidationDomainError(
            message=f"AeroBuildup evaluation failed at bounds: {e}"
        ) from e
    except Exception as e:
        logger.error(
            "Unexpected AeroBuildup failure for aeroplane %s at bounds [%g, %g]: %s",
            aeroplane_uuid,
            lower,
            upper,
            e,
            exc_info=True,
        )
        raise InternalError(
            message=f"AeroBuildup evaluation failed unexpectedly: {e}"
        ) from e

    if f_lower * f_upper > 0:
        logger.warning(
            "AeroBuildup trim root not bracketed for aeroplane %s: "
            "residual(%s=%g)=%g, residual(%s=%g)=%g — target %s=%g not achievable "
            "within [%g, %g]",
            aeroplane_uuid,
            request.trim_variable,
            lower,
            f_lower,
            request.trim_variable,
            upper,
            f_upper,
            target_coeff,
            target_val,
            lower,
            upper,
        )
        return AeroBuildupTrimResult(
            converged=False,
            trim_variable=request.trim_variable,
            trimmed_deflection=0.0,
            target_coefficient=target_coeff,
            achieved_value=None,
            aero_coefficients={},
            stability_derivatives={},
        )

    try:
        trimmed_deflection = brentq(residual, lower, upper, xtol=1e-6, maxiter=50)
    except ValueError as e:
        logger.warning(
            "AeroBuildup brentq failed for aeroplane %s, %s targeting %s=%g: %s",
            aeroplane_uuid,
            request.trim_variable,
            target_coeff,
            target_val,
            e,
        )
        return AeroBuildupTrimResult(
            converged=False,
            trim_variable=request.trim_variable,
            trimmed_deflection=0.0,
            target_coefficient=target_coeff,
            achieved_value=None,
            aero_coefficients={},
            stability_derivatives={},
        )

    # Re-run at converged deflection for full coefficient and derivative set
    try:
        final_result = _run_single_aerobuildup(
            asb_airplane,
            op_point,
            op.xyz_ref,
            request.trim_variable,
            trimmed_deflection,
        )
    except Exception as e:
        logger.error(
            "Final AeroBuildup evaluation failed at trimmed deflection %g for "
            "aeroplane %s: %s",
            trimmed_deflection,
            aeroplane_uuid,
            e,
            exc_info=True,
        )
        return AeroBuildupTrimResult(
            converged=True,
            trim_variable=request.trim_variable,
            trimmed_deflection=round(trimmed_deflection, 6),
            target_coefficient=target_coeff,
            achieved_value=None,
            aero_coefficients={},
            stability_derivatives={},
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
    if target_coeff not in final_result:
        logger.warning(
            "Target coefficient '%s' missing from final AeroBuildup result for aeroplane %s",
            target_coeff,
            aeroplane_uuid,
        )

    return AeroBuildupTrimResult(
        converged=True,
        trim_variable=request.trim_variable,
        trimmed_deflection=round(trimmed_deflection, 6),
        target_coefficient=target_coeff,
        achieved_value=round(achieved, 8),
        aero_coefficients=aero,
        stability_derivatives=derivs,
    )
