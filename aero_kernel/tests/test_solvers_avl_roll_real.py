"""The AVL steady roll against the real AVL binary (aero tier); fleet goldens are in S6's module."""

import asyncio
import math
import re
import sys
from pathlib import Path

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


# The kernel's AVL roll against the independent reference of
#     poetry run python scripts/sim_export/crrcsim/avl_roll_reference.py --strips 96
# (C_L 0.7, delta 20 deg, core ratio 0.25, trimmed steady roll). That script imports nothing from
# aero_kernel: it reads the fleet's JSON and contour files itself, builds its own sine-to-tip stations
# with the aileron ends exact, splits the wing at the hinge and writes its own file. Its values at 24 /
# 48 / 96 strips are BRYAN 0.28644 / 0.28625 / 0.28679 and JAGUAR 0.27928 / 0.28042 / 0.28077, flat:
# the sine-to-tip spacing removes the O(1/N) tip error of the roll damping that uniform strips carry
# (Richardson over uniform runs: 0.2864 / 0.2801). The constants are the 96-strip values. The first
# reference numbers, 0.2800 and 0.2744, were the linearised -Cld01 * delta / Clp of a coarser uniform
# mesh; this reference corrects a wrong definition. Tolerance rel 1 %, fixed before the measurement:
# a miss means looking at the writer, never at the tolerance. Caveat: Clp and Cld01 each still move
# about 0.5 % in opposite directions between 48 and 96 strips, so only the ratio is converged.
INDEPENDENT = {FleetMember.BRYAN: 0.28679, FleetMember.JAGUAR: 0.28077}
CONVERGENCE_CODES = {"avl_mesh_not_converged", "avl_refinement_unchecked"}


@pytest.mark.parametrize("member", list(FleetMember))
async def test_the_driven_mesh_agrees_with_the_independent_reference_and_passes_its_refinement_check(
    member: FleetMember,
) -> None:
    airplane = AirplaneGeometry.model_validate(reference_document(member))
    async with SolverRuntime(max_workers=1) as runtime:
        found = await AvlAdapter(runtime).steady_roll(airplane, 0.7, 20.0)
    assert math.isclose(found.p_hat, INDEPENDENT[member], rel_tol=1e-2)
    assert not CONVERGENCE_CODES & {w.code for w in found.warnings}


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/sim_export/crrcsim/avl_roll_reference.py"


async def test_the_constants_are_what_the_reference_script_prints() -> None:
    """The constants above cannot drift from their source: run the script (96 strips) and compare to
    the printed five decimals."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        str(SCRIPT),
        "--strips",
        "96",
        stdout=asyncio.subprocess.PIPE,
    )
    async with asyncio.timeout(600):
        stdout, _ = await process.communicate()
    assert process.returncode == 0
    found = {
        match.group(1): float(match.group(2))
        for match in re.finditer(r"^(BRYAN|JAGUAR) 96:(\d\.\d+)$", stdout.decode(), re.MULTILINE)
    }
    assert set(found) == {"BRYAN", "JAGUAR"}
    for member in FleetMember:
        assert math.isclose(found[member.name], INDEPENDENT[member], abs_tol=1e-5), member
