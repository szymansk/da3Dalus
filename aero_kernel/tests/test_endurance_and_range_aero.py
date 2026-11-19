"""Endurance, range and the cruise target with the real AeroBuildup on the Avistar Elite (aero tier, gh-1415).

The drive train is the Avistar's: AXI 4120/14 (Kv, R_m, I_0 published), APC 13x8E (published table),
the 4S 6 Ah pack; the maximum power, the pack mass, the C-rate and the cell voltage are the marked
test values of ``components_builders`` (nobody publishes them as the catalogue field). The assertions
are consistency checks, not a validation: the paper publishes a flight time of 10 to 15 min
(Table 2) that is no battery-limited endurance at a speed, so no published value compares.

The cross-check of the optimum is a brute-force scan over the speed with the very same part-load
function (the kernel's ``battery-power`` at a given ``flight-speed``).
"""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.components import Components
from aero_kernel.engine import evaluate
from aero_kernel.reference_fleet import FleetMember, aircraft_input
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityStatus
from aero_kernel.tests.components_builders import (
    TEST_C_RATE,
    TEST_CELL_VOLTAGE_V,
    TEST_MAX_POWER_W,
    TEST_PACK_MASS_G,
    apc_13x8e_table,
    components_of,
)
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close, solvers_with

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

CRUISE_MS = 18.0
E_BAT_WH = 6.0 * 14.8  # 6 Ah on the 4S pack at the nominal 3.7 V per cell
HEAVY_MASS_KG = 3.95
SCAN_SPEEDS = [12.0 + 0.5 * k for k in range(0, 17)]  # 12 to 20 m/s, until the first hole


def avistar(values: dict[str, float]) -> AircraftInput:
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
    base = aircraft_input(FleetMember.AVISTAR_ELITE, {"altitude": 0.0, **values})
    return base.model_copy(update={"components": Components.model_validate(components)})


async def compute(values: dict[str, float], *slugs: str) -> ComputeResult:
    return await evaluate(shipped_build(), avistar(values), request(*slugs), solvers=solvers_with())


def value_of(result: ComputeResult, slug: str) -> float:
    found = {q.slug: q for q in result.quantities}[slug]
    assert found.status is QuantityStatus.OK, found
    assert found.value is not None
    return found.value


async def test_the_cruise_target_is_the_energy_over_the_battery_power_at_the_target() -> None:
    values = {"flight-speed": CRUISE_MS, "cruise-speed-target": CRUISE_MS}
    result = await compute(
        values, "battery-power", "endurance-at-cruise-target", "range-at-cruise-target"
    )
    power = value_of(result, "battery-power")
    t = value_of(result, "endurance-at-cruise-target")
    assert close(t, 3600.0 * E_BAT_WH / power, 1e-9)  # one endurance value by hand
    assert close(value_of(result, "range-at-cruise-target"), CRUISE_MS * t, 1e-12)


async def test_the_optimum_equals_a_brute_force_scan_and_the_estimate_does_not_exceed_it() -> None:
    # 3.95 kg is the second test aircraft of the paper: its two estimate speeds lie where the part-load
    # search finds a balance (at 3.70 kg the minimum-drag speed falls into a hole of the table coverage)
    values = {"aircraft-mass": HEAVY_MASS_KG}
    result = await compute(
        values,
        "endurance-estimate",
        "range-estimate",
        "max-endurance",
        "max-range",
    )
    powers: dict[float, float] = {}
    for v in SCAN_SPEEDS:
        scan = await compute({**values, "flight-speed": v}, "battery-power")
        found = {q.slug: q for q in scan.quantities}["battery-power"]
        if found.status is not QuantityStatus.OK or found.value is None:
            break  # the domain of the optimiser ends at the first speed without a balance, too
        powers[v] = found.value
    assert len(powers) >= 8
    t_scan = max(3600.0 * E_BAT_WH / p for p in powers.values())
    r_scan = max(3600.0 * E_BAT_WH * v / p for v, p in powers.items())
    t_max, r_max = value_of(result, "max-endurance"), value_of(result, "max-range")
    # the optimiser refines between scan speeds, so it is at least the scan's best (to the tolerance)
    assert t_max >= t_scan * (1.0 - 1e-4)
    assert r_max >= r_scan * (1.0 - 1e-4)
    assert t_max <= t_scan * 1.01  # and the scan's half-metre step is close to it
    assert r_max <= r_scan * 1.01
    # the estimate is a point of the optimiser's problem where its speed lies inside the domain
    assert value_of(result, "endurance-estimate") <= t_max * (1.0 + 1e-6)
    assert value_of(result, "range-estimate") <= r_max * (1.0 + 1e-6)


async def test_the_estimate_is_the_declared_failure_where_the_part_load_search_has_a_hole() -> None:
    # at 3.70 kg the minimum-drag speed (17.58 m/s) falls into the hole of the table coverage
    # (17.0 to 17.75 m/s have no balance); both outputs of the formula end in the declared failure
    result = await compute({}, "endurance-estimate", "range-estimate")
    for q in result.quantities:
        assert q.error is not None
        assert q.error.code == "outside_propeller_table"
