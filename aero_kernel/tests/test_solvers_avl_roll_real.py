"""The AVL steady roll against the real AVL binary (aero tier); fleet goldens are in S6's module."""

import math

import pytest
from aero_kernel.runtime import SolverRuntime
from aero_kernel.solvers.avl import AvlAdapter, AvlRoll
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
