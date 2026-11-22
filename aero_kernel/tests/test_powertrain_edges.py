"""The edges of the powertrain chain: the table's edges, windmilling, level-flight search, input checks."""

import math
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


def flat_table(rpms: tuple[float, ...], ct: tuple[float, ...], cp: tuple[float, ...]) -> Components:
    """A table with the given blocks, each flat over ``J`` in 0 to 3 (``C_T`` and ``C_P`` per block)."""
    document = complete_components_with_table().model_dump()
    document["propeller"]["table"] = {
        "blocks": [
            {"rpm": rpm, "j": [0.0, 3.0], "ct": [t, t], "cp": [p, p]}
            for rpm, t, p in zip(rpms, ct, cp, strict=True)
        ]
    }
    return Components.model_validate(document)


def test_with_two_torque_balances_the_equilibrium_is_the_highest_one() -> None:
    """Blocks 1000/2000/2500/3000 rpm, flat in J, at V = 0, K_v 300 rpm/V (free run 4440 rpm).

    The C_P per block is 0.5, 1.5, 0.5, 1.5 times the C_P that zeroes the residual Q_m - Q_p there, so
    the residual is positive, negative, positive, negative: two sign changes, 1000 to 2000 rpm and 2500
    to 3000 rpm. The full-throttle speed is the highest crossing (the thrust-dependent quantities
    are those of the highest speed the drive train holds). The expected root is a plain bisection of
    Q_m(n) - C_P(n) rho n^2 D^5 / (2 pi) on the piecewise-linear C_P between the blocks 2500 and 3000 rpm.
    """
    kv, i0, rm = 300.0, 1.2, 0.082
    kv_rad = 2.0 * math.pi * kv / 60.0

    def motor_q(
        n: float,
    ) -> float:  # n in 1/s: Q_m = (I - I_0) / K_v', I = (U - 2 pi n / K_v') / R_m
        return ((U_BAT - 2.0 * math.pi * n / kv_rad) / rm - i0) / kv_rad

    def q_per_cp(n: float) -> float:  # Q_p / C_P = rho n^2 D^5 / (2 pi)
        return RHO * n * n * D_PROP**5 / (2.0 * math.pi)

    rpms = (1000.0, 2000.0, 2500.0, 3000.0)
    factors = (0.5, 1.5, 0.5, 1.5)
    cps = tuple(
        f * motor_q(r / 60.0) / q_per_cp(r / 60.0) for r, f in zip(rpms, factors, strict=True)
    )
    components = flat_table(rpms, (0.1,) * 4, cps)

    def residual(n: float) -> float:
        fraction = (n * 60.0 - 2500.0) / 500.0  # between the blocks 2500 and 3000 rpm
        c_p = cps[2] + fraction * (cps[3] - cps[2])
        return motor_q(n) - c_p * q_per_cp(n)

    low, high = 2500.0 / 60.0, 3000.0 / 60.0
    assert residual(low) > 0.0 > residual(high)
    for _ in range(80):
        middle = 0.5 * (low + high)
        low, high = (middle, high) if residual(middle) > 0.0 else (low, middle)
    upper_root = 0.5 * (low + high)

    got = equilibrium(
        context_for("motor-propeller-equilibrium"),
        components, 0.0, RHO, kv, i0, rm, U_BAT, D_PROP,
    )  # fmt: skip
    assert math.isclose(got.n_prop, upper_root, rel_tol=1e-6)
    assert 2500.0 < got.n_prop * 60.0 < 3000.0  # not the lower crossing between 1000 and 2000 rpm


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


def test_exactly_on_an_inner_block_the_upper_block_has_no_weight_and_no_range_check() -> None:
    """Blocks 1200, 2400, 3600 rpm with J ranges 0.8, 0.8, 0.2: at 2400 rpm the upper neighbour ends at
    J = 0.2, but its weight at exactly 2400 rpm is zero, so J = 0.5 is read from the 2400 rpm block
    alone (C_T 0.1, C_P 0.04). One rpm above, the interpolation needs the 3600 rpm block and fails."""
    document = complete_components_with_table().model_dump()
    document["propeller"]["table"] = {
        "blocks": [
            {"rpm": rpm, "j": [0.0, top], "ct": [0.1, 0.1], "cp": [0.04, 0.04]}
            for rpm, top in zip((1200.0, 2400.0, 3600.0), (0.8, 0.8, 0.2), strict=True)
        ]
    }
    components = Components.model_validate(document)
    got = table_lookup(components, 0.5, 2400.0 / 60)
    assert (got.c_t, got.c_p) == (0.1, 0.04)
    with pytest.raises(FormulaError) as caught:
        table_lookup(components, 0.5, 2401.0 / 60)
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
    assert "this kernel accepts version 3" in message
    assert "propeller performance table" in message
