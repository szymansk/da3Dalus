"""Polar, air state and the first-extremum search of the stall problem (ch. 8.12, canon K32)."""

import math

import pytest
from aero_kernel.schema import Polar
from aero_kernel.solvers.air import AirState
from aero_kernel.solvers.stall_math import first_extremum
from pydantic import ValidationError

ALPHAS = (-2.0, 0.0, 2.0, 4.0, 6.0)


def polar(**change: object) -> Polar:
    fields: dict[str, object] = {
        "alpha_deg": ALPHAS,
        "cl": (-0.1, 0.1, 0.3, 0.5, 0.7),
        "cd": (0.02, 0.01, 0.01, 0.02, 0.03),
        "cm": (0.0, -0.01, -0.02, -0.03, -0.04),
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
        {"cm": (0.0, 0.0, 0.0, 0.0, math.inf)},
    ],
)
def test_a_polar_rejects_unequal_series_a_non_rising_alpha_and_non_finite_values(
    change: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        polar(**change)


def test_a_polar_needs_two_samples() -> None:
    with pytest.raises(ValidationError):
        Polar(alpha_deg=(0.0,), cl=(0.0,), cd=(0.0,), cm=(0.0,))


def test_an_air_state_has_a_kinematic_viscosity() -> None:
    air = AirState(density=1.2, dynamic_viscosity=1.8e-5, speed_of_sound=340.0)
    assert math.isclose(air.kinematic_viscosity, 1.5e-5, rel_tol=1e-12)


@pytest.mark.parametrize("field", ["density", "dynamic_viscosity", "speed_of_sound"])
@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_an_air_state_must_be_positive_and_finite(field: str, bad: float) -> None:
    fields = {"density": 1.2, "dynamic_viscosity": 1.8e-5, "speed_of_sound": 340.0, field: bad}
    with pytest.raises(ValidationError):
        AirState(**fields)


def test_the_first_peak_is_the_first_local_maximum_scanning_upwards() -> None:
    cl = [0.0, 0.4, 0.8, 1.1, 1.2, 1.0, 0.9, 1.0, 0.8]  # a second, lower maximum follows
    assert first_extremum(cl, maximum=True) == 4


def test_a_plateau_peak_is_the_last_sample_of_the_plateau() -> None:
    assert first_extremum([0.0, 0.5, 1.0, 1.0, 0.9], maximum=True) == 3


def test_the_first_trough_is_the_first_local_minimum() -> None:
    assert first_extremum([0.0, -0.4, -0.8, -0.7, -0.9], maximum=False) == 2


def test_a_series_that_never_turns_has_no_extremum() -> None:
    assert first_extremum([0.0, 0.5, 1.0, 1.5], maximum=True) is None
    assert first_extremum([0.0, 0.5], maximum=True) is None
    assert first_extremum([], maximum=True) is None
