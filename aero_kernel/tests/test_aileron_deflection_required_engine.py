"""aileron-deflection-required through the engine on the shipped canon, with stub adapters.

The stub AeroBuildup roll saturates, ``p(delta) = P_MAX sin(pi delta / 2 DELTA_PEAK)`` (rad/s) up to
its peak, so the inverse is known in closed form, ``delta = (2 DELTA_PEAK / pi) asin(p / P_MAX)``; the stub AVL roll is linear,
``p_hat = K_AVL delta``, so its inverse is ``delta = p_hat / K_AVL``.
"""

import math

import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.schema import KernelWarning, QuantityResult, QuantityStatus, ReasonCode
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.avl import AvlRoll
from aero_kernel.solvers.opti import SteadyRoll
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.np_builders import StubAvl
from aero_kernel.tests.stall_stubs import StubOpti
from aero_kernel.tests.test_roll_rate_engine import (
    deflections,
    flap_and_aileron,
    only,
    plane,
    run,
)

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
    result = await run(
        "aileron-deflection-required-approach",
        airplane=flap_and_aileron(),
        delta=None,
        opti=opti,
        avl=avl,
        extra={"roll-rate-target-approach": 100.0, "flap-deflection-landing": 30.0},
    )
    assert only(result).status is QuantityStatus.OK, result
    assert opti.roll_calls
    assert avl.roll_calls
    for airplane in (*(call[0] for call in opti.roll_calls), *(call[0] for call in avl.roll_calls)):
        assert deflections(airplane) == {"flap": 30.0, "aileron": 0.0}
    assert all(close(call[1], 1.19 / 1.69, 1e-9) for call in avl.roll_calls)


async def test_no_aileron_role_means_not_applicable() -> None:
    quantity = only(await run(SLUG, airplane=plane("elevator"), delta=None, extra=CRUISE))
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.CONDITION_NOT_MET


class WarningAvl(LinearAvl):
    """A linear AVL roll that, like the adapter, warns when ``|p_hat|`` is beyond its range."""

    def __init__(self, k: float) -> None:
        super().__init__()
        self.k = k

    async def steady_roll(
        self, airplane: AirplaneGeometry, cl: float, delta_a_deg: float
    ) -> AvlRoll:
        self.roll_calls.append((airplane, cl, delta_a_deg))
        p_hat = self.k * delta_a_deg
        warnings = ()
        if abs(p_hat) > 0.10:
            warnings = (
                KernelWarning.of(
                    "avl_roll_rate_beyond_range",
                    "beyond range",
                    origin="roll-rate",
                    detail={"p_hat": p_hat, "limit": 0.10},
                ),
            )
        return AvlRoll(p_hat=p_hat, warnings=warnings)


async def test_the_reference_run_beyond_the_avl_range_does_not_warn_about_the_answer() -> None:
    """The reference run (5 deg, p_hat 0.15) is beyond 0.10; the target (p_hat 0.05) is not."""
    quantity = await solve(
        {**CRUISE, "roll-rate-target-cruise": math.degrees(0.05 * 2.0 * V_CRUISE / B_REF)},
        avl=WarningAvl(0.03),
    )
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == {AB, AVL}
    codes = [w.code for w in quantity.warnings]
    assert "avl_roll_rate_beyond_range" not in codes
    assert "world_outside_validity" not in codes


async def test_a_target_beyond_the_avl_range_declares_only_the_target_based_exclusion() -> None:
    quantity = await solve(
        {**CRUISE, "roll-rate-target-cruise": math.degrees(0.20 * 2.0 * V_CRUISE / B_REF)},
        avl=WarningAvl(0.03),
    )
    codes = [w.code for w in quantity.warnings]
    assert "avl_roll_rate_beyond_range" not in codes
    assert codes.count("world_outside_validity") == 1


@pytest.mark.parametrize("k", [0.0, 0.00001 / 5.0, -0.01])
async def test_an_avl_reference_without_roll_is_the_declared_error_not_a_scaled_angle(
    k: float,
) -> None:
    """p_hat at the reference of 0, of 0.00001 (below the print floor, quantisation noise) or
    negative (a reversed device) is the error AeroBuildup gives for a roll that does not rise."""

    class Flat(LinearAvl):
        async def steady_roll(
            self, airplane: AirplaneGeometry, cl: float, delta_a_deg: float
        ) -> AvlRoll:
            self.roll_calls.append((airplane, cl, delta_a_deg))
            return AvlRoll(p_hat=k * delta_a_deg, warnings=())

    quantity = await solve(avl=Flat())
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "target_above_method_maximum"
    assert quantity.error.world == AVL


async def test_a_reversed_device_is_the_same_error_in_the_aerobuildup_world() -> None:
    class Reversed(SaturatingOpti):
        async def steady_roll(
            self,
            airplane: AirplaneGeometry,
            mass_kg: float,
            gravity: float,
            air: AirState,
            v_ms: float,
            delta_a_deg: float,
        ) -> SteadyRoll:
            return SteadyRoll(
                p_rad_s=-0.1 * delta_a_deg, alpha_deg=4.0, warnings=(), confidence=None
            )

    quantity = await solve(opti=Reversed())
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "target_above_method_maximum"
    assert quantity.error.world == AB
    assert quantity.error.detail["delta_a_deg"] == 0.0
    assert quantity.error.detail["search_step_deg"] == 5.0


async def test_the_maximum_is_stated_as_the_highest_value_of_the_search_grid() -> None:
    quantity = await solve({**CRUISE, "roll-rate-target-cruise": math.degrees(1.2 * P_MAX)})
    assert quantity.error is not None
    assert quantity.error.detail["search_step_deg"] == 5.0
    assert "search grid" in quantity.error.message


async def test_a_roll_rate_that_jumps_over_the_target_is_not_converged_after_the_refinements() -> (
    None
):
    """A step in the roll rate has no root the regula falsi can reach: the refinements are
    bounded by ``opt_roll_max_refinements`` and the answer is not_converged, never a value."""

    class Jump(SaturatingOpti):
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
            rate = 0.5 if delta_a_deg < 7.5 else 2.0
            return SteadyRoll(p_rad_s=rate, alpha_deg=4.0, warnings=(), confidence=None)

    opti = Jump()
    quantity = await solve({**CRUISE, "roll-rate-target-cruise": math.degrees(1.0)}, opti)
    assert quantity.status is QuantityStatus.ERROR
    assert quantity.error is not None
    assert quantity.error.code == "not_converged"
    assert len(opti.roll_calls) == 2 + 40  # the march (5, 10 deg) and the 40 refinements
