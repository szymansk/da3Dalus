"""The AVL steady roll against the real AVL binary (aero tier); fleet goldens are in S6's module."""

import math

import pytest
from aero_kernel.geometry import AirplaneGeometry
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.avl import AvlAdapter, AvlRoll
from aero_kernel.tests.reference_fleet import FleetMember, reference_document
from aero_kernel.tests.test_solvers_opti_roll_real import aileron_trainer

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]


async def roll(delta: float, cl: float = 0.6) -> AvlRoll:
    async with SolverRuntime(max_workers=1) as runtime:
        return await AvlAdapter(runtime).steady_roll(aileron_trainer(), cl, delta)


async def test_a_positive_command_rolls_right_and_the_negative_one_mirrors_it() -> None:
    """The sign follows the side as written, AVL reports stability-axis p'b/2V: +20 deg gives a
    positive roll, -20 deg exactly the negative (AVL prints five decimals)."""
    plus, minus = await roll(20.0), await roll(-20.0)
    assert plus.p_hat > 0.0
    assert math.isclose(minus.p_hat, -plus.p_hat, abs_tol=1e-4)


async def test_a_zero_command_gives_zero_roll() -> None:
    found = await roll(0.0)
    assert math.isclose(found.p_hat, 0.0, abs_tol=1e-4)
    assert "avl_roll_rate_beyond_range" not in [w.code for w in found.warnings]


# The split-at-hinge mesh (front 12, aft 8, Nspan 24) against the expert's split file at C_L 0.7, delta
# 20 deg, core ratio 0.25 (AVL prints five decimals), run with the kernel's own commands: the trimmed
# steady roll (`a c 0.7`, `r rm 0`, `d1 d1 20`), which is the canon's definition. The expert's first
# numbers, 0.2800 and 0.2744, are the linearisation -Cld01 * delta / Clp at p = 0; AVL's forces are not
# exactly linear in p and alpha re-trims, so the trimmed values are 0.2793 and 0.2738 (0.23 % lower;
# the unsplit file shows the same offset). The single full-chord surface at 10 chordwise vortices gave
# 0.2623 and 0.2478. Reproduction of the expert's file, not a golden (S6); the spanwise convergence of
# the refined check is a separate study (AVL_CONVERGENCE.md).
SPLIT_TRIMMED = {FleetMember.BRYAN: 0.27932, FleetMember.JAGUAR: 0.27376}


@pytest.mark.parametrize("member", list(FleetMember))
async def test_the_split_mesh_reproduces_the_experts_trimmed_roll(member: FleetMember) -> None:
    airplane = AirplaneGeometry.model_validate(reference_document(member))
    async with SolverRuntime(max_workers=1) as runtime:
        found = await AvlAdapter(runtime).steady_roll(airplane, 0.7, 20.0)
    assert math.isclose(found.p_hat, SPLIT_TRIMMED[member], abs_tol=2e-5)
