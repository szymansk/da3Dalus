"""The level-flight point at a given speed of the OPT adapter (gh-1411): the single-speed reading of the
level-flight polar, built on the same ``_level_point``.

Fast tier: the worker with the closed-form stand-in of ``test_solvers_opti_level`` (lift ``q S C_L(alpha)``
with a first peak at 23 deg, drag ``q S (C_D0 + k C_L^2)``), and the adapter with a canned worker.
"""

import math

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.runtime import WorkerDiagnostics, WorkerOutcome
from aero_kernel.solvers import opti as opti_module
from aero_kernel.solvers.opti import (
    LevelPoint,
    LevelPointRequest,
    OptiAdapter,
    level_point_worker,
    level_polar_worker,
)
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.solver_builders import AIR, K_E_D0, InProcessRuntime, airplane, drag_notice
from aero_kernel.tests.stall_stubs import CD0, K
from aero_kernel.tests.test_solvers_opti_level import (
    AREA,
    GRAVITY,
    MASS,
    TOLERANCE,
    installed,
    request,
    stand_in_cl,
)

pytestmark = pytest.mark.asyncio


def point_request(v_ms: float, n_load: float = 1.0) -> LevelPointRequest:
    return LevelPointRequest(
        airplane=airplane(),
        mass_kg=MASS,
        gravity=GRAVITY,
        air=AIR,
        v_ms=v_ms,
        n_load=n_load,
        k_e_d0=K_E_D0,
        lift_tolerance=TOLERANCE,
    )


async def test_the_point_carries_the_weight_at_the_given_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed(monkeypatch)
    weight = MASS * GRAVITY
    speed = math.sqrt(2.0 * weight / (AIR.density * AREA * 0.6))  # the speed of C_L = 0.6
    found = level_point_worker(point_request(speed)).value
    q_s = 0.5 * AIR.density * speed * speed * AREA
    assert found.v_ms == speed
    assert close(found.lift_n, weight, 1e-6)
    assert close(found.cl, 0.6, 1e-6)
    assert close(stand_in_cl(found.alpha_deg), 0.6, 1e-6)
    assert close(found.cd, CD0 + K * 0.6**2, 1e-6)
    assert close(found.drag_n, q_s * (CD0 + K * 0.6**2), 1e-6)


async def test_the_point_is_the_polar_point_of_the_same_speed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One solve in the kernel: the polar's point at C_L = 0.4 and the single-speed point agree."""
    installed(monkeypatch)
    polar = level_polar_worker(request((0.2, 0.4, 0.6))).value
    found = level_point_worker(point_request(polar.v_ms[1])).value
    assert close(found.alpha_deg, polar.alpha_deg[1], 1e-9)
    assert close(found.cl, polar.cl[1], 1e-9)
    assert close(found.cd, polar.cd[1], 1e-9)


async def test_a_speed_the_wing_cannot_carry_the_weight_at_is_not_converged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed(monkeypatch)
    slow = math.sqrt(2.0 * MASS * GRAVITY / (AIR.density * AREA * 2.0))  # C_L = 2 > the peak 1.25
    with pytest.raises(FormulaError) as caught:
        level_point_worker(point_request(slow))
    assert (caught.value.category, caught.value.code) == (
        ErrorCategory.NOT_CONVERGED,
        "not_converged",
    )


async def test_the_adapter_hands_over_the_speed_and_adds_the_regime_and_the_drag_notice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[LevelPointRequest] = []
    canned = LevelPoint(v_ms=18.0, alpha_deg=3.0, cl=0.3, cd=0.05, lift_n=4.9, drag_n=0.8)

    def worker(given: LevelPointRequest) -> WorkerOutcome[LevelPoint]:
        seen.append(given)
        return WorkerOutcome(value=canned, diagnostics=WorkerDiagnostics(duration_s=0.0))

    monkeypatch.setattr(opti_module, "level_point_worker", worker)
    result = await OptiAdapter(InProcessRuntime()).level_flight_point(
        airplane(), MASS, GRAVITY, AIR, 18.0, 1.5
    )
    (given,) = seen
    assert (given.mass_kg, given.gravity, given.air, given.v_ms, given.n_load) == (
        MASS,
        GRAVITY,
        AIR,
        18.0,
        1.5,
    )
    assert given.k_e_d0 == K_E_D0
    assert given.lift_tolerance == 1e-6
    assert result.point == canned
    assert result.warnings == (drag_notice(),)  # 18 m/s: no regime warning on this stand-in


@pytest.mark.parametrize("speed", [0.0, -3.0, math.nan, math.inf])
async def test_an_inadmissible_speed_is_refused_before_any_solve(speed: float) -> None:
    with pytest.raises(FormulaError) as caught:
        await OptiAdapter(InProcessRuntime()).level_flight_point(
            airplane(), MASS, GRAVITY, AIR, speed, 1.0
        )
    assert caught.value.category is ErrorCategory.INVALID_INPUT


@pytest.mark.parametrize("n_load", [-0.5, math.nan, math.inf])
async def test_an_inadmissible_load_factor_is_refused_before_any_solve(n_load: float) -> None:
    with pytest.raises(FormulaError) as caught:
        await OptiAdapter(InProcessRuntime()).level_flight_point(
            airplane(), MASS, GRAVITY, AIR, 18.0, n_load
        )
    assert caught.value.category is ErrorCategory.INVALID_INPUT
    assert caught.value.parameter == "n_load"


async def test_a_load_factor_scales_the_lift_the_point_carries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """At 18 m/s and n = 2 the lift is 2 m g: C_L = 2 * 2 m g / (rho S V^2); the drag follows the polar."""
    installed(monkeypatch)
    found = level_point_worker(point_request(18.0, 2.0)).value
    q_s = 0.5 * AIR.density * 18.0**2 * AREA
    expected_cl = 2.0 * 2.0 * MASS * GRAVITY / (2.0 * q_s)
    assert close(found.lift_n, 2.0 * MASS * GRAVITY, 1e-6)
    assert close(found.cl, expected_cl, 1e-6)
    assert close(stand_in_cl(found.alpha_deg), expected_cl, 1e-6)
    assert close(found.cd, CD0 + K * expected_cl**2, 1e-6)


async def test_a_load_factor_of_zero_is_the_zero_lift_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The stand-in lift curve crosses zero at -2 deg, where the drag is the zero-lift drag."""
    installed(monkeypatch)
    found = level_point_worker(point_request(18.0, 0.0)).value
    q_s = 0.5 * AIR.density * 18.0**2 * AREA
    assert abs(found.alpha_deg + 2.0) <= 1e-6
    assert abs(found.lift_n) <= TOLERANCE * MASS * GRAVITY
    assert close(found.drag_n, q_s * CD0, 1e-6)


async def test_the_wing_limit_is_named_in_the_failure_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    installed(monkeypatch)
    slow = math.sqrt(2.0 * MASS * GRAVITY / (AIR.density * AREA * 2.0))
    with pytest.raises(FormulaError) as caught:
        level_point_worker(point_request(slow))
    assert caught.value.detail is not None
    assert caught.value.detail["limit"] == "wing_lift"


async def test_a_sweep_without_a_peak_is_not_the_wing_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No first C_L peak inside the sweep is a solver failure, not a stall: it carries no wing-limit tag."""
    installed(monkeypatch, lambda alpha: 0.05 * (alpha + 20.0))  # rises over the whole sweep
    with pytest.raises(FormulaError) as caught:
        level_point_worker(point_request(18.0))
    assert "no peak" in caught.value.message
    assert "limit" not in caught.value.detail


async def test_a_zero_lift_angle_outside_the_sweep_is_not_the_wing_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The lift curve is above zero everywhere below its peak: the zero-lift point does not exist, no stall."""
    installed(monkeypatch, lambda alpha: 0.5 + 0.1 * (alpha + 15.0) - 0.002 * (alpha + 15.0) ** 2)
    with pytest.raises(FormulaError) as caught:
        level_point_worker(point_request(18.0, 0.0))
    assert "zero-lift angle" in caught.value.message
    assert "limit" not in caught.value.detail


# A lift curve whose first peak lies between two samples of the 0.25 deg sweep: the sampled peak
# (16.5 deg) is a little lower than the curve's own (C_L = 1.3356 at 16.47 deg), like the Avistar Elite's
# at its first peak. Curvature and position are those measured there (gh-1426).
PEAK_ALPHA, PEAK_CL, CURVATURE = 16.47, 1.3356, 0.0052


def peaked_cl(alpha: float) -> float:
    return PEAK_CL - CURVATURE * (alpha - PEAK_ALPHA) ** 2


def level_speed(level: float) -> float:
    return math.sqrt(2.0 * MASS * GRAVITY / (AIR.density * AREA * level))


@pytest.mark.parametrize("below_peak", [1.0e-5, 1.1e-5, 3.0e-6, 1.0e-4])
async def test_a_lift_just_below_the_true_peak_is_reached_on_the_branch_before_it(
    monkeypatch: pytest.MonkeyPatch, below_peak: float
) -> None:
    """The lift is reachable (it lies below the curve's peak), so the point is the root before the peak.

    The secant used to jump over the peak for such a target, and the outcome depended on where it
    stopped: the wing limit at one lift, ``did not reach the weight`` at another a hair away.
    """
    installed(monkeypatch, peaked_cl)
    level = PEAK_CL - below_peak
    found = level_point_worker(point_request(level_speed(level))).value
    assert close(found.cl, level, 2 * TOLERANCE)
    assert found.alpha_deg < PEAK_ALPHA
    assert close(peaked_cl(found.alpha_deg), level, 2 * TOLERANCE)


async def test_the_wing_limit_starts_exactly_at_the_lift_maximum_of_the_curve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Across the maximum of the curve (between two samples), a lift is reached if and only if it is at
    most the maximum: the classification is a function of the lift, not of where a search stops."""
    installed(monkeypatch, peaked_cl)
    for offset in range(-20, 21):
        level = PEAK_CL + offset * 1.0e-6
        if offset == 0:
            continue  # the maximum itself is within the tolerance of both outcomes
        speed = level_speed(level)
        if offset < 0:
            found = level_point_worker(point_request(speed)).value
            assert close(found.cl, level, 2 * TOLERANCE)
            continue
        with pytest.raises(FormulaError) as caught:
            level_point_worker(point_request(speed))
        assert caught.value.detail["limit"] == "wing_lift", offset


@pytest.mark.parametrize("above_peak", [1.0e-9, 1.0e-3, 0.5])
async def test_a_lift_above_the_maximum_is_the_wing_limit(
    monkeypatch: pytest.MonkeyPatch, above_peak: float
) -> None:
    installed(monkeypatch, peaked_cl)
    with pytest.raises(FormulaError) as caught:
        level_point_worker(point_request(level_speed(PEAK_CL + above_peak)))
    assert caught.value.detail["limit"] == "wing_lift"
