"""``motor-propeller-part-load`` with the real AeroBuildup on the Avistar Elite (aero tier, gh-1411).

The drive train is the Avistar's: AXI 4120/14 (Kv, R_m, I_0 and efficiency published), APC 13x8E (its
published performance table), the 4S pack; the maximum power, the pack mass, the C-rate and the cell
voltage are the marked test values of ``components_builders`` (nobody publishes them as the catalogue
field). The assertions are physical consistency and plausibility, not a validation: no measured
cruise power of this aircraft is published.
"""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.components import Components
from aero_kernel.engine import evaluate
from aero_kernel.reference_fleet import FleetMember, aircraft_input
from aero_kernel.schema import AircraftInput, QuantityStatus
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

CRUISE_MS = 18.0


async def test_the_avistar_cruises_on_a_battery_power_the_drive_train_can_deliver() -> None:
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
    base = aircraft_input(FleetMember.AVISTAR_ELITE, {"flight-speed": CRUISE_MS, "altitude": 0.0})
    aircraft: AircraftInput = base.model_copy(
        update={"components": Components.model_validate(components)}
    )
    result = await evaluate(
        shipped_build(),
        aircraft,
        request(
            "propeller-speed-part-load", "battery-current", "battery-power", "thrust-demand-ratio"
        ),
        solvers=solvers_with(),
    )
    got = {q.slug: q for q in result.quantities}
    assert all(q.status is QuantityStatus.OK for q in got.values()), got
    power, current = got["battery-power"].value, got["battery-current"].value
    assert power is not None
    assert current is not None
    assert 20.0 < power < 600.0  # a 3.7 kg trainer at 18 m/s: tens to a few hundred watts
    assert abs(current - power / 14.8) <= 1e-9 * power  # U_bat = 4 x 3.7 V
    assert got["thrust-demand-ratio"].value is not None
    assert 0.0 < got["thrust-demand-ratio"].value < 1.0  # part load: below full throttle
