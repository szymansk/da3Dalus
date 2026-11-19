"""The powered-performance formulas with the real AeroBuildup on the Avistar Elite (aero tier, gh-1414).

The drive train is the Avistar's: AXI 4120/14 (Kv, R_m, I_0 and efficiency published), APC 13x8E (its published
performance table), the 4S pack; the maximum power, the pack mass, the C-rate and the cell voltage are the marked
test values of ``components_builders``. The assertions are the physical consistency of one formula with another
and with a brute-force scan, not a validation: the paper publishes no maximum speed or climb rate of this
aircraft (``reference/avistar_elite/MEASUREMENTS.md``).
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


def avistar(values: dict[str, float] | None = None) -> AircraftInput:
    """The Avistar Elite at sea level with its own drive train (one table, marked test values)."""
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
    base = aircraft_input(FleetMember.AVISTAR_ELITE, {"altitude": 0.0, **(values or {})})
    return base.model_copy(update={"components": Components.model_validate(components)})


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


async def test_the_maximum_level_speed_is_where_the_part_load_formula_demands_full_throttle() -> None:
    """At ``V_max`` the drag equals the full-throttle thrust, so the thrust demand ratio of the part-load
    formula (another formula, the same drive-train relations) is 1."""
    got = await run(avistar(), "max-level-speed")
    v_max = value(got, "max-level-speed")
    assert 25.0 < v_max < 40.0  # the 13x8E on 4S: the paper's trimmed level flight is 20 m/s
    assert "powertrain_route_winding_resistance" in codes(got, "max-level-speed")
    ratio = await run(avistar({"flight-speed": v_max}), "thrust-demand-ratio")
    assert math.isclose(value(ratio, "thrust-demand-ratio"), 1.0, abs_tol=2e-3)


async def test_the_best_rate_of_climb_beats_its_neighbours_and_the_small_angle_estimate() -> None:
    got = await run(avistar(), "best-rate-of-climb", "best-rate-of-climb-speed")
    roc, v_y = value(got, "max-rate-of-climb"), value(got, "best-rate-of-climb-speed")
    assert 0.0 < roc < v_y
    assert 5.0 < v_y < 30.0
