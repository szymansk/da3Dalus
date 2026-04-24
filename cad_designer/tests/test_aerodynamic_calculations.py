"""Tests for aerodynamic_calculations module."""

import math

import numpy as np
import pytest

from cad_designer.aerosandbox.aerodynamic_calculations import (
    analyze_static_longitudinal_stability,
    best_range_speed,
    calculate_cl_max,
    calculate_CL_per_CD_max,
    calculate_stall_velocity,
    compute_derivative,
    estimate_motor_down_and_right_thrust,
    suggest_wing_incidence_angle,
)


# ---------------------------------------------------------------------------
# calculate_stall_velocity
# ---------------------------------------------------------------------------
class TestCalculateStallVelocity:
    """Tests for stall velocity calculation."""

    def test_known_values(self):
        """Verify against hand-calculated stall velocity.

        V_stall = sqrt(2 * W / (rho * S * CL_max))
        W = 5 * 9.81 = 49.05 N
        V = sqrt(2 * 49.05 / (1.225 * 0.5 * 1.5))
        V = sqrt(98.1 / 0.91875) = sqrt(106.775...) ~ 10.333 m/s
        """
        v = calculate_stall_velocity(CL_max=1.5, mass_kg=5.0, wing_area_m2=0.5)
        expected = math.sqrt(2 * 5.0 * 9.81 / (1.225 * 0.5 * 1.5))
        assert pytest.approx(v, rel=1e-6) == expected

    def test_return_kmh(self):
        """When return_kmh=True, should return tuple (m/s, km/h)."""
        result = calculate_stall_velocity(
            CL_max=1.5, mass_kg=5.0, wing_area_m2=0.5, return_kmh=True
        )
        assert isinstance(result, tuple)
        v_ms, v_kmh = result
        assert pytest.approx(v_kmh, rel=1e-6) == v_ms * 3.6

    def test_return_ms_only(self):
        """When return_kmh=False (default), should return a scalar."""
        result = calculate_stall_velocity(CL_max=1.5, mass_kg=5.0, wing_area_m2=0.5)
        assert isinstance(result, (float, np.floating))

    def test_higher_mass_increases_stall_speed(self):
        """Heavier aircraft should have higher stall speed."""
        v_light = calculate_stall_velocity(CL_max=1.5, mass_kg=2.0, wing_area_m2=0.5)
        v_heavy = calculate_stall_velocity(CL_max=1.5, mass_kg=10.0, wing_area_m2=0.5)
        assert v_heavy > v_light

    def test_higher_cl_max_decreases_stall_speed(self):
        """Higher CL_max should reduce stall speed."""
        v_low_cl = calculate_stall_velocity(CL_max=1.0, mass_kg=5.0, wing_area_m2=0.5)
        v_high_cl = calculate_stall_velocity(CL_max=2.0, mass_kg=5.0, wing_area_m2=0.5)
        assert v_high_cl < v_low_cl

    def test_larger_wing_decreases_stall_speed(self):
        """Larger wing area should reduce stall speed."""
        v_small = calculate_stall_velocity(CL_max=1.5, mass_kg=5.0, wing_area_m2=0.3)
        v_large = calculate_stall_velocity(CL_max=1.5, mass_kg=5.0, wing_area_m2=1.0)
        assert v_large < v_small

    def test_custom_rho_and_g(self):
        """Custom air density and gravity should be used."""
        v = calculate_stall_velocity(
            CL_max=1.5, mass_kg=5.0, wing_area_m2=0.5, rho=0.9, g=9.0
        )
        expected = math.sqrt(2 * 5.0 * 9.0 / (0.9 * 0.5 * 1.5))
        assert pytest.approx(v, rel=1e-6) == expected


# ---------------------------------------------------------------------------
# analyze_static_longitudinal_stability
# ---------------------------------------------------------------------------
class TestAnalyzeStaticLongitudinalStability:
    """Tests for static longitudinal stability analysis."""

    def test_stable_negative_slope(self):
        """Negative dCm/dalpha should be 'Stable'."""
        alpha = [0, 2, 4, 6, 8, 10]
        Cm = [0.1, 0.08, 0.06, 0.04, 0.02, 0.0]  # slope ~ -0.01
        result, slope = analyze_static_longitudinal_stability(alpha, Cm)
        assert "Stable" in result
        assert slope < -0.005

    def test_unstable_positive_slope(self):
        """Positive dCm/dalpha should be 'Unstable'."""
        alpha = [0, 2, 4, 6, 8, 10]
        Cm = [0.0, 0.02, 0.04, 0.06, 0.08, 0.1]  # slope ~ +0.01
        result, slope = analyze_static_longitudinal_stability(alpha, Cm)
        assert "Unstable" in result
        assert slope > 0.005

    def test_neutral_stability(self):
        """Near-zero slope should be 'Neutrally Stable'."""
        alpha = [0, 2, 4, 6, 8, 10]
        Cm = [0.05, 0.05, 0.05, 0.05, 0.05, 0.05]  # slope ~ 0
        result, slope = analyze_static_longitudinal_stability(alpha, Cm)
        assert "Neutrally Stable" in result
        assert abs(slope) <= 0.005

    def test_slope_included_in_result_string(self):
        """The result string should contain the numerical slope."""
        alpha = [0, 5, 10]
        Cm = [0.1, 0.0, -0.1]
        result, slope = analyze_static_longitudinal_stability(alpha, Cm)
        assert "dCm/d" in result

    def test_accepts_numpy_arrays(self):
        """Should work with numpy arrays as input."""
        alpha = np.array([0, 5, 10])
        Cm = np.array([0.1, 0.0, -0.1])
        result, slope = analyze_static_longitudinal_stability(alpha, Cm)
        assert isinstance(slope, float)


# ---------------------------------------------------------------------------
# calculate_cl_max
# ---------------------------------------------------------------------------
class TestCalculateClMax:
    """Tests for CL_max estimation via spline interpolation."""

    def test_parabolic_cl_curve(self):
        """A parabolic CL curve should find the peak correctly."""
        # CL = -0.01 * (alpha - 12)^2 + 1.5  => peak at alpha=12, CL=1.5
        alpha = list(range(0, 21))
        CL = [-0.01 * (a - 12) ** 2 + 1.5 for a in alpha]
        stall_alpha, cl_max = calculate_cl_max(alpha, CL)
        assert pytest.approx(stall_alpha, abs=0.5) == 12.0
        assert pytest.approx(float(cl_max), abs=0.05) == 1.5

    def test_cl_max_is_maximum(self):
        """Returned CL_max should be >= all input CL values (within tolerance)."""
        alpha = list(range(-5, 16))
        CL = [-0.01 * (a - 10) ** 2 + 1.2 for a in alpha]
        _, cl_max = calculate_cl_max(alpha, CL)
        assert float(cl_max) >= max(CL) - 0.01

    def test_stall_alpha_within_range(self):
        """Stall alpha should be within the input alpha range."""
        alpha = list(range(0, 20))
        CL = [-0.005 * (a - 14) ** 2 + 1.8 for a in alpha]
        stall_alpha, _ = calculate_cl_max(alpha, CL)
        assert alpha[0] <= stall_alpha <= alpha[-1]


# ---------------------------------------------------------------------------
# calculate_CL_per_CD_max
# ---------------------------------------------------------------------------
class TestCalculateCLPerCDMax:
    """Tests for maximum lift-to-drag ratio calculation."""

    def test_known_best_aoa(self):
        """Should find the AoA with maximum CL/CD."""
        alpha = [0, 2, 4, 6, 8, 10]
        CL = [0.0, 0.3, 0.6, 0.9, 1.0, 0.95]
        CD = [0.02, 0.025, 0.035, 0.06, 0.1, 0.15]

        best_aoa, max_LD, cl_at_best = calculate_CL_per_CD_max(alpha, CL, CD)

        # Manually compute: CL/CD = [0, 12, 17.14, 15, 10, 6.33]
        # Best is index 2 (alpha=4, CL/CD=17.14)
        assert best_aoa == 4
        assert pytest.approx(max_LD, rel=1e-6) == 0.6 / 0.035
        assert cl_at_best == 0.6

    def test_returns_three_values(self):
        """Should return (best_aoa, max_LD, CL_at_best)."""
        alpha = [0, 5, 10]
        CL = [0.1, 0.5, 0.8]
        CD = [0.01, 0.03, 0.08]
        result = calculate_CL_per_CD_max(alpha, CL, CD)
        assert len(result) == 3

    def test_single_point(self):
        """Should handle a single data point."""
        alpha = [5]
        CL = [0.5]
        CD = [0.03]
        best_aoa, max_LD, cl_at_best = calculate_CL_per_CD_max(alpha, CL, CD)
        assert best_aoa == 5
        assert pytest.approx(max_LD, rel=1e-6) == 0.5 / 0.03


# ---------------------------------------------------------------------------
# best_range_speed
# ---------------------------------------------------------------------------
class TestBestRangeSpeed:
    """Tests for best range speed calculation."""

    def test_known_values(self):
        """Verify against hand calculation.

        V = sqrt(2 * W / (rho * S * CL))
        W = 5 * 9.81 = 49.05
        V = sqrt(2 * 49.05 / (1.225 * 0.5 * 0.8))
        """
        CL = 0.8
        mass = 5.0
        area = 0.5
        v = best_range_speed(CL, mass, area)
        expected = math.sqrt(2 * mass * 9.81 / (1.225 * area * CL))
        assert pytest.approx(v, rel=1e-6) == expected

    def test_higher_mass_increases_speed(self):
        """Heavier aircraft needs higher speed for best range."""
        v_light = best_range_speed(0.8, 2.0, 0.5)
        v_heavy = best_range_speed(0.8, 10.0, 0.5)
        assert v_heavy > v_light

    def test_higher_cl_decreases_speed(self):
        """Higher CL at best L/D means lower speed."""
        v_low_cl = best_range_speed(0.5, 5.0, 0.5)
        v_high_cl = best_range_speed(1.2, 5.0, 0.5)
        assert v_high_cl < v_low_cl

    def test_custom_rho_and_gravity(self):
        """Custom air density and gravity should be used."""
        v = best_range_speed(0.8, 5.0, 0.5, rho=0.9, gravity=9.0)
        expected = math.sqrt(2 * 5.0 * 9.0 / (0.9 * 0.5 * 0.8))
        assert pytest.approx(v, rel=1e-6) == expected


# ---------------------------------------------------------------------------
# estimate_motor_down_and_right_thrust
# ---------------------------------------------------------------------------
class TestEstimateMotorDownAndRightThrust:
    """Tests for motor thrust angle estimation."""

    def test_returns_two_values(self):
        """Should return (sturz_deg, zug_deg)."""
        result = estimate_motor_down_and_right_thrust(
            mass_kg=2.0,
            prop_diameter_inch=10.0,
            wing_span_m=1.2,
            wing_chord_m=0.2,
            wing_area_m2=0.24,
        )
        assert len(result) == 2

    def test_values_within_bounds(self):
        """Down-thrust should be [1, 5] and right-thrust <= 5."""
        sturz, zug = estimate_motor_down_and_right_thrust(
            mass_kg=2.0,
            prop_diameter_inch=10.0,
            wing_span_m=1.2,
            wing_chord_m=0.2,
            wing_area_m2=0.24,
        )
        assert 1.0 <= sturz <= 5.0
        assert zug <= 5.0

    def test_custom_thrust(self):
        """Providing explicit thrust_N should override the default estimate."""
        sturz_default, _ = estimate_motor_down_and_right_thrust(
            mass_kg=2.0,
            prop_diameter_inch=10.0,
            wing_span_m=1.2,
            wing_chord_m=0.2,
            wing_area_m2=0.24,
        )
        sturz_custom, _ = estimate_motor_down_and_right_thrust(
            mass_kg=2.0,
            prop_diameter_inch=10.0,
            wing_span_m=1.2,
            wing_chord_m=0.2,
            wing_area_m2=0.24,
            thrust_N=50.0,
        )
        # Different thrust should (potentially) give different down-thrust
        # At minimum, neither should exceed bounds
        assert 1.0 <= sturz_custom <= 5.0

    def test_large_motor_offset_increases_right_thrust(self):
        """Larger motor mount offset should increase right-thrust."""
        _, zug_small = estimate_motor_down_and_right_thrust(
            mass_kg=2.0,
            prop_diameter_inch=10.0,
            wing_span_m=1.2,
            wing_chord_m=0.2,
            wing_area_m2=0.24,
            motor_mount_offset_m=0.01,
        )
        _, zug_large = estimate_motor_down_and_right_thrust(
            mass_kg=2.0,
            prop_diameter_inch=10.0,
            wing_span_m=1.2,
            wing_chord_m=0.2,
            wing_area_m2=0.24,
            motor_mount_offset_m=0.1,
        )
        assert zug_large >= zug_small

    def test_results_are_rounded(self):
        """Results should be rounded to 2 decimal places."""
        sturz, zug = estimate_motor_down_and_right_thrust(
            mass_kg=2.0,
            prop_diameter_inch=10.0,
            wing_span_m=1.2,
            wing_chord_m=0.2,
            wing_area_m2=0.24,
        )
        assert sturz == round(sturz, 2)
        assert zug == round(zug, 2)


# ---------------------------------------------------------------------------
# suggest_wing_incidence_angle
# ---------------------------------------------------------------------------
class TestSuggestWingIncidenceAngle:
    """Tests for wing incidence angle suggestion."""

    def test_linear_cm_crossing_zero(self):
        """A linear Cm that crosses zero should find the trim alpha."""
        # Cm = -0.02 * alpha + 0.06  => Cm=0 at alpha=3
        alpha = list(range(-5, 16))
        Cm = [-0.02 * a + 0.06 for a in alpha]
        new_incidence, trim_alpha = suggest_wing_incidence_angle(alpha, Cm)
        assert pytest.approx(trim_alpha, abs=0.5) == 3.0

    def test_current_incidence_offset(self):
        """Non-zero current incidence should shift the suggestion."""
        alpha = list(range(-5, 16))
        Cm = [-0.02 * a + 0.06 for a in alpha]
        inc_0, _ = suggest_wing_incidence_angle(alpha, Cm, current_incidence_deg=0.0)
        inc_5, _ = suggest_wing_incidence_angle(alpha, Cm, current_incidence_deg=5.0)
        # Difference should be 5 degrees
        assert pytest.approx(inc_5 - inc_0, abs=0.1) == 5.0

    def test_returns_rounded_values(self):
        """Both returned values should be rounded to 2 decimal places."""
        alpha = list(range(-5, 16))
        Cm = [-0.02 * a + 0.06 for a in alpha]
        new_inc, trim_a = suggest_wing_incidence_angle(alpha, Cm)
        assert new_inc == round(new_inc, 2)
        assert trim_a == round(trim_a, 2)


# ---------------------------------------------------------------------------
# compute_derivative
# ---------------------------------------------------------------------------
class TestComputeDerivative:
    """Tests for the compute_derivative helper."""

    def test_linear_slope(self):
        """A perfectly linear function should return exact slope."""
        x = np.array([0, 1, 2, 3, 4])
        y = 2.5 * x + 1.0
        slope = compute_derivative(x, y)
        assert pytest.approx(slope, rel=1e-6) == 2.5

    def test_negative_slope(self):
        """Negative slope should be correctly identified."""
        x = np.array([0, 1, 2, 3])
        y = -3.0 * x + 10.0
        slope = compute_derivative(x, y)
        assert pytest.approx(slope, rel=1e-6) == -3.0

    def test_zero_slope(self):
        """Constant function should give zero slope."""
        x = np.array([0, 1, 2, 3])
        y = np.array([5.0, 5.0, 5.0, 5.0])
        slope = compute_derivative(x, y)
        assert pytest.approx(slope, abs=1e-10) == 0.0

    def test_returns_float(self):
        """Result should be a Python float."""
        x = np.array([0, 1, 2])
        y = np.array([0, 1, 2])
        slope = compute_derivative(x, y)
        assert isinstance(slope, float)

    def test_noisy_data_approximation(self):
        """With small noise, slope should be close to the true value."""
        np.random.seed(42)
        x = np.linspace(0, 10, 100)
        y = 1.5 * x + np.random.normal(0, 0.1, 100)
        slope = compute_derivative(x, y)
        assert pytest.approx(slope, abs=0.05) == 1.5
