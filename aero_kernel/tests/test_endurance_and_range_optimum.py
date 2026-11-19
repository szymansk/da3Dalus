"""``endurance-and-range-optimum``: the greatest flight time and range, and its declared domain.

The aerodynamic boundary is the speed-dependent stub of ``endurance_builders`` (``D = 0.01 V^2 +
200 / V^2`` N, minimum drag at 11.9 m/s); the drive train is checked against the separately written
plain-Python model of ``powertrain_reference``. The cross-check is a brute-force scan over the speed
with that independent model: the optimiser's value must equal the scan's minimum to the accuracy the
canon's tolerance implies (second order in the speed error).
"""

from typing import Any

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.errors import FormulaError
from aero_kernel.formulas.endurance_and_range import endurance_and_range
from aero_kernel.formulas.endurance_and_range_optimum import endurance_and_range_optimum
from aero_kernel.schema import KernelWarning
from aero_kernel.tests import powertrain_reference as reference
from aero_kernel.tests.endurance_builders import E_BAT_WH, SpeedOpti, bound, context_of
from aero_kernel.tests.formula_builders import close

V_S = 6.0
SLUG = "endurance-and-range-optimum"


def optimum_inputs(v_s: float = V_S, **extra: float) -> dict[str, Any]:
    return bound(SLUG, {"stall-speed": v_s, **extra})


def brute_force(opti: SpeedOpti, lowest: float, highest: float = 20.0) -> tuple[float, float]:
    """The least battery power and least power over speed of the independent model, step 0.05 m/s."""
    powers: list[tuple[float, float]] = []
    v = lowest
    while v <= highest:
        powers.append((v, reference.part_load(v, opti.drag(v)).p_bat))
        v += 0.05
    return min(p for _, p in powers), min(p / v for v, p in powers)


@pytest.mark.asyncio
async def test_the_optimum_equals_the_brute_force_scan_of_the_independent_model() -> None:
    opti = SpeedOpti()
    got = await endurance_and_range_optimum(optimum_inputs(), context_of(SLUG, opti))
    p_min, e_per_m_min = brute_force(opti, V_S)
    assert close(got["t_max"], 3600.0 * E_BAT_WH / p_min, 2e-4)
    assert close(got["r_max"], 3600.0 * E_BAT_WH / e_per_m_min, 2e-4)


@pytest.mark.asyncio
async def test_the_estimate_at_a_speed_inside_the_domain_does_not_exceed_the_optimum() -> None:
    opti = SpeedOpti()
    estimate = await endurance_and_range(
        bound("endurance-and-range", {"minimum-sink-speed": 10.0, "minimum-drag-speed": 12.0}),
        context_of("endurance-and-range", opti),
    )
    best = await endurance_and_range_optimum(optimum_inputs(), context_of(SLUG, opti))
    assert estimate["t_est"] <= best["t_max"] * (1.0 + 1e-9)
    assert estimate["r_est"] <= best["r_max"] * (1.0 + 1e-9)


@pytest.mark.asyncio
async def test_an_interior_optimum_is_not_reported_as_a_bound_and_the_route_is_declared() -> None:
    ctx = context_of(SLUG, SpeedOpti())
    await endurance_and_range_optimum(optimum_inputs(), ctx)
    codes = [w.code for w in ctx.warnings]
    assert "optimum_at_domain_bound" not in codes
    assert codes.count("powertrain_route_winding_resistance") == 1


@pytest.mark.asyncio
async def test_every_speed_is_evaluated_once_whichever_search_asks() -> None:
    opti = SpeedOpti()
    await endurance_and_range_optimum(optimum_inputs(), context_of(SLUG, opti))
    assert len(opti.speeds) == len(set(opti.speeds))
    assert 20 <= len(opti.speeds) <= 45  # the scan plus two golden-section refinements


@pytest.mark.asyncio
async def test_the_optimum_embeds_only_the_part_load_chain_and_reads_the_stall_speed() -> None:
    ctx = context_of(SLUG, SpeedOpti())
    await endurance_and_range_optimum(optimum_inputs(), ctx)
    formula = shipped_build().model.formula(SLUG)
    assert formula is not None
    assert set(formula.embeds) == {"calc:motor-propeller-part-load.default"}
    assert set(ctx.embedded_requests) == set(formula.embeds_closure)
    assert formula.inputs["v_s"] == "calc:stall-speed"


@pytest.mark.asyncio
async def test_a_stall_speed_above_the_best_speeds_puts_the_optimum_on_the_stall_bound() -> None:
    opti = SpeedOpti()
    ctx = context_of(SLUG, opti)
    got = await endurance_and_range_optimum(optimum_inputs(v_s=14.0), ctx)
    bounds = [w for w in ctx.warnings if w.code == "optimum_at_domain_bound"]
    assert {str(w.detail["objective"]) for w in bounds} == {"endurance", "range"}
    assert all(w.detail["bound"] == "stall_speed" for w in bounds)
    assert all(w.detail["edge_v_ms"] == 14.0 for w in bounds)
    p_stall = reference.part_load(14.0, opti.drag(14.0)).p_bat
    assert close(got["t_max"], 3600.0 * E_BAT_WH / p_stall, 1e-6)
    assert close(got["r_max"], 3600.0 * E_BAT_WH * 14.0 / p_stall, 1e-6)


@pytest.mark.asyncio
async def test_speeds_the_wing_cannot_fly_start_the_domain_above_them() -> None:
    # the level-flight solve fails below 11 m/s: the domain starts there, and the best speeds (10 and
    # 12 m/s) put the endurance optimum on that edge
    ctx = context_of(SLUG, SpeedOpti(min_speed=11.0))
    await endurance_and_range_optimum(optimum_inputs(), ctx)
    bounds = {w.detail["objective"]: w for w in ctx.warnings if w.code == "optimum_at_domain_bound"}
    assert bounds["endurance"].detail["bound"] == "level_flight_solution"
    assert 10.0 < float(str(bounds["endurance"].detail["v_ms"])) < 11.2


@pytest.mark.asyncio
async def test_no_speed_inside_the_domain_is_a_declared_failure() -> None:
    with pytest.raises(FormulaError) as caught:
        await endurance_and_range_optimum(
            optimum_inputs(), context_of(SLUG, SpeedOpti(min_speed=1.0e6))
        )
    assert caught.value.code == "no_level_flight_speed"


@pytest.mark.asyncio
async def test_the_table_limit_ends_the_domain_and_is_named_where_it_binds() -> None:
    # D = 100 / V^2 falls with the speed, so the battery power keeps falling until the drag drops
    # below the thrust of the table's lowest rpm block (the table has no balance there, about 8.3
    # m/s here): the optimum lies on that edge
    ctx = context_of(SLUG, SpeedOpti(a=0.0, b=100.0))
    await endurance_and_range_optimum(optimum_inputs(), ctx)
    bounds = [w for w in ctx.warnings if w.code == "optimum_at_domain_bound"]
    assert bounds
    assert all(w.detail["bound"] == "propeller_table" for w in bounds)


@pytest.mark.asyncio
async def test_the_mach_limit_of_the_regime_ends_the_scan() -> None:
    # a speed of sound of 30 m/s makes the Mach limit 0.3 * 30 = 9 m/s: nothing above is searched
    opti = SpeedOpti()
    ctx = context_of(SLUG, opti)
    await endurance_and_range_optimum(optimum_inputs(**{"speed-of-sound": 30.0}), ctx)
    assert max(opti.speeds) <= 9.0
    bounds = [w for w in ctx.warnings if w.code == "optimum_at_domain_bound"]
    assert bounds
    assert all(w.detail["bound"] == "mach_limit" for w in bounds)


@pytest.mark.asyncio
async def test_a_failure_that_is_not_about_the_speed_passes_unchanged() -> None:
    x = optimum_inputs()
    x["r_m"] = None
    with pytest.raises(FormulaError) as caught:
        await endurance_and_range_optimum(x, context_of(SLUG, SpeedOpti()))
    assert (caught.value.code, caught.value.parameter) == ("missing_input", "r_m")


@pytest.mark.asyncio
async def test_only_the_caveats_of_the_two_answer_speeds_are_forwarded() -> None:
    caveat = KernelWarning.of(
        "induced_drag_viscous_factor_removed", "the kernel's drag", origin=None
    )
    ctx = context_of(SLUG, SpeedOpti(warnings=(caveat,)))
    await endurance_and_range_optimum(optimum_inputs(), ctx)
    assert [w.code for w in ctx.warnings].count("induced_drag_viscous_factor_removed") == 1
