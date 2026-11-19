"""``endurance-and-range`` and ``cruise-target-performance``: flight time and range from the battery power.

The aerodynamic boundary is the speed-dependent stub of ``endurance_builders`` (``D = 0.01 V^2 +
200 / V^2`` N); the drive train is checked against the separately written plain-Python model of
``powertrain_reference``. Hand values (T-Motor AT2814 KV900, APC 13x8E, 14.8 V, 74 Wh):

- ``t = 3600 E_bat / P_bat`` and ``R = V t``, the energy balance of the canon entries.
"""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.errors import FormulaError
from aero_kernel.formulas.cruise_target_performance import cruise_target_performance
from aero_kernel.formulas.endurance_and_range import endurance_and_range
from aero_kernel.schema import AircraftInput, KernelWarning, QuantityStatus
from aero_kernel.tests import powertrain_reference as reference
from aero_kernel.tests.components_builders import complete_components_with_table
from aero_kernel.tests.endurance_builders import (
    E_BAT_WH,
    MASS,
    SpeedOpti,
    bound,
    context_of,
)
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import close, solvers_with
from aero_kernel.tests.wing_builders import airplane_document

V_MP, V_MD, V_CRUISE = 10.0, 12.0, 14.0
CRUISE_APP = "at_cruise_speed_target"


def battery_power(opti: SpeedOpti, v: float) -> float:
    """The independent battery power in W at the speed: the reference drive train at the stub's drag."""
    return reference.part_load(v, opti.drag(v)).p_bat


@pytest.mark.asyncio
async def test_the_estimate_is_the_energy_over_the_battery_power_at_the_two_speeds() -> None:
    opti = SpeedOpti()
    ctx = context_of("endurance-and-range", opti)
    got = await endurance_and_range(
        bound("endurance-and-range", {"minimum-sink-speed": V_MP, "minimum-drag-speed": V_MD}),
        ctx,
    )
    p_mp, p_md = battery_power(opti, V_MP), battery_power(opti, V_MD)
    assert close(got["t_est"], 3600.0 * E_BAT_WH / p_mp, 1e-6)
    assert close(got["r_est"], 3600.0 * E_BAT_WH * V_MD / p_md, 1e-6)
    assert opti.speeds == [V_MP, V_MD]  # one level-flight solve per speed, nothing else


@pytest.mark.asyncio
async def test_one_endurance_value_by_hand() -> None:
    # at 10 m/s the stub's drag is 0.01 * 100 + 200 / 100 = 3.0 N; the reference battery power is
    # 59.11 W (plain-Python bisection on the published table): 3600 * 74 / 59.11 = 4507 s
    opti = SpeedOpti()
    got = await endurance_and_range(
        bound("endurance-and-range", {"minimum-sink-speed": V_MP, "minimum-drag-speed": V_MD}),
        context_of("endurance-and-range", opti),
    )
    assert abs(got["t_est"] - 3600.0 * 74.0 / 59.11) < 5.0


@pytest.mark.asyncio
async def test_the_estimate_embeds_the_part_load_chain_and_declares_the_route() -> None:
    ctx = context_of("endurance-and-range", SpeedOpti())
    await endurance_and_range(
        bound("endurance-and-range", {"minimum-sink-speed": V_MP, "minimum-drag-speed": V_MD}),
        ctx,
    )
    formula = shipped_build().model.formula("endurance-and-range")
    assert formula is not None
    assert set(ctx.embedded_requests) == set(formula.embeds_closure)
    assert set(formula.embeds) == {"calc:motor-propeller-part-load.default"}
    codes = [w.code for w in ctx.warnings]
    assert codes.count("powertrain_route_winding_resistance") == 1


@pytest.mark.asyncio
async def test_the_caveats_of_the_level_flight_solves_are_forwarded_once_each() -> None:
    caveat = KernelWarning.of(
        "induced_drag_viscous_factor_removed", "the kernel's drag", origin=None
    )
    ctx = context_of("endurance-and-range", SpeedOpti(warnings=(caveat,)))
    await endurance_and_range(
        bound("endurance-and-range", {"minimum-sink-speed": V_MP, "minimum-drag-speed": V_MD}),
        ctx,
    )
    assert [w.code for w in ctx.warnings].count("induced_drag_viscous_factor_removed") == 1


@pytest.mark.asyncio
async def test_a_speed_the_drive_train_cannot_hold_is_a_value_with_a_warning() -> None:
    # a stub with a large drag: the demand exceeds the full-throttle thrust at 10 m/s (T_full ~ 26 N)
    opti = SpeedOpti(a=0.0, b=2800.0)
    ctx = context_of("endurance-and-range", opti)
    got = await endurance_and_range(
        bound("endurance-and-range", {"minimum-sink-speed": V_MP, "minimum-drag-speed": V_MD}),
        ctx,
    )
    assert got["t_est"] > 0.0
    violated = [w for w in ctx.warnings if w.code == "postcondition_violated"]
    assert violated
    assert violated[0].detail["postcondition"] == "demand_within_full_throttle"


@pytest.mark.asyncio
async def test_an_absent_winding_resistance_is_missing_input_not_route_a() -> None:
    x = bound("endurance-and-range", {"minimum-sink-speed": V_MP, "minimum-drag-speed": V_MD})
    x["r_m"] = None
    with pytest.raises(FormulaError) as caught:
        await endurance_and_range(x, context_of("endurance-and-range", SpeedOpti()))
    assert (caught.value.code, caught.value.parameter) == ("missing_input", "r_m")


@pytest.mark.asyncio
async def test_a_speed_the_wing_cannot_fly_is_the_declared_failure() -> None:
    opti = SpeedOpti(min_speed=11.0)
    with pytest.raises(FormulaError) as caught:
        await endurance_and_range(
            bound("endurance-and-range", {"minimum-sink-speed": V_MP, "minimum-drag-speed": V_MD}),
            context_of("endurance-and-range", opti),
        )
    assert caught.value.code == "not_converged"


@pytest.mark.asyncio
async def test_cruise_target_performance_is_the_same_balance_at_the_target_speed() -> None:
    opti = SpeedOpti()
    ctx = context_of("cruise-target-performance", opti)
    got = await cruise_target_performance(
        bound("cruise-target-performance", {"cruise-speed-target": V_CRUISE}, CRUISE_APP), ctx
    )
    p = battery_power(opti, V_CRUISE)
    assert close(got["t_cruise"], 3600.0 * E_BAT_WH / p, 1e-6)
    assert close(got["r_cruise"], V_CRUISE * got["t_cruise"], 1e-12)
    assert opti.speeds == [V_CRUISE]
    formula = shipped_build().model.formula("cruise-target-performance")
    assert formula is not None
    assert set(ctx.embedded_requests) == set(formula.embeds_closure)


@pytest.mark.asyncio
async def test_cruise_target_beyond_full_throttle_warns_and_still_gives_the_value() -> None:
    ctx = context_of("cruise-target-performance", SpeedOpti(a=0.0, b=2800.0))
    got = await cruise_target_performance(
        bound("cruise-target-performance", {"cruise-speed-target": V_MP}, CRUISE_APP), ctx
    )
    assert got["t_cruise"] > 0.0
    assert "postcondition_violated" in [w.code for w in ctx.warnings]


@pytest.mark.asyncio
async def test_cruise_target_with_an_absent_no_load_current_is_missing_input() -> None:
    x = bound("cruise-target-performance", {"cruise-speed-target": V_CRUISE}, CRUISE_APP)
    x["i_0"] = None
    with pytest.raises(FormulaError) as caught:
        await cruise_target_performance(x, context_of("cruise-target-performance", SpeedOpti()))
    assert (caught.value.code, caught.value.parameter) == ("missing_input", "i_0")


@pytest.mark.asyncio
async def test_through_the_engine_an_embedder_reaches_a_relation_two_levels_down() -> None:
    """The engine hands out the embeds closure: ``cruise-target-performance`` embeds only the part-load
    relation, which reaches the equilibrium (and through it the table lookup) through the same context;
    without the closure the call would end as ``internal`` (a ``KeyError``). A cycle in the closure is
    refused by the importer (``test_importer_rules``: 'is in its own embeds closure (a cycle)')."""
    from aero_kernel.engine import evaluate

    aircraft = AircraftInput.model_validate(
        {
            "airplane": airplane_document(),
            "components": complete_components_with_table().model_dump(),
            "values": {
                "aircraft-mass": MASS,
                "altitude": 0.0,
                "cruise-speed-target": V_CRUISE,
            },
        }
    )
    result = await evaluate(
        shipped_build(),
        aircraft,
        request("endurance-at-cruise-target", "range-at-cruise-target"),
        solvers=solvers_with(opti=SpeedOpti()),
    )
    got = {q.slug: q for q in result.quantities}
    assert all(q.status is QuantityStatus.OK for q in got.values()), got
    formula = shipped_build().model.formula("cruise-target-performance")
    assert formula is not None
    assert formula.embeds == ("calc:motor-propeller-part-load.default",)
    assert "calc:motor-propeller-equilibrium.default" in formula.embeds_closure
    assert got["endurance-at-cruise-target"].unit == "s"
    assert got["range-at-cruise-target"].unit == "m"


def test_a_drive_train_that_draws_no_power_gives_no_flight_time() -> None:
    from aero_kernel.formulas.motor_propeller_part_load import energy_over_power

    with pytest.raises(FormulaError) as caught:
        energy_over_power(74.0, 0.0, 10.0)
    assert caught.value.code == "non_positive_battery_power"
    assert close(energy_over_power(74.0, 60.0, 10.0), 3600.0 * 74.0 / 60.0, 1e-12)
