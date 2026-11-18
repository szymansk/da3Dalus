"""Canon formula ``butterfly-approach``: how far crow may be mixed in on the approach (ch. 8.5, 8.12).

The stall problem of ``stall-speed`` with the airplane in crow configuration, swept over the mix
``s`` from the landing configuration (``s = 0``) to full crow (``s = 1``): ``V_S0(s)``. The approach
speed keeps the reserve of the landing configuration, ``V_app(s) = V_app V_S0(s) / V_S0(0)``; the
glide angle is read at that speed in the configuration; ``s_max`` is where ``V_S0`` reaches the
approach speed flown without crow.

The sweep is not an embed: the formula varies the configuration itself (ARCHITECTURE ch. 8.5). It
states the stall guard as its own postcondition, with the check function ``stall-speed`` uses.
"""

import asyncio
from collections.abc import Mapping

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.devices import crow_configuration
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.flap_validity import warn_flap_validity
from aero_kernel.formulas.stall_speed import first_extremum_check
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import CheckResult, formula, postcondition
from aero_kernel.schema import Curve, KernelWarning, StallCurve
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import Stall

__all__ = ["butterfly_approach", "optimum_at_first_cl_peak"]

# The stall problem is the level one: L = m g (the definition of the load factor n = L / W = 1, as
# stated in ``stall-speed``'s applications); the glide reads the same lift.
LEVEL_LOAD_FACTOR = 1.0


def _invalid(message: str, hint: str, parameter: str) -> FormulaError:
    return FormulaError(
        ErrorCategory.INVALID_INPUT, "non_positive_value", message, hint, parameter=parameter
    )


def _require_admissible(x: Inputs) -> tuple[float, float, float, float]:
    """The crow angles and the approach speed, refused if they cannot describe a crow approach.

    ``delta_a_crow`` is the angle the ailerons are raised: zero or positive, the sign convention of
    the geometry (trailing edge down positive) is applied by the configuration.

    Raises:
        FormulaError: ``invalid_input`` for a negative aileron angle or an approach speed that is
            not above 0.
    """
    v_app, flap_ldg = number(x, "v_app"), number(x, "delta_f_ldg")
    flap_crow, aileron_up = number(x, "delta_f_crow"), number(x, "delta_a_crow")
    if not v_app > 0.0:
        raise _invalid(f"v_app = {v_app} is not above 0", "give the approach speed in m/s", "v_app")
    if aileron_up < 0.0:
        raise FormulaError(
            ErrorCategory.INVALID_INPUT,
            "value_above_maximum",
            f"delta_a_crow = {aileron_up} deg is negative: it is the angle the ailerons are raised",
            "give the aileron angle of full crow as a positive number of degrees up",
            parameter="delta_a_crow",
        )
    return v_app, flap_ldg, flap_crow, aileron_up


def _forward_once(
    ctx: Context, seen: set[tuple[str, str]], warnings: tuple[KernelWarning, ...]
) -> None:
    """Report an adapter caveat once; a regime caveat repeats at every mix."""
    for warning in warnings:
        key = (warning.code, warning.message)
        if key not in seen:
            seen.add(key)
            forward_warnings(ctx, (warning,))


def _crossing(mixes: list[float], speeds: list[float], v_app: float) -> float | None:
    """The mix where the stall speed first reaches ``v_app``, interpolated linearly, or ``None``."""
    for k, speed in enumerate(speeds):
        if speed < v_app:
            continue
        if k == 0:
            return mixes[0]
        share = (v_app - speeds[k - 1]) / (speed - speeds[k - 1])
        return mixes[k - 1] + share * (mixes[k] - mixes[k - 1])
    return None


async def _stalls(
    ctx: Context,
    configurations: list[AirplaneGeometry],
    x: Inputs,
    air: AirState,
) -> list[Stall]:
    mass, gravity = number(x, "m"), number(x, "g")
    return list(
        await asyncio.gather(
            *(
                ctx.solvers.opti.stall(
                    airplane,
                    mass,
                    gravity,
                    LEVEL_LOAD_FACTOR,
                    air,
                )
                for airplane in configurations
            )
        )
    )


@formula("butterfly-approach")
async def butterfly_approach(x: Inputs, ctx: Context) -> dict[str, float | Curve]:
    """The stall speed, the approach speed and the glide angle over the crow mix, and ``s_max``.

    Args:
        x: ``airplane`` the landing configuration, ``m`` the mass in kg, ``g`` the gravity in m/s^2,
            the ISA air state ``rho`` in kg/m^3, ``mu`` in Pa s and ``a`` in m/s, ``v_app`` the
            approach speed in m/s, ``delta_f_ldg`` the landing flap angle, ``delta_f_crow`` the
            flap angle of full crow and ``delta_a_crow`` the aileron angle (up) of full crow, all
            in degrees.
        ctx: The formula context; ``ctx.solvers.opti`` solves the stall problems and reads the glide.

    Returns:
        ``v_s0_curve`` in m/s, ``v_app_curve`` in m/s and ``gamma_curve`` in degrees over the mix,
        and ``s_max`` the largest mix at the approach speed flown without crow.

    Raises:
        TypeError: If ``airplane`` is not the geometry or a number is not a number.
        FormulaError: ``invalid_input`` for a negative crow aileron angle or an approach speed not
            above 0; from the adapter, unchanged (``tool_unavailable``, ``not_converged``);
            ``unsupported_configuration`` (the message says "fully mixable") if the stall speed does not reach the
            approach speed up to full crow: there is no largest mix, the values are in ``detail``.
    """
    v_app, flap_ldg, flap_crow, aileron_up = _require_admissible(x)
    airplane, air = airplane_of(x), air_state(x)
    steps = round(config().butterfly_mix_steps.value)
    mixes = [k / steps for k in range(steps + 1)]
    configurations = [
        crow_configuration(airplane, s, flap_ldg, flap_crow, aileron_up) for s in mixes
    ]
    stalls = await _stalls(ctx, configurations, x, air)
    seen: set[tuple[str, str]] = set()
    for stall in stalls:
        _forward_once(ctx, seen, stall.warnings)
    warn_flap_validity(ctx, configurations[-1], stalls[-1].solution.diagnostics)
    speeds = [stall.solution.v_s for stall in stalls]
    approach = [v_app * v_s / speeds[0] for v_s in speeds]
    glides = await asyncio.gather(
        *(
            ctx.solvers.opti.glide_point(
                configuration,
                number(x, "m"),
                number(x, "g"),
                air,
                speed,
            )
            for configuration, speed in zip(configurations, approach, strict=True)
        )
    )
    for glide in glides:
        _forward_once(ctx, seen, glide.warnings)
    s_max = _crossing(mixes, speeds, v_app)
    if s_max is None:
        raise FormulaError(
            ErrorCategory.UNSUPPORTED_CONFIGURATION,
            "unsupported_configuration",
            f"the stall speed stays below the approach speed {v_app:.4g} m/s up to full crow "
            f"(V_S0(1) = {speeds[-1]:.4g} m/s): there is no largest mix, the airplane is fully mixable",
            "this is a result, not a failure: read V_S0(s), V_app(s) and the glide angle from the "
            "detail",
            detail={
                "mix": [*mixes],
                "v_s0_m_s": [*speeds],
                "v_app_m_s": [*approach],
                "glide_angle_deg": [g.solution.glide_angle_deg for g in glides],
                "v_app_without_crow_m_s": v_app,
            },
        )
    stall_curve = StallCurve(
        x=tuple(mixes),
        y=tuple(speeds),
        alpha_s=tuple(s.solution.alpha_s for s in stalls),
        cl_max=tuple(s.solution.cl_max for s in stalls),
        polars=tuple(s.solution.polar for s in stalls),
    )
    return {
        "v_s0_curve": stall_curve,
        "v_app_curve": Curve(x=tuple(mixes), y=tuple(approach)),
        "gamma_curve": Curve(x=tuple(mixes), y=tuple(g.solution.glide_angle_deg for g in glides)),
        "s_max": s_max,
    }


@postcondition("butterfly-approach", "optimum_at_first_cl_peak")
def optimum_at_first_cl_peak(x: Mapping[str, object], y: Mapping[str, object]) -> CheckResult:
    """At every mix the stall optimum is the first sampled C_L peak (K32, the check of ``stall-speed``)."""
    curve = y["v_s0_curve"]
    if not isinstance(curve, StallCurve):
        return CheckResult(
            state="unchecked", message="the first C_L peak is read off the sweeps of the curve"
        )
    for s, alpha_s, cl_max, polar in zip(
        curve.x, curve.alpha_s, curve.cl_max, curve.polars, strict=True
    ):
        result = first_extremum_check(polar, alpha_s, cl_max, upright=True)
        if result.state != "held":
            return CheckResult(
                state=result.state,
                message=f"at the mix s = {s:g}: {result.message}",
                detail={"mix": s},
            )
    return CheckResult(state="held", message="the optimum is the first C_L peak at every mix")
