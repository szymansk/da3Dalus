"""aileron-deflection-required through the engine on the shipped canon, with stub adapters.

The stub AeroBuildup roll saturates, ``p(delta) = P_MAX sin(pi delta / 2 DELTA_PEAK)`` (rad/s) up to
its peak, so the inverse is known in closed form, ``delta = (2 DELTA_PEAK / pi) asin(p / P_MAX)``; the stub AVL roll is linear,
``p_hat = K_AVL delta``, so its inverse is ``delta = p_hat / K_AVL``.
"""

import math

import pytest
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import QuantityResult, QuantityStatus, ReasonCode
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.avl import AvlRoll
from aero_kernel.solvers.opti import SteadyRoll
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.np_builders import StubAvl
from aero_kernel.tests.stall_stubs import StubOpti
from aero_kernel.tests.test_roll_rate_engine import GRAVITY, MASS, RHO, only, plane, run

pytestmark = pytest.mark.asyncio

P_MAX, DELTA_PEAK = 12.0, 40.0  # rad/s, deg: the stub AeroBuildup roll peaks here
K_AVL = 0.004  # p_hat per degree: the stub AVL roll
V_CRUISE, B_REF = 15.0, 0.8
CRUISE = {"cruise-speed-target": V_CRUISE, "roll-rate-target-cruise": 100.0}
AB, AVL = "aileron-deflection-required=aerobuildup", "aileron-deflection-required=avl"
SLUG = "aileron-deflection-required-cruise"


def _stub_rate(delta: float) -> float:
    """``P_MAX sin(pi delta / 2 DELTA_PEAK)``: rises to ``P_MAX`` at ``DELTA_PEAK``, then falls."""
    return P_MAX * math.sin(math.pi * delta / (2.0 * DELTA_PEAK))


class SaturatingOpti(StubOpti):
    """A steady roll that saturates in the command, as AeroBuildup does."""

    async def steady_roll(
        self,
        airplane: AirplaneGeometry,
        mass_kg: float,
        gravity: float,
        air: AirState,
        v_ms: float,
        delta_a_deg: float,
    ) -> SteadyRoll:
        self.roll_calls.append((airplane, mass_kg, gravity, air, v_ms, delta_a_deg))
        if self.roll_failure is not None:
            raise self.roll_failure
        return SteadyRoll(
            p_rad_s=_stub_rate(delta_a_deg),
            alpha_deg=4.0,
            warnings=(),
            confidence=None,
        )


class LinearAvl(StubAvl):
    """A steady roll that is linear in the command, as AVL's is."""

    async def steady_roll(
        self, airplane: AirplaneGeometry, cl: float, delta_a_deg: float
    ) -> AvlRoll:
        self.roll_calls.append((airplane, cl, delta_a_deg))
        return AvlRoll(p_hat=K_AVL * delta_a_deg, warnings=self.canned_warnings)


def target_hat(p_deg_s: float, speed: float = V_CRUISE) -> float:
    return math.radians(p_deg_s) * B_REF / (2.0 * speed)


def ab_delta(p_deg_s: float) -> float:
    return 2.0 * DELTA_PEAK / math.pi * math.asin(math.radians(p_deg_s) / P_MAX)


async def solve(
    extra: dict[str, float] | None = None,
    opti: StubOpti | None = None,
    avl: StubAvl | None = None,
    slug: str = SLUG,
) -> QuantityResult:
    return only(
        await run(
            slug,
            delta=None,
            opti=opti or SaturatingOpti(),
            avl=avl or LinearAvl(),
            extra=extra or CRUISE,
        )
    )


async def test_the_interval_spans_both_worlds_with_the_closed_form_inverse() -> None:
    quantity = await solve()
    assert quantity.status is QuantityStatus.OK, quantity
    assert (quantity.unit, quantity.tool) == ("deg", "OPT")
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == {AB, AVL}
    assert close(quantity.interval.worlds[AB], ab_delta(100.0), 1e-3)
    assert close(quantity.interval.worlds[AVL], target_hat(100.0) / K_AVL, 1e-9)


async def test_without_a_target_the_quantity_does_not_exist() -> None:
    quantity = await solve({"cruise-speed-target": V_CRUISE})
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.NOT_GIVEN


async def test_a_negative_target_gives_the_mirrored_deflection() -> None:
    plus = await solve()
    minus = await solve({**CRUISE, "roll-rate-target-cruise": -100.0})
    assert plus.interval is not None
    assert minus.interval is not None
    for world in (AB, AVL):
        assert close(minus.interval.worlds[world], -plus.interval.worlds[world], 1e-3)


async def test_a_zero_target_needs_no_deflection_and_no_solve() -> None:
    opti, avl = SaturatingOpti(), LinearAvl()
    quantity = await solve({**CRUISE, "roll-rate-target-cruise": 0.0}, opti, avl)
    assert quantity.interval is not None
    assert quantity.interval.worlds == {AB: 0.0, AVL: 0.0}
    assert opti.roll_calls == []
    assert avl.roll_calls == []


async def test_the_search_runs_on_the_clean_airplane_at_the_target_speed() -> None:
    opti, avl = SaturatingOpti(), LinearAvl()
    await solve(opti=opti, avl=avl)
    assert opti.roll_calls
    for airplane, mass, gravity, air, speed, _ in opti.roll_calls:
        assert (mass, gravity, air.density, speed) == (MASS, GRAVITY, RHO, V_CRUISE)
        assert airplane == plane()
    for airplane, cl, _ in avl.roll_calls:
        assert airplane == plane()
        assert cl > 0.0


async def test_the_returned_deflection_reproduces_the_target_through_the_roll() -> None:
    """The returned angle, fed back to the stub roll, gives the target within the tolerance."""
    quantity = await solve()
    assert quantity.interval is not None
    p_back = _stub_rate(quantity.interval.worlds[AB])
    assert close(p_back, math.radians(100.0), 1e-3)


async def test_a_target_above_the_aerobuildup_maximum_is_an_error_with_the_avl_value() -> None:
    p_max_deg_s = math.degrees(P_MAX)
    quantity = await solve({**CRUISE, "roll-rate-target-cruise": 1.2 * p_max_deg_s})
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.value is None
    assert quantity.error is not None
    assert quantity.error.code == "target_above_method_maximum"
    assert quantity.error.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert quantity.error.world == AB
    maximum = quantity.error.detail["max_roll_rate_deg_s"]
    assert isinstance(maximum, float)
    assert 0.95 * p_max_deg_s < maximum <= p_max_deg_s
    assert isinstance(quantity.error.detail["delta_a_deg"], float)
    worlds_ok = quantity.error.detail["worlds_ok"]
    assert isinstance(worlds_ok, dict)
    assert list(worlds_ok) == [AVL]


async def test_a_failure_of_the_roll_is_an_error_never_a_dropped_world() -> None:
    opti = SaturatingOpti()
    opti.roll_failure = FormulaError(
        ErrorCategory.NOT_CONVERGED, "not_converged", "no roll", "check the speed"
    )
    quantity = await solve(opti=opti)
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "not_converged"


async def test_a_roll_that_never_stops_increasing_is_not_converged_at_the_search_limit() -> None:
    class Unbounded(SaturatingOpti):
        async def steady_roll(
            self,
            airplane: AirplaneGeometry,
            mass_kg: float,
            gravity: float,
            air: AirState,
            v_ms: float,
            delta_a_deg: float,
        ) -> SteadyRoll:
            self.roll_calls.append((airplane, mass_kg, gravity, air, v_ms, delta_a_deg))
            return SteadyRoll(
                p_rad_s=1e-3 * delta_a_deg, alpha_deg=4.0, warnings=(), confidence=None
            )

    quantity = await solve({**CRUISE, "roll-rate-target-cruise": 1000.0}, Unbounded())
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "not_converged"


@pytest.mark.parametrize("p_hat_target", [0.1001, 0.25])
async def test_the_avl_world_beyond_its_range_is_dropped_and_declared(p_hat_target: float) -> None:
    target = math.degrees(p_hat_target * 2.0 * V_CRUISE / B_REF)
    quantity = await solve({**CRUISE, "roll-rate-target-cruise": target})
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == {AB}
    (warning,) = [w for w in quantity.warnings if w.code == "world_outside_validity"]
    assert warning.world == AVL
    assert warning.detail["limit"] == 0.1
    assert close(float(warning.detail["p_hat"]), p_hat_target, 1e-9)  # pyright: ignore[reportArgumentType]
    assert close(float(warning.detail["delta_a_deg"]), p_hat_target / K_AVL, 1e-9)  # pyright: ignore[reportArgumentType]


async def test_the_avl_world_at_the_limit_stays_in_the_interval() -> None:
    target = math.degrees(0.10 * 2.0 * V_CRUISE / B_REF)
    quantity = await solve({**CRUISE, "roll-rate-target-cruise": target})
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == {AB, AVL}
    assert not [w for w in quantity.warnings if w.code == "world_outside_validity"]


async def test_a_deflection_beyond_the_reference_is_noticed_once_per_world() -> None:
    quantity = await solve({**CRUISE, "roll-rate-target-cruise": math.degrees(0.9 * P_MAX)})
    assert quantity.interval is not None
    assert quantity.interval.worlds[AB] > 25.0
    beyond = [w for w in quantity.warnings if w.code == "aileron_deflection_beyond_reference"]
    assert sorted(str(w.world) for w in beyond) == sorted((AB, AVL))
    by_world = {str(w.world): float(w.detail["deflection_deg"]) for w in beyond}  # pyright: ignore[reportArgumentType]
    assert close(by_world[AB], quantity.interval.worlds[AB], 1e-9)
    # the AVL world left the interval (p_hat 0.288 > 0.10); its angle is in its declaration
    (dropped,) = [w for w in quantity.warnings if w.code == "world_outside_validity"]
    assert close(by_world[AVL], float(dropped.detail["delta_a_deg"]), 1e-9)  # pyright: ignore[reportArgumentType]


async def test_the_approach_application_uses_the_approach_speed() -> None:
    opti = SaturatingOpti()
    quantity = await solve(
        {"roll-rate-target-approach": 100.0}, opti=opti, slug="aileron-deflection-required-approach"
    )
    assert quantity.status is QuantityStatus.OK, quantity
    speeds = {call[4] for call in opti.roll_calls}
    assert len(speeds) == 1
    assert V_CRUISE not in speeds


async def test_no_aileron_role_means_not_applicable() -> None:
    quantity = only(await run(SLUG, airplane=plane("elevator"), delta=None, extra=CRUISE))
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.CONDITION_NOT_MET
