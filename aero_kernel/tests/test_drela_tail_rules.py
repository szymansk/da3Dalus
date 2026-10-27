"""The Drela rules ``horizontal-tail-volume`` and ``turn-sideslip`` judge the kernel's values end to end (fast tier)."""

from typing import Any

import pytest
from aero_kernel.evaluation import RuleStatus, RuleVerdict, evaluate_rules, shipped_rule_table
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.graph import facts_from_geometry
from aero_kernel.tests.chain_builders import WORLD_X_NP, document, fin, run_chain
from aero_kernel.tests.test_turn_sideslip import hand_values, with_aileron

pytestmark = pytest.mark.asyncio

TAIL_RULES = ("horizontal-tail-volume", "turn-sideslip")


async def verdicts_of(airplane: AirplaneGeometry) -> dict[str, RuleVerdict]:
    run = await run_chain(*TAIL_RULES, airplane=airplane)
    judged = evaluate_rules(shipped_rule_table(), run.result, facts_from_geometry(airplane))
    return {verdict.rule_id: verdict for verdict in judged if verdict.rule_id in TAIL_RULES}


async def test_both_quantities_are_evaluated_end_to_end_on_an_aircraft_without_ailerons() -> None:
    found = await verdicts_of(document(fin()))
    volume, sideslip = found["horizontal-tail-volume"], found["turn-sideslip"]
    assert volume.status is RuleStatus.INSIDE
    assert (volume.band.min, volume.band.max) == (0.30, 0.60)
    assert volume.interval is not None
    assert sideslip.status is RuleStatus.INSIDE
    assert sideslip.level == "within-typical-limit-range"
    _, expected_deg = hand_values()
    assert sideslip.interval is not None
    assert set(sideslip.interval.worlds) == set(WORLD_X_NP)
    assert all(abs(value - expected_deg) < 1e-9 for value in sideslip.interval.worlds.values())


async def test_with_ailerons_the_turn_sideslip_rule_does_not_apply_but_the_volume_is_judged() -> (
    None
):
    found = await verdicts_of(with_aileron())
    assert found["turn-sideslip"].status is RuleStatus.NOT_APPLICABLE
    assert found["horizontal-tail-volume"].status is RuleStatus.INSIDE


async def test_without_a_horizontal_tail_the_volume_rule_does_not_apply() -> None:
    plane: Any = document(fin(), tail=False)
    found = await verdicts_of(plane)
    assert found["horizontal-tail-volume"].status is RuleStatus.NOT_APPLICABLE
