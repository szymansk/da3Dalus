"""The edges of the powertrain chain: the table's edges, windmilling, level-flight search, input checks."""

from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.components import Components
from aero_kernel.engine import evaluate
from aero_kernel.errors import FormulaError
from aero_kernel.formulas.motor_propeller_equilibrium import equilibrium
from aero_kernel.formulas.motor_propeller_part_load import motor_propeller_part_load
from aero_kernel.formulas.propeller_table_lookup import table_lookup
from aero_kernel.schema import AircraftInput, KernelWarning
from aero_kernel.tests.components_builders import (
    apc_13x8e_table,
    complete_components_with_table,
)
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import solvers_with
from aero_kernel.tests.test_motor_propeller_part_load import LinearOpti
from aero_kernel.tests.test_motor_propeller_part_load import bound_inputs as part_load_inputs
from aero_kernel.tests.test_motor_propeller_part_load import context as part_load_context
from aero_kernel.tests.test_powertrain_chain import context_for
from aero_kernel.tests.wing_builders import airplane_document
from pydantic import ValidationError

RHO, D_PROP, U_BAT = 1.225, 13 * 0.0254, 14.8


def small_table(cp: tuple[float, float], j_max: tuple[float, float, float]) -> Components:
    """A three-block table (1000, 2000, 3000 rpm), flat ``C_T`` 0.1, linear ``C_P`` over ``J``."""
    document = complete_components_with_table().model_dump()
    document["propeller"]["table"] = {
        "blocks": [
            {"rpm": rpm, "j": [0.0, top], "ct": [0.1, 0.1], "cp": list(cp)}
            for rpm, top in zip((1000.0, 2000.0, 3000.0), j_max, strict=True)
        ]
    }
    return Components.model_validate(document)


def test_exactly_on_the_last_block_the_top_block_alone_decides() -> None:
    blocks = apc_13x8e_table()["blocks"]
    last, before = blocks[-1], blocks[-2]
    j = 0.5 * (
        before["j"][-1] + last["j"][-1]
    )  # beyond the previous block's range, inside the last
    assert before["j"][-1] < j < last["j"][-1]
    got = table_lookup(complete_components_with_table(), j, last["rpm"] / 60)
    assert abs(got.c_t) < 0.01
    with pytest.raises(FormulaError) as caught:
        table_lookup(complete_components_with_table(), j, (last["rpm"] - 1.0) / 60)
    assert caught.value.code == "outside_propeller_table"


def test_a_balance_where_the_table_has_no_data_is_reported_as_not_found() -> None:
    """The 1000 rpm block covers J up to 0.2 only. At 5 m/s the whole interval from 1000 to 2000 rpm is
    uncovered by the interpolation (it needs both blocks, and J there is above 0.45), so the coverage
    edge of the pair is the 2000 rpm grid point itself: the true balance near 1300 rpm lies where the
    table has no data. (Pinned by gh-1413 as 'not searched'; since gh-1417 the search does locate a
    coverage edge, but here there is none, so the failure stays and its message says why.)"""
    components = small_table((5.0, 5.0), (0.2, 0.5, 0.8))
    with pytest.raises(FormulaError) as caught:
        equilibrium(
            context_for("motor-propeller-equilibrium"),
            components, 5.0, RHO, 162.0, 1.2, 0.082, U_BAT, D_PROP,
        )  # fmt: skip
    assert caught.value.code == "outside_propeller_table"
    assert "no balance found where the table covers the advance ratio" in caught.value.message
    assert caught.value.detail["covered_grid_points"] == 2
    assert caught.value.detail["grid_points"] == 3
    assert caught.value.detail["coverage_edges"] == 0


def test_a_propeller_driven_by_the_airstream_is_the_truthful_windmilling_failure() -> None:
    components = small_table((0.05, -0.5), (3.0, 3.0, 3.0))  # C_P < 0 from J = 0.3 on
    with pytest.raises(FormulaError) as caught:
        equilibrium(
            context_for("motor-propeller-equilibrium"),
            components, 10.0, RHO, 900.0, 1.2, 0.082, U_BAT, D_PROP,
        )  # fmt: skip
    assert caught.value.code == "propeller_windmilling"
    assert "windmilling is not modelled" in caught.value.message


@pytest.mark.asyncio
async def test_the_level_flight_points_caveats_are_forwarded() -> None:
    note = KernelWarning.of("reynolds_bubble_sensitive", "low Re", detail={"v_ms": 10.0})
    ctx = part_load_context(LinearOpti(warnings=(note,)))
    await motor_propeller_part_load(part_load_inputs(), ctx)
    assert [w.detail for w in ctx.warnings if w.code == "reynolds_bubble_sensitive"] == [
        {"v_ms": 10.0}
    ]


@pytest.mark.asyncio
async def test_a_specific_energy_not_above_zero_is_refused_at_the_input() -> None:
    aircraft = AircraftInput.model_validate(
        {
            "airplane": airplane_document(),
            "values": {
                "aircraft-mass": 3.4,
                "battery-energy-required": 89.6,
                "battery-specific-energy": 0.0,
            },
        }
    )
    result = await evaluate(
        shipped_build(), aircraft, request("predicted-battery-mass"), solvers=solvers_with()
    )
    assert [(e.code, e.input_path) for e in result.input_errors] == [
        ("non_positive_value", "values.battery-specific-energy")
    ]


def test_a_version_one_components_document_is_refused_with_a_message_that_names_the_contract() -> (
    None
):
    document: dict[str, Any] = {
        "airplane": airplane_document(),
        "components": {"schema_version": 1, "propeller": {"diameter_in": 13.0}},
        "values": {"aircraft-mass": 3.4},
    }
    with pytest.raises(ValidationError) as caught:
        AircraftInput.model_validate(document)
    message = str(caught.value)
    assert "components.schema_version" in message
    assert "this kernel accepts version 2" in message
    assert "propeller performance table" in message
