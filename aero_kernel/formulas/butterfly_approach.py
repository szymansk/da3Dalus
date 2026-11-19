"""Canon formula ``butterfly-approach``: how far crow may be mixed in on the approach (ch. 8.5, 8.12).

The stall problem of ``stall-speed`` with the airplane in crow configuration, swept over the mix
``s`` from the landing configuration (``s = 0``) to full crow (``s = 1``): ``V_S0(s)``. The approach
speed keeps the reserve of the landing configuration, ``V_app(s) = V_app V_S0(s) / V_S0(0)``; the
glide angle is read at that speed in the configuration; ``s_max`` is where ``V_S0`` reaches the
approach speed flown without crow.

The sweep is not an embed: the formula varies the configuration itself (ARCHITECTURE ch. 8.5). It
states the stall guard as its own postcondition, with the check function ``stall-speed`` uses.

**Caveats forwarded** (ADR 0020): the adapters report a caveat per solve, and over eleven mixes
that would repeat each regime message with another Reynolds number. The formula forwards (a) the
caveats of the two solves the answer rests on, the landing stall at ``s = 0`` (``V_app`` is a
multiple of it) and the sample that closes the bracket of ``s_max`` (full crow where there is no
crossing), with the glide read at the same mixes, and (b) one ``control_surface_fit_range_unknown``
that carries, per device, the largest deflection and the lowest NeuralFoil confidence over the
whole sweep. The regime and drag messages of the other mixes are dropped; the validity declaration
(``flap_deflection_beyond_validity``, ``flap_confidence_low``) is made on the mix with the largest
deflection.
"""

import asyncio
from collections.abc import Mapping, Sequence

from aero_kernel.config import config
from aero_kernel.context import Context, Inputs
from aero_kernel.devices import crow_configuration, flap_deflections
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.flap_validity import warn_flap_validity
from aero_kernel.formulas.stall_speed import first_extremum_check
from aero_kernel.formulas.values import air_state, airplane_of, forward_warnings, number
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.registry import CheckResult, formula, postcondition, precondition
from aero_kernel.schema import Curve, KernelWarning, StallCurve
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.opti import GlidePoint, Stall
from pydantic import JsonValue

__all__ = [
    "approach_speed_positive",
    "butterfly_approach",
    "crow_aileron_not_negative",
    "optimum_at_first_cl_peak",
]

FIT_RANGE = "control_surface_fit_range_unknown"
CHECK = "optimum_at_first_cl_peak"


@precondition("butterfly-approach", "approach_speed_positive")
def approach_speed_positive(x: Mapping[str, object]) -> CheckResult:
    """The approach speed must be above 0: the sweep scales it with the stall speeds."""
    v_app = number(x, "v_app")
    if v_app > 0.0:
        return CheckResult(state="held", message=f"the approach speed {v_app} m/s is above zero")
    return CheckResult(
        state="violated",
        message=f"the approach speed {v_app} m/s is not above zero; give it in m/s",
    )


@precondition("butterfly-approach", "crow_aileron_not_negative")
def crow_aileron_not_negative(x: Mapping[str, object]) -> CheckResult:
    """The crow aileron angle is the angle the ailerons are raised: zero or positive degrees."""
    angle = number(x, "delta_a_crow")
    if angle >= 0.0:
        return CheckResult(
            state="held", message=f"the crow aileron angle {angle} deg is not negative"
        )
    return CheckResult(
        state="violated",
        message=(
            f"the crow aileron angle {angle} deg is negative: it is the angle the ailerons are "
            "raised, give a positive number of degrees up"
        ),
    )


def _crossing(
    mixes: Sequence[float], speeds: Sequence[float], v_app: float
) -> tuple[float, int] | None:
    """The mix where the stall speed first reaches ``v_app`` and the index of the sample closing it.

    Linear between the two samples that bracket the crossing; ``(0, 0)`` where the landing stall
    already reaches ``v_app``; ``None`` where it never does.
    """
    for k, speed in enumerate(speeds):
        if speed < v_app:
            continue
        if k == 0:
            return mixes[0], 0
        share = (v_app - speeds[k - 1]) / (speed - speeds[k - 1])
        return mixes[k - 1] + share * (mixes[k] - mixes[k - 1]), k
    return None


def _largest_deflection(configuration: AirplaneGeometry) -> float:
    return max((abs(angle) for _, _, angle in flap_deflections(configuration)), default=0.0)


def _records(warning: KernelWarning, key: str) -> list[Mapping[str, JsonValue]]:
    found = warning.detail.get(key)
    if not isinstance(found, list):
        return []
    return [item for item in found if isinstance(item, dict)]


def _worst_fit_range(found: Sequence[KernelWarning]) -> KernelWarning | None:
    """One ``control_surface_fit_range_unknown`` with, per device, the worst case of the sweep."""
    fits = [w for w in found if w.code == FIT_RANGE]
    if not fits:
        return None
    angles: dict[tuple[str, str], float] = {}
    confidence: dict[tuple[str, str], float] = {}
    lowest: list[float] = []
    for warning in fits:
        for record in _records(warning, "flaps"):
            key = (str(record["wing"]), str(record["device"]))
            angle = record["deflection_deg"]
            if isinstance(angle, int | float) and abs(angle) >= abs(angles.get(key, 0.0)):
                angles[key] = float(angle)
        for record in _records(warning, "devices"):
            key = (str(record["wing"]), str(record["device"]))
            mean = record["mean_confidence"]
            if isinstance(mean, int | float):
                confidence[key] = min(float(mean), confidence.get(key, float(mean)))
        floor = warning.detail.get("min_confidence")
        if isinstance(floor, int | float):
            lowest.append(float(floor))
    detail: dict[str, JsonValue] = {
        "flaps": [{"wing": w, "device": d, "deflection_deg": a} for (w, d), a in angles.items()],
    }
    if confidence:
        detail["devices"] = [
            {"wing": w, "device": d, "mean_confidence": c} for (w, d), c in confidence.items()
        ]
    if lowest:
        detail["min_confidence"] = min(lowest)
    return KernelWarning.of(FIT_RANGE, fits[0].message, detail=detail)


def _forward_caveats(
    ctx: Context, stalls: Sequence[Stall], glides: Sequence[GlidePoint], closing: int
) -> None:
    """Forward the caveats of the reference solves once, and the worst fit range of the sweep."""
    seen: set[tuple[str, str]] = set()
    reference = [stalls[0], stalls[closing]]
    reference += [glides[k] for k in {0, closing} if k < len(glides)]
    for solve in reference:
        for warning in solve.warnings:
            key = (warning.code, warning.message)
            if warning.code != FIT_RANGE and key not in seen:
                seen.add(key)
                forward_warnings(ctx, (warning,))
    worst = _worst_fit_range([w for s in (*stalls, *glides) for w in s.warnings])
    if worst is not None:
        forward_warnings(ctx, (worst,))


async def _stalls(
    ctx: Context, configurations: Sequence[AirplaneGeometry], x: Inputs, air: AirState
) -> list[Stall]:
    mass, gravity, n_load = number(x, "m"), number(x, "g"), number(x, "n_load")
    return list(
        await asyncio.gather(
            *(
                ctx.solvers.opti.stall(airplane, mass, gravity, n_load, air)
                for airplane in configurations
            )
        )
    )


def _stall_curve(mixes: Sequence[float], stalls: Sequence[Stall]) -> StallCurve:
    return StallCurve(
        x=tuple(mixes),
        y=tuple(s.solution.v_s for s in stalls),
        alpha_s=tuple(s.solution.alpha_s for s in stalls),
        cl_max=tuple(s.solution.cl_max for s in stalls),
        polars=tuple(s.solution.polar for s in stalls),
    )


def _off_peak(curve: StallCurve) -> FormulaError | None:
    """The error naming the mix whose stall optimum is not the first C_L peak, if there is one."""
    result = optimum_at_first_cl_peak({}, {"v_s0_curve": curve})
    if result.state != "violated":
        return None
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "postcondition_violated",
        f"The postcondition `{CHECK}` of `butterfly-approach` is violated: {result.message}",
        "The value was discarded; the evaluation is not trustworthy.",
        detail={"postcondition": CHECK, **result.detail},
    )


async def _glides(
    ctx: Context,
    configurations: Sequence[AirplaneGeometry],
    speeds: Sequence[float],
    x: Inputs,
    air: AirState,
) -> list[GlidePoint]:
    mass, gravity = number(x, "m"), number(x, "g")
    return list(
        await asyncio.gather(
            *(
                ctx.solvers.opti.glide_point(configuration, mass, gravity, air, speed)
                for configuration, speed in zip(configurations, speeds, strict=True)
            )
        )
    )


def _fully_mixable(
    v_app: float,
    mixes: Sequence[float],
    speeds: Sequence[float],
    approach: Sequence[float],
    glides: Sequence[GlidePoint],
) -> FormulaError:
    return FormulaError(
        ErrorCategory.UNSUPPORTED_CONFIGURATION,
        "unsupported_configuration",
        f"the stall speed stays below the approach speed {v_app:.4g} m/s up to full crow "
        f"(V_S0(1) = {speeds[-1]:.4g} m/s): there is no largest mix, the airplane is fully mixable",
        "this is a result, not a failure: read V_S0(s), V_app(s) and the glide angle from the detail",
        detail={
            "mix": [*mixes],
            "v_s0_m_s": [*speeds],
            "v_app_m_s": [*approach],
            "glide_angle_deg": [g.solution.glide_angle_deg for g in glides],
            "v_app_without_crow_m_s": v_app,
        },
    )


@formula("butterfly-approach")
async def butterfly_approach(x: Inputs, ctx: Context) -> dict[str, float | Curve]:
    """The stall speed, the approach speed and the glide angle over the crow mix, and ``s_max``.

    Args:
        x: ``airplane`` the landing configuration, ``m`` the mass in kg, ``g`` the gravity in m/s^2,
            ``n_load`` the load factor of the stall problem (1, bound by the canon), the ISA air
            state ``rho`` in kg/m^3, ``mu`` in Pa s and ``a`` in m/s, ``v_app`` the approach speed in
            m/s, ``delta_f_ldg`` the landing flap angle, ``delta_f_crow`` the flap angle of full crow
            and ``delta_a_crow`` the aileron angle (up) of full crow, all in degrees; the
            preconditions hold ``v_app > 0`` and ``delta_a_crow >= 0``.
        ctx: The formula context; ``ctx.solvers.opti`` solves the stall problems and reads the glide.

    Returns:
        ``v_s0_curve`` in m/s, ``v_app_curve`` in m/s and ``gamma_curve`` in degrees over the mix,
        and ``s_max`` the largest mix at the approach speed flown without crow. Where the landing
        stall speed is already at or above the approach speed, ``s_max`` is 0 and ``gamma_curve``
        is empty: no glide exists below the stall speed, so none is read.

    Raises:
        TypeError: If ``airplane`` is not the geometry or a number is not a number.
        FormulaError: From the adapter, unchanged (``tool_unavailable``, ``not_converged``);
            ``unsupported_configuration`` (``postcondition_violated``) if one mix is not at its
            first C_L peak, the mix in ``detail``, also where there is no largest mix;
            ``unsupported_configuration`` (the message says "fully mixable") if the stall speed
            does not reach the approach speed up to full crow: there is no largest mix, the
            values are in ``detail``.
    """
    v_app, air, airplane = number(x, "v_app"), air_state(x), airplane_of(x)
    flap_ldg, flap_crow = number(x, "delta_f_ldg"), number(x, "delta_f_crow")
    aileron_up = number(x, "delta_a_crow")
    steps = round(config().butterfly_mix_steps.value)
    mixes = [k / steps for k in range(steps + 1)]
    configurations = [
        crow_configuration(airplane, s, flap_ldg, flap_crow, aileron_up) for s in mixes
    ]
    stalls = await _stalls(ctx, configurations, x, air)
    curve = _stall_curve(mixes, stalls)
    speeds = list(curve.y)
    approach = [v_app * v_s / speeds[0] for v_s in speeds]
    found = _crossing(mixes, speeds, v_app)
    worst = max(range(len(configurations)), key=lambda k: _largest_deflection(configurations[k]))
    warn_flap_validity(ctx, configurations[worst], stalls[worst].solution.diagnostics)
    if found is not None and found[1] == 0:
        _forward_caveats(ctx, stalls, [], 0)
        return {
            "v_s0_curve": curve,
            "v_app_curve": Curve(x=tuple(mixes), y=tuple(approach)),
            "gamma_curve": Curve(x=(), y=()),
            "s_max": mixes[0],
        }
    if found is None and (off_peak := _off_peak(curve)) is not None:
        raise off_peak
    glides = await _glides(ctx, configurations, approach, x, air)
    _forward_caveats(ctx, stalls, glides, len(mixes) - 1 if found is None else found[1])
    if found is None:
        raise _fully_mixable(v_app, mixes, speeds, approach, glides)
    return {
        "v_s0_curve": curve,
        "v_app_curve": Curve(x=tuple(mixes), y=tuple(approach)),
        "gamma_curve": Curve(x=tuple(mixes), y=tuple(g.solution.glide_angle_deg for g in glides)),
        "s_max": found[0],
    }


@postcondition("butterfly-approach", CHECK)
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
