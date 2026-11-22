"""The powertrain chain: advance ratio, table lookup, thrust, torque balance, static T/W, battery mass.

Hand and independent computations (no kernel code; ``numpy`` and the published APC 13x8E table of
``reference/powertrain/apc_13x8e.json``): the T-Motor AT2814 KV900 (Kv 900 rpm/V, R_m 0.082 ohm, I_0 1.2 A,
all published) on the 4S Avistar pack, U_bat = 14.8 V (a nominal 4 x 3.7 V), at sea level
(rho = 1.225 kg/m^3), D = 13 in = 0.3302 m, bisection of the torque balance on rpm:

- static:   n = 8898.305 rpm, I = 59.9146 A, Q = 0.62298 N m, T = 32.9713 N
- 10 m/s:   n = 8662.075 rpm, I = 63.1155 A, Q = 0.65694 N m, T = 27.0365 N
"""

import math
from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.components import Components
from aero_kernel.context import Context
from aero_kernel.engine import evaluate
from aero_kernel.errors import FormulaError
from aero_kernel.formulas.advance_ratio_from_speed import advance_ratio, advance_ratio_from_speed
from aero_kernel.formulas.battery_mass_from_capacity import battery_mass_from_capacity
from aero_kernel.formulas.motor_propeller_equilibrium import (
    equilibrium,
    motor_propeller_equilibrium,
)
from aero_kernel.formulas.propeller_table_lookup import propeller_table_lookup, table_lookup
from aero_kernel.formulas.static_thrust_to_weight import static_thrust_to_weight
from aero_kernel.formulas.thrust_at_airspeed_from_coefficient import (
    thrust,
    thrust_at_airspeed_from_coefficient,
)
from aero_kernel.registry import DEFAULT_REGISTRY
from aero_kernel.schema import AircraftInput, ComputeResult, QuantityResult, QuantityStatus
from aero_kernel.tests import powertrain_reference as reference
from aero_kernel.tests.components_builders import (
    apc_13x8e_table,
    complete_components,
    complete_components_with_table,
)
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close, inputs_from_model, solvers_with
from aero_kernel.tests.wing_builders import airplane_document

RHO = 1.225
D_PROP = 13 * 0.0254
U_BAT = 14.8
G = 9.80665


def context(embeds: tuple[str, ...] = ()) -> Context:
    relations = {item: DEFAULT_REGISTRY.relation_of(item.split(".")[0]) for item in embeds}
    return Context(
        origin="t",
        solvers=solvers_with(),
        relations={k: v for k, v in relations.items() if v is not None},
    )


def context_for(slug: str) -> Context:
    """The context of a formula: the relations of its canon ``embeds`` (what the engine hands out)."""
    formula = shipped_build().model.formula(slug)
    assert formula is not None
    return context(tuple(formula.embeds))


def table() -> list[dict[str, Any]]:
    return apc_13x8e_table()["blocks"]


def independent_balance(v: float) -> tuple[float, float, float, float]:
    """rpm, I, Q and T of the balance, from the independent plain-Python computation."""
    point = reference.full_throttle(v)
    return point.rpm, point.current, point.torque, point.thrust


def bound_inputs(formula: str, **extra: Any) -> dict[str, Any]:
    """``x`` of a formula built from the model, with the AT2814 on a 14.8 V pack."""
    components = complete_components_with_table()
    by_quantity: dict[str, Any] = {
        "components": components,
        "air-density": RHO,
        "motor-voltage-constant": 900.0,
        "motor-no-load-current": 1.2,
        "motor-circuit-resistance": 0.082,
        "battery-voltage": U_BAT,
        "motor-max-power": 650.0,
        "propeller-diameter": D_PROP,
        "motor-efficiency": 0.8,
        "flight-speed": 0.0,
        "weight": 3.4 * G,
    }
    by_quantity.update(extra)
    model = shipped_build().model
    needed = model.formula(formula)
    assert needed is not None
    wanted = set(needed.application("default").bind.values())
    return inputs_from_model(
        model,
        formula,
        {k.removeprefix("calc:"): v for k, v in by_quantity.items() if f"calc:{k}" in wanted},
    )


# --- advance-ratio-from-speed and thrust-at-airspeed-from-coefficient ---------------------------


@pytest.mark.asyncio
async def test_the_advance_ratio_is_speed_over_revolutions_times_diameter() -> None:
    # 10 m/s, 150 1/s, 0.3302 m: J = 10 / (150 * 0.3302) = 0.201898...
    x = inputs_from_model(
        shipped_build().model,
        "advance-ratio-from-speed",
        {"flight-speed": 10.0, "propeller-speed": 150.0, "propeller-diameter": 0.3302},
    )
    got = await advance_ratio_from_speed(x, context())
    assert close(got["j"], 10.0 / (150.0 * 0.3302), 1e-12)
    assert advance_ratio(0.0, 150.0, 0.3302) == 0.0


@pytest.mark.asyncio
@pytest.mark.parametrize("n_prop", [0.0, -3.0])
async def test_a_propeller_that_does_not_turn_has_no_advance_ratio(n_prop: float) -> None:
    with pytest.raises(FormulaError) as caught:
        advance_ratio(5.0, n_prop, 0.3302)
    assert caught.value.code == "non_positive_value"
    assert caught.value.parameter == "n_prop"


@pytest.mark.parametrize("d_prop", [0.0, -0.33, math.nan])
def test_a_propeller_without_a_diameter_has_no_advance_ratio(d_prop: float) -> None:
    # D_prop = 0 would divide by zero, a negative or undefined diameter has no meaning
    with pytest.raises(FormulaError) as caught:
        advance_ratio(5.0, 150.0, d_prop)
    assert caught.value.code == "non_positive_value"


def test_an_undefined_propeller_speed_has_no_advance_ratio() -> None:
    with pytest.raises(FormulaError) as caught:
        advance_ratio(5.0, math.nan, 0.3302)
    assert caught.value.code == "non_positive_value"


def test_the_advance_ratio_hand_value() -> None:
    # J = V / (n D) = 10 / (150 * 0.3302) = 10 / 49.53 = 0.2018978
    assert close(advance_ratio(10.0, 150.0, 0.3302), 0.2018978, 1e-6)


@pytest.mark.asyncio
async def test_the_thrust_is_the_definition_of_the_coefficient_read_backwards() -> None:
    # C_T 0.1, rho 1.225, n 100 1/s, D 0.3302 m: T = 0.1 * 1.225 * 1e4 * 0.3302^4 = 14.5604...
    x = inputs_from_model(
        shipped_build().model,
        "thrust-at-airspeed-from-coefficient",
        {
            "thrust-coefficient": 0.1,
            "air-density": 1.225,
            "propeller-speed": 100.0,
            "propeller-diameter": 0.3302,
        },
    )
    got = await thrust_at_airspeed_from_coefficient(x, context())
    assert close(got["t"], 0.1 * 1.225 * 1e4 * 0.3302**4, 1e-12)
    assert thrust(-0.01, 1.225, 100.0, 0.3302) < 0.0  # a negative C_T is passed on, not clamped


# --- propeller-table-lookup -----------------------------------------------------------------


def test_a_point_of_the_table_is_returned_exactly() -> None:
    block = table()[4]  # 5000 rpm
    got = table_lookup(complete_components_with_table(), block["j"][7], 5000.0 / 60)
    assert got.c_t == block["ct"][7]
    assert got.c_p == block["cp"][7]


def test_between_two_points_and_two_blocks_the_lookup_is_bilinear() -> None:
    blocks = table()
    low, high = blocks[3], blocks[4]  # 4000 and 5000 rpm
    j = 0.5 * (low["j"][5] + low["j"][6])
    # by hand: the J-midpoint of the two points of each block, then the rpm quarter point
    at_low = 0.5 * (low["ct"][5] + low["ct"][6])
    at_high = reference.lerp(j, high["j"], high["ct"])
    expected = at_low + 0.25 * (at_high - at_low)
    got = table_lookup(complete_components_with_table(), j, 4250.0 / 60)
    assert close(got.c_t, expected, 1e-12)


@pytest.mark.parametrize("rpm", [999.0, 18000.5])
def test_a_speed_outside_the_blocks_is_a_declared_failure_not_an_extrapolation(rpm: float) -> None:
    with pytest.raises(FormulaError) as caught:
        table_lookup(complete_components_with_table(), 0.1, rpm / 60)
    assert caught.value.code == "outside_propeller_table"
    assert caught.value.detail["rpm_min"] == 1000.0


def test_an_advance_ratio_beyond_the_tabulated_range_is_a_declared_failure() -> None:
    j_max = table()[0]["j"][-1]
    with pytest.raises(FormulaError) as caught:
        table_lookup(complete_components_with_table(), j_max + 0.01, 1000.0 / 60)
    assert caught.value.code == "outside_propeller_table"
    assert caught.value.detail["rpm"] == 1000.0


def test_an_absent_table_is_missing_input_naming_the_field() -> None:
    with pytest.raises(FormulaError) as caught:
        table_lookup(complete_components(), 0.1, 100.0)
    assert caught.value.code == "missing_input"
    assert caught.value.detail["inputs"] == ["components.propeller.table"]
    no_propeller = Components.model_validate({"schema_version": 3})
    with pytest.raises(FormulaError) as without:
        table_lookup(no_propeller, 0.1, 100.0)
    assert without.value.detail["inputs"] == ["components.propeller"]


@pytest.mark.asyncio
async def test_the_formula_returns_both_coefficients() -> None:
    x = inputs_from_model(
        shipped_build().model,
        "propeller-table-lookup",
        {
            "components": complete_components_with_table(),
            "advance-ratio": 0.0,
            "propeller-speed": 5000.0 / 60,
        },
    )
    got = await propeller_table_lookup(x, context())
    assert got == {"c_t": table()[4]["ct"][0], "c_p": table()[4]["cp"][0]}


# --- motor-propeller-equilibrium ------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("v", [0.0, 10.0])
async def test_the_balance_matches_the_independent_solution(v: float) -> None:
    rpm, current, q_m, _ = independent_balance(v)
    x = bound_inputs("motor-propeller-equilibrium", **{"flight-speed": v})
    ctx = context_for("motor-propeller-equilibrium")
    got = await motor_propeller_equilibrium(x, ctx)
    assert close(got["n_prop"] * 60, rpm, 1e-7)
    assert close(got["q_m"], q_m, 1e-6)
    # motor torque equals propeller torque: the current follows from either side
    kv_rad = 2 * math.pi * 900.0 / 60
    assert close(got["q_m"] * kv_rad + 1.2, current, 1e-6)
    assert [w.code for w in ctx.warnings] == ["powertrain_route_winding_resistance"]
    assert ctx.warnings[0].severity == "notice"


@pytest.mark.asyncio
async def test_the_hand_values_of_the_two_operating_points() -> None:
    for v, rpm, torque in ((0.0, 8898.305, 0.62298), (10.0, 8662.075, 0.65694)):
        x = bound_inputs("motor-propeller-equilibrium", **{"flight-speed": v})
        got = await motor_propeller_equilibrium(x, context_for("motor-propeller-equilibrium"))
        assert close(got["n_prop"] * 60, rpm, 1e-6)
        assert close(got["q_m"], torque, 1e-4)


@pytest.mark.parametrize(("name", "path"), [("r_m", "rm_ohm"), ("i_0", "io_no_load_a")])
def test_route_a_and_a_default_current_are_not_built_an_absent_value_fails(
    name: str, path: str
) -> None:
    arguments: dict[str, Any] = {
        "components": complete_components_with_table(),
        "v": 0.0,
        "rho": RHO,
        "k_v": 900.0,
        "i_0": 1.2,
        "r_m": 0.082,
        "u_bat": U_BAT,
        "d_prop": D_PROP,
    }
    arguments[name] = None
    with pytest.raises(FormulaError) as caught:
        equilibrium(context_for("motor-propeller-equilibrium"), **arguments)
    assert caught.value.code == "missing_input"
    assert caught.value.parameter == name
    assert caught.value.detail["inputs"] == [f"components.motor.{path}"]


def test_a_free_run_speed_below_the_first_block_has_no_balance() -> None:
    with pytest.raises(FormulaError) as caught:
        equilibrium(
            context_for("motor-propeller-equilibrium"),
            complete_components_with_table(),
            0.0,
            RHO,
            40.0,
            1.2,
            0.082,
            U_BAT,
            D_PROP,
        )
    assert caught.value.code == "outside_propeller_table"
    assert caught.value.detail["covered_grid_points"] == 0


def test_a_motor_that_pulls_the_propeller_beyond_the_last_block_has_no_balance() -> None:
    with pytest.raises(FormulaError) as caught:
        equilibrium(
            context_for("motor-propeller-equilibrium"),
            complete_components_with_table(),
            0.0,
            RHO,
            1500.0,
            1.2,
            1e-4,
            U_BAT,
            D_PROP,
        )
    assert caught.value.code == "outside_propeller_table"


def test_the_relation_is_one_function_for_the_formula_and_the_embedders() -> None:
    assert DEFAULT_REGISTRY.relation_of("motor-propeller-equilibrium") is equilibrium
    assert DEFAULT_REGISTRY.relation_of("propeller-table-lookup") is table_lookup
    assert DEFAULT_REGISTRY.relation_of("advance-ratio-from-speed") is advance_ratio
    assert DEFAULT_REGISTRY.relation_of("thrust-at-airspeed-from-coefficient") is thrust
    assert DEFAULT_REGISTRY.relation_of("stall-speed") is None


# --- static-thrust-to-weight ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_static_thrust_to_weight_is_the_hand_thrust_over_the_weight() -> None:
    model = shipped_build().model
    formula = model.formula("static-thrust-to-weight")
    assert formula is not None
    ctx = context(tuple(formula.embeds))
    x = bound_inputs("static-thrust-to-weight")
    got = await static_thrust_to_weight(x, ctx)
    _, _, _, t_static = independent_balance(0.0)
    assert close(got["t0_w"], t_static / (3.4 * G), 1e-6)
    assert close(got["t0_w"], 32.9713 / (3.4 * G), 1e-5)  # the hand value
    # the route notice (Q-PT-6, ADR 0020): R_m is the winding only, route B
    assert [w.code for w in ctx.warnings] == ["powertrain_route_winding_resistance"]
    assert ctx.warnings[0].detail == {"route": "B"}
    assert set(ctx.embedded_requests) == set(formula.embeds)  # the embedding test (ch. 8.12)


# --- battery-mass-from-capacity -------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_battery_mass_is_the_energy_over_the_specific_energy() -> None:
    # 89.6 Wh / 140 Wh/kg = 0.64 kg
    x = inputs_from_model(
        shipped_build().model,
        "battery-mass-from-capacity",
        {"battery-energy-required": 89.6, "battery-specific-energy": 140.0},
    )
    got = await battery_mass_from_capacity(x, context())
    assert close(got["m_bat_pred"], 0.64, 1e-12)


# --- through the engine ---------------------------------------------------------------------


def aircraft(components: Components | None, **values: float) -> AircraftInput:
    document: dict[str, Any] = {
        "airplane": airplane_document(),
        "values": {"aircraft-mass": 3.4, "altitude": 0.0} | values,
    }
    if components is not None:
        document["components"] = components.model_dump()
    return AircraftInput.model_validate(document)


def by_slug(result: ComputeResult) -> dict[str, QuantityResult]:
    return {q.slug: q for q in result.quantities}


@pytest.mark.asyncio
async def test_the_chain_through_the_engine_gives_the_independent_values() -> None:
    result = await evaluate(
        shipped_build(),
        aircraft(complete_components_with_table(), **{"flight-speed": 10.0}),
        request(
            "propeller-speed",
            "motor-torque",
            "advance-ratio",
            "thrust-coefficient",
            "thrust-at-airspeed",
            "static-thrust-to-weight",
        ),
        solvers=solvers_with(),
    )
    got = by_slug(result)
    for slug, quantity in got.items():
        assert quantity.status is QuantityStatus.OK, (slug, quantity.error)
    rpm, _, q_m, t_cruise = independent_balance(10.0)
    assert close(got["propeller-speed"].value, rpm / 60, 1e-5)
    assert close(got["motor-torque"].value, q_m, 1e-5)
    assert close(got["advance-ratio"].value, 10.0 / (rpm / 60 * D_PROP), 1e-5)
    assert close(got["thrust-at-airspeed"].value, t_cruise, 1e-4)
    assert close(
        got["static-thrust-to-weight"].value, independent_balance(0.0)[3] / (3.4 * G), 1e-5
    )
    assert "powertrain_route_winding_resistance" in [
        w.code for w in got["static-thrust-to-weight"].warnings
    ]


@pytest.mark.asyncio
async def test_q30_at_zero_speed_the_thrust_node_equals_the_thrust_inside_the_static_ratio() -> (
    None
):
    result = await evaluate(
        shipped_build(),
        aircraft(complete_components_with_table(), **{"flight-speed": 0.0}),
        request("thrust-at-airspeed", "static-thrust-to-weight", "weight"),
        solvers=solvers_with(),
    )
    got = by_slug(result)
    thrust_node, ratio, weight = (
        got["thrust-at-airspeed"].value,
        got["static-thrust-to-weight"].value,
        got["weight"].value,
    )
    assert thrust_node is not None
    assert ratio is not None
    assert weight is not None
    assert close(ratio * weight, thrust_node, 1e-14)  # one relation function, one value


@pytest.mark.asyncio
async def test_a_table_less_aircraft_fails_with_the_missing_field_named() -> None:
    result = await evaluate(
        shipped_build(),
        aircraft(complete_components(), **{"flight-speed": 10.0}),
        request("thrust-coefficient", "static-thrust-to-weight"),
        solvers=solvers_with(),
    )
    got = by_slug(result)
    assert got["static-thrust-to-weight"].status is QuantityStatus.ERROR
    assert got["thrust-coefficient"].status is QuantityStatus.ERROR
    for quantity in got.values():
        assert quantity.error is not None
        assert "components.propeller.table" in quantity.error.message or quantity.error.code in {
            "upstream_failed",
            "missing_input",
        }
