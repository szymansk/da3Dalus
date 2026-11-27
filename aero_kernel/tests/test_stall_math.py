"""Polar, air state and the main-extremum search of the stall problem (ch. 8.12, canon K32)."""

import math

import pytest
from aero_kernel.schema import Polar
from aero_kernel.solvers.air import AirState, FixedAtmosphere
from aero_kernel.solvers.stall_math import main_extremum, main_extremum_from_zero
from pydantic import ValidationError

ALPHAS = (-2.0, 0.0, 2.0, 4.0, 6.0)


def polar(**change: object) -> Polar:
    fields: dict[str, object] = {
        "alpha_deg": ALPHAS,
        "cl": (-0.1, 0.1, 0.3, 0.5, 0.7),
        "cd": (0.02, 0.01, 0.01, 0.02, 0.03),
    }
    return Polar.model_validate({**fields, **change})


def test_a_polar_holds_equally_long_finite_series_over_rising_alpha() -> None:
    assert polar().alpha_deg == ALPHAS


@pytest.mark.parametrize(
    "change",
    [
        {"cl": (0.0, 0.1)},
        {"alpha_deg": (0.0, 0.0, 1.0, 2.0, 3.0)},
        {"alpha_deg": (2.0, 1.0, 0.0, -1.0, -2.0)},
        {"cd": (0.0, 0.0, 0.0, 0.0, math.nan)},
        {"cl": (0.0, 0.0, 0.0, 0.0, math.inf)},
    ],
)
def test_a_polar_rejects_unequal_series_a_non_rising_alpha_and_non_finite_values(
    change: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        polar(**change)


def test_a_polar_needs_two_samples() -> None:
    with pytest.raises(ValidationError):
        Polar(alpha_deg=(0.0,), cl=(0.0,), cd=(0.0,))


def test_an_air_state_has_a_kinematic_viscosity() -> None:
    air = AirState(density=1.2, dynamic_viscosity=1.8e-5, speed_of_sound=340.0)
    assert math.isclose(air.kinematic_viscosity, 1.5e-5, rel_tol=1e-12)


@pytest.mark.parametrize("field", ["density", "dynamic_viscosity", "speed_of_sound"])
@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_an_air_state_must_be_positive_and_finite(field: str, bad: float) -> None:
    fields = {"density": 1.2, "dynamic_viscosity": 1.8e-5, "speed_of_sound": 340.0, field: bad}
    with pytest.raises(ValidationError):
        AirState(**fields)


def test_the_main_peak_is_the_record_maximum_with_the_largest_fall_behind_it() -> None:
    """A shoulder (0.9 at index 2, falls 0.02 before the curve is above it again) precedes the real
    maximum (1.2 at index 5, falls 0.3 to the end), gh-1423."""
    cl = [0.0, 0.5, 0.9, 0.88, 1.0, 1.2, 1.0, 0.9]
    assert main_extremum(cl, maximum=True) == 5


def test_the_main_peak_stays_the_first_one_when_a_lower_maximum_follows() -> None:
    """The BRYAN shape: 1.2 at index 4, then a post-stall plateau with a lower maximum (1.0), which
    is no candidate because a higher maximum was already found."""
    cl = [0.0, 0.4, 0.8, 1.1, 1.2, 1.0, 0.9, 1.0, 0.8]
    assert main_extremum(cl, maximum=True) == 4


def test_a_slightly_higher_plateau_behind_the_stall_is_not_the_main_peak() -> None:
    """The WINDFREAK shape: 0.860 at index 2 falls by 0.116 to 0.744 before the curve is above it
    again; the plateau maximum 0.885 at index 5 is higher but falls only 0.011 (to 0.874) up to the
    end. The largest fall decides, not the height."""
    cl = [0.0, 0.5, 0.860, 0.744, 0.80, 0.885, 0.874, 0.88]
    assert main_extremum(cl, maximum=True) == 2


def test_a_lower_maximum_with_a_large_fall_is_no_candidate_after_a_higher_one() -> None:
    """The EXTRA_300_EP shape: 1.130 at index 2 with 0.029 behind it, then 1.087 at index 4 with
    0.236 behind it. The second is lower than the first, so it is no maximum of the scan; the fall
    of the first runs to the end of the series: 1.130 - 0.851 = 0.279."""
    cl = [0.0, 0.8, 1.130, 1.101, 1.087, 0.95, 0.851]
    assert main_extremum(cl, maximum=True) == 2


def test_the_fall_behind_a_maximum_ends_where_the_curve_is_above_it_again() -> None:
    """Record maxima 0.9 (index 1, falls 0.05 to 0.85, then the curve is above it), 1.0 (index 3,
    falls 0.7 to 0.3, then the curve is above it) and 1.2 (index 5, falls 0.1 to the end): the one
    with the largest fall is index 3, although index 5 is higher."""
    cl = [0.0, 0.9, 0.85, 1.0, 0.3, 1.2, 1.1]
    assert main_extremum(cl, maximum=True) == 3


def test_a_series_still_rising_at_its_end_keeps_its_interior_maximum() -> None:
    """The end of the sweep is no maximum: 1.5 at the last sample does not replace 1.1 at index 2
    (which falls 0.2 before the curve is above it again); 1.0 at index 4 is no record."""
    cl = [0.0, 0.6, 1.1, 0.9, 1.0, 0.95, 1.3, 1.5]
    assert main_extremum(cl, maximum=True) == 2


def test_of_two_maxima_with_the_same_fall_the_first_in_scan_order_is_taken() -> None:
    """Record maxima 1.0 (index 1, falls 0.5) and 1.5 (index 3, falls 0.5): the lower angle."""
    assert main_extremum([0.0, 1.0, 0.5, 1.5, 1.0], maximum=True) == 1


def test_a_second_maximum_of_exactly_the_same_height_is_no_record() -> None:
    assert main_extremum([0.0, 1.0, 0.5, 1.0, 0.2], maximum=True) == 1


def test_a_plateau_peak_is_the_last_sample_of_the_plateau() -> None:
    assert main_extremum([0.0, 0.5, 1.0, 1.0, 0.9], maximum=True) == 3


def test_the_main_trough_is_the_record_minimum_with_the_largest_rise_behind_it() -> None:
    """Mirror. Record minima -0.8 (index 2, rises 0.3 to -0.5 before the curve is below it again)
    and -0.95 (index 5, rises 0.05 to the end): index 2, although index 5 is lower."""
    assert main_extremum([0.0, -0.4, -0.8, -0.5, -0.7, -0.95, -0.9], maximum=False) == 2


def test_a_series_that_never_turns_has_no_extremum() -> None:
    assert main_extremum([0.0, 0.5, 1.0, 1.5], maximum=True) is None
    assert main_extremum([0.0, 0.5], maximum=True) is None
    assert main_extremum([], maximum=True) is None


def test_a_fixed_atmosphere_answers_from_its_state_with_ideal_gas_temperature_and_pressure() -> (
    None
):
    air = AirState(density=1.225, dynamic_viscosity=1.7894e-5, speed_of_sound=340.294)
    atmosphere = FixedAtmosphere(air)
    assert (atmosphere.density(), atmosphere.dynamic_viscosity()) == (1.225, 1.7894e-5)
    assert atmosphere.speed_of_sound() == 340.294
    assert atmosphere.ratio_of_specific_heats() == 1.4
    assert math.isclose(atmosphere.temperature(), 340.294**2 / (1.4 * 287.0500676), rel_tol=1e-12)
    assert math.isclose(
        atmosphere.pressure(), 1.225 * 287.0500676 * atmosphere.temperature(), rel_tol=1e-12
    )


def test_a_boundary_sample_is_never_an_extremum() -> None:
    """A falling series has its maximum at the first sample, a rising one at the last: neither
    is a turning point (ADR 0020), and a wrapped index must not make it one."""
    assert main_extremum([3.0, 2.0, 1.0], maximum=True) is None
    assert main_extremum([1.0, 2.0, 3.0], maximum=False) is None
    assert main_extremum([1.0, 2.0, 3.0], maximum=True) is None
    assert main_extremum([3.0, 2.0, 1.0], maximum=False) is None


# --- main_extremum_from_zero (canon K32: the scan starts at alpha = 0, P2-F02) -----------------


def test_an_upright_scan_ignores_a_local_maximum_below_alpha_zero() -> None:
    """The lift recovers past the negative stall: the maximum at -3 deg is not C_L,max.

    Hand reading of the series (alpha: C_L): -4: -0.4, -3: -0.3, -2: -0.5, -1: -0.2, 0: 0.0,
    1: 0.3, 2: 0.6, 3: 0.5, 4: 0.4. A scan from the first sample stops at -3 deg (index 1,
    -0.3 >= -0.4 and -0.3 > -0.5); the scan from alpha = 0 rises through 0.3 to 0.6 and stops
    at +2 deg (index 6, 0.6 > 0.5).
    """
    alphas = (-4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0)
    cl = (-0.4, -0.3, -0.5, -0.2, 0.0, 0.3, 0.6, 0.5, 0.4)
    assert main_extremum_from_zero(alphas, cl, upright=True) == 6


def test_an_inverted_scan_takes_the_trough_below_zero_not_the_one_above() -> None:
    """Scanning down from alpha = 0 the series reads 0.0, -0.3, -0.6, -0.5, -0.4: trough at -2 deg.

    The trough at +2 deg (-0.9, index 6) lies on the other side of zero and must not be taken.
    """
    alphas = (-4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0)
    cl = (-0.4, -0.5, -0.6, -0.3, 0.0, -0.2, -0.9, -0.1, 0.2)
    assert main_extremum_from_zero(alphas, cl, upright=False) == 2


def test_a_grid_without_alpha_zero_starts_at_the_nearest_sample() -> None:
    """Nearest sample to 0 is +0.5 deg (index 2); from there C_L reads 0.4, 0.6, 0.9, 0.7.

    The peak at 3.5 deg (index 4) is the answer; a scan from the first sample would stop at the
    -1.5 deg bump (index 1, 0.5).
    """
    alphas = (-3.0, -1.5, 0.5, 2.0, 3.5, 5.0)
    cl = (0.1, 0.5, 0.4, 0.6, 0.9, 0.7)
    assert main_extremum_from_zero(alphas, cl, upright=True) == 4


def test_an_empty_series_and_a_series_that_does_not_turn_have_no_extremum() -> None:
    assert main_extremum_from_zero((), (), upright=True) is None
    assert main_extremum_from_zero((0.0, 1.0, 2.0), (0.0, 0.5, 1.0), upright=True) is None
    assert main_extremum_from_zero((-2.0, -1.0, 0.0), (0.0, -0.5, -1.0), upright=False) is None


def test_an_upright_scan_takes_the_main_maximum_above_alpha_zero_past_a_shoulder() -> None:
    """The Avistar shape (gh-1423): a shoulder at 2 deg (0.6, then 0.59) and the maximum 0.9 at 5 deg.

    The maximum below zero (-0.3 at -3 deg) lies on the other side and is never taken.
    """
    alphas = (-4.0, -3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)
    cl = (-0.4, -0.3, -0.5, -0.2, 0.0, 0.3, 0.6, 0.59, 0.8, 0.9, 0.7)
    assert main_extremum_from_zero(alphas, cl, upright=True) == 9


def test_an_inverted_scan_takes_the_main_minimum_below_alpha_zero() -> None:
    """Scanning down from 0: -0.3, -0.6 (trough, rises 0.05), -0.55, -0.8 (trough, rises 0.1), -0.7:
    both are record minima, the one at -4 deg has the larger rise behind it."""
    alphas = (-5.0, -4.0, -3.0, -2.0, -1.0, 0.0, 1.0)
    cl = (-0.7, -0.8, -0.55, -0.6, -0.3, 0.0, 0.3)
    assert main_extremum_from_zero(alphas, cl, upright=False) == 1
