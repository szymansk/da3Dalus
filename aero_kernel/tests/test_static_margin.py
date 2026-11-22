"""static-margin: SM = (x_NP - x_CG) / c_MAC against literal hand values (fast tier, P2-F14)."""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.formulas.static_margin import static_margin
from aero_kernel.tests.formula_builders import StubAtmosphere, context_with, inputs_from_model, near

pytestmark = pytest.mark.asyncio


def margin_inputs(x_cg: float) -> dict[str, float]:
    """The ``x`` of static-margin from the canon's binding: NP 0.14 m, c_MAC 0.20 m, the given CG."""
    return {
        **inputs_from_model(
            shipped_build().model,
            "static-margin",
            {
                "neutral-point": 0.14,
                "centre-of-gravity-measured": x_cg,
                "mean-aerodynamic-chord": 0.20,
            },
        )
    }  # type: ignore[dict-item]


async def test_a_cg_ahead_of_the_neutral_point_has_a_positive_margin() -> None:
    """(0.14 - 0.12) / 0.20 = 0.10: the neutral point lies 10 % of a chord behind the CG."""
    found = await static_margin(margin_inputs(0.12), context_with(StubAtmosphere({})))
    assert set(found) == {"sm"}
    assert near(found["sm"], 0.10, 1e-12)


async def test_a_cg_behind_the_neutral_point_is_an_unstable_number_not_an_error() -> None:
    """(0.14 - 0.16) / 0.20 = -0.10: the formula computes, it does not judge (canon A10)."""
    found = await static_margin(margin_inputs(0.16), context_with(StubAtmosphere({})))
    assert near(found["sm"], -0.10, 1e-12)


async def test_a_cg_on_the_neutral_point_is_a_zero_margin() -> None:
    found = await static_margin(margin_inputs(0.14), context_with(StubAtmosphere({})))
    assert found["sm"] == 0.0
