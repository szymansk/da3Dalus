"""Canon formula ``static-margin-probe``: SM = -C_m,alpha / C_L,alpha from AeroBuildup at V_md (ch. 8.5)."""

from aero_kernel.context import Context, Inputs
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.registry import formula

__all__ = ["static_margin_probe"]

# The rule of the agreement tolerance (``rules.yaml``).
AGREEMENT_RULE = "static-margin-probe-agreement"


@formula("static-margin-probe")
async def static_margin_probe(x: Inputs, ctx: Context) -> dict[str, float]:
    """The static margin from the moment slope, a test of the design CG and not a second truth (A7).

    AeroBuildup runs at the minimum-drag speed and the angle of attack of ``L = m g``, with the moment
    reference at the design CG; ``SM_probe = -C_m,alpha / C_L,alpha`` (Sadraey Eq. 11.17, 11.18). The
    probe is compared with the target: a deviation beyond the rule's ``agreement_tolerance`` is
    declared, never averaged, and the value stays. AeroBuildup has no wing-tail downwash and so biases
    the probe toward a larger margin; that is declared on every value. Under worlds it runs once per
    assignment of ``neutral-point``, because the design CG is one (A11).

    Args:
        x: ``airplane``, ``m`` in kg, ``g`` in m/s^2, the ISA state ``rho`` in kg/m^3, ``mu`` in Pa s
            and ``a`` in m/s, ``v_md`` in m/s, ``x_cg`` the design CG in m and ``sm_target`` the
            target static margin (dimensionless).
        ctx: The formula context; ``ctx.solvers.opti`` is the OPT adapter, ``ctx.solvers.rules`` the rules.

    Returns:
        ``c_m_alpha`` in 1/rad and ``sm_probe`` (dimensionless).

    Raises:
        FormulaError: From the adapter, unchanged.
    """
    found = await ctx.solvers.opti.moment_slope(
        airplane_of(x),
        number(x, "m"),
        number(x, "g"),
        air_state(x),
        number(x, "v_md"),
        number(x, "x_cg"),
    )
    forward_warnings(ctx, found.warnings)
    slopes = found.solution
    margin = -slopes.cm_alpha / slopes.cl_alpha
    ctx.warn(
        "aerobuildup_no_downwash",
        "AeroBuildup has no wing-tail downwash, so the static margin from the moment slope is "
        "biased toward a larger margin than the neutral point worlds give (Sharpe 2024, 5.3, 5.4).",
        {"alpha_deg": slopes.alpha_deg, "cl": slopes.cl},
    )
    tolerance = ctx.solvers.rules.value(AGREEMENT_RULE, "agreement_tolerance")
    target = number(x, "sm_target")
    if abs(margin - target) > tolerance:
        ctx.warn(
            "static_margin_probe_disagrees",
            f"The static margin from the moment slope, {margin:.4f}, differs from the target "
            f"{target:.4f} by more than {tolerance:g} of the mean aerodynamic chord. Both are "
            "reported; they are not averaged.",
            {
                "sm_probe": margin,
                "sm_target": target,
                "deviation": margin - target,
                "agreement_tolerance": tolerance,
            },
        )
    return {"c_m_alpha": slopes.cm_alpha, "sm_probe": margin}
