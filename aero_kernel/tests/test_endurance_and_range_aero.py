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
SCAN_SPEEDS = [12.0 + 0.5 * k for k in range(0, 17)]  # 12 to 20 m/s, inside the table's reach


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
    result = await compute(
        {},
        "endurance-estimate",
        "range-estimate",
        "max-endurance",
        "max-range",
        "minimum-sink-speed",
        "minimum-drag-speed",
        "stall-speed",
    )
    powers: dict[float, float] = {}
    for v in SCAN_SPEEDS:
        scan = await compute({"flight-speed": v}, "battery-power")
        powers[v] = value_of(scan, "battery-power")
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
