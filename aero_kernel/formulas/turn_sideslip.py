"""Canon formula ``turn-sideslip``: Drela's beta_turn of an aircraft without ailerons (ARCHITECTURE ch. 8.5)."""

import math

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import number
from aero_kernel.registry import CheckResult, formula, precondition

__all__ = ["dihedral_effect_stabilising", "turn_sideslip"]

# r_hat_max = rho g b C_L / (8 W/S): the worst steady level turn, phi = 45 deg. With the lift balance
# L cos(phi) = W at a fixed C_L, r_hat = rho g b C_L sin(2 phi) / (8 W/S), largest at sin(2 phi) = 1
# (derived in the canon entry, step 3: coordinated-turn kinematics, not printed by Drela).
_WORST_TURN_DIVISOR = 8.0


@precondition("turn-sideslip", "dihedral_effect_stabilising")
def dihedral_effect_stabilising(x: Inputs) -> CheckResult:
    """``C_l,beta`` must be negative: only then does a roll-stable sideslip balance exist.

    With ``C_l,beta`` zero the gain divides by zero; positive, ``kappa`` changes sign and means
    nothing for the turn. A value that is not a number does not hold either.
    """
    value = number(x, "c_l_beta")
    if math.isnan(value):
        return CheckResult(state="violated", message="C_l,beta is not a number")
    if value < 0.0:
        return CheckResult(state="held", message=f"C_l,beta = {value} is negative")
    return CheckResult(
        state="violated",
        message=f"C_l,beta = {value} is not negative: no roll-stable sideslip balance exists",
    )


@formula("turn-sideslip")
async def turn_sideslip(x: Inputs, ctx: Context) -> dict[str, float]:
    """The sideslip that cancels the rolling moment of the worst steady level turn.

    ``r_hat_max = rho g b C_L,mp / (8 W/S)`` (the turn at 45 degrees of bank), ``kappa = -C_l,r /
    C_l,beta`` from the AVL derivatives at ``V_mp`` (the canon quantities of
    ``lateral-static-stability-mp``, none recomputed: ADR 0022) and ``beta = kappa r_hat_max`` in
    radians, reported in degrees. Under worlds it runs once per assignment of ``neutral-point``,
    because the derivatives are about the design CG (A11). A number, no band (A10): Drela's 5 to 15
    degrees belongs to the evaluation.

    Args:
        x: ``rho`` in kg/m^3, ``g`` in m/s^2, ``b_ref`` in m, ``w_s`` the wing loading in N/m^2,
            ``c_l_mp`` the lift coefficient at minimum sink, ``c_l_beta`` and ``c_l_r`` the AVL
            derivatives per rad.
        ctx: The formula context (unused: no solver, no caveat of its own).

    Returns:
        ``beta_turn`` in degrees and ``kappa`` (dimensionless).
    """
    r_hat_max = (
        number(x, "rho")
        * number(x, "g")
        * number(x, "b_ref")
        * number(x, "c_l_mp")
        / (_WORST_TURN_DIVISOR * number(x, "w_s"))
    )
    kappa = -number(x, "c_l_r") / number(x, "c_l_beta")
    return {"beta_turn": math.degrees(kappa * r_hat_max), "kappa": kappa}
