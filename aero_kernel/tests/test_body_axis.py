"""The straight body axis AeroBuildup sees (#1358, canon rule ``fuselage-axis-straightened``)."""

import math
from typing import Any

import numpy as np
from aero_kernel.body_axis import aerobuildup_bodies, straight_axis
from aero_kernel.config import config
from aero_kernel.geometry import Fuselage
from aero_kernel.solver_bodies import solver_bodies
from aero_kernel.tests.formula_builders import all_near, near
from aero_kernel.tests.test_solver_bodies import airplane, body, canopy, fuselage_box, section

TOLERANCE = 1e-9


def fuselage(sections: list[dict[str, Any]], **fields: Any) -> Fuselage:
    return Fuselage.model_validate({"name": "Rumpf", **body(sections), **fields})


def stepped() -> Fuselage:
    """A body whose centre steps up by 0.03 m between two close sections (the CHEKKER kink)."""
    return fuselage(
        [
            section(0.0, 0.0, 0.0, z=0.0),
            section(0.20, 0.05, 0.04, n=2.5, n_lower=3.0, y=0.001, z=0.0),
            section(0.22, 0.05, 0.05, z=0.03),
            section(0.80, 0.02, 0.02, z=0.03),
        ]
    )


def least_squares(x: list[float], z: list[float]) -> list[float]:
    slope, intercept = np.polyfit(x, z, 1)
    return [slope * x_i + intercept for x_i in x]


def test_every_centre_moves_in_z_onto_the_least_squares_line_through_all_centres() -> None:
    original = stepped()
    found, straightening = straight_axis(original, TOLERANCE)
    assert straightening is not None
    x = [s.xyz[0] for s in original.x_secs]
    expected = least_squares(x, [s.xyz[2] for s in original.x_secs])
    assert all_near([s.xyz[2] for s in found.x_secs], expected, tol=1e-15)


def test_nothing_but_the_z_of_the_centres_changes() -> None:
    original = stepped()
    found, _ = straight_axis(original, TOLERANCE)
    assert found.name == original.name
    for before, after in zip(original.x_secs, found.x_secs, strict=True):
        assert after.xyz[:2] == before.xyz[:2]
        assert (after.a, after.b, after.n, after.n_lower) == (
            before.a,
            before.b,
            before.n,
            before.n_lower,
        )
        assert after.contour == before.contour


def test_the_straightening_reports_the_largest_shift_and_where_it_is() -> None:
    original = stepped()
    found, straightening = straight_axis(original, TOLERANCE)
    assert straightening is not None
    shifts = [abs(a.xyz[2] - b.xyz[2]) for a, b in zip(found.x_secs, original.x_secs, strict=True)]
    index = shifts.index(max(shifts))
    assert straightening.fuselage == "Rumpf"
    assert straightening.sections == 4
    assert near(straightening.largest_shift, max(shifts), tol=1e-15)
    assert straightening.section_index == index
    assert straightening.x == original.x_secs[index].xyz[0]


def test_a_body_whose_centres_are_on_a_line_is_unchanged_and_not_declared() -> None:
    inclined = fuselage([section(x, 0.03, 0.03, z=0.1 * x - 0.02) for x in (0.0, 0.3, 0.7, 1.1)])
    found, straightening = straight_axis(inclined, TOLERANCE)
    assert found is inclined
    assert straightening is None


def test_a_level_body_is_unchanged() -> None:
    level = fuselage([section(x, 0.03, 0.03, z=0.02) for x in (0.0, 0.5, 1.0)])
    assert straight_axis(level, TOLERANCE) == (level, None)


def test_a_body_with_two_sections_is_on_its_line() -> None:
    two = fuselage([section(0.0, 0.03, 0.03, z=0.0), section(0.4, 0.03, 0.03, z=0.07)])
    assert straight_axis(two, TOLERANCE) == (two, None)


def test_a_body_with_one_section_is_unchanged() -> None:
    one = fuselage([section(0.0, 0.03, 0.03, z=0.05)])
    assert straight_axis(one, TOLERANCE) == (one, None)


def test_a_shift_within_the_tolerance_is_no_straightening() -> None:
    almost = fuselage(
        [section(x, 0.03, 0.03, z=z) for x, z in ((0.0, 0.0), (0.5, 1e-10), (1.0, 0.0))]
    )
    assert straight_axis(almost, TOLERANCE) == (almost, None)
    found, straightening = straight_axis(almost, 1e-12)
    assert straightening is not None
    assert math.isclose(straightening.largest_shift, 2e-10 / 3.0, rel_tol=1e-6)
    assert found is not almost


def test_aerobuildup_gets_the_merged_bodies_straightened_after_the_merge() -> None:
    """The canopy envelope lifts the merged centre; the line is fitted through the merged body."""
    plane = airplane(Rumpf=fuselage_box(), Haube=canopy())
    (merged,) = solver_bodies(plane)
    result = aerobuildup_bodies(plane)
    (found,) = result.bodies
    expected, straightening = straight_axis(merged, config().opt_body_axis_tolerance.value)
    assert straightening is not None
    assert found == expected
    assert result.straightenings == (straightening,)
    assert [s.xyz[0] for s in found.x_secs] == [s.xyz[0] for s in merged.x_secs]


def test_a_straight_airplane_hands_its_bodies_over_unchanged() -> None:
    plane = airplane(Rumpf=fuselage_box())
    result = aerobuildup_bodies(plane)
    assert result.bodies == solver_bodies(plane)
    assert result.straightenings == ()


def test_a_mirrored_body_is_left_to_the_conversion_that_refuses_it() -> None:
    """AeroSandbox has no mirrored body (``aerosandbox-fuselage-shape``): nothing to straighten."""
    mirrored = body([section(0.0, 0.01, 0.01, y=0.3), section(0.1, 0.01, 0.01, y=0.3, z=0.02)])
    mirrored["x_secs"].append(section(0.4, 0.01, 0.01, y=0.3))
    mirrored["symmetric"] = True
    plane = airplane(Pod=mirrored)
    result = aerobuildup_bodies(plane)
    assert result.bodies == solver_bodies(plane)
    assert result.straightenings == ()
