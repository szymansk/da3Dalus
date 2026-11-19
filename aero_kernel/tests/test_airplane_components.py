"""``airplane-components``: a plain read of the pushed components (ARCHITECTURE ch. 8.8, 8.11).

Hand computation for the complete document (T-Motor AT2814 KV900 Rm, Io and Kv, the Avistar pack capacity
and APC 13x8E; efficiency 80 %, power 650 W, pack mass 560 g, C-rate 25 and cell voltage 3.7 V are test values):

- m_bat = 560 g / 1000 = 0.56 kg;  Q_bat = 6000 mAh;  U_cell = 3.7 V;  U_bat = 4 * 3.7 = 14.8 V
- E_bat = 6000 / 1000 * 14.8 = 88.8 Wh;  I_bat,max = 25 * 6000 / 1000 = 150 A
- K_v = 900 rpm/V, I_0 = 1.2 A, R_m = 0.082 ohm, P_mot,max = 650 W, eta_mot = 80 / 100 = 0.8
- D_prop = 13 in * 0.0254 = 0.3302 m
"""

from typing import Any

import pytest
from aero_kernel.api import CachedKernel
from aero_kernel.build import shipped_build
from aero_kernel.components import Components
from aero_kernel.engine import evaluate
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.formulas.airplane_components import airplane_components
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.tests.components_builders import complete_components, components_of
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close, inputs_from_model, solvers_with
from aero_kernel.tests.wing_builders import airplane_document

pytestmark = pytest.mark.asyncio

HAND = {
    "battery-mass": (0.56, "kg"),
    "battery-charge-capacity": (6000.0, "mAh"),
    "battery-capacity": (88.8, "Wh"),
    "battery-c-rate": (25.0, "1/h"),
    "battery-current-allowed": (150.0, "A"),
    "cell-voltage-nominal": (3.7, "V"),
    "motor-voltage-constant": (900.0, "rpm/V"),
    "motor-no-load-current": (1.2, "A"),
    "motor-circuit-resistance": (0.082, "ohm"),
    "motor-efficiency": (0.8, "1"),
    "battery-voltage": (14.8, "V"),
    "motor-max-power": (650.0, "W"),
    "propeller-diameter": (0.3302, "m"),
}
PARAMETER_OF = {
    "battery-mass": "m_bat",
    "battery-charge-capacity": "q_bat",
    "battery-capacity": "e_bat",
    "battery-c-rate": "c_rate",
    "battery-current-allowed": "i_bat_max",
    "cell-voltage-nominal": "u_cell",
    "motor-voltage-constant": "k_v",
    "motor-no-load-current": "i_0",
    "motor-circuit-resistance": "r_m",
    "motor-efficiency": "eta_mot",
    "battery-voltage": "u_bat",
    "motor-max-power": "p_mot_max",
    "propeller-diameter": "d_prop",
}


def aircraft_with(components: Components | None) -> AircraftInput:
    document: dict[str, Any] = {
        "airplane": airplane_document(),
        "values": {"aircraft-mass": 0.151},
    }
    if components is not None:
        document["components"] = components.model_dump()
    return AircraftInput.model_validate(document)


async def compute_all(components: Components | None) -> ComputeResult:
    return await evaluate(
        shipped_build(),
        aircraft_with(components),
        request(*HAND),
        solvers=solvers_with(),
    )


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


async def test_every_quantity_of_the_entry_has_its_hand_computed_value_and_unit() -> None:
    result = await compute_all(complete_components())
    quantities = by_slug(result)
    assert set(quantities) == set(HAND)
    for slug, (value, unit) in HAND.items():
        got = quantities[slug]
        assert got.status is QuantityStatus.OK, (slug, got)
        assert got.value is not None
        assert close(got.value, value, 1e-12), (slug, got.value, value)
        assert got.unit == unit
        assert got.tool == "KAT"
        assert got.warnings == ()
    assert result.provenance.defaults_used == ()
    assert result.provenance.tool_versions == {}


async def test_the_formula_is_called_with_the_components_and_returns_the_parameters() -> None:
    model = shipped_build().model
    x = inputs_from_model(model, "airplane-components", {"components": complete_components()})
    returned = await airplane_components(x, _context())
    assert set(returned) == set(PARAMETER_OF.values())
    for slug, (value, _) in HAND.items():
        assert close(returned[PARAMETER_OF[slug]], value, 1e-12)


def _context() -> Any:
    from aero_kernel.context import Context

    return Context(origin="battery-mass", solvers=solvers_with())


async def test_a_missing_components_is_the_ordinary_missing_input_of_that_quantity() -> None:
    result = await compute_all(None)
    for quantity in result.quantities:
        assert quantity.status is QuantityStatus.ERROR
        assert quantity.error is not None
        assert quantity.error.code == "missing_input"
        assert quantity.error.category is ErrorCategory.INVALID_INPUT
        assert quantity.error.input_path == "components"
        assert "`components`" in quantity.error.message
        assert "AircraftInput.components" in quantity.error.hint


@pytest.mark.parametrize(
    ("part", "name", "path"),
    [
        ("motor", "rm_ohm", "components.motor.rm_ohm"),
        ("motor", "io_no_load_a", "components.motor.io_no_load_a"),
        ("motor", "efficiency_pct", "components.motor.efficiency_pct"),
        ("motor", "max_power_w", "components.motor.max_power_w"),
        ("battery", "mass_g", "components.battery.mass_g"),
        ("battery", "c_rate", "components.battery.c_rate"),
        ("battery", "cell_voltage_v", "components.battery.cell_voltage_v"),
    ],
)
async def test_an_absent_catalogue_value_fails_the_formula_and_names_the_field(
    part: str, name: str, path: str
) -> None:
    document: dict[str, Any] = complete_components().model_dump()
    del document[part][name]
    result = await compute_all(Components.model_validate(document))
    assert len(result.quantities) == len(HAND)
    for quantity in result.quantities:
        assert quantity.status is QuantityStatus.ERROR
        assert quantity.value is None
        assert quantity.error is not None
        assert quantity.error.code == "missing_input"
        assert quantity.error.category is ErrorCategory.INVALID_INPUT
        assert quantity.error.input_path == "components"
        assert f"`{path}`" in quantity.error.message
        assert quantity.error.detail == {"inputs": [path]}


async def test_every_absent_field_is_named_in_catalogue_order() -> None:
    result = await compute_all(
        components_of("axi_4120_14", "thunder_power_prolitex_4s_6000", "apc_13x8e")
    )
    error = result.quantities[0].error
    assert error is not None
    assert error.detail == {
        "inputs": [
            "components.motor.max_power_w",
            "components.battery.mass_g",
            "components.battery.c_rate",
            "components.battery.cell_voltage_v",
        ]
    }
    assert "`components.motor.max_power_w`" in error.message
    assert "`components.battery.mass_g`" in error.message


async def test_a_missing_part_is_named_as_a_part() -> None:
    document = complete_components().model_dump()
    document["propeller"] = None
    result = await compute_all(Components.model_validate(document))
    error = result.quantities[0].error
    assert error is not None
    assert error.detail == {"inputs": ["components.propeller"]}


async def test_the_failure_does_not_touch_a_quantity_that_reads_no_component() -> None:
    result = await evaluate(
        shipped_build(),
        aircraft_with(None),
        request("battery-mass", "weight"),
        solvers=solvers_with(),
    )
    quantities = by_slug(result)
    assert quantities["battery-mass"].status is QuantityStatus.ERROR
    assert quantities["weight"].status is QuantityStatus.OK


async def test_the_formula_raises_missing_input_for_an_absent_value_never_a_substitute() -> None:
    document = complete_components().model_dump()
    del document["motor"]["rm_ohm"]
    model = shipped_build().model
    x = inputs_from_model(
        model, "airplane-components", {"components": Components.model_validate(document)}
    )
    with pytest.raises(FormulaError) as raised:
        await airplane_components(x, _context())
    assert raised.value.code == "missing_input"
    assert raised.value.parameter == "components"


async def test_a_changed_component_changes_the_cached_value() -> None:
    other = complete_components().model_dump()
    other["battery"]["mass_g"] = 600.0
    async with CachedKernel(max_entries=16) as kernel:
        first = await kernel.compute(aircraft_with(complete_components()), request("battery-mass"))
        second = await kernel.compute(
            aircraft_with(Components.model_validate(other)), request("battery-mass")
        )
        again = await kernel.compute(aircraft_with(complete_components()), request("battery-mass"))
    assert [r.quantities[0].value for r in (first, second, again)] == [0.56, 0.6, 0.56]


async def test_a_field_found_present_but_absent_is_a_defect_not_a_user_error() -> None:
    from aero_kernel.formulas.airplane_components import held

    with pytest.raises(TypeError, match=r"components\.motor\.rm_ohm"):
        held(None, "components.motor.rm_ohm")
