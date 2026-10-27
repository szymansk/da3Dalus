"""The equivalent symmetric super-ellipse of a section with two shape exponents (gh-1307)."""

import math

import numpy as np
import pytest
from aero_kernel.config import config
from aero_kernel.geometry import AirplaneGeometry, FuselageXSecSuperEllipse
from aero_kernel.superellipse import (
    equivalent_exponent,
    quadrant_area_fraction,
)
from aero_kernel.tests.formula_builders import close
from aero_kernel.tests.reference_fleet import FleetMember, reference_document

# The perimeter of the equivalent section is only approximately that of the two halves. The bound is
# what the reference fleet needs (measured 2.06 % on WIESEL's section 43, 0.004 % on CHEKKER's); a
# section whose halves differ more would need a looser one, and the warning says it is approximate.
FLEET_PERIMETER_BOUND = 0.025
EXACT_PERIMETER_POINTS = 20001


def test_the_quadrant_area_fraction_of_the_known_shapes() -> None:
    """Diamond 1/2, ellipse pi/4 of the bounding box quadrant; the square (n -> inf) is 1."""
    assert close(quadrant_area_fraction(1.0), 0.5, 1e-12)
    assert close(quadrant_area_fraction(2.0), math.pi / 4.0, 1e-12)
    assert abs(quadrant_area_fraction(1e6) - 1.0) < 1e-5


def test_the_quadrant_area_fraction_does_not_overflow_for_a_tiny_exponent() -> None:
    """Gamma(1 + 2/n) overflows a float for n < 0.012; the logarithm form does not."""
    assert 0.0 < quadrant_area_fraction(0.005) < 0.5


def test_the_fraction_grows_with_the_exponent() -> None:
    values = [quadrant_area_fraction(n) for n in (1.04, 1.5, 2.0, 3.0, 10.0, 50.0)]
    assert values == sorted(values)


@pytest.mark.parametrize(
    ("upper", "lower"), [(2.0, 3.0), (2.0, 50.0), (1.04, 2.0), (4.0, 4.5), (0.5, 7.0)]
)
def test_the_equivalent_section_has_the_area_of_the_two_halves(upper: float, lower: float) -> None:
    """Upper half 2ab f(n), lower half 2ab f(n_lower); symmetric section 4ab f(n_eq)."""
    equivalent = equivalent_exponent(upper, lower)
    sum_of_halves = quadrant_area_fraction(upper) + quadrant_area_fraction(lower)
    symmetric = 2.0 * quadrant_area_fraction(equivalent)
    tolerance = config().opt_fuselage_area_tolerance.value
    assert close(symmetric, sum_of_halves, tolerance)


@pytest.mark.parametrize(("upper", "lower"), [(2.0, 3.0), (2.0, 50.0), (1.04, 2.0)])
def test_the_equivalent_exponent_lies_between_the_two_and_ignores_their_order(
    upper: float, lower: float
) -> None:
    equivalent = equivalent_exponent(upper, lower)
    assert min(upper, lower) < equivalent < max(upper, lower)
    assert close(equivalent_exponent(lower, upper), equivalent, 1e-9)


def test_equal_exponents_are_their_own_equivalent() -> None:
    assert equivalent_exponent(2.5, 2.5) == 2.5


def half_perimeter(a: float, b: float, n: float) -> float:
    """The length of the upper half of the outline (``z >= 0``), summed over a fine polyline."""
    t = np.linspace(0.0, math.pi, EXACT_PERIMETER_POINTS)
    y = a * np.sign(np.cos(t)) * np.abs(np.cos(t)) ** (2.0 / n)
    z = b * np.abs(np.sin(t)) ** (2.0 / n)
    return float(np.sum(np.hypot(np.diff(y), np.diff(z))))


def substituted_sections(member: FleetMember) -> list[FuselageXSecSuperEllipse]:
    """Every fuselage section of the aircraft that has two different exponents."""
    plane = AirplaneGeometry.model_validate(reference_document(member))
    return [
        section
        for fuselage in (plane.fuselages or {}).values()
        for section in fuselage.x_secs
        if section.n_lower is not None and section.n_lower != section.n
    ]


@pytest.mark.parametrize("member", [FleetMember.CHEKKER, FleetMember.WIESEL])
def test_the_fleet_sections_keep_the_perimeter_to_the_stated_bound(member: FleetMember) -> None:
    """The canon states the perimeter is kept only approximately: measured on the real sections."""
    sections = [s for s in substituted_sections(member) if s.a > 0.0 and s.b > 0.0]
    assert sections
    for section in sections:
        assert section.n_lower is not None
        true = half_perimeter(section.a, section.b, section.n) + half_perimeter(
            section.a, section.b, section.n_lower
        )
        equivalent = equivalent_exponent(section.n, section.n_lower)
        symmetric = 2.0 * half_perimeter(section.a, section.b, equivalent)
        assert abs(symmetric / true - 1.0) < FLEET_PERIMETER_BOUND


def test_a_half_perimeter_of_the_circle_is_pi_a() -> None:
    assert close(half_perimeter(2.0, 2.0, 2.0), 2.0 * math.pi, 1e-6)
