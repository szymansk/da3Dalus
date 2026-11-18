"""parabolic-polar-fit (#1401): the least-squares fit, the window, the declarations, through the engine."""

import math
from collections.abc import Callable, Sequence
from itertools import pairwise

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.context import Value
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.parabolic_polar_fit import ParabolaFit, fit_parabola, parabolic_polar_fit
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import KernelWarning, QuantityStatus, WarningSeverity
from aero_kernel.solvers.opti import LevelPolar
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.formula_builders import (
    StubAtmosphere,
    close,
    context_with,
    inputs_from_model,
)
from aero_kernel.tests.stall_stubs import CD0, UPRIGHT_PEAK, K, StubOpti, parabolic_level_polar
from aero_kernel.tests.test_roll_rate_engine import GRAVITY, MASS, RHO, plane, run

pytestmark = pytest.mark.asyncio

MODEL = shipped_build().model
CL_MAX = UPRIGHT_PEAK[1]
POINTS = 48  # the canon rule's fit_points
AIR = {
    "air-density": RHO,
    "dynamic-viscosity": 1.7894e-5,
    "speed-of-sound": 340.294,
}


def fit_inputs(cl_max: float = CL_MAX, ar: float = 8.0) -> dict[str, Value]:
    airplane: AirplaneGeometry = plane()
    return dict(
        inputs_from_model(
            MODEL,
            "parabolic-polar-fit",
            {
                "airplane": airplane,
                "aircraft-mass": MASS,
                "gravity": GRAVITY,
                "aspect-ratio": ar,
                "max-lift-coefficient": cl_max,
                **AIR,
            },
        )
    )


def detail_of(warning: KernelWarning, key: str) -> float:
    value = warning.detail[key]
    assert isinstance(value, float)
    return value


def window(cl_max: float) -> tuple[float, float]:
    return max(0.1, 0.1 * cl_max), 0.85 * cl_max


def polar_of(cd_of_cl: Callable[[float], float], levels: Sequence[float]) -> LevelPolar:
    return LevelPolar(
        v_ms=tuple(10.0 for _ in levels),
        alpha_deg=tuple(5.0 for _ in levels),
        cl=tuple(levels),
        cd=tuple(cd_of_cl(level) for level in levels),
    )


async def test_fit_recovers_an_exact_parabola() -> None:
    """Hand values: cd = 0.03 + 0.05 cl^2 is its own fit, with no residual."""
    levels = (0.2, 0.4, 0.6, 0.8)
    fit = fit_parabola(levels, tuple(0.03 + 0.05 * cl * cl for cl in levels))
    assert close(fit.cd0, 0.03, 1e-12)
    assert close(fit.k, 0.05, 1e-12)
    assert fit.rms < 1e-15
    assert fit.max_abs < 1e-15


async def test_fit_of_a_polar_that_is_no_parabola_is_the_least_squares_line_in_cl_squared() -> None:
    """Hand values: x = C_L^2 = (1, 2, 3), y = C_D = (1, 3, 2): slope Sxy/Sxx = 1/2, intercept 2 - 0.5 * 2 = 1.

    Residuals (-0.5, 1, -0.5): RMS sqrt(1.5 / 3), largest 1.
    """
    fit = fit_parabola((1.0, math.sqrt(2.0), math.sqrt(3.0)), (1.0, 3.0, 2.0))
    assert close(fit.k, 0.5, 1e-12)
    assert close(fit.cd0, 1.0, 1e-12)
    assert close(fit.rms, math.sqrt(0.5), 1e-12)
    assert close(fit.max_abs, 1.0, 1e-12)


async def test_the_fit_asks_for_equally_spaced_levels_in_the_window_and_returns_cd0_and_e() -> None:
    """Window BR-16: [max(0.1, 0.1 CL_max), 0.85 CL_max]; e = 1 / (pi AR k) with k = 0.05."""
    opti = StubOpti()
    ctx = context_with(StubAtmosphere({}), opti=opti)
    result = await parabolic_polar_fit(fit_inputs(), ctx)
    assert set(result) == {"cd0", "e_osw"}
    assert close(result["cd0"], CD0, 1e-9)
    assert close(result["e_osw"], 1.0 / (math.pi * 8.0 * K), 1e-9)
    ((_, mass, gravity, air, levels),) = opti.level_calls
    assert (mass, gravity, air.density) == (MASS, GRAVITY, RHO)
    low, high = window(CL_MAX)
    assert len(levels) == POINTS
    assert close(levels[0], low, 1e-12)
    assert close(levels[-1], high, 1e-12)
    steps = {round(b - a, 12) for a, b in pairwise(levels)}
    assert len(steps) == 1


async def test_a_low_cl_max_puts_the_lower_end_on_the_floor() -> None:
    """C_L,max = 0.5: 0.1 * 0.5 = 0.05 is below the floor 0.1, so the window is [0.1, 0.425]."""
    opti = StubOpti()
    await parabolic_polar_fit(fit_inputs(cl_max=0.5), context_with(StubAtmosphere({}), opti=opti))
    ((_, _, _, _, levels),) = opti.level_calls
    assert close(levels[0], 0.1, 1e-12)
    assert close(levels[-1], 0.425, 1e-12)


async def test_an_empty_window_is_refused() -> None:
    """C_L,max = 0.1: the window [0.1, 0.085] is empty."""
    ctx = context_with(StubAtmosphere({}), opti=StubOpti())
    with pytest.raises(FormulaError) as raised:
        await parabolic_polar_fit(fit_inputs(cl_max=0.1), ctx)
    assert raised.value.category is ErrorCategory.INVALID_INPUT
    assert raised.value.parameter == "cl_max"


async def test_every_fit_declares_its_residual() -> None:
    ctx = context_with(StubAtmosphere({}), opti=StubOpti())
    await parabolic_polar_fit(fit_inputs(), ctx)
    (warning,) = [w for w in ctx.warnings if w.code == "polar_fit_residual"]
    assert warning.severity is WarningSeverity.NOTICE
    assert warning.detail["points"] == POINTS
    low, high = window(CL_MAX)
    assert close(detail_of(warning, "cl_min"), low, 1e-12)
    assert close(detail_of(warning, "cl_max"), high, 1e-12)
    assert detail_of(warning, "rms") < 1e-12
    assert not [w for w in ctx.warnings if w.code == "polar_fit_nonphysical"]


async def test_the_residual_is_the_scatter_of_the_solver_drag_about_the_parabola() -> None:
    """The solver drag is the parabola plus a constant 0.001 on every other point: RMS 0.0005 *sqrt(...)."""
    opti = StubOpti()

    def answer(levels: Sequence[float]) -> LevelPolar:
        base = parabolic_level_polar(levels)
        bumped = tuple(cd + (0.001 if i % 2 else 0.0) for i, cd in enumerate(base.cd))
        return base.model_copy(update={"cd": bumped})

    opti.level_answer = answer
    ctx = context_with(StubAtmosphere({}), opti=opti)
    result = await parabolic_polar_fit(fit_inputs(), ctx)
    (warning,) = [w for w in ctx.warnings if w.code == "polar_fit_residual"]
    rms = warning.detail["rms"]
    assert isinstance(rms, float)
    assert 0.0003 < rms < 0.0006
    assert close(result["cd0"], CD0 + 0.0005, 0.1)


def falling(cl: float) -> float:
    return 0.05 - 0.02 * cl * cl


def below_zero(cl: float) -> float:
    return -0.01 + 0.05 * cl * cl


def nearly_flat(cl: float) -> float:
    return 0.03 + 0.001 * cl * cl


@pytest.mark.parametrize(
    ("cd_of_cl", "reason"),
    [
        (falling, "k_not_positive"),
        (below_zero, "cd0_not_positive"),
        (nearly_flat, "e_above_maximum"),
    ],
)
async def test_a_nonphysical_fit_is_declared_as_an_error_warning_and_the_numbers_are_returned(
    cd_of_cl: Callable[[float], float], reason: str
) -> None:
    """k <= 0 (e <= 0), C_D0 <= 0 and e above 1 are not physical (ADR 0020): declared, never replaced."""
    opti = StubOpti()
    opti.level_answer = lambda levels: polar_of(cd_of_cl, tuple(levels))
    ctx = context_with(StubAtmosphere({}), opti=opti)
    result = await parabolic_polar_fit(fit_inputs(), ctx)
    assert set(result) == {"cd0", "e_osw"}
    (warning,) = [w for w in ctx.warnings if w.code == "polar_fit_nonphysical"]
    assert warning.severity is WarningSeverity.ERROR
    assert reason in warning.detail["reasons"]  # pyright: ignore[reportOperatorIssue]


async def test_a_flat_polar_is_declared_nonphysical() -> None:
    """A drag independent of C_L has a slope of zero up to rounding: e is absurd or negative, declared."""
    opti = StubOpti()
    opti.level_answer = lambda levels: polar_of(lambda _cl: 0.04, tuple(levels))
    ctx = context_with(StubAtmosphere({}), opti=opti)
    await parabolic_polar_fit(fit_inputs(), ctx)
    (warning,) = [w for w in ctx.warnings if w.code == "polar_fit_nonphysical"]
    reasons = warning.detail["reasons"]
    assert isinstance(reasons, list)
    assert set(reasons) & {"k_not_positive", "e_above_maximum"}


def zero_slope(_cl: Sequence[float], _cd: Sequence[float]) -> ParabolaFit:
    return ParabolaFit(cd0=0.04, k=0.0, rms=0.0, max_abs=0.0)


async def test_a_slope_of_exactly_zero_has_no_finite_oswald_factor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aero_kernel.formulas.parabolic_polar_fit as module

    monkeypatch.setattr(
        module,
        "fit_parabola",
        zero_slope,
    )
    ctx = context_with(StubAtmosphere({}), opti=StubOpti())
    with pytest.raises(FormulaError) as raised:
        await parabolic_polar_fit(fit_inputs(), ctx)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


async def test_a_solver_drag_at_or_below_zero_is_a_defective_result() -> None:
    opti = StubOpti()
    opti.level_answer = lambda levels: polar_of(lambda _cl: 0.0, tuple(levels))
    ctx = context_with(StubAtmosphere({}), opti=opti)
    with pytest.raises(FormulaError) as raised:
        await parabolic_polar_fit(fit_inputs(), ctx)
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


async def test_the_solver_caveats_are_forwarded() -> None:
    opti = StubOpti()
    from aero_kernel.solvers.opti import induced_drag_notice

    opti.level_warnings = (induced_drag_notice(0.83625),)
    ctx = context_with(StubAtmosphere({}), opti=opti)
    await parabolic_polar_fit(fit_inputs(), ctx)
    assert "induced_drag_viscous_factor_removed" in [w.code for w in ctx.warnings]


async def test_the_chain_end_to_end_with_stubs_gives_the_closed_forms_of_the_stub_parabola() -> (
    None
):
    """Through the engine: C_D0 = 0.03, k = 0.05; the probe E_max = 1 / (2 sqrt(C_D0 k)) = 12.9099...

    The stub's own best-glide answer is the same closed form, so the probe and the optimisation agree.
    """
    result = await run(
        "zero-lift-drag-coefficient",
        "oswald-efficiency",
        "induced-drag-factor",
        "max-lift-to-drag-probe",
        "max-lift-to-drag-ratio",
        delta=None,
    )
    by_slug = {q.slug: q for q in result.quantities}
    assert all(q.status is QuantityStatus.OK for q in result.quantities), result.quantities
    assert close(by_slug["zero-lift-drag-coefficient"].value, CD0, 1e-9)
    wing = stand_in_main_wing_properties(plane())
    ar = wing.b_ref**2 / wing.s_ref
    assert close(by_slug["oswald-efficiency"].value, 1.0 / (math.pi * ar * K), 1e-9)
    assert close(by_slug["induced-drag-factor"].value, K, 1e-9)
    assert close(by_slug["max-lift-to-drag-probe"].value, 1.0 / (2.0 * math.sqrt(CD0 * K)), 1e-9)
    assert close(by_slug["max-lift-to-drag-ratio"].value, 1.0 / (2.0 * math.sqrt(CD0 * K)), 1e-9)


async def test_a_nonphysical_fit_stops_the_chain_at_the_induced_drag_factor() -> None:
    """A fitted slope below zero gives e < 0: the fit's own values stay, k and the probes are errors."""
    opti = StubOpti()
    opti.level_answer = lambda levels: polar_of(lambda cl: 0.05 - 0.02 * cl * cl, tuple(levels))
    result = await run(
        "oswald-efficiency", "induced-drag-factor", "max-lift-to-drag-probe", opti=opti, delta=None
    )
    by_slug = {q.slug: q for q in result.quantities}
    assert by_slug["oswald-efficiency"].status is QuantityStatus.OK
    assert by_slug["oswald-efficiency"].value is not None
    assert by_slug["oswald-efficiency"].value < 0.0
    assert any(w.code == "polar_fit_nonphysical" for w in by_slug["oswald-efficiency"].warnings)
    assert by_slug["induced-drag-factor"].status is QuantityStatus.ERROR
    assert by_slug["max-lift-to-drag-probe"].status is not QuantityStatus.OK
