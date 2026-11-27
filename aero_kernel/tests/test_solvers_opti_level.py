"""The level-flight polar of the OPT adapter: every point at the speed where it carries the weight (#1401).

Fast tier: the adapter with a canned worker, and the worker with a closed-form stand-in for AeroBuildup
(lift ``q S C_L(alpha)`` with a main peak, drag ``q S (C_D0 + k C_L^2)``).
"""

import math
from collections.abc import Callable
from types import SimpleNamespace

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.aerobuildup import LiftCurve
from aero_kernel.solvers.opti import (
    LevelPolar,
    LevelPolarRequest,
    OptiAdapter,
)
from aero_kernel.solvers.regime import regime_by_surface
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.planform_stand_in import canon_bands, stand_in_surface_sections
from aero_kernel.tests.solver_builders import AIR, K_E_D0, InProcessRuntime, airplane, drag_notice
from aero_kernel.tests.stall_stubs import CD0, K

pytestmark = pytest.mark.asyncio

MASS, GRAVITY, AREA = 0.5, 9.80665, 0.28
LEVELS = (0.2, 0.4, 0.6, 0.8, 1.0)
TOLERANCE = 1e-6


def stand_in_cl(alpha: float) -> float:
    """A lift curve with a main peak at alpha = 23 deg (C_L = 1.25): 0.1 (a + 2) - 0.002 (a + 2)^2."""
    return 0.1 * (alpha + 2.0) - 0.002 * (alpha + 2.0) ** 2


def installed(
    monkeypatch: pytest.MonkeyPatch, cl_of_alpha: Callable[[float], float] = stand_in_cl
) -> list[tuple[float, float]]:
    """Replace AeroBuildup by the stand-in; returns the (speed, alpha) of every evaluation."""
    calls: list[tuple[float, float]] = []

    def convert(_airplane: object) -> SimpleNamespace:
        return SimpleNamespace(s_ref=AREA)

    def sweep(
        _plane: object, air: object, speed: float, alphas: list[float], _size: str
    ) -> LiftCurve:
        return LiftCurve(alpha_deg=tuple(alphas), cl=tuple(cl_of_alpha(a) for a in alphas))

    def forces(
        _plane: object, air: object, speed: float, alpha: float, _size: str, _k: float
    ) -> tuple[float, float]:
        calls.append((speed, alpha))
        q = 0.5 * AIR.density * speed * speed
        cl = cl_of_alpha(alpha)
        return q * AREA * cl, q * AREA * (CD0 + K * cl * cl)

    monkeypatch.setattr(opti_module, "to_asb_airplane", convert)
    monkeypatch.setattr(opti_module, "sweep_lift", sweep)
    monkeypatch.setattr(opti_module, "evaluate_forces", forces)
    return calls


def request(levels: tuple[float, ...] = LEVELS) -> LevelPolarRequest:
    return LevelPolarRequest(
        airplane=airplane(),
        mass_kg=MASS,
        gravity=GRAVITY,
        air=AIR,
        cl_levels=levels,
        k_e_d0=K_E_D0,
        lift_tolerance=TOLERANCE,
    )


async def test_every_point_is_flown_at_the_speed_where_it_carries_the_weight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hand values: V = sqrt(2 m g / (rho S C_L)); the lift at the found alpha equals m g, so C_L is the level."""
    installed(monkeypatch)
    polar = opti_module.level_polar_worker(request()).value
    for level, v, alpha, cl, cd in zip(
        LEVELS, polar.v_ms, polar.alpha_deg, polar.cl, polar.cd, strict=True
    ):
        assert close(v, math.sqrt(2.0 * MASS * GRAVITY / (AIR.density * AREA * level)), 1e-12)
        assert close(cl, level, 2 * TOLERANCE)
        assert close(stand_in_cl(alpha), level, 2 * TOLERANCE)
        assert close(cd, CD0 + K * level * level, 1e-5)


async def test_the_angle_is_refined_beyond_the_sweep_interpolation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The curve is not linear between two 0.25 deg samples, so the interpolation alone would miss."""
    calls = installed(monkeypatch)
    opti_module.level_polar_worker(request((0.6, 0.8, 1.0)))
    assert len(calls) > 3  # more than one evaluation per point: the secant ran


async def test_a_level_beyond_the_first_peak_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed(monkeypatch)
    with pytest.raises(FormulaError) as raised:
        opti_module.level_polar_worker(request((0.4, 0.8, 1.4)))
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert raised.value.detail is not None
    assert raised.value.detail["cl"] == 1.4


async def test_a_lift_curve_without_a_peak_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed(monkeypatch, cl_of_alpha=lambda alpha: 0.1 * (alpha + 2.0))
    with pytest.raises(FormulaError) as raised:
        opti_module.level_polar_worker(request())
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


async def test_a_lift_that_never_reaches_the_weight_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sweep promises the level, the evaluation never delivers it and the secant slope is zero."""
    installed(monkeypatch)

    def flat(*_args: object) -> tuple[float, float]:
        return 1.0, 0.1

    monkeypatch.setattr(opti_module, "evaluate_forces", flat)
    with pytest.raises(FormulaError) as raised:
        opti_module.level_polar_worker(request((0.4, 0.8, 1.0)))
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


async def test_a_secant_that_does_not_settle_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One step is allowed and the first evaluation misses the weight: the point is not converged."""
    installed(monkeypatch)
    weight = MASS * GRAVITY

    def always_high(
        _plane: object, _air: object, speed: float, alpha: float, _size: str, _k: float
    ) -> tuple[float, float]:
        return weight * (1.5 + 0.01 * alpha), 0.1

    monkeypatch.setattr(opti_module, "evaluate_forces", always_high)
    shipped = opti_module.config()
    one_step = shipped.model_copy(
        update={
            "opt_level_max_steps": shipped.opt_level_max_steps.model_copy(update={"value": 1.0})
        }
    )
    monkeypatch.setattr(opti_module, "config", lambda: one_step)
    with pytest.raises(FormulaError) as raised:
        opti_module.level_polar_worker(request((0.4, 0.8, 1.0)))
    assert raised.value.category is ErrorCategory.NOT_CONVERGED


def canned(polar: LevelPolar) -> object:
    def worker(_request: LevelPolarRequest) -> WorkerOutcome[LevelPolar]:
        return WorkerOutcome(value=polar, diagnostics=WorkerDiagnostics(duration_s=0.0))

    return worker


def polar_at(speeds: tuple[float, ...]) -> LevelPolar:
    levels = LEVELS[: len(speeds)]
    return LevelPolar(
        v_ms=speeds,
        alpha_deg=tuple(5.0 for _ in speeds),
        cl=levels,
        cd=tuple(CD0 + K * level * level for level in levels),
    )


async def test_the_adapter_hands_the_worker_everything_it_needs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[LevelPolarRequest] = []

    def worker(given: LevelPolarRequest) -> WorkerOutcome[LevelPolar]:
        seen.append(given)
        return WorkerOutcome(
            value=polar_at((18.0, 12.0, 9.0)), diagnostics=WorkerDiagnostics(duration_s=0.0)
        )

    monkeypatch.setattr(opti_module, "level_polar_worker", worker)
    plane = airplane()
    result = await OptiAdapter(InProcessRuntime()).level_polar(
        plane, MASS, GRAVITY, AIR, LEVELS[:3]
    )
    (given,) = seen
    assert (given.mass_kg, given.gravity, given.air, given.cl_levels) == (
        MASS,
        GRAVITY,
        AIR,
        LEVELS[:3],
    )
    assert given.airplane == plane
    assert given.k_e_d0 == K_E_D0
    assert given.lift_tolerance == 1e-6
    assert result.polar == polar_at((18.0, 12.0, 9.0))


async def test_the_regime_warnings_are_those_of_the_slowest_and_the_fastest_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Chords 0.2 and 0.1 m: at 6 m/s Re 8.2e4 and 4.1e4 (bubble-sensitive), at 18 m/s no warning.

    The drag notice comes last, once.
    """
    monkeypatch.setattr(opti_module, "level_polar_worker", canned(polar_at((18.0, 12.0, 6.0))))
    result = await OptiAdapter(InProcessRuntime()).level_polar(
        airplane(), MASS, GRAVITY, AIR, LEVELS[:3]
    )
    slow = regime_by_surface(
        stand_in_surface_sections(airplane()),
        6.0,
        AIR.speed_of_sound,
        AIR.kinematic_viscosity,
        canon_bands(),
    )
    assert [w.code for w in slow] == ["reynolds_bubble_sensitive"]
    assert result.warnings == (*slow, drag_notice())


async def test_the_regime_warnings_of_the_fastest_point_are_carried_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both extremes are checked (ADR 0028), the slowest point first.

    Stand-in MAC of chords 0.2 / 0.1 m: 0.1556 m; nu = 1.7894e-5 / 1.225 = 1.4607e-5 m^2/s.
    Slowest point, 6 m/s: Re = 6 * 0.1556 / 1.4607e-5 = 6.4e4, bubble-sensitive (below 7e4).
    Fastest point, 120 m/s: Re = 120 * 0.1556 / 1.4607e-5 = 1.28e6, above the band's 1e6, and
    Mach = 120 / 340.294 = 0.353, above 0.3. The drag notice comes last.
    """
    monkeypatch.setattr(opti_module, "level_polar_worker", canned(polar_at((120.0, 12.0, 6.0))))
    result = await OptiAdapter(InProcessRuntime()).level_polar(
        airplane(), MASS, GRAVITY, AIR, LEVELS[:3]
    )
    assert [w.code for w in result.warnings] == [
        "reynolds_bubble_sensitive",
        "reynolds_above_band",
        "mach_above_limit",
        "induced_drag_viscous_factor_removed",
    ]
    bubble, above, mach, _notice = result.warnings
    assert (bubble.detail["wing"], above.detail["wing"]) == ("Main", "Main")
    # both are a ``notice`` (ARCHITECTURE ch. 8.8: Re_MAC > 1e6; 0.3 < M <= 0.6)
    assert (above.severity, mach.severity) == ("notice", "notice")
    found = mach.detail["mach"]
    assert isinstance(found, float)
    assert math.isclose(found, 120.0 / 340.294, rel_tol=1e-12)


async def test_a_regime_warning_that_both_extremes_share_is_given_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(opti_module, "level_polar_worker", canned(polar_at((6.0, 6.0, 6.0))))
    result = await OptiAdapter(InProcessRuntime()).level_polar(
        airplane(), MASS, GRAVITY, AIR, LEVELS[:3]
    )
    assert [w.code for w in result.warnings] == ["reynolds_bubble_sensitive", drag_notice().code]


async def test_a_deflected_flap_is_declared(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(opti_module, "level_polar_worker", canned(polar_at((18.0, 12.0, 9.0))))
    flapped = airplane(device=("flap", 10.0), hinge=0.75)
    result = await OptiAdapter(InProcessRuntime()).level_polar(
        flapped, MASS, GRAVITY, AIR, LEVELS[:3]
    )
    assert "control_surface_fit_range_unknown" in [w.code for w in result.warnings]


@pytest.mark.parametrize(
    "levels",
    [(0.2, 0.4), (0.4, 0.2, 0.6), (0.0, 0.2, 0.4), (0.2, 0.4, math.nan), (0.2, 0.2, 0.4)],
)
async def test_levels_that_are_not_three_rising_positive_numbers_are_refused(
    levels: tuple[float, ...],
) -> None:
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).level_polar(airplane(), MASS, GRAVITY, AIR, levels)
    assert raised.value.category is ErrorCategory.INVALID_INPUT


async def test_a_deflected_aileron_is_refused() -> None:
    plane = airplane(device=("aileron", 4.0))
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).level_polar(plane, MASS, GRAVITY, AIR, LEVELS[:3])
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


async def test_a_missing_aerosandbox_is_tool_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(OptiAdapter, "requirements", {"no-such-distribution": "no_such_xyz"})
    with pytest.raises(FormulaError) as raised:
        await OptiAdapter(InProcessRuntime()).level_polar(
            airplane(), MASS, GRAVITY, AIR, LEVELS[:3]
        )
    assert raised.value.category is ErrorCategory.TOOL_UNAVAILABLE


async def test_the_polar_needs_equally_long_series_of_at_least_three_points() -> None:
    with pytest.raises(ValueError, match="at least 3"):
        LevelPolar(v_ms=(1.0, 2.0), alpha_deg=(1.0, 2.0), cl=(0.1, 0.2), cd=(0.03, 0.03))


async def test_an_evaluation_that_disagrees_with_the_sweep_does_not_leave_the_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sweep reaches C_L = 0.8 near 7 deg, but the evaluation's lift is linear and weak: the search
    stays inside the two samples that enclose the root (the branch before the main peak) and, since the
    evaluation never reaches the weight there, ends as a plain failure, not as the wing limit."""
    installed(monkeypatch)
    weight = MASS * GRAVITY

    def weak_linear(
        _plane: object, _air: object, speed: float, alpha: float, _size: str, _k: float
    ) -> tuple[float, float]:
        q = 0.5 * AIR.density * speed * speed
        return q * AREA * 0.03 * (alpha + 2.0), 0.1 * weight

    monkeypatch.setattr(opti_module, "evaluate_forces", weak_linear)
    with pytest.raises(FormulaError) as raised:
        opti_module.level_polar_worker(request((0.4, 0.6, 0.8)))
    assert raised.value.category is ErrorCategory.NOT_CONVERGED
    assert "did not reach the weight" in raised.value.message
    assert "limit" not in raised.value.detail
