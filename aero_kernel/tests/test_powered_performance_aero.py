"""The powered-performance formulas with the real AeroBuildup on the Avistar Elite (aero tier, gh-1414).

The drive train is the Avistar's: AXI 4120/14 (Kv, R_m, I_0 and efficiency published), APC 13x8E (its published
performance table), the 4S pack; the maximum power, the pack mass, the C-rate and the cell voltage are the marked
test values of ``components_builders``. The assertions are the consistency of one formula with another and with
bounds worked out by hand, not a validation: the paper publishes no maximum speed, climb rate or turn rate of
this aircraft (``reference/avistar_elite/MEASUREMENTS.md``). Cost on an Apple laptop: about 3 s for the level
speed, 30 s for the climb, 90 s for the two turns.

Hand bounds at 20 m/s (sea level, 3.70 kg, W = 36.29 N): the full-throttle thrust is 18.76 N, the level drag
2.26 N (both reproduced by ``xcheck`` in the evidence sheet). The climb angle satisfies
``W sin(gamma) = T - D(cos gamma) >= T - D(1)`` (a steeper path needs less lift, so less induced drag), so
``ROC_max >= 20 (18.76 - 2.26) / 36.29 = 9.09 m/s``; the thrust power is at most 376 W over the whole speed
range, so ``ROC_max <= 376 / 36.29 = 10.4 m/s``.
"""

import math

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.components import Components
from aero_kernel.engine import evaluate
from aero_kernel.reference_fleet import FleetMember, aircraft_input
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.tests.components_builders import (
    TEST_C_RATE,
    TEST_CELL_VOLTAGE_V,
    TEST_MAX_POWER_W,
    TEST_PACK_MASS_G,
    apc_13x8e_table,
    components_of,
)
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import solvers_with

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]


def with_avistar_drive(
    member: FleetMember, values: dict[str, float] | None = None
) -> AircraftInput:
    """A fleet airframe at sea level with the Avistar Elite's drive train (one table, marked test values)."""
    components = components_of(
        "axi_4120_14",
        "thunder_power_prolitex_4s_6000",
        "apc_13x8e",
        motor={"max_power_w": TEST_MAX_POWER_W},
        battery={
            "mass_g": TEST_PACK_MASS_G,
            "c_rate": TEST_C_RATE,
            "cell_voltage_v": TEST_CELL_VOLTAGE_V,
        },
    ).model_dump()
    components["propeller"]["table"] = apc_13x8e_table()
    base = aircraft_input(member, {"altitude": 0.0, **(values or {})})
    return base.model_copy(update={"components": Components.model_validate(components)})


def avistar(values: dict[str, float] | None = None) -> AircraftInput:
    """The Avistar Elite at sea level with its own drive train."""
    return with_avistar_drive(FleetMember.AVISTAR_ELITE, values)


async def run(aircraft: AircraftInput, *slugs: str) -> dict[str, QuantityResult]:
    result: ComputeResult = await evaluate(
        shipped_build(), aircraft, request(*slugs), solvers=solvers_with()
    )
    return {q.slug: q for q in result.quantities}


def value(got: dict[str, QuantityResult], slug: str) -> float:
    quantity = got[slug]
    assert quantity.status is QuantityStatus.OK, quantity
    assert quantity.value is not None
    return quantity.value


def codes(got: dict[str, QuantityResult], slug: str) -> list[str]:
    return [w.code for w in got[slug].warnings]


async def test_the_maximum_level_speed_is_where_the_part_load_formula_demands_full_throttle() -> (
    None
):
    """At ``V_max`` the drag equals the full-throttle thrust, so the thrust demand ratio of the part-load
    formula (another formula, the same drive-train relations) is 1."""
    got = await run(avistar(), "max-level-speed")
    v_max = value(got, "max-level-speed")
    assert 25.0 < v_max < 38.0  # below the table's end near 38 m/s; the paper trims at 20 m/s
    assert "powertrain_route_winding_resistance" in codes(got, "max-level-speed")
    ratio = await run(avistar({"flight-speed": v_max}), "thrust-demand-ratio")
    assert math.isclose(value(ratio, "thrust-demand-ratio"), 1.0, abs_tol=2e-3)


async def test_the_dive_speed_is_the_declared_table_failure_on_the_avistar() -> None:
    """The dive ends far beyond the 13x8E's advance-ratio range (it covers up to about 38 m/s)."""
    got = await run(avistar(), "dive-speed")
    error = got["dive-speed"].error
    assert got["dive-speed"].status is QuantityStatus.ERROR
    assert error is not None
    assert error.code == "outside_propeller_table"


async def test_the_best_rate_of_climb_lies_between_the_hand_bounds() -> None:
    got = await run(avistar(), "max-rate-of-climb", "best-rate-of-climb-speed")
    roc, v_y = value(got, "max-rate-of-climb"), value(got, "best-rate-of-climb-speed")
    assert 9.09 <= roc <= 10.4
    assert 10.0 < v_y < 30.0
    assert "powered_limit_declared" not in codes(got, "max-rate-of-climb")  # an interior optimum


async def test_the_sustained_turns_are_consistent_with_each_other_and_say_which_limit_binds() -> (
    None
):
    """``omega_max`` is the largest rate over all states, so it is at least the rate of the tightest state,
    ``V_r / r_min``; each names the limit that ends the turn."""
    got = await run(
        avistar(),
        "max-sustained-turn-rate",
        "max-sustained-turn-rate-speed",
        "min-sustained-turn-radius",
        "min-sustained-turn-radius-speed",
    )
    omega = value(got, "max-sustained-turn-rate")
    radius, v_r = (
        value(got, "min-sustained-turn-radius"),
        value(got, "min-sustained-turn-radius-speed"),
    )
    assert math.degrees(v_r / radius) <= omega
    assert 0.0 < radius < 100.0
    for slug in ("max-sustained-turn-rate", "min-sustained-turn-radius"):
        assert "powered_limit_declared" in codes(got, slug)


@pytest.mark.parametrize(
    "member",
    [FleetMember.BRYAN, FleetMember.CHEKKER, FleetMember.SUPER_TRIDENT],
    ids=lambda m: m.name,
)
async def test_the_level_speed_computes_where_the_scan_from_two_m_s_ended_in_the_solver(
    member: FleetMember,
) -> None:
    """gh-1419: at 2 m/s the sweep of these three airframes shows no lift peak, which ended the formula as
    ``not_converged``. The scan now starts at the clean stall speed, so it computes. The bounds are the
    range of the other 13 airframes with this drive train (31.5 to 39.0 m/s, the table ends near 42 m/s)."""
    got = await run(with_avistar_drive(member), "max-level-speed", "stall-speed")
    v_max, v_s = value(got, "max-level-speed"), value(got, "stall-speed")
    assert v_s < v_max < 42.0
    assert 25.0 < v_max < 42.0


async def test_the_climbs_of_a_real_airframe_with_a_non_vertical_optimum_compute_from_the_new_start() -> (
    None
):
    """gh-1419: ULTRA_STICK_120 (T_0 / W below 1): the climb scan starts at the stall speed at the steepest angle
    the static thrust holds, both climbs compute, and the best angle is flown above the stall speed."""
    got = await run(
        with_avistar_drive(FleetMember.ULTRA_STICK_120),
        "stall-speed",
        "best-angle-of-climb-speed",
        "max-climb-angle",
        "best-rate-of-climb-speed",
        "max-rate-of-climb",
    )
    v_s, v_x = value(got, "stall-speed"), value(got, "best-angle-of-climb-speed")
    assert v_s < v_x < 20.0  # measured 14.6 m/s against 11.5 m/s
    assert 5.0 < value(got, "max-climb-angle") < 15.0  # measured 10.2 deg
    assert 2.0 < value(got, "max-rate-of-climb") < 4.0  # measured 3.0 m/s


async def test_a_real_airframe_that_can_climb_vertically_starts_its_climb_scan_at_the_declared_floor() -> (
    None
):
    """RV7 with the Avistar drive train has a static thrust above its weight: the climb needs no lift, the scan
    starts at the floor (declared), and the answer is the vertical climb."""
    got = await run(
        with_avistar_drive(FleetMember.RV7), "best-angle-of-climb-speed", "max-climb-angle"
    )
    assert math.isclose(value(got, "max-climb-angle"), 90.0)
    declared = [
        w.detail.get("limit")
        for w in got["max-climb-angle"].warnings
        if w.code == "powered_limit_declared"
    ]
    assert "scan_floor" in declared


async def test_a_climb_scan_start_below_the_stall_speed_can_still_end_in_the_solver_miles_magister() -> (
    None
):
    """The limitation of gh-1419, recorded and not hidden: MILES_MAGISTER (static thrust above weight, floor start at
    half the stall speed, 3.5 m/s) is a case where the sweep shows no lift peak at the start, which ends the climbs
    as ``not_converged`` (an open decision of the maintainer, gh-1419)."""
    got = await run(
        with_avistar_drive(FleetMember.MILES_MAGISTER),
        "best-angle-of-climb-speed",
        "best-rate-of-climb-speed",
    )
    for slug in ("best-angle-of-climb-speed", "best-rate-of-climb-speed"):
        error = got[slug].error
        assert got[slug].status is QuantityStatus.ERROR
        assert error is not None
        assert error.code == "not_converged"
        assert "no peak" in error.message
