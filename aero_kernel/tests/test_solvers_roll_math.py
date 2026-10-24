"""The pure helpers of the steady roll against hand values (fast tier, no AeroSandbox)."""

import math

from aero_kernel.solvers.roll_math import (
    alpha_for_lift_coefficient,
    body_rates,
    control_effectiveness,
    stability_rolling_moment,
)
from aero_kernel.tests.formula_builders import close


class Degrees:
    """Sine and cosine in degrees, as ``aerosandbox.numpy`` provides them."""

    def sind(self, x: float) -> float:
        return math.sin(math.radians(x))

    def cosd(self, x: float) -> float:
        return math.cos(math.radians(x))


def test_effectiveness_of_the_bryan_hinge_is_the_planned_value() -> None:
    """tau = 1 - 0.7803^2.7514: ln 0.7803 = -0.24800, times 2.7514 = -0.68235, exp = 0.50532."""
    assert math.isclose(control_effectiveness(0.7803), 0.494681, abs_tol=2e-6)
    assert math.isclose(control_effectiveness(0.0), 1.0, abs_tol=1e-12)


def test_body_rates_of_a_rotation_about_the_stability_axis() -> None:
    """p = 0.5 at alpha = 30 deg: p_b = 0.5 cos 30 = 0.4330127, r_b = 0.5 sin 30 = 0.25."""
    p_body, r_body = body_rates(0.5, 30.0, Degrees())
    assert close(p_body, 0.5 * math.sqrt(3.0) / 2.0, 1e-12)
    assert close(r_body, 0.25, 1e-12)


def test_stability_rolling_moment_is_cl_cos_alpha_plus_cn_sin_alpha() -> None:
    """Cl = 0.01, Cn = 0.02 at 30 deg: 0.01 * 0.8660254 + 0.02 * 0.5 = 0.018660254."""
    assert close(stability_rolling_moment(0.01, 0.02, 30.0, Degrees()), 0.0186602540378, 1e-11)


def test_alpha_for_lift_interpolates_between_the_enclosing_samples() -> None:
    alphas = [-1.0, 0.0, 1.0, 2.0, 3.0, 4.0]
    cl = [-0.1, 0.2, 0.4, 0.6, 0.8, 0.7]
    assert close(alpha_for_lift_coefficient(alphas, cl, 4, 0.5) or math.nan, 1.5, 1e-12)
    assert alpha_for_lift_coefficient(alphas, cl, 4, 0.9) is None
    assert close(alpha_for_lift_coefficient(alphas, cl, 4, 0.1) or math.nan, -1.0 / 3.0, 1e-12)
    assert alpha_for_lift_coefficient(alphas, cl, 4, -0.5) is None


def test_alpha_for_lift_takes_the_crossing_nearest_the_peak_on_a_non_monotonic_curve() -> None:
    """cl = 0.5, 0.3, 0.6, 0.8, 0.7 with the peak at index 3 and C_L 0.5 wanted: the scan from the
    peak finds the pair (1, 2) first (0.3 <= 0.5 <= 0.6), at 1 + (0.5 - 0.3) / 0.3 = 1.6667; the
    sample 0 (0.5) is an earlier, farther crossing that must not be returned."""
    alphas = [0.0, 1.0, 2.0, 3.0, 4.0]
    cl = [0.5, 0.3, 0.6, 0.8, 0.7]
    assert close(alpha_for_lift_coefficient(alphas, cl, 3, 0.5) or math.nan, 1.0 + 2.0 / 3.0, 1e-12)
