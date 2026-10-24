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


# The driven mesh (wing split at the hinge, front 12 / aft 8 chordwise, 24 strips per half span in one
# sine-to-tip distribution with the device ends exact) against the expert's independent resampling of
# the same geometry at C_L 0.7, delta 20 deg, core ratio 0.25, run with the kernel's own commands: the
# trimmed steady roll (`a c 0.7`, `r rm 0`, `d1 d1 20`), which is the canon's definition. His numbers
# for 24 / 48 / 96 strips are BRYAN .2866 / .2860 / .2862 and JAGUAR .2792 / .2799 / .2799 (flat; the
# sine-to-tip spacing removes the O(1/N) tip error of the roll damping, which uniform strips carry:
# Richardson over uniform runs gives .2864 / .2801). His first set, .2800 and .2744, was the linearised
# -Cld01 * delta / Clp of a coarser, uniform mesh; this reference corrects a wrong definition. Reproduction of an
# independent writer, not a golden (S6): abs 3e-4. Caveat: Clp and Cld01 each still move about 0.5 % in
# opposite directions between 48 and 96 strips, so only the ratio p is converged, never quote them.
INDEPENDENT = {FleetMember.BRYAN: 0.2866, FleetMember.JAGUAR: 0.2792}
CONVERGENCE_CODES = {"avl_mesh_not_converged", "avl_refinement_unchecked"}


@pytest.mark.parametrize("member", list(FleetMember))
async def test_the_driven_mesh_reproduces_the_independent_roll_and_passes_its_refinement_check(
    member: FleetMember,
) -> None:
    airplane = AirplaneGeometry.model_validate(reference_document(member))
    async with SolverRuntime(max_workers=1) as runtime:
        found = await AvlAdapter(runtime).steady_roll(airplane, 0.7, 20.0)
    assert math.isclose(found.p_hat, INDEPENDENT[member], abs_tol=3e-4)
    assert not CONVERGENCE_CODES & {w.code for w in found.warnings}
