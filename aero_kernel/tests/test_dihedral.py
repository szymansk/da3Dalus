"""The equivalent dihedral of a polyhedral wing by the strip-theory weighting (canon ``spiral-parameter``)."""

import math

import pytest
from aero_kernel.dihedral import equivalent_dihedral_deg
from aero_kernel.errors import ErrorCategory, FormulaError
from aero_kernel.geometry import Wing
from aero_kernel.tests.formula_builders import close


def wing(
    rows: list[tuple[float, float, float]],
    *,
    symmetric: bool = True,
    surface_type: str = "main_wing",
) -> Wing:
    """A surface from (y, z, chord) rows in the stored order, leading edges at x = 0."""
    return Wing.model_validate(
        {
            "name": "W",
            "symmetric": symmetric,
            "surface_type": surface_type,
            "x_secs": [
                {"xyz_le": [0.0, y, z], "chord": c, "twist": 0.0, "airfoil": "naca0012"}
                for y, z, c in rows
            ],
        }
    )


def test_the_entrys_check_inner_60_percent_flat_outer_40_percent_at_10_degrees() -> None:
    """Hand value of the entry: constant chord, W = 0.18 and 0.32, so 0.32 * 10 / 0.5 = 6.4 deg."""
    rise = 0.4 * math.tan(math.radians(10.0))
    found = equivalent_dihedral_deg(wing([(0.0, 0.0, 0.2), (0.6, 0.0, 0.2), (1.0, rise, 0.2)]))
    assert close(found, 6.4, 1e-12)


def test_a_wing_of_one_dihedral_gives_that_dihedral_whatever_the_taper() -> None:
    rise = 0.8 * math.tan(math.radians(4.0))
    found = equivalent_dihedral_deg(wing([(0.0, 0.0, 0.3), (0.8, rise, 0.1)]))
    assert close(found, 4.0, 1e-12)


def test_a_tapered_panel_weights_by_the_exact_integral_of_chord_times_y() -> None:
    """Panel 1 flat, chord 0.3 -> 0.2 over y 0..0.5; panel 2 at 10 deg, chord 0.2 -> 0.1 over y 0.5..1.

    W1 = int (0.3 - 0.2 y) y dy = 0.15 y^2 - 0.2 y^3 / 3 from 0 to 0.5 = 0.0375 - 0.0083333 = 0.0291667;
    W2 = int (0.2 - 0.2 (y - 0.5)) y dy = int (0.3 - 0.2 y) y dy = 0.15 y^2 - 0.2 y^3 / 3 from 0.5 to 1
    = (0.15 - 0.0666667) - 0.0291667 = 0.0541667. Gamma_eq = 10 * W2 / (W1 + W2).
    """
    rise = 0.5 * math.tan(math.radians(10.0))
    found = equivalent_dihedral_deg(wing([(0.0, 0.0, 0.3), (0.5, 0.0, 0.2), (1.0, rise, 0.1)]))
    assert close(found, 10.0 * 0.0541667 / (0.0291667 + 0.0541667), 1e-5)


def test_anhedral_is_negative_and_a_tip_first_store_gives_the_same_value() -> None:
    root_first = wing([(0.0, 0.0, 0.2), (0.6, 0.0, 0.2), (1.0, -0.07, 0.2)])
    tip_first = wing([(1.0, -0.07, 0.2), (0.6, 0.0, 0.2), (0.0, 0.0, 0.2)])
    found = equivalent_dihedral_deg(root_first)
    assert found < 0.0
    assert close(equivalent_dihedral_deg(tip_first), found, 1e-12)


def test_a_root_off_the_centreline_weights_only_the_wing_that_exists() -> None:
    """The gap at the centreline carries no dihedral; the weighting starts at the root rib."""
    found = equivalent_dihedral_deg(wing([(0.1, 0.0, 0.2), (0.6, 0.0, 0.2), (1.0, 0.07, 0.2)]))
    assert 0.0 < found < math.degrees(math.atan2(0.07, 0.4))


def test_an_unmirrored_main_wing_has_no_semi_span_and_is_refused() -> None:
    unmirrored = wing([(-1.0, 0.0, 0.2), (1.0, 0.0, 0.2)], symmetric=False)
    with pytest.raises(FormulaError, match="mirrored") as raised:
        equivalent_dihedral_deg(unmirrored)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION
    assert raised.value.code == "unsupported_layout"


def test_a_wing_without_a_span_has_no_weighting_and_is_refused() -> None:
    spanless = wing([(0.0, 0.0, 0.2), (0.0, 0.1, 0.2)])
    with pytest.raises(FormulaError, match="no span") as raised:
        equivalent_dihedral_deg(spanless)
    assert raised.value.category is ErrorCategory.UNSUPPORTED_CONFIGURATION


def test_the_main_wing_is_chosen_by_type_not_by_position() -> None:
    from aero_kernel.dihedral import main_wing_dihedral_deg
    from aero_kernel.geometry import AirplaneGeometry

    def plan(*extra: str) -> AirplaneGeometry:
        wings = {
            f"w{index}": {
                "name": f"w{index}",
                "symmetric": True,
                "surface_type": kind,
                "x_secs": [
                    {"xyz_le": [0.0, 0.0, 0.0], "chord": 0.2, "twist": 0.0, "airfoil": "naca0012"},
                    {"xyz_le": [0.0, 0.5, rise], "chord": 0.2, "twist": 0.0, "airfoil": "naca0012"},
                ],
            }
            for index, (kind, rise) in enumerate(zip(extra, (0.5, 0.0), strict=True))
        }
        return AirplaneGeometry.model_validate({"name": "t", "wings": wings})

    # the tail comes first in the document and has 45 degrees; the main wing is flat
    assert main_wing_dihedral_deg(plan("horizontal_tail", "main_wing")) == 0.0
    two_tails = plan("horizontal_tail", "horizontal_tail")
    with pytest.raises(ValueError, match="exactly one main wing"):
        main_wing_dihedral_deg(two_tails)
