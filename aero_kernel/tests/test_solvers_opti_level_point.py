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


async def test_a_point_that_settles_beyond_the_first_peak_is_the_wing_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The secant ends past the sweep's first C_L peak: not on the branch before the stall, so the wing limit."""
    installed(monkeypatch)

    def settled_past_the_peak(_sweep: object, _level: float, _speed: float) -> tuple[float, float]:
        return 10.0, 8.0

    monkeypatch.setattr(opti_module, "_level_alpha", settled_past_the_peak)
    level = stand_in_cl(10.0)  # the lift at the (wrong) angle equals the weight at this speed
    speed = math.sqrt(2.0 * MASS * GRAVITY / (AIR.density * AREA * level))
    with pytest.raises(FormulaError) as caught:
        level_point_worker(point_request(speed))
    assert caught.value.detail["limit"] == "wing_lift"
    assert "beyond the first C_L peak" in caught.value.message
