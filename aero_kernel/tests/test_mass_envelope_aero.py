"""``mass-envelope`` with the real AeroBuildup on the Avistar Elite (aero tier, gh-1420).

The drive train is the Avistar's: AXI 4120/14 (Kv, R_m, I_0 and efficiency published), APC 13x8E (its published
performance table), the 4S pack; the maximum power, the pack mass, the C-rate and the cell voltage are the marked
test values of ``components_builders`` (they stand in for unpublished motor data). The assertions are the
consistency of the formula with the other formulas at the masses it names, not a validation: the paper
publishes no mass envelope of this aircraft (``reference/avistar_elite/MEASUREMENTS.md``), and none is known to
the project for any RC aircraft. Cost on an Apple laptop: about 45 s for the two roots.
"""

import pytest
from aero_kernel.build import shipped_build
from aero_kernel.engine import evaluate
from aero_kernel.schema import AircraftInput, QuantityResult, QuantityStatus
from aero_kernel.tests.engine_builders import request
from aero_kernel.tests.formula_builders import solvers_with
from aero_kernel.tests.test_powered_performance_aero import avistar, codes, value

pytestmark = [pytest.mark.aero, pytest.mark.asyncio]

CURRENT_KG = 3.70


async def run(aircraft: AircraftInput, *slugs: str) -> dict[str, QuantityResult]:
    """The quantities with the long runs included (``mass-envelope`` is cost class ``minutes``, K28)."""
    result = await evaluate(
        shipped_build(), aircraft, request(*slugs, long_runs=True), solvers=solvers_with()
    )
    return {q.slug: q for q in result.quantities}


# the Avistar Elite as measured in the paper


async def test_the_two_largest_masses_end_the_state_they_name_and_the_curves_are_not_requestable() -> (
    None
):
    got = await run(
        avistar(),
        "max-mass-level-flight",
        "max-mass-lift-off",
        "speed-range-over-mass",
        "climb-rate-over-mass",
    )
    m_level, m_to = value(got, "max-mass-level-flight"), value(got, "max-mass-lift-off")
    assert CURRENT_KG < m_to < m_level  # the overloaded bomber: it cruises, it cannot climb out
    assert "powertrain_route_winding_resistance" in codes(got, "max-mass-level-flight")
    for slug in ("speed-range-over-mass", "climb-rate-over-mass"):  # ARCHITECTURE ch. 8.3
        error = got[slug].error
        assert got[slug].status is QuantityStatus.ERROR
        assert error is not None
        assert error.code == "non_scalar_result"

    # the hand check, with the other formulas: a little below the largest level-flight mass the airplane
    # still climbs (a little), a little above it nothing climbs and level flight has no speed
    below = await run(avistar({"aircraft-mass": 0.995 * m_level}), "max-rate-of-climb")
    assert 0.0 < value(below, "max-rate-of-climb") < 0.5  # m/s: the climb has almost closed
    above = await run(avistar({"aircraft-mass": 1.005 * m_level}), "max-rate-of-climb")
    assert above["max-rate-of-climb"].status is QuantityStatus.ERROR
    assert above["max-rate-of-climb"].error is not None
    assert above["max-rate-of-climb"].error.code == "no_feasible_speed"
