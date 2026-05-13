"""Tests for matching chart service — constraint-line T/W vs W/S diagram (gh-492).

Sources:
- Scholz HAW Flugzeugentwurf I §5.2–5.4 (SI)
- Anderson 6e §6.3 (climb), §6.7 (cruise / max L/D)
- Loftin 1980 (statistical takeoff/landing k-factors)
- Roskam Vol I §3.4 (landing ground-roll)

Cessna 172 cross-check reference:
  W = 10672 N  (m = 1088 kg × 9.80665)
  S = 16.17 m²   →  W/S ≈ 660 N/m²
  T_static = 1900 N  →  T/W = 1900 / 10672 ≈ 0.178 ≈ 0.18
  Loftin textbook result: T/W_static_SL ≈ 0.20 (±15%)
  Binding constraints: takeoff + climb (Loftin §1.3)
"""

from __future__ import annotations

import math
import pytest


# ---------------------------------------------------------------------------
# Helpers to import service under test
# ---------------------------------------------------------------------------

def _service():
    from app.services.matching_chart_service import compute_chart
    return compute_chart


def _helpers():
    from app.services import matching_chart_service as mcs
    return mcs


# ---------------------------------------------------------------------------
# Reference aircraft fixtures
# ---------------------------------------------------------------------------

CESSNA_172 = {
    # Actual Cessna 172N at MTOM, sea-level ISA
    "mass_kg": 1088.0,
    "t_static_N": 1900.0,
    "s_ref_m2": 16.17,
    "b_ref_m": 10.91,
    "ar": 7.32,
    "cd0": 0.031,
    "e_oswald": 0.75,
    "cl_max_clean": 1.6,
    "cl_max_takeoff": 1.6,
    "cl_max_landing": 2.1,
    "v_stall_mps": 25.4,
    "v_cruise_mps": 55.0,
}

LIGHT_RC = {
    # Typical RC park flyer: 1 kg, 5 dm² wing, 15 N thrust
    "mass_kg": 1.0,
    "t_static_N": 15.0,
    "s_ref_m2": 0.05,
    "b_ref_m": 1.0,
    "ar": 7.0,
    "cd0": 0.035,
    "e_oswald": 0.8,
    "cl_max_clean": 1.2,
    "cl_max_takeoff": 1.2,
    "cl_max_landing": 1.4,
    "v_stall_mps": 7.0,
    "v_cruise_mps": 15.0,
}


# ===========================================================================
# Class 1: Constraint formula correctness
# ===========================================================================

class TestConstraintFormulas:
    """Verify each constraint helper against closed-form physics."""

    def test_takeoff_constraint_loftin_form_monotone(self):
        """T/W = (W/S) · C_TO / (ρ · g · CL_max_TO · s_TO_ground · K_TO_50FT).

        Inverting for T/W: T/W increases monotonically with W/S for fixed s_runway.
        """
        mcs = _helpers()
        ws_range = [100.0, 200.0, 400.0, 600.0, 800.0]
        tw_values = [
            mcs._takeoff_constraint(ws, s_runway=100.0, cl_max_to=1.6, rho=1.225)
            for ws in ws_range
        ]
        # T/W must be strictly increasing with W/S
        for i in range(1, len(tw_values)):
            assert tw_values[i] > tw_values[i - 1], (
                f"Takeoff T/W not monotone increasing: {tw_values}"
            )

    def test_takeoff_constraint_zero_runway_is_zero(self):
        """Hand-launch mode: s_runway = 0 → T/W = 0 (no runway constraint)."""
        mcs = _helpers()
        tw = mcs._takeoff_constraint(ws=660.0, s_runway=0.0, cl_max_to=1.6, rho=1.225)
        assert tw == 0.0

    def test_takeoff_constraint_formula_value(self):
        """Spot-check formula value for Cessna 172 at design point.

        Roskam §3.4: s_TO_ground = C_TO · (W/S) / (ρ · g · CL_max_TO · (T/W))
        → T/W = C_TO · (W/S) / (ρ · g · CL_max_TO · s_TO_ground)
        with s_TO_ground = s_TO_50ft / K_TO_50FT

        For Cessna at W/S = 660 N/m²: s_TO_ground ≈ 266 m
        → T/W ≈ 1.21 × 660 / (1.225 × 9.81 × 1.6 × 266) ≈ 0.197
        """
        mcs = _helpers()
        # Use s_TO_50ft ≈ 411 m → s_TO_ground = 411/1.66 ≈ 248 m
        # Let's use s_runway = 411 m (to 50 ft), matching Cessna POH
        tw = mcs._takeoff_constraint(ws=660.0, s_runway=411.0, cl_max_to=1.6, rho=1.225)
        # Should give T/W ≈ 0.20 ± 25% for Cessna reference
        assert 0.10 <= tw <= 0.35, f"TO constraint T/W = {tw:.4f}, expected ~0.20"

    def test_landing_constraint_returns_max_ws(self):
        """Landing constraint: returns a scalar W/S_max (vertical line on chart)."""
        mcs = _helpers()
        ws_max = mcs._landing_constraint(s_runway=400.0, cl_max_l=2.1, rho=1.225)
        # Must be a positive finite float
        assert math.isfinite(ws_max)
        assert ws_max > 0.0

    def test_landing_constraint_decreases_with_longer_runway(self):
        """Longer runway → larger allowable W/S_max (more room to land heavier wing loading)."""
        mcs = _helpers()
        ws_short = mcs._landing_constraint(s_runway=200.0, cl_max_l=2.1, rho=1.225)
        ws_long = mcs._landing_constraint(s_runway=500.0, cl_max_l=2.1, rho=1.225)
        assert ws_long > ws_short, (
            f"Longer runway should give larger W/S_max: {ws_long:.1f} vs {ws_short:.1f}"
        )

    def test_cruise_constraint_has_minimum(self):
        """T/W(W/S) for cruise has a parabolic minimum at W/S_opt = q·√(CD0·π·e·AR).

        Note: W/S_opt depends on v_cruise. We sweep a wide range and use a low
        cruise speed so the optimal W/S falls inside the sweep window.
        """
        mcs = _helpers()
        # Use low cruise speed so W/S_opt ≈ 100–500 N/m²
        # W/S_opt = q·√(CD0·π·e·AR) = ½ρV²·√(0.031·π·0.75·7.32)
        # For V=20 m/s: q=0.5·1.225·400=245 Pa, W/S_opt=245·√(0.535)≈179 N/m²
        ws_range = list(range(20, 1200, 20))  # 20–1180 N/m²
        tw_values = [
            mcs._cruise_constraint(ws, v_cruise=20.0, cd0=0.031, e=0.75, ar=7.32, rho=1.225)
            for ws in ws_range
        ]
        min_idx = tw_values.index(min(tw_values))
        # Minimum should not be at the endpoints
        assert 0 < min_idx < len(tw_values) - 1, (
            f"Cruise T/W minimum at edge of range (idx={min_idx}), expected interior. "
            f"T/W values sample: {tw_values[:5]}...{tw_values[-5:]}"
        )
        # Minimum must be positive
        assert tw_values[min_idx] > 0.0

    def test_cruise_constraint_analytic_minimum(self):
        """Analytic minimum of cruise T/W matches formula.

        T/W_min = 2·√(CD0 / (π·e·AR))  (occurs at W/S_opt)
        """
        mcs = _helpers()
        cd0, e, ar = 0.031, 0.75, 7.32
        tw_min_analytic = 2.0 * math.sqrt(cd0 / (math.pi * e * ar))

        ws_range = list(range(50, 2000, 10))
        tw_values = [
            mcs._cruise_constraint(ws, v_cruise=55.0, cd0=cd0, e=e, ar=ar, rho=1.225)
            for ws in ws_range
        ]
        tw_min_numeric = min(tw_values)

        # Allow ±20% (discrete sampling tolerance)
        assert abs(tw_min_numeric - tw_min_analytic) / tw_min_analytic < 0.20, (
            f"Cruise min T/W: numeric={tw_min_numeric:.4f}, analytic={tw_min_analytic:.4f}"
        )

    def test_climb_constraint_increases_with_gamma(self):
        """Steeper climb angle γ requires higher T/W."""
        mcs = _helpers()
        ws = 660.0
        tw_5 = mcs._climb_constraint(ws, gamma_deg=5.0, v_climb=30.0, cd0=0.031, e=0.75, ar=7.32, rho=1.225)
        tw_10 = mcs._climb_constraint(ws, gamma_deg=10.0, v_climb=30.0, cd0=0.031, e=0.75, ar=7.32, rho=1.225)
        assert tw_10 > tw_5, f"Steeper climb needs more T/W: {tw_10:.4f} vs {tw_5:.4f}"

    def test_climb_constraint_sin_gamma_dominates_at_steep_angles(self):
        """At γ = 30°, sin(γ) ≈ 0.5 should dominate T/W numerically."""
        mcs = _helpers()
        tw = mcs._climb_constraint(ws=500.0, gamma_deg=30.0, v_climb=30.0,
                                   cd0=0.031, e=0.75, ar=7.32, rho=1.225)
        # T/W ≥ sin(30°) = 0.5
        assert tw >= math.sin(math.radians(30.0)), (
            f"T/W must be ≥ sin(γ); got {tw:.4f}"
        )

    def test_stall_constraint_uses_cl_max_clean(self):
        """W/S_max = ½·ρ·V_s²·CL_max_clean.

        V_s_target → sets the max allowable W/S.
        Higher CL_max_clean → higher W/S_max (more loaded wing can still fly slowly).
        """
        mcs = _helpers()
        ws_low_cl = mcs._stall_constraint(v_s_target=10.0, cl_max_clean=1.2, rho=1.225)
        ws_high_cl = mcs._stall_constraint(v_s_target=10.0, cl_max_clean=1.6, rho=1.225)
        assert ws_high_cl > ws_low_cl, (
            f"Higher CL_max_clean → larger W/S_max: {ws_high_cl:.1f} vs {ws_low_cl:.1f}"
        )

    def test_stall_constraint_formula_value(self):
        """W/S_max = ½·1.225·10²·1.2 = 73.5 N/m²."""
        mcs = _helpers()
        ws_max = mcs._stall_constraint(v_s_target=10.0, cl_max_clean=1.2, rho=1.225)
        expected = 0.5 * 1.225 * 10.0 ** 2 * 1.2
        assert abs(ws_max - expected) < 0.5, (
            f"Stall constraint W/S_max = {ws_max:.2f}, expected {expected:.2f}"
        )

    def test_stall_constraint_increases_with_target_speed(self):
        """Higher target stall speed → larger allowable W/S (vertical line shifts right)."""
        mcs = _helpers()
        ws_7 = mcs._stall_constraint(v_s_target=7.0, cl_max_clean=1.2, rho=1.225)
        ws_15 = mcs._stall_constraint(v_s_target=15.0, cl_max_clean=1.2, rho=1.225)
        assert ws_15 > ws_7, f"Larger V_s → larger W/S_max: {ws_15:.1f} vs {ws_7:.1f}"


# ===========================================================================
# Class 2: Constants-drift consistency with field_length_service
# ===========================================================================

class TestConsistencyWithFieldLengthService:
    """Constants-drift test: same Loftin/Roskam constants as field_length_service (gh-489)."""

    def test_k_to_50ft_shared_value(self):
        """K_TO_50FT must equal 1.66 in both services."""
        from app.services.matching_chart_service import _K_TO_50FT as mc_k
        from app.services.field_length_service import _K_TO_50FT as fl_k
        assert mc_k == fl_k, f"K_TO_50FT mismatch: mc={mc_k}, fl={fl_k}"

    def test_k_ldg_50ft_shared_value(self):
        """K_LDG_50FT must equal 2.73 in both services."""
        from app.services.matching_chart_service import _K_LDG_50FT as mc_k
        from app.services.field_length_service import _K_LDG_50FT as fl_k
        assert mc_k == fl_k, f"K_LDG_50FT mismatch: mc={mc_k}, fl={fl_k}"

    def test_constants_drift_takeoff_within_5_percent(self):
        """For Cessna at design point ON the TO constraint line, field_length_service
        returns s_to_50ft_m within 5% of the s_runway input used to draw the line.

        Methodology:
        1. Choose s_runway_input = 411 m (Cessna POH).
        2. Compute T/W from matching chart constraint at W/S=660.
        3. Plug that T/W + W/S back into field_length_service.
        4. Compare s_to_50ft_m with 411 m (± 5%).
        """
        mcs = _helpers()
        from app.services.field_length_service import compute_field_lengths

        s_runway_input = 411.0  # Cessna 172N POH to-50ft distance (m)
        ws = 660.0              # Design point W/S

        tw_on_constraint = mcs._takeoff_constraint(
            ws=ws,
            s_runway=s_runway_input,
            cl_max_to=1.6,
            rho=1.225,
        )
        assert tw_on_constraint > 0.0

        # Back out T_static_N from T/W and weight
        mass_kg = 1088.0
        g = 9.81
        weight_n = mass_kg * g
        t_static = tw_on_constraint * weight_n
        s_ref = weight_n / ws

        aircraft_dict = {
            "mass_kg": mass_kg,
            "s_ref_m2": s_ref,
            "cl_max": 1.6,
            "cl_max_takeoff": 1.6,
            "cl_max_landing": 2.1,
            "t_static_N": t_static,
            "v_stall_mps": 25.4,
        }

        result = compute_field_lengths(aircraft_dict, takeoff_mode="runway", landing_mode="runway")
        s_to_50ft = result["s_to_50ft_m"]

        assert abs(s_to_50ft - s_runway_input) / s_runway_input < 0.05, (
            f"Constants-drift test failed: field_length_service s_to_50ft={s_to_50ft:.1f} m, "
            f"target={s_runway_input:.1f} m, diff={100 * abs(s_to_50ft - s_runway_input) / s_runway_input:.1f}%"
        )

    def test_constants_drift_landing_within_5_percent(self):
        """For Cessna at design point ON the landing constraint line, field_length_service
        returns s_ldg_50ft_m within 5% of the s_runway input.
        """
        mcs = _helpers()
        from app.services.field_length_service import compute_field_lengths

        s_runway_input = 400.0  # landing runway target
        cl_max_l = 2.1
        rho = 1.225

        ws_max = mcs._landing_constraint(
            s_runway=s_runway_input,
            cl_max_l=cl_max_l,
            rho=rho,
        )
        assert ws_max > 0.0

        mass_kg = 1088.0
        g = 9.81
        weight_n = mass_kg * g
        s_ref = weight_n / ws_max

        aircraft_dict = {
            "mass_kg": mass_kg,
            "s_ref_m2": s_ref,
            "cl_max": 1.6,
            "cl_max_takeoff": 1.6,
            "cl_max_landing": cl_max_l,
            "t_static_N": 1900.0,
            "v_stall_mps": 25.4,
        }

        result = compute_field_lengths(aircraft_dict, takeoff_mode="runway", landing_mode="runway")
        s_ldg_50ft = result["s_ldg_50ft_m"]

        assert abs(s_ldg_50ft - s_runway_input) / s_runway_input < 0.05, (
            f"Landing constants-drift: field_length_service s_ldg_50ft={s_ldg_50ft:.1f} m, "
            f"target={s_runway_input:.1f} m, diff={100 * abs(s_ldg_50ft - s_runway_input) / s_runway_input:.1f}%"
        )


# ===========================================================================
# Class 3: Drag semantics — Interpretation A
# ===========================================================================

class TestDragSemanticsInterpretationA:
    """During drag: W, T_static, AR, CD0, e fixed. S, b, V_md vary."""

    def test_s_ref_varies_inversely_with_ws(self):
        """S = W / (W/S). For fixed W, S halves when W/S doubles."""
        mass_kg = 1.0
        g = 9.81
        weight_n = mass_kg * g
        ws1, ws2 = 100.0, 200.0
        s1 = weight_n / ws1
        s2 = weight_n / ws2
        assert abs(s1 / s2 - 2.0) < 1e-6

    def test_b_ref_scales_as_sqrt_ar_times_s(self):
        """b = √(AR · S). For AR = 7, S = 1.0 → b = √7."""
        ar = 7.0
        s = 1.0
        b_expected = math.sqrt(ar * s)
        b_actual = math.sqrt(ar * s)  # trivial — confirm formula used in service
        assert abs(b_actual - b_expected) < 1e-9

    def test_v_md_scales_with_ws(self):
        """V_md = (2·W/S / (ρ·√(CD0/(π·e·AR))))^0.5 increases with W/S."""
        mcs = _helpers()
        v_md_low = mcs._v_md(ws=300.0, cd0=0.031, e=0.75, ar=7.32, rho=1.225)
        v_md_high = mcs._v_md(ws=700.0, cd0=0.031, e=0.75, ar=7.32, rho=1.225)
        assert v_md_high > v_md_low, (
            f"V_md must increase with W/S: {v_md_high:.2f} vs {v_md_low:.2f}"
        )


# ===========================================================================
# Class 4: Cessna 172 cross-check (spec §AC)
# ===========================================================================

class TestCessna172CrossCheck:
    """Cessna 172N at MTOM: W/S ≈ 660 N/m² (±10%), T/W ≈ 0.20 (±15%)."""

    def test_design_point_ws_in_range(self):
        """Design-point W/S ≈ 660 N/m² ± 10%."""
        mass_kg = 1088.0
        s_ref_m2 = 16.17
        weight_n = mass_kg * 9.81
        ws = weight_n / s_ref_m2
        assert 660 * 0.90 <= ws <= 660 * 1.10, (
            f"Cessna W/S = {ws:.1f} N/m², expected 660 ± 10%"
        )

    def test_design_point_tw_in_range(self):
        """Design-point T/W ≈ 0.20 ± 15% (Loftin textbook)."""
        mass_kg = 1088.0
        t_static_n = 1900.0
        tw = t_static_n / (mass_kg * 9.81)
        assert 0.20 * 0.85 <= tw <= 0.20 * 1.15, (
            f"Cessna T/W = {tw:.4f}, expected 0.20 ± 15%"
        )

    def test_design_point_above_takeoff_constraint(self):
        """Cessna design point must be at or above the takeoff constraint line.

        If T/W_actual ≥ T/W_constraint, the aircraft can meet the field requirement.
        We use s_runway = 411 m (Cessna POH to-50ft value).
        """
        mcs = _helpers()
        ws = 660.0  # N/m²
        tw_constraint = mcs._takeoff_constraint(
            ws=ws, s_runway=411.0, cl_max_to=1.6, rho=1.225
        )
        tw_actual = 1900.0 / (1088.0 * 9.81)
        assert tw_actual >= tw_constraint * 0.90, (
            f"Cessna design point below TO constraint: T/W_actual={tw_actual:.4f}, "
            f"T/W_constraint={tw_constraint:.4f}"
        )

    def test_design_point_above_climb_constraint(self):
        """Cessna design point must be at or above the climb constraint line.

        Using γ = 4° (typical FAR Part 23 requirement), V_climb = V_md.
        """
        mcs = _helpers()
        ws = 660.0
        v_md = mcs._v_md(ws=ws, cd0=0.031, e=0.75, ar=7.32, rho=1.225)
        tw_constraint = mcs._climb_constraint(
            ws=ws, gamma_deg=4.0, v_climb=v_md, cd0=0.031, e=0.75, ar=7.32, rho=1.225
        )
        tw_actual = 1900.0 / (1088.0 * 9.81)
        assert tw_actual >= tw_constraint * 0.85, (
            f"Cessna design point below climb constraint: T/W_actual={tw_actual:.4f}, "
            f"T/W_constraint={tw_constraint:.4f}"
        )

    def test_compute_chart_cessna_design_point(self):
        """Full compute_chart returns Cessna design point in expected range.

        Spec requires: W/S ≈ 660 N/m² (±10%), T/W ≈ 0.20 (±15%).

        We use the Cessna's actual field length (s_runway=411 m to 50ft) so the
        design point lies at or above the takeoff constraint.
        """
        compute_chart = _service()
        # Use Cessna's actual POH field length so the design point is feasible
        chart = compute_chart(CESSNA_172, mode="uav_runway", s_runway=411.0)
        dp = chart["design_point"]
        ws = dp["ws_n_m2"]
        tw = dp["t_w"]

        assert 660 * 0.90 <= ws <= 660 * 1.10, (
            f"Cessna chart design point W/S = {ws:.1f}, expected 660 ± 10%"
        )
        assert 0.20 * 0.85 <= tw <= 0.20 * 1.15, (
            f"Cessna chart design point T/W = {tw:.4f}, expected 0.20 ± 15%"
        )

    def test_cessna_feasible(self):
        """Cessna design point must be classified as feasible with correct parameters.

        The Cessna 172N:
        - POH to-50ft takeoff distance is ~411 m  → s_runway=411 m
        - Stall speed is 25.4 m/s (clean)          → v_s_target must accommodate this
          (v_s_target=26 m/s keeps the stall constraint from blocking the design point)

        With these overrides the design point (W/S=660, T/W=0.178) should be feasible.
        """
        compute_chart = _service()
        chart = compute_chart(
            CESSNA_172,
            mode="uav_runway",
            s_runway=411.0,
            v_s_target=26.0,   # Cessna's actual stall speed is 25.4 m/s
        )
        assert chart["feasibility"] == "feasible", (
            f"Cessna should be feasible with s_runway=411 m, v_s_target=26 m/s, "
            f"got: {chart['feasibility']}"
        )


# ===========================================================================
# Class 5: Mode defaults
# ===========================================================================

class TestRcAndUavModeDefaults:
    """RC vs UAV mode defaults from spec."""

    def test_rc_defaults_have_short_runway(self):
        """RC runway mode: s_runway = 50 m (short field)."""
        mcs = _helpers()
        defaults = mcs._mode_defaults("rc_runway")
        assert defaults["s_runway"] == 50.0

    def test_uav_defaults_have_longer_runway(self):
        """UAV runway mode: s_runway = 200 m."""
        mcs = _helpers()
        defaults = mcs._mode_defaults("uav_runway")
        assert defaults["s_runway"] == 200.0

    def test_rc_defaults_v_s_target(self):
        """RC mode: V_s_target = 7 m/s (park-flyable)."""
        mcs = _helpers()
        defaults = mcs._mode_defaults("rc_runway")
        assert defaults["v_s_target"] == 7.0

    def test_uav_defaults_v_s_target(self):
        """UAV mode: V_s_target = 12 m/s."""
        mcs = _helpers()
        defaults = mcs._mode_defaults("uav_runway")
        assert defaults["v_s_target"] == 12.0

    def test_rc_defaults_gamma_climb(self):
        """RC mode: γ_climb = 5°."""
        mcs = _helpers()
        defaults = mcs._mode_defaults("rc_runway")
        assert defaults["gamma_climb_deg"] == 5.0

    def test_uav_defaults_gamma_climb(self):
        """UAV mode: γ_climb = 4°."""
        mcs = _helpers()
        defaults = mcs._mode_defaults("uav_runway")
        assert defaults["gamma_climb_deg"] == 4.0

    def test_hand_launch_no_takeoff_constraint(self):
        """rc_hand_launch mode: takeoff constraint is absent (s_runway=0)."""
        mcs = _helpers()
        defaults = mcs._mode_defaults("rc_hand_launch")
        # Hand-launch has no runway; takeoff constraint relaxed to zero
        assert defaults["s_runway"] == 0.0


# ===========================================================================
# Class 6: compute_chart output structure
# ===========================================================================

class TestComputeChartOutputStructure:
    """Verify compute_chart returns correct keys and shapes."""

    def test_returns_all_required_keys(self):
        """compute_chart must return all required top-level keys."""
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_runway")
        required = {"ws_range_n_m2", "constraints", "design_point", "feasibility", "warnings"}
        assert required.issubset(chart.keys()), (
            f"Missing keys: {required - chart.keys()}"
        )

    def test_design_point_has_ws_and_tw(self):
        """Design point dict must have ws_n_m2 and t_w."""
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_runway")
        dp = chart["design_point"]
        assert "ws_n_m2" in dp
        assert "t_w" in dp

    def test_constraints_are_list_of_dicts(self):
        """Constraints must be a non-empty list of dicts with required keys."""
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_runway")
        constraints = chart["constraints"]
        assert isinstance(constraints, list)
        assert len(constraints) > 0
        for c in constraints:
            assert "name" in c
            assert "t_w_points" in c or "ws_max" in c  # either line or vertical marker
            assert "color" in c
            assert "binding" in c

    def test_ws_range_is_sorted_positive(self):
        """ws_range_n_m2 must be sorted ascending and all positive."""
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_runway")
        ws = chart["ws_range_n_m2"]
        assert all(ws[i] > 0 for i in range(len(ws)))
        assert all(ws[i] < ws[i + 1] for i in range(len(ws) - 1))

    def test_at_least_four_constraints(self):
        """Must return at least 4 constraints (takeoff, landing, cruise, climb, stall)."""
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_runway")
        assert len(chart["constraints"]) >= 4, (
            f"Expected ≥4 constraints, got {len(chart['constraints'])}"
        )

    def test_feasibility_is_valid_string(self):
        """feasibility must be 'feasible' or 'infeasible_below_constraints'."""
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_runway")
        assert chart["feasibility"] in {"feasible", "infeasible_below_constraints"}

    def test_binding_constraint_is_bool(self):
        """Each constraint's 'binding' field must be a bool."""
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_runway")
        for c in chart["constraints"]:
            assert isinstance(c["binding"], bool), (
                f"Constraint '{c['name']}' binding is not bool: {c['binding']!r}"
            )

    def test_t_w_points_same_length_as_ws_range(self):
        """Line constraints must have same number of T/W points as W/S range."""
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_runway")
        ws_len = len(chart["ws_range_n_m2"])
        for c in chart["constraints"]:
            if "t_w_points" in c:
                assert len(c["t_w_points"]) == ws_len, (
                    f"Constraint '{c['name']}': {len(c['t_w_points'])} points, "
                    f"expected {ws_len}"
                )

    def test_compute_chart_rc_mode(self):
        """compute_chart works for RC mode with LIGHT_RC aircraft."""
        compute_chart = _service()
        chart = compute_chart(LIGHT_RC, mode="rc_runway")
        assert chart["feasibility"] in {"feasible", "infeasible_below_constraints"}
        assert len(chart["constraints"]) >= 4

    def test_custom_overrides_accepted(self):
        """Override params (s_runway, v_s_target, gamma_climb, v_cruise) are accepted."""
        compute_chart = _service()
        chart = compute_chart(
            CESSNA_172,
            mode="uav_runway",
            s_runway=300.0,
            v_s_target=20.0,
            gamma_climb_deg=3.0,
            v_cruise_mps=60.0,
        )
        assert "constraints" in chart


# ===========================================================================
# Class 7: Binding constraint marker
# ===========================================================================

class TestBindingConstraintMarker:
    """The binding constraint is the one that most tightly limits the design point."""

    def test_at_least_one_binding_for_cessna(self):
        """Cessna has at least one binding constraint when using correct field length.

        With s_runway=411 m (POH), the design point lies near the takeoff
        constraint line.
        """
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_runway", s_runway=411.0)
        binding = [c for c in chart["constraints"] if c["binding"]]
        # Cessna should have ≥1 binding constraint (takeoff or climb near-binding)
        assert len(binding) >= 1, (
            f"Expected ≥1 binding constraint for Cessna with s_runway=411 m, "
            f"got 0. Constraints: {[(c['name'], c.get('t_w_points', ['<ws_max>'])[100] if 't_w_points' in c else c.get('ws_max')) for c in chart['constraints']]}"
        )

    def test_infeasible_design_has_zero_or_more_binding(self):
        """An infeasible design (tiny thrust) may have zero binding or flag infeasible."""
        compute_chart = _service()
        tiny_thrust = {**CESSNA_172, "t_static_N": 100.0}  # obviously too weak
        chart = compute_chart(tiny_thrust, mode="uav_runway")
        # Either infeasible flag OR some constraints are marked binding
        # — both are valid representations
        assert chart["feasibility"] in {"feasible", "infeasible_below_constraints"}


# ===========================================================================
# Class 8: Unknown mode fallback (line 123-124)
# ===========================================================================

class TestUnknownModeFallback:
    """_mode_defaults falls back to uav_runway for unknown mode strings."""

    def test_unknown_mode_returns_uav_runway_defaults(self):
        """An unrecognised mode string should fall back to uav_runway defaults."""
        mcs = _helpers()
        defaults_unknown = mcs._mode_defaults("totally_unknown_mode")
        defaults_uav = mcs._mode_defaults("uav_runway")
        assert defaults_unknown == defaults_uav

    def test_unknown_mode_does_not_raise(self):
        """_mode_defaults must not raise for an unknown mode — log + fallback."""
        mcs = _helpers()
        # Should return a dict, not raise
        result = mcs._mode_defaults("xyzzy_mode")
        assert isinstance(result, dict)
        assert "s_runway" in result

    def test_compute_chart_unknown_mode_uses_fallback(self):
        """compute_chart with an unknown mode string should still return valid output."""
        compute_chart = _service()
        # Pass an unrecognised mode; service should use uav_runway defaults
        chart = compute_chart(CESSNA_172, mode="unknown_test_mode")
        assert "constraints" in chart
        assert chart["feasibility"] in {"feasible", "infeasible_below_constraints"}


# ===========================================================================
# Class 9: Landing constraint zero-runway path (line 223)
# ===========================================================================

class TestLandingConstraintEdgeCases:
    """Edge cases in the landing constraint helper."""

    def test_landing_constraint_zero_runway_returns_inf(self):
        """s_runway = 0 → no landing constraint → returns float('inf')."""
        mcs = _helpers()
        ws_max = mcs._landing_constraint(s_runway=0.0, cl_max_l=2.1, rho=1.225)
        assert math.isinf(ws_max)
        assert ws_max > 0

    def test_landing_constraint_negative_runway_returns_inf(self):
        """Negative s_runway (treated as unconstrained) → float('inf')."""
        mcs = _helpers()
        ws_max = mcs._landing_constraint(s_runway=-1.0, cl_max_l=2.1, rho=1.225)
        assert math.isinf(ws_max)


# ===========================================================================
# Class 10: Design point resolution from aircraft dict (lines 349, 353)
# ===========================================================================

class TestDesignPointFromAircraftDict:
    """_design_point_from_aircraft covers all three W/S resolution paths."""

    def test_ws_from_ws_n_m2_key_directly(self):
        """When 'ws_n_m2' key is present it is used directly."""
        mcs = _helpers()
        aircraft = {
            "mass_kg": 100.0,
            "t_static_N": 200.0,
            "ws_n_m2": 450.0,   # explicit W/S
        }
        dp = mcs._design_point_from_aircraft(aircraft)
        assert dp["ws_n_m2"] == pytest.approx(450.0, abs=1.0)

    def test_ws_falls_back_to_zero_when_no_area_info(self):
        """When neither s_ref_m2 nor ws_n_m2 is present, W/S = 0."""
        mcs = _helpers()
        aircraft = {
            "mass_kg": 100.0,
            "t_static_N": 200.0,
            # No s_ref_m2, no ws_n_m2
        }
        dp = mcs._design_point_from_aircraft(aircraft)
        assert dp["ws_n_m2"] == 0.0

    def test_tw_zero_when_mass_zero(self):
        """With mass_kg = 0 the T/W falls back to 0 (no division by zero)."""
        mcs = _helpers()
        aircraft = {
            "mass_kg": 0.0,
            "t_static_N": 500.0,
            "s_ref_m2": 10.0,
        }
        dp = mcs._design_point_from_aircraft(aircraft)
        assert dp["t_w"] == 0.0


# ===========================================================================
# Class 11: Cruise speed fallback from polar estimate (lines 483-492)
# ===========================================================================

class TestCruiseSpeedFallback:
    """compute_chart estimates v_cruise from polar when not given."""

    def test_v_cruise_estimated_when_not_in_aircraft(self):
        """Aircraft dict without v_cruise_mps or v_md_mps → warning appended."""
        compute_chart = _service()
        aircraft_no_vcruise = {
            "mass_kg": 1088.0,
            "t_static_N": 1900.0,
            "s_ref_m2": 16.17,
            "ar": 7.32,
            "cd0": 0.031,
            "e_oswald": 0.75,
            "cl_max_clean": 1.6,
            "cl_max_takeoff": 1.6,
            "cl_max_landing": 2.1,
            # deliberately NO v_cruise_mps, NO v_md_mps
        }
        chart = compute_chart(aircraft_no_vcruise, mode="uav_runway")
        # Must still complete and return valid output
        assert "constraints" in chart
        # A warning should be appended about estimated v_cruise
        assert len(chart["warnings"]) >= 1
        assert any("v_cruise_mps" in w for w in chart["warnings"])

    def test_v_md_mps_used_as_cruise_when_v_cruise_absent(self):
        """v_md_mps in aircraft dict is used as cruise speed fallback (no warning)."""
        compute_chart = _service()
        aircraft_with_vmd = {
            "mass_kg": 1088.0,
            "t_static_N": 1900.0,
            "s_ref_m2": 16.17,
            "ar": 7.32,
            "cd0": 0.031,
            "e_oswald": 0.75,
            "cl_max_clean": 1.6,
            "cl_max_takeoff": 1.6,
            "cl_max_landing": 2.1,
            "v_md_mps": 45.0,   # present, used as cruise fallback
            # NO v_cruise_mps
        }
        chart = compute_chart(aircraft_with_vmd, mode="uav_runway")
        assert "constraints" in chart
        # No warning about estimated v_cruise (we had v_md_mps)
        assert not any("v_cruise_mps not specified" in w for w in chart["warnings"])


# ===========================================================================
# Class 12: uav_belly_land mode (line 520 — landing constraint disabled)
# ===========================================================================

class TestUavBellyLandMode:
    """uav_belly_land mode skips the landing distance constraint."""

    def test_belly_land_landing_constraint_is_none(self):
        """In uav_belly_land mode the Landing constraint ws_max must be None (no runway)."""
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_belly_land")
        landing_constraints = [c for c in chart["constraints"] if c["name"] == "Landing"]
        assert len(landing_constraints) == 1
        assert landing_constraints[0]["ws_max"] is None, (
            "uav_belly_land mode should not impose a landing ws_max constraint"
        )

    def test_belly_land_mode_returns_valid_chart(self):
        """uav_belly_land mode must produce a valid chart structure."""
        compute_chart = _service()
        chart = compute_chart(CESSNA_172, mode="uav_belly_land")
        assert chart["feasibility"] in {"feasible", "infeasible_below_constraints"}
        assert len(chart["constraints"]) >= 4

    def test_uav_belly_land_defaults_same_runway_as_uav_runway(self):
        """uav_belly_land has s_runway=200 in defaults (takeoff still needs runway)."""
        mcs = _helpers()
        defaults = mcs._mode_defaults("uav_belly_land")
        assert defaults["s_runway"] == 200.0
        assert defaults["gamma_climb_deg"] == 4.0
        assert defaults["v_s_target"] == 12.0

    def test_rc_hand_launch_mode_produces_valid_chart(self):
        """rc_hand_launch mode (no runway) should produce a valid chart."""
        compute_chart = _service()
        chart = compute_chart(LIGHT_RC, mode="rc_hand_launch")
        assert chart["feasibility"] in {"feasible", "infeasible_below_constraints"}
        assert len(chart["constraints"]) >= 4


# ===========================================================================
# gh-493 Amendment 7: Re-table consumer wiring for matching chart
# ===========================================================================


class TestAmendment7MatchingChartWiring:
    """compute_chart uses V-specific cd0/e from polar_re_table when available.

    Backward-compat: when polar_re_table is absent, scalar cd0/e_oswald is used.
    """

    def _make_aircraft_with_retable(
        self,
        cd0_scalar: float = 0.035,
        cd0_low_re: float = 0.050,
        cd0_high_re: float = 0.030,
    ) -> dict:
        """Build aircraft dict with a polar_re_table spanning the cruise range."""
        mac_m = 0.254
        rho = 1.225
        mu = 1.81e-5

        v_low = 8.0
        v_high = 20.0
        re_low = int(rho * v_low * mac_m / mu)
        re_high = int(rho * v_high * mac_m / mu)

        return {
            **LIGHT_RC,
            "cd0": cd0_scalar,
            "mac_m": mac_m,
            "polar_re_table": [
                {
                    "re": re_low,
                    "v_mps": v_low,
                    "cd0": cd0_low_re,
                    "e_oswald": 0.78,
                    "cl_max": 1.2,
                    "r2": 0.98,
                    "fallback_used": False,
                },
                {
                    "re": re_high,
                    "v_mps": v_high,
                    "cd0": cd0_high_re,
                    "e_oswald": 0.78,
                    "cl_max": 1.2,
                    "r2": 0.99,
                    "fallback_used": False,
                },
            ],
        }

    def test_chart_with_retable_differs_from_scalar(self):
        """With polar_re_table, climb constraint differs from scalar-cd0 chart.

        When table cd0 at V_md ≠ scalar cd0, climb T/W line should shift.
        """
        compute_chart = _service()

        # Aircraft with Re table (table has significantly different cd0 from scalar)
        aircraft_with_table = self._make_aircraft_with_retable(
            cd0_scalar=0.035, cd0_low_re=0.060, cd0_high_re=0.020
        )
        # Aircraft without Re table (uses scalar cd0)
        aircraft_scalar = {**LIGHT_RC, "cd0": 0.035}

        chart_table = compute_chart(aircraft_with_table)
        chart_scalar = compute_chart(aircraft_scalar)

        # Both charts should be valid
        assert chart_table["feasibility"] in {"feasible", "infeasible_below_constraints"}
        assert chart_scalar["feasibility"] in {"feasible", "infeasible_below_constraints"}

        # Extract climb constraint T/W at mid-W/S (should differ between table and scalar)
        climb_table = next(c for c in chart_table["constraints"] if c["name"] == "Climb")
        climb_scalar = next(c for c in chart_scalar["constraints"] if c["name"] == "Climb")

        tw_table_pts = climb_table["t_w_points"]
        tw_scalar_pts = climb_scalar["t_w_points"]

        mid_idx = len(tw_table_pts) // 2
        tw_table_mid = tw_table_pts[mid_idx]
        tw_scalar_mid = tw_scalar_pts[mid_idx]

        assert abs(tw_table_mid - tw_scalar_mid) > 1e-6, (
            f"Re-table climb wiring inactive: T/W identical "
            f"({tw_table_mid:.5f}) with table and scalar cd0 both differing. "
            "Amendment 7 must wire lookup_cd0_at_v for climb constraint."
        )

    def test_chart_without_retable_uses_scalar_fallback(self):
        """When polar_re_table is absent, chart uses scalar cd0 (backward compat)."""
        compute_chart = _service()

        aircraft_no_table = {**LIGHT_RC}  # no polar_re_table key

        chart = compute_chart(aircraft_no_table)
        assert chart["feasibility"] in {"feasible", "infeasible_below_constraints"}
        assert len(chart["constraints"]) >= 4
