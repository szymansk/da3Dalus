"""Tests for takeoff and landing field length computation (gh-489).

Covers:
- Roskam Vol I §3.4 simplified ground-roll formula
- Four-assertion Cessna 172N cross-check at MTOM sea-level ISA
- CL_max auto-detect from flap config (no-flaps, slotted, Fowler+slat)
- RC launch/recovery modes: hand_launch, bungee/catapult, belly_land
- Thrust-absent guard (t_static_N absent → ServiceException)
"""

from __future__ import annotations

import math
import pytest


# ---------------------------------------------------------------------------
# Reference aircraft
# ---------------------------------------------------------------------------

CESSNA_172 = {
    "mass_kg": 1088.0,
    "s_ref_m2": 16.17,
    "cl_max": 1.5,
    "cl_max_takeoff": 1.5,
    "cl_max_landing": 2.1,
    "t_static_N": 1900.0,  # approximately 0.75 * T_static_zero = 0.75 * 2535
    "v_stall_mps": 25.4,  # matches POH stall speed
}


# ---------------------------------------------------------------------------
# Convenience import helpers
# ---------------------------------------------------------------------------


def _service():
    from app.services.field_length_service import compute_field_lengths

    return compute_field_lengths


def _helpers():
    from app.services import field_length_service as fls

    return fls


# ===========================================================================
# Cessna 172N cross-check (4 assertions, ±15%)
# ===========================================================================


class TestFieldLengthRunway:
    """Cessna 172N at MTOM, sea level ISA — cross-check against POH data.

    Sources:
    - POH ground roll ≈ 266 m (875 ft)
    - POH total to 50 ft ≈ 411 m (1350 ft) — with obstacle factor
    - POH landing ground roll ≈ 160 m (525 ft)
    - POH total from 50 ft ≈ 393 m (1290 ft)

    We allow ±15% tolerance because the simplified Roskam formula
    (energy method) is an approximation.
    """

    def test_cessna172_to_ground(self):
        """s_TO_ground ≈ 270 m ± 15%."""
        result = _service()(CESSNA_172, takeoff_mode="runway", landing_mode="runway")
        s = result["s_to_ground_m"]
        assert 270 * 0.85 <= s <= 270 * 1.15, f"Expected s_TO_ground ≈ 270 m ±15%, got {s:.1f} m"

    def test_cessna172_to_50ft(self):
        """s_TO_50ft ≈ 470 m ± 15%.

        Note: Roskam k_TO=1.66 relative to ground roll gives a longer
        estimate than the POH 50-ft figure. We use 470 m as the reference
        because k_TO=1.66 is conservative and the spec explicitly requires it.
        """
        result = _service()(CESSNA_172, takeoff_mode="runway", landing_mode="runway")
        s = result["s_to_50ft_m"]
        assert 470 * 0.85 <= s <= 470 * 1.15, f"Expected s_TO_50ft ≈ 470 m ±15%, got {s:.1f} m"

    def test_cessna172_ldg_ground(self):
        """s_LDG_ground ≈ 160 m ± 15%."""
        result = _service()(CESSNA_172, takeoff_mode="runway", landing_mode="runway")
        s = result["s_ldg_ground_m"]
        assert 160 * 0.85 <= s <= 160 * 1.15, f"Expected s_LDG_ground ≈ 160 m ±15%, got {s:.1f} m"

    def test_cessna172_ldg_50ft(self):
        """s_LDG_50ft ≈ 410 m ± 15%."""
        result = _service()(CESSNA_172, takeoff_mode="runway", landing_mode="runway")
        s = result["s_ldg_50ft_m"]
        assert 410 * 0.85 <= s <= 410 * 1.15, f"Expected s_LDG_50ft ≈ 410 m ±15%, got {s:.1f} m"

    def test_result_contains_required_fields(self):
        """Result dict has all required output fields."""
        result = _service()(CESSNA_172)
        required = {
            "s_to_ground_m",
            "s_to_50ft_m",
            "s_ldg_ground_m",
            "s_ldg_50ft_m",
            "vto_obstacle_mps",
            "vapp_mps",
            "mode_takeoff",
            "mode_landing",
            "warnings",
        }
        missing = required - result.keys()
        assert not missing, f"Missing output keys: {missing}"

    def test_vto_obstacle_is_1_2_vstall(self):
        """V_TO_obstacle = 1.2 · V_stall (Roskam standard V_LOF)."""
        result = _service()(CESSNA_172)
        v_stall = CESSNA_172["v_stall_mps"]
        assert abs(result["vto_obstacle_mps"] - 1.2 * v_stall) < 0.1

    def test_vapp_is_1_3_vstall(self):
        """V_app = 1.3 · V_stall (Roskam standard approach speed)."""
        result = _service()(CESSNA_172)
        v_stall = CESSNA_172["v_stall_mps"]
        assert abs(result["vapp_mps"] - 1.3 * v_stall) < 0.1

    def test_per_config_v_s_used_when_available(self):
        """gh-526: when v_s_to_mps and v_s0_mps are in the aircraft context,
        V_LOF and V_APP must be derived from them (per-flap-config physics),
        not from the clean v_stall_mps."""
        aircraft = dict(CESSNA_172)
        # Simulate gh-526 context: takeoff stall ~7% below clean, landing
        # ~17% below clean (matches Anderson §4.10 plain-flap envelope).
        aircraft["v_s_to_mps"] = 23.7  # 0.93 × 25.4
        aircraft["v_s0_mps"] = 21.0  # 0.83 × 25.4
        result = _service()(aircraft)
        assert abs(result["vto_obstacle_mps"] - 1.2 * 23.7) < 0.1
        assert abs(result["vapp_mps"] - 1.3 * 21.0) < 0.1

    def test_legacy_context_falls_back_to_v_stall_mps(self):
        """Pre-gh-526 contexts have no v_s_to_mps / v_s0_mps. Field-length
        service must fall back to the clean v_stall_mps unchanged."""
        aircraft = dict(CESSNA_172)
        # No v_s_to_mps / v_s0_mps keys → legacy behaviour
        assert "v_s_to_mps" not in aircraft
        assert "v_s0_mps" not in aircraft
        result = _service()(aircraft)
        v_stall = aircraft["v_stall_mps"]
        assert abs(result["vto_obstacle_mps"] - 1.2 * v_stall) < 0.1
        assert abs(result["vapp_mps"] - 1.3 * v_stall) < 0.1


# ===========================================================================
# CL_max auto-detect from flap config
# ===========================================================================


class TestClMaxAutoDetect:
    """CL_max uplift factors based on flap configuration."""

    def test_no_flap_keeps_cl_max(self):
        """No flaps → cl_max_takeoff = cl_max (1.0×), cl_max_landing = cl_max (1.0×)."""
        from app.services.field_length_service import detect_cl_max_flap_factors

        to_factor, ldg_factor = detect_cl_max_flap_factors(flap_type=None)
        assert to_factor == pytest.approx(1.0)
        assert ldg_factor == pytest.approx(1.0)

    def test_plain_flap_uplift(self):
        """plain flap → 1.1× TO, 1.3× LDG."""
        from app.services.field_length_service import detect_cl_max_flap_factors

        to_factor, ldg_factor = detect_cl_max_flap_factors(flap_type="plain")
        assert to_factor == pytest.approx(1.1)
        assert ldg_factor == pytest.approx(1.3)

    def test_slotted_flap_uplift(self):
        """slotted flap → 1.1× TO, 1.3× LDG."""
        from app.services.field_length_service import detect_cl_max_flap_factors

        to_factor, ldg_factor = detect_cl_max_flap_factors(flap_type="slotted")
        assert to_factor == pytest.approx(1.1)
        assert ldg_factor == pytest.approx(1.3)

    def test_fowler_slat_uplift(self):
        """Fowler/slat → 1.3× TO, 1.6× LDG."""
        from app.services.field_length_service import detect_cl_max_flap_factors

        to_factor, ldg_factor = detect_cl_max_flap_factors(flap_type="fowler")
        assert to_factor == pytest.approx(1.3)
        assert ldg_factor == pytest.approx(1.6)

    def test_compute_uses_override_cl_max_takeoff(self):
        """Explicit cl_max_takeoff in inputs overrides auto-detect."""
        aircraft = {**CESSNA_172, "cl_max_takeoff": 2.0, "cl_max_landing": 2.5}
        result = _service()(aircraft)
        # With higher CL_max_TO, ground roll should be shorter than with 1.5
        baseline = _service()(CESSNA_172)
        assert result["s_to_ground_m"] < baseline["s_to_ground_m"]


# ===========================================================================
# Hand-launch mode
# ===========================================================================


class TestHandLaunch:
    """Hand-launch RC mode: v_throw physics floor at 1.10·V_S."""

    def _aircraft_with_throw(self, v_throw: float) -> dict:
        return {**CESSNA_172, "v_throw_mps": v_throw}

    def test_v_throw_below_1_10_raises(self):
        """v_throw < 1.10 · V_S → ServiceException (physics floor violated)."""
        from app.core.exceptions import ServiceException

        v_stall = CESSNA_172["v_stall_mps"]
        aircraft = self._aircraft_with_throw(v_throw=1.05 * v_stall)
        with pytest.raises(ServiceException, match="v_throw"):
            _service()(aircraft, takeoff_mode="hand_launch")

    def test_v_throw_equal_to_1_10_passes(self):
        """v_throw = 1.10 · V_S passes without error."""
        v_stall = CESSNA_172["v_stall_mps"]
        aircraft = self._aircraft_with_throw(v_throw=1.10 * v_stall)
        result = _service()(aircraft, takeoff_mode="hand_launch")
        assert result["s_to_ground_m"] == pytest.approx(0.0)

    def test_v_throw_above_1_10_passes(self):
        """v_throw > 1.10 · V_S passes and sets s_TO_ground = 0."""
        v_stall = CESSNA_172["v_stall_mps"]
        aircraft = self._aircraft_with_throw(v_throw=1.20 * v_stall)
        result = _service()(aircraft, takeoff_mode="hand_launch")
        assert result["s_to_ground_m"] == pytest.approx(0.0)

    def test_v_throw_1_10_warns_below_1_20(self):
        """v_throw = 1.12 · V_S (between 1.10 and 1.20) → warning in result."""
        v_stall = CESSNA_172["v_stall_mps"]
        aircraft = self._aircraft_with_throw(v_throw=1.12 * v_stall)
        result = _service()(aircraft, takeoff_mode="hand_launch")
        assert result["s_to_ground_m"] == pytest.approx(0.0)
        assert any(
            "climb" in w.lower() or "margin" in w.lower() or "1.20" in w for w in result["warnings"]
        )

    def test_v_throw_above_1_20_no_climb_warning(self):
        """v_throw ≥ 1.20 · V_S → no climb-out margin warning."""
        v_stall = CESSNA_172["v_stall_mps"]
        aircraft = self._aircraft_with_throw(v_throw=1.25 * v_stall)
        result = _service()(aircraft, takeoff_mode="hand_launch")
        # No warning about climb margin
        climb_warnings = [
            w for w in result["warnings"] if "climb" in w.lower() or "margin" in w.lower()
        ]
        assert not climb_warnings

    def test_hand_launch_default_v_throw_10mps(self):
        """When v_throw not provided, default 10 m/s is used.

        A Cessna 172 has V_S = 25.4 m/s, so 10 m/s < 1.10 · V_S → error.
        A small RC glider with V_S = 8 m/s: 10 m/s > 1.10 · V_S → ok.
        """
        from app.core.exceptions import ServiceException

        # Cessna V_S=25.4 → 10 < 1.10×25.4=27.9 → error expected
        with pytest.raises(ServiceException, match="v_throw"):
            _service()(CESSNA_172, takeoff_mode="hand_launch")

    def test_hand_launch_s_to_50ft_zero(self):
        """For hand launch: s_to_50ft_m is also zero (ground roll is the launch itself)."""
        v_stall = CESSNA_172["v_stall_mps"]
        aircraft = self._aircraft_with_throw(v_throw=1.20 * v_stall)
        result = _service()(aircraft, takeoff_mode="hand_launch")
        assert result["s_to_50ft_m"] == pytest.approx(0.0)


# ===========================================================================
# Bungee / Catapult mode
# ===========================================================================


class TestBungeeCatapult:
    """Bungee and catapult launch modes."""

    def test_bungee_force_stretch_inputs(self):
        """bungee_force_N + stretch_m computes v_release and normal ground roll
        if v_release < V_LOF."""
        from app.services.field_length_service import compute_bungee_release_speed

        mass_kg = 5.0
        bungee_force_N = 50.0
        stretch_m = 3.0
        # Energy = 0.5 * F * x (linear spring approximation)
        # v_release = sqrt(F * x / mass) for uniform force (avg = F/2)
        v = compute_bungee_release_speed(mass_kg, bungee_force_N, stretch_m)
        expected = math.sqrt(bungee_force_N * stretch_m / mass_kg)
        assert abs(v - expected) < 0.1

    def test_release_above_v_lof_zero_ground(self):
        """v_release ≥ V_LOF → s_TO_ground = 0."""
        from app.services.field_length_service import _v_lof

        aircraft = {
            **CESSNA_172,
            "mass_kg": 5.0,
            "s_ref_m2": 0.5,
            "v_stall_mps": 8.0,
            "cl_max_takeoff": 1.5,
        }
        v_lof = _v_lof(aircraft["v_stall_mps"])
        # Set v_release higher than V_LOF
        aircraft_with_release = {**aircraft, "v_release_mps": v_lof + 2.0}
        result = _service()(aircraft_with_release, takeoff_mode="bungee")
        assert result["s_to_ground_m"] == pytest.approx(0.0)

    def test_release_below_v_lof_rolls(self):
        """v_release < V_LOF → ground roll > 0 (covers remaining speed)."""
        aircraft = {
            "mass_kg": 5.0,
            "s_ref_m2": 0.5,
            "cl_max": 1.5,
            "cl_max_takeoff": 1.5,
            "cl_max_landing": 2.0,
            "t_static_N": 30.0,
            "v_stall_mps": 8.0,
            "v_release_mps": 1.0,  # very slow → must roll
        }
        result = _service()(aircraft, takeoff_mode="bungee")
        assert result["s_to_ground_m"] > 0.0

    def test_catapult_mode_same_formula_as_bungee(self):
        """Catapult mode with v_release behaves same as bungee with v_release."""
        aircraft = {**CESSNA_172, "v_release_mps": 5.0}
        r_bungee = _service()(aircraft, takeoff_mode="bungee")
        r_catapult = _service()(aircraft, takeoff_mode="catapult")
        assert r_bungee["s_to_ground_m"] == pytest.approx(r_catapult["s_to_ground_m"])


# ===========================================================================
# Belly landing mode
# ===========================================================================


class TestBellyLand:
    """Belly landing uses μ=0.5 (grass + fuselage friction)."""

    def test_belly_shorter_than_runway(self):
        """Belly-land (μ=0.5) is shorter than runway braking (μ_brake=0.4).

        Higher friction coefficient → shorter stopping distance.
        """
        r_runway = _service()(CESSNA_172, landing_mode="runway")
        r_belly = _service()(CESSNA_172, landing_mode="belly_land")
        assert r_belly["s_ldg_ground_m"] < r_runway["s_ldg_ground_m"], (
            f"Expected belly ({r_belly['s_ldg_ground_m']:.1f} m) "
            f"< runway ({r_runway['s_ldg_ground_m']:.1f} m)"
        )

    def test_belly_land_approximately_80pct_of_runway(self):
        """Belly-land s_LDG ≈ 80–95% of wheeled runway distance (typical)."""
        r_runway = _service()(CESSNA_172, landing_mode="runway")
        r_belly = _service()(CESSNA_172, landing_mode="belly_land")
        ratio = r_belly["s_ldg_ground_m"] / r_runway["s_ldg_ground_m"]
        # μ=0.5 / μ=0.4 scaling → roughly 0.80 of runway distance
        assert 0.70 <= ratio <= 0.99, f"Belly/runway ratio = {ratio:.3f}, expected ≈ 0.80"


# ===========================================================================
# Thrust missing guard
# ===========================================================================


class TestThrustMissing:
    """t_static_N is required for takeoff; missing → ServiceException."""

    def test_block_with_error_when_t_static_absent(self):
        """ServiceException raised when t_static_N is missing."""
        from app.core.exceptions import ServiceException

        aircraft_no_thrust = {k: v for k, v in CESSNA_172.items() if k != "t_static_N"}
        with pytest.raises(ServiceException, match="t_static_N"):
            _service()(aircraft_no_thrust, takeoff_mode="runway")

    def test_block_for_hand_launch_without_thrust_requirement(self):
        """Hand-launch does NOT require thrust (it's human-powered launch).

        So hand_launch with missing t_static_N and valid v_throw should succeed.
        """
        v_stall = CESSNA_172["v_stall_mps"]
        aircraft = {
            "mass_kg": CESSNA_172["mass_kg"],
            "s_ref_m2": CESSNA_172["s_ref_m2"],
            "cl_max": CESSNA_172["cl_max"],
            "cl_max_landing": CESSNA_172["cl_max_landing"],
            # no t_static_N
            "v_stall_mps": v_stall,
            "v_throw_mps": 1.20 * v_stall,
        }
        # Should NOT raise — hand_launch doesn't need engine thrust
        result = _service()(aircraft, takeoff_mode="hand_launch", landing_mode="runway")
        assert result["s_to_ground_m"] == pytest.approx(0.0)


# ===========================================================================
# Internal helper unit tests
# ===========================================================================


class TestHelpers:
    """Unit tests for internal computation helpers."""

    def test_v_lof(self):
        """V_LOF = 1.2 · V_stall."""
        from app.services.field_length_service import _v_lof

        assert _v_lof(25.0) == pytest.approx(30.0)

    def test_v_app(self):
        """V_app = 1.3 · V_stall."""
        from app.services.field_length_service import _v_app

        assert _v_app(25.0) == pytest.approx(32.5)

    def test_s_to_ground_formula(self):
        """s_TO_ground = 1.21 (W/S) / (rho g CL_max_TO (T/W)).

        Manual calculation: W/S = 1088 * 9.81 / 16.17 ≈ 659.9 N/m²
        T/W = 1900 / (1088 * 9.81) ≈ 0.1780
        s_TO = 1.21 * 659.9 / (1.225 * 9.81 * 1.5 * 0.1780)
             = 798.5 / (3.204)  ≈ 249 m
        (Within ±15% of 270 m target)
        """
        from app.services.field_length_service import _compute_s_to_ground

        mass_kg = CESSNA_172["mass_kg"]
        s_ref = CESSNA_172["s_ref_m2"]
        cl_max_to = CESSNA_172["cl_max_takeoff"]
        t_static = CESSNA_172["t_static_N"]
        s = _compute_s_to_ground(mass_kg, s_ref, cl_max_to, t_static)
        # Should be in the correct ballpark (≈249-270 m)
        assert 200 <= s <= 350

    def test_s_ldg_ground_formula(self):
        """s_LDG_ground = k_LDG (W/S) / (rho CL_max_LDG).

        Manual check: produces a positive value in reasonable range.
        """
        from app.services.field_length_service import _compute_s_ldg_ground

        mass_kg = CESSNA_172["mass_kg"]
        s_ref = CESSNA_172["s_ref_m2"]
        cl_max_ldg = CESSNA_172["cl_max_landing"]
        s = _compute_s_ldg_ground(mass_kg, s_ref, cl_max_ldg)
        assert 100 <= s <= 250

    def test_obstacle_factor_50ft(self):
        """_apply_obstacle_factor multiplies by k correctly."""
        from app.services.field_length_service import _apply_obstacle_factor

        assert _apply_obstacle_factor(100.0, 1.66) == pytest.approx(166.0)
        assert _apply_obstacle_factor(100.0, 1.5) == pytest.approx(150.0)

    def test_bungee_release_speed_zero_stretch(self):
        """Zero stretch → zero release speed."""
        from app.services.field_length_service import compute_bungee_release_speed

        v = compute_bungee_release_speed(5.0, 50.0, 0.0)
        assert v == pytest.approx(0.0)

    def test_ground_roll_positive_for_valid_inputs(self):
        """Both s_TO and s_LDG are positive for valid inputs."""
        result = _service()(CESSNA_172)
        assert result["s_to_ground_m"] > 0
        assert result["s_ldg_ground_m"] > 0

    def test_50ft_distances_exceed_ground_roll(self):
        """50-ft obstacle distances are always larger than ground roll."""
        result = _service()(CESSNA_172)
        assert result["s_to_50ft_m"] > result["s_to_ground_m"]
        assert result["s_ldg_50ft_m"] > result["s_ldg_ground_m"]
