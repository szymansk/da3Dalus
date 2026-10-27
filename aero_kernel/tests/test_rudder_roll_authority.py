"""rudder-roll-authority: V_V B at V_md and V_mp, per neutral-point world (fast tier)."""

import pytest
from aero_kernel.evaluation import RuleStatus, evaluate_rules, shipped_rule_table
from aero_kernel.formulas.rudder_roll_authority import rudder_roll_authority
from aero_kernel.graph import facts_from_geometry
from aero_kernel.schema import QuantityStatus
from aero_kernel.tests.chain_builders import WORLD_X_NP, document, fin, run_chain
from aero_kernel.tests.formula_builders import StubAtmosphere, StubGeometry, close, context_with
from aero_kernel.tests.test_turn_sideslip import with_aileron

pytestmark = pytest.mark.asyncio

POINTS = ("md", "mp")


async def test_the_formula_is_the_product_of_the_tail_volume_and_the_spiral_parameter() -> None:
    context = context_with(StubAtmosphere({}), geometry=StubGeometry())
    found = await rudder_roll_authority(
        {"v_v": 0.04, "b_spiral_md": 2.0, "b_spiral_mp": 1.0}, context
    )
    assert close(found["rra_md"], 0.08, 1e-12)
    assert close(found["rra_mp"], 0.04, 1e-12)


@pytest.mark.parametrize("point", POINTS)
async def test_each_world_multiplies_its_own_factors_at_each_speed(point: str) -> None:
    slugs = ("vertical-tail-volume", f"spiral-parameter-{point}", f"rudder-roll-authority-{point}")
    run = await run_chain(*slugs)
    volume, spiral, product = (run.quantity(slug) for slug in slugs)
    for quantity in (volume, spiral, product):
        assert quantity.status is QuantityStatus.OK, quantity
        assert quantity.interval is not None
        assert set(quantity.interval.worlds) == set(WORLD_X_NP)
    assert product.unit == "1"
    for world in WORLD_X_NP:
        expected = volume.interval.worlds[world] * spiral.interval.worlds[world]  # type: ignore[union-attr]
        assert close(product.interval.worlds[world], expected, 1e-12), world  # type: ignore[union-attr]


async def test_with_ailerons_the_rudder_roll_authority_does_not_apply() -> None:
    run = await run_chain("rudder-roll-authority-mp", airplane=with_aileron())
    quantity = run.quantity("rudder-roll-authority-mp")
    assert quantity.status is QuantityStatus.NOT_APPLICABLE
    assert quantity.interval is None


async def test_the_drela_rule_judges_the_minimum_sink_value_end_to_end() -> None:
    plane = document(fin())
    run = await run_chain("rudder-roll-authority-mp", airplane=plane)
    judged = evaluate_rules(shipped_rule_table(), run.result, facts_from_geometry(plane))
    (verdict,) = [v for v in judged if v.rule_id == "rudder-roll-authority"]
    assert verdict.quantity == "rudder-roll-authority-mp"
    assert verdict.status is not RuleStatus.NOT_AVAILABLE
    assert verdict.interval is not None
    assert set(verdict.interval.worlds) == set(WORLD_X_NP)
