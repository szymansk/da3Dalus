"""roll-rate-cruise-target through the engine on the shipped canon, stub adapters (two worlds)."""

import math

import pytest
from aero_kernel.schema import QuantityStatus, ReasonCode
from aero_kernel.tests.asb_fakes import stand_in_main_wing_properties
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.np_builders import StubAvl
from aero_kernel.tests.stall_stubs import StubOpti
from aero_kernel.tests.test_roll_rate_engine import GRAVITY, MASS, RHO, only, plane, run

pytestmark = pytest.mark.asyncio

V_CRUISE = 15.0
B_REF = 0.8
TARGET = {"cruise-speed-target": V_CRUISE}
AB_WORLD, AVL_WORLD = "roll-rate-cruise-target=aerobuildup", "roll-rate-cruise-target=avl"


async def test_without_a_cruise_speed_target_the_quantity_does_not_exist() -> None:
    quantity = only(await run("roll-rate-cruise"))
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.reason is not None
    assert quantity.reason.code is ReasonCode.NOT_GIVEN
    assert quantity.error is None


async def test_the_interval_spans_both_worlds_at_the_cruise_speed_target() -> None:
    """Hand values: AeroBuildup p = 3 rad/s; AVL p_hat = 0.08 -> p = 0.08 * 2 V / b rad/s."""
    quantity = only(await run("roll-rate-cruise", extra=TARGET))
    assert quantity.status is QuantityStatus.OK, quantity
    assert (quantity.unit, quantity.tool) == ("deg/s", "OPT")
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == {AB_WORLD, AVL_WORLD}
    assert close(quantity.interval.worlds[AB_WORLD], math.degrees(3.0), 1e-12)
    avl_rate = math.degrees(0.08 * 2.0 * V_CRUISE / B_REF)
    assert close(quantity.interval.worlds[AVL_WORLD], avl_rate, 1e-12)


async def test_both_worlds_are_solved_on_the_clean_airplane_at_the_target_speed() -> None:
    opti, avl = StubOpti(), StubAvl()
    await run("roll-rate-cruise", opti=opti, avl=avl, extra=TARGET)
    ((airplane, mass, gravity, air, speed, delta),) = opti.roll_calls
    assert (mass, gravity, air.density, speed, delta) == (MASS, GRAVITY, RHO, V_CRUISE, 20.0)
    assert airplane == plane()
    ((avl_airplane, cl, avl_delta),) = avl.roll_calls
    area = stand_in_main_wing_properties(avl_airplane).s_ref
    assert close(cl, MASS * GRAVITY / (0.5 * RHO * V_CRUISE**2 * area), 1e-12)
    assert avl_delta == 20.0


@pytest.mark.parametrize("p_hat", [0.1001, 0.25])
async def test_the_avl_world_beyond_its_range_is_dropped_and_declared(p_hat: float) -> None:
    avl = StubAvl()
    avl.p_hat = p_hat
    quantity = only(await run("roll-rate-cruise", avl=avl, extra=TARGET))
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == {AB_WORLD}
    (warning,) = [w for w in quantity.warnings if w.code == "world_outside_validity"]
    assert warning.world == AVL_WORLD
    assert warning.detail["limit"] == 0.1
    assert warning.detail["p_hat"] == p_hat
    p_deg_s = warning.detail["p_deg_s"]
    assert isinstance(p_deg_s, float)
    assert close(p_deg_s, math.degrees(p_hat * 2.0 * V_CRUISE / B_REF), 1e-12)


async def test_the_avl_world_at_the_limit_stays_in_the_interval() -> None:
    avl = StubAvl()
    avl.p_hat = 0.10
    quantity = only(await run("roll-rate-cruise", avl=avl, extra=TARGET))
    assert quantity.interval is not None
    assert set(quantity.interval.worlds) == {AB_WORLD, AVL_WORLD}


async def test_no_aileron_role_means_not_applicable() -> None:
    quantity = only(
        await run("roll-rate-cruise", airplane=plane("elevator"), delta=None, extra=TARGET)
    )
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
