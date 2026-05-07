"""AVL trim analysis service — trims operating points using AVL indirect constraints."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import UUID4

from app.schemas.aeroanalysisschema import (
    AVLTrimRequest,
    AVLTrimResult,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Coefficient keys to extract from AVL results
_AERO_COEFF_KEYS = {"CL", "CD", "CY", "Cm", "Cl", "Cn", "CDind", "CDff", "e", "CLff", "CYff"}
_FORCE_MOMENT_KEYS = {"L", "D", "Y", "l_b", "m_b", "n_b"}
_STATE_KEYS = {"alpha", "beta", "mach"}
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


def _categorize_results(raw: dict, control_names: set[str]) -> AVLTrimResult:
    """Split raw AVL output into categorized trim result."""
    aero = {k: v for k, v in raw.items() if k in _AERO_COEFF_KEYS}
    forces = {k: v for k, v in raw.items() if k in _FORCE_MOMENT_KEYS}
    state = {k: v for k, v in raw.items() if k in _STATE_KEYS}
    derivs = {k: v for k, v in raw.items() if k in _STABILITY_DERIV_KEYS}
    deflections = {k: v for k, v in raw.items() if k in control_names}

    converged = "CL" in raw  # If AVL produced coefficients, it converged

    return AVLTrimResult(
        converged=converged,
        trimmed_deflections=deflections,
        trimmed_state=state,
        aero_coefficients=aero,
        forces_and_moments=forces,
        stability_derivatives=derivs,
        raw_results={k: v for k, v in raw.items() if isinstance(v, (int, float))},
    )


async def trim_with_avl(
    db: Session,
    aeroplane_uuid: UUID4,
    request: AVLTrimRequest,
) -> AVLTrimResult:
    """Run AVL trim analysis for an aeroplane at a given operating point.

    Uses AVL's native indirect constraints to find control deflections
    (or alpha/beta) that achieve the specified trim targets.
    """
    import aerosandbox as asb

    from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
    from app.core.exceptions import InternalError, ValidationDomainError
    from app.schemas.aeroanalysisschema import CdclConfig, SpacingConfig
    from app.services.analysis_service import get_aeroplane_schema_or_raise
    from app.services.avl_geometry_service import (
        build_avl_geometry_file,
        get_user_avl_content,
        inject_cdcl,
    )
    from app.services.avl_runner import AVLRunner
    from app.services.avl_strip_forces import get_control_surface_index_map

    # Let ServiceException subclasses (NotFoundError, etc.) propagate naturally
    plane_schema = get_aeroplane_schema_or_raise(db, aeroplane_uuid)
    op = request.operating_point

    user_avl_content = get_user_avl_content(db, aeroplane_uuid)
    if user_avl_content is None:
        cdcl_config = op.cdcl_config or CdclConfig()
        spacing_config = op.spacing_config or SpacingConfig()
        avl_file = build_avl_geometry_file(plane_schema, spacing_config)
        inject_cdcl(avl_file, plane_schema, op, cdcl_config)
        user_avl_content = repr(avl_file)

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

    runner = AVLRunner(
        airplane=asb_airplane,
        op_point=op_point,
        xyz_ref=op.xyz_ref,
        timeout=60,
    )

    try:
        result = runner.run_trim(
            avl_file_content=user_avl_content,
            trim_constraints=request.trim_constraints,
            control_overrides=op.control_deflections,
        )
    except ValueError as e:
        raise ValidationDomainError(message=str(e)) from e
    except (FileNotFoundError, RuntimeError) as e:
        logger.error(
            "AVL trim execution failed for aeroplane %s with constraints %s: %s",
            aeroplane_uuid,
            [f"{tc.variable}->{tc.target.value}={tc.value}" for tc in request.trim_constraints],
            e,
        )
        raise InternalError(message=f"AVL trim failed: {e}") from e

    cs_map = get_control_surface_index_map(asb_airplane)
    trimmed = _categorize_results(result, set(cs_map.keys()))
    if not trimmed.converged:
        logger.warning(
            "AVL trim did not converge for aeroplane %s: raw keys=%s",
            aeroplane_uuid,
            list(result.keys()),
        )
    return trimmed
