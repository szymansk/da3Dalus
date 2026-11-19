"""``mass-envelope`` with the real AeroBuildup on the Avistar Elite (aero tier, gh-1420).

The drive train is the Avistar's: AXI 4120/14 (Kv, R_m, I_0 and efficiency published), APC 13x8E (its published
performance table), the 4S pack; the maximum power, the pack mass, the C-rate and the cell voltage are the marked
test values of ``components_builders`` (they stand in for unpublished motor data). The assertions are the
consistency of the formula with the other formulas at the masses it names, not a validation: the paper
publishes no mass envelope of this aircraft (``reference/avistar_elite/MEASUREMENTS.md``), and none is known to
the project for any RC aircraft. Cost on an Apple laptop: about 3.5 minutes (two roots and six curve samples).
"""

import math

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


async def test_the_two_largest_masses_end_the_state_they_name_and_the_climb_curve_is_the_formulas_climb() -> (
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
    # the climb curve is a result (gh-1424): the samples are the climb search of best-rate-of-climb itself
    climb = got["climb-rate-over-mass"].curve
    assert got["climb-rate-over-mass"].status is QuantityStatus.OK
    assert climb is not None
    assert (climb.x_quantity, climb.x_unit) == ("aircraft-mass", "kg")
    assert climb.x[0] == CURRENT_KG
    assert math.isclose(
        climb.x[-1], m_level, rel_tol=1e-12
    )  # closed by the root, where no climb is left
    assert climb.y[-1] == 0.0
    assert all(
        a > b for a, b in zip(climb.y, climb.y[1:], strict=False)
    )  # the climb falls with the mass
    at_current = await run(avistar(), "max-rate-of-climb")
    assert math.isclose(climb.y[0], value(at_current, "max-rate-of-climb"), rel_tol=1e-9)
    # a curve_pair is not a result: the speed range is computed and not requestable
    speed_range = got["speed-range-over-mass"]
    assert speed_range.status is QuantityStatus.ERROR
    assert speed_range.error is not None
    assert speed_range.error.code == "non_scalar_result"

    # the hand check, with the other formulas: a little below the largest level-flight mass the airplane
    # still climbs (a little), above it nothing climbs and level flight has no speed. Above is 2 percent,
    # not 0.5: at 1.005 times the root the level-point solve sits on the lift peak and gives either the wing
    # limit or a plain not_converged depending on the 7th digit of the mass (bug #1426, reproduced; not
    # warm start or order), so the check keeps clear of that knife edge until the defect is fixed.
    below = await run(avistar({"aircraft-mass": 0.995 * m_level}), "max-rate-of-climb")
    assert 0.0 < value(below, "max-rate-of-climb") < 0.5  # m/s: the climb has almost closed
    above = await run(avistar({"aircraft-mass": 1.02 * m_level}), "max-rate-of-climb")
    assert above["max-rate-of-climb"].status is QuantityStatus.ERROR
    assert above["max-rate-of-climb"].error is not None
    assert above["max-rate-of-climb"].error.code == "no_feasible_speed"
