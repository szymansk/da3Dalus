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


def point_request(v_ms: float) -> LevelPointRequest:
    return LevelPointRequest(
        airplane=airplane(),
        mass_kg=MASS,
        gravity=GRAVITY,
        air=AIR,
        v_ms=v_ms,
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
        airplane(), MASS, GRAVITY, AIR, 18.0
    )
    (given,) = seen
    assert (given.mass_kg, given.gravity, given.air, given.v_ms) == (MASS, GRAVITY, AIR, 18.0)
    assert given.k_e_d0 == K_E_D0
    assert given.lift_tolerance == 1e-6
    assert result.point == canned
    assert result.warnings == (drag_notice(),)  # 18 m/s: no regime warning on this stand-in


@pytest.mark.parametrize("speed", [0.0, -3.0, math.nan, math.inf])
async def test_an_inadmissible_speed_is_refused_before_any_solve(speed: float) -> None:
    with pytest.raises(FormulaError) as caught:
        await OptiAdapter(InProcessRuntime()).level_flight_point(
            airplane(), MASS, GRAVITY, AIR, speed
        )
    assert caught.value.category is ErrorCategory.INVALID_INPUT
