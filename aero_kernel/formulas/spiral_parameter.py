"""Canon formula ``spiral-parameter``: Drela's B = l_V,CG Gamma_eq / (b_ref C_L) at V_md and V_mp (ch. 8.5)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.dihedral import main_wing_dihedral_deg
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.values import airplane_of, number
from aero_kernel.registry import formula

__all__ = ["spiral_parameter"]


def _spiral(arm: float, dihedral_deg: float, span: float, cl: float, speed: str) -> float:
    """``B = l_V,CG Gamma_eq / (b_ref C_L)`` with ``Gamma_eq`` in degrees, as Drela defines it.

    Raises:
        FormulaError: ``invalid_input`` for a lift coefficient that is not positive.
    """
    if not cl > 0.0:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "invalid_input",
            f"the lift coefficient at {speed} is {cl}: B is defined for a positive lift coefficient",
            "give a positive mass, gravity, density, speed and reference area",
            parameter="m",
        )
    return arm * dihedral_deg / (span * cl)


@formula("spiral-parameter")
async def spiral_parameter(x: Inputs, ctx: Context) -> dict[str, float]:
    """Drela's spiral parameter at the minimum-drag and the minimum-sink speed.

    ``Gamma_eq`` is the strip-theory equivalent dihedral of the main wing in degrees
    (:func:`aero_kernel.dihedral.main_wing_dihedral_deg`); ``C_L(V) = m g / (1/2 rho V^2 S_ref)``.
    ``S_ref``, ``b_ref`` and the arm are the quantities of ``airplane-geometry`` and
    ``vertical-tail-arm`` (ADR 0022); under worlds it runs once per assignment of ``neutral-point``
    (A11). Numbers, no verdicts (A10): which value governs is the evaluation's.

    Args:
        x: ``airplane``, ``s_ref`` in m^2, ``b_ref`` in m, ``l_v_cg`` in m, ``m`` in kg, ``g`` in
            m/s^2, ``rho`` in kg/m^3, ``v_md`` and ``v_mp`` in m/s.
        ctx: The formula context (unused: no solver, no caveat of its own).

    Returns:
        ``b_spiral_md`` and ``b_spiral_mp`` (dimensionless).

    Raises:
        FormulaError: ``unsupported_layout`` for an unmirrored main wing; ``invalid_input`` for a
            lift coefficient that is not positive.
    """
    gamma = main_wing_dihedral_deg(airplane_of(x))
    weight = number(x, "m") * number(x, "g")
    pressure_area = 0.5 * number(x, "rho") * number(x, "s_ref")
    arm, span = number(x, "l_v_cg"), number(x, "b_ref")
    return {
        "b_spiral_md": _spiral(
            arm, gamma, span, weight / (pressure_area * number(x, "v_md") ** 2), "V_md"
        ),
        "b_spiral_mp": _spiral(
            arm, gamma, span, weight / (pressure_area * number(x, "v_mp") ** 2), "V_mp"
        ),
    }
