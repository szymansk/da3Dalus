"""Tests for powertrain solution-space service + endpoint (gh-975).

Acceptance Criteria (from GH #975 and the spec):
1. Invariant hand-calc: P_aero(V_cruise), E_Wh match formula.
2. More S → lower I_peak, lower min mAh, same Wh (voltage up → current down).
3. Feasible floors: capacity_floor_mah > 0, hyperbola points non-empty.
4. Catalog match: motor ✓ when a qualifying motor is present;
   battery/esc absent in empty DB → no match, no crash.
5. Missing context → warnings list non-empty, computation still returns.
6. Validation errors: V_top ≤ V_cruise → ValidationDomainError;
   t_target ≤ 0 → ValidationDomainError.
7. Endpoint returns the full schema + respects assumption overrides.
8. Band invariant: i_peak_hi ≥ i_peak_mid ≥ i_peak_lo (more η → less current).
"""

from __future__ import annotations

import math
import uuid

import pytest
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationDomainError
from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
from app.models.component import ComponentModel
from app.schemas.powertrain_solution_space import SolutionSpaceAssumptions
from app.services.powertrain_solution_space_service import (
    _p_aero,
    _p_elec,
    compute_solution_space,
)
from app.tests.conftest import make_aeroplane

# ---------------------------------------------------------------------------
# Constants matching the service
# ---------------------------------------------------------------------------
G = 9.80665
RHO = 1.225


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_assumption(session: Session, aeroplane_id: int, param: str, value: float) -> None:
    row = DesignAssumptionModel(
        aeroplane_id=aeroplane_id,
        parameter_name=param,
        estimate_value=value,
        active_source="ESTIMATE",
    )
    session.add(row)
    session.flush()


def _make_rc_plane(session: Session, name: str = "sol-space-test") -> AeroplaneModel:
    """Create a small RC trainer with a fully-populated computation context."""
    plane = make_aeroplane(session, name=name)
    _seed_assumption(session, plane.id, "mass", 1.5)
    _seed_assumption(session, plane.id, "cd0", 0.035)
    plane.assumption_computation_context = {
        "s_ref_m2": 0.40,
        "e_oswald": 0.78,
        "aspect_ratio": 8.0,
        "v_cruise_mps": 14.0,
        "v_md_mps": 14.0,
    }
    session.flush()
    session.commit()
    return plane


def _make_plane_no_context(session: Session) -> AeroplaneModel:
    """Create an aeroplane with NO computation context at all."""
    plane = make_aeroplane(session, name="no-ctx-plane")
    session.commit()
    return plane


def _default_assumptions(**overrides) -> SolutionSpaceAssumptions:
    defaults = {
        "cell_counts": [2, 3, 4, 6],
        "eta_prop_lo": 0.65,
        "eta_prop_hi": 0.78,
        "eta_motor": 0.85,
        "eta_esc": 0.94,
        "dod": 0.80,
        "esc_margin": 1.4,
        "c_margin": 1.25,
        "load_rpm_factor": 0.85,
        "prop_pd": 0.65,
        "t_target_min": 10.0,
        "v_top_mps": 22.0,  # > v_cruise=14.0
    }
    defaults.update(overrides)
    return SolutionSpaceAssumptions(**defaults)


def _seed_brushless_motor(session: Session, max_power_w: float) -> ComponentModel:
    m = ComponentModel(
        name="Test Motor",
        component_type="brushless_motor",
        specs={"max_power_w": max_power_w, "kv_rpm_v": 900},
    )
    session.add(m)
    session.flush()
    return m


# ===========================================================================
# 1. Unit tests for internal helpers (_p_aero, _p_elec)
# ===========================================================================


class TestPhysicsHelpers:
    def test_p_aero_formula(self):
        """Hand-calc: P_aero at V=14 m/s for a 1.5 kg RC plane."""
        mass = 1.5
        v = 14.0
        cd0 = 0.035
        e = 0.78
        ar = 8.0
        s_ref = 0.40

        q = 0.5 * RHO * v * v
        cl = (mass * G) / (q * s_ref)
        k = 1.0 / (math.pi * e * ar)
        cd = cd0 + k * cl * cl
        expected = q * s_ref * cd * v

        result = _p_aero(RHO, v, mass, G, cd0, e, ar, s_ref)
        assert abs(result - expected) < 1e-6, f"P_aero {result:.3f} ≠ expected {expected:.3f}"

    def test_p_aero_zero_speed_returns_inf(self):
        assert _p_aero(RHO, 0, 1.5, G, 0.03, 0.78, 8.0, 0.4) == float("inf")

    def test_p_elec_formula(self):
        """P_elec = P_aero / (η_prop · η_motor · η_esc)."""
        p_aero = 50.0
        eta = 0.72 * 0.85 * 0.94
        expected = p_aero / eta
        result = _p_elec(p_aero, 0.72, 0.85, 0.94)
        assert abs(result - expected) < 1e-6


# ===========================================================================
# 2. Invariant hand-calc tests on compute_solution_space
# ===========================================================================


class TestInvariants:
    def test_energy_wh_matches_formula(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions(t_target_min=10.0)
            result = compute_solution_space(db, plane, assumptions)

        # Hand-calc: P_elec at cruise (mid η = (0.65+0.78)/2 = 0.715)
        eta_mid = (0.65 + 0.78) / 2.0
        p_aero_cruise = _p_aero(RHO, 14.0, 1.5, G, 0.035, 0.78, 8.0, 0.40)
        p_cruise_elec = _p_elec(p_aero_cruise, eta_mid, 0.85, 0.94)
        expected_wh = p_cruise_elec * (10.0 / 60.0) / 0.80

        assert abs(result.energy_wh - expected_wh) < 0.5, (
            f"energy_wh {result.energy_wh:.2f} ≠ hand-calc {expected_wh:.2f}"
        )

    def test_p_aero_cruise_and_top_in_response(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        assert result.p_aero_cruise_w > 0
        assert result.p_aero_top_w > result.p_aero_cruise_w, (
            "Top speed > cruise → P_aero(top) should exceed P_aero(cruise)"
        )

    def test_v_top_default_is_1_4x_cruise(self, client_and_db):
        """When v_top_mps not supplied, service uses 1.4 × V_cruise."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions(v_top_mps=None)
            result = compute_solution_space(db, plane, assumptions)

        assert abs(result.v_top_mps - 14.0 * 1.4) < 0.01


# ===========================================================================
# 3. Cell-count monotonicity (more S → lower I_peak, lower mAh, same Wh)
# ===========================================================================


class TestCellCountMonotonicity:
    def test_more_S_lower_i_peak(self, client_and_db):
        """More cells → higher voltage → less current at same power."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions(cell_counts=[2, 3, 4, 6])
            result = compute_solution_space(db, plane, assumptions)

        i_peaks = {r.cell_count: r.i_peak_a for r in result.rows}
        assert i_peaks[2] > i_peaks[3] > i_peaks[4] > i_peaks[6], (
            f"I_peak should decrease with S: {i_peaks}"
        )

    def test_more_S_lower_capacity_min(self, client_and_db):
        """More cells → higher V_nom → less mAh needed for same Wh."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions(cell_counts=[2, 3, 4, 6])
            result = compute_solution_space(db, plane, assumptions)

        caps = {r.cell_count: r.capacity_mah_min for r in result.rows}
        assert caps[2] > caps[3] > caps[4] > caps[6], (
            f"capacity_mah_min should decrease with S: {caps}"
        )

    def test_same_energy_wh_across_cell_counts(self, client_and_db):
        """Energy [Wh] is independent of cell count (same flight time / cruise power)."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions(cell_counts=[2, 3, 4, 6])
            result = compute_solution_space(db, plane, assumptions)

        # The response's top-level energy_wh is the shared value
        wh_ref = result.energy_wh
        assert wh_ref > 0

        # Verify mAh × V_nom = same Wh for all S (within float precision)
        for row in result.rows:
            wh_derived = row.capacity_mah_min / 1000.0 * row.v_nom_v
            assert abs(wh_derived - wh_ref) < 0.05, (
                f"S={row.cell_count}: mAh×V_nom={wh_derived:.3f} ≠ E_Wh={wh_ref:.3f}"
            )


# ===========================================================================
# 4. Feasible regions
# ===========================================================================


class TestFeasibleRegions:
    def test_feasible_regions_count_matches_cell_counts(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions(cell_counts=[3, 4])
            result = compute_solution_space(db, plane, assumptions)

        assert len(result.feasible_regions) == 2

    def test_capacity_floor_positive(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        for fr in result.feasible_regions:
            assert fr.capacity_floor_mah > 0, f"S={fr.cell_count}: floor ≤ 0"

    def test_hyperbola_points_non_empty(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        for fr in result.feasible_regions:
            assert len(fr.capacity_curve_mah) > 0, f"S={fr.cell_count}: no curve points"
            assert len(fr.c_rate_curve) == len(fr.capacity_curve_mah)

    def test_hyperbola_is_decreasing(self, client_and_db):
        """C-rate hyperbola: more capacity → lower required C-rate."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        for fr in result.feasible_regions:
            c_rates = fr.c_rate_curve
            for i in range(1, len(c_rates)):
                assert c_rates[i] <= c_rates[i - 1], (
                    f"S={fr.cell_count}: C-rate should decrease as capacity increases"
                )


# ===========================================================================
# 5. Catalog matching
# ===========================================================================


class TestCatalogMatch:
    def test_motor_match_when_qualifying_motor_present(self, client_and_db):
        """A motor with max_power_w ≥ P_aero_top should flag has_motor_match=True."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            # First get the expected P_aero_top
            result_no_motor = compute_solution_space(db, plane, assumptions)
            p_top = result_no_motor.p_aero_top_w
            # Seed a motor that clearly meets the spec
            _seed_brushless_motor(db, max_power_w=p_top * 2.0)
            db.commit()

        with SessionLocal() as db:
            plane2 = (
                db.query(AeroplaneModel).filter(AeroplaneModel.name == "sol-space-test").first()
            )
            result = compute_solution_space(db, plane2, assumptions)

        for row in result.rows:
            assert row.has_motor_match is True, (
                f"S={row.cell_count}: expected motor match with P_top={p_top:.0f}W"
            )

    def test_no_crash_when_battery_esc_absent(self, client_and_db):
        """With 0 batteries and 0 ESCs in DB, should return False matches gracefully."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        for row in result.rows:
            assert row.has_battery_match is False
            assert row.has_esc_match is False

    def test_motor_no_match_when_underpowered(self, client_and_db):
        """A motor with max_power_w < P_aero_top should not match."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result_pre = compute_solution_space(db, plane, assumptions)
            p_top = result_pre.p_aero_top_w
            _seed_brushless_motor(db, max_power_w=p_top * 0.1)  # underpowered
            db.commit()

        with SessionLocal() as db:
            plane2 = (
                db.query(AeroplaneModel).filter(AeroplaneModel.name == "sol-space-test").first()
            )
            result = compute_solution_space(db, plane2, assumptions)

        for row in result.rows:
            assert row.has_motor_match is False


# ===========================================================================
# 6. Missing context → design warnings
# ===========================================================================


class TestMissingContextWarnings:
    def test_missing_context_produces_warnings(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_no_context(db)
            assumptions = _default_assumptions(v_top_mps=25.0)
            result = compute_solution_space(db, plane, assumptions)

        assert len(result.warnings) > 0, "Expected warnings when context is empty"

    def test_missing_context_warns_about_s_ref(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_no_context(db)
            assumptions = _default_assumptions(v_top_mps=25.0)
            result = compute_solution_space(db, plane, assumptions)

        warning_text = " ".join(result.warnings)
        assert "s_ref_m2" in warning_text.lower() or "s_ref" in warning_text.lower()

    def test_missing_context_still_returns_rows(self, client_and_db):
        """Even with missing context, we get rows (fallback defaults used)."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_no_context(db)
            assumptions = _default_assumptions(v_top_mps=25.0)
            result = compute_solution_space(db, plane, assumptions)

        assert len(result.rows) == len(assumptions.cell_counts)

    def test_missing_e_oswald_warns(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db, name="partial-ctx-plane")
            _seed_assumption(db, plane.id, "mass", 1.5)
            # Context has s_ref but missing e_oswald
            plane.assumption_computation_context = {
                "s_ref_m2": 0.40,
                "aspect_ratio": 8.0,
                "v_cruise_mps": 14.0,
                # e_oswald intentionally absent
            }
            db.flush()
            db.commit()
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        warning_text = " ".join(result.warnings).lower()
        assert "e_oswald" in warning_text


# ===========================================================================
# 7. Validation errors
# ===========================================================================


class TestValidationErrors:
    def test_v_top_equal_v_cruise_raises(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            # V_top = V_cruise = 14.0 → should raise
            assumptions = _default_assumptions(v_top_mps=14.0)
            with pytest.raises(ValidationDomainError, match="V_top"):
                compute_solution_space(db, plane, assumptions)

    def test_v_top_below_v_cruise_raises(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions(v_top_mps=10.0)  # < 14.0
            with pytest.raises(ValidationDomainError):
                compute_solution_space(db, plane, assumptions)

    def test_negative_t_target_rejected_by_schema(self):
        """Pydantic should reject t_target_min ≤ 0 at schema level."""
        with pytest.raises(PydanticValidationError):
            _default_assumptions(t_target_min=-5.0)

    def test_zero_t_target_rejected_by_schema(self):
        with pytest.raises(PydanticValidationError):
            _default_assumptions(t_target_min=0.0)


# ===========================================================================
# 8. Band invariant: i_peak_hi ≥ i_peak_mid ≥ i_peak_lo
# ===========================================================================


class TestBandInvariant:
    def test_band_ordering(self, client_and_db):
        """Low η_prop → more current (high end). High η_prop → less current (low end)."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        for row in result.rows:
            assert row.i_peak_hi_a >= row.i_peak_a >= row.i_peak_lo_a, (
                f"S={row.cell_count}: band ordering violated: "
                f"hi={row.i_peak_hi_a:.2f} mid={row.i_peak_a:.2f} lo={row.i_peak_lo_a:.2f}"
            )

    def test_cap_band_ordering(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        for row in result.rows:
            assert row.capacity_mah_min_hi >= row.capacity_mah_min >= row.capacity_mah_min_lo, (
                f"S={row.cell_count}: cap band ordering violated"
            )


# ===========================================================================
# 8b. I_peak absolute hand-calc (no double-counting of efficiencies)
# ===========================================================================


class TestIPeakHandCalc:
    """I_peak must be battery current = P_battery / V_sag.

    P_top_elec is ALREADY battery electrical power (P_aero / (η_prop·η_motor·η_esc)).
    Battery current is simply I = P_bat / V_sag — dividing again by η_motor·η_esc
    double-counts the efficiencies and underestimates the current by that factor.
    """

    def test_i_peak_absolute_value(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        # Reconstruct the mid-η battery power at V_top from the response.
        eta_mid = (assumptions.eta_prop_lo + assumptions.eta_prop_hi) / 2.0
        p_aero_top = result.p_aero_top_w
        p_bat_top = _p_elec(p_aero_top, eta_mid, assumptions.eta_motor, assumptions.eta_esc)

        for row in result.rows:
            v_sag = row.cell_count * 3.5
            expected_i = p_bat_top / v_sag
            assert row.i_peak_a == pytest.approx(expected_i, rel=1e-6), (
                f"S={row.cell_count}: i_peak {row.i_peak_a:.3f} ≠ "
                f"P_bat/V_sag {expected_i:.3f}"
            )

    def test_esc_min_follows_i_peak(self, client_and_db):
        """esc_min must equal i_peak × esc_margin (with the corrected i_peak)."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        for row in result.rows:
            assert row.esc_min_a == pytest.approx(
                row.i_peak_a * assumptions.esc_margin, rel=1e-6
            )

    def test_region_c_floor_uses_corrected_i_peak(self, client_and_db):
        """Feasible-region i_peak must match the (corrected) row i_peak."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        by_cells = {fr.cell_count: fr for fr in result.feasible_regions}
        for row in result.rows:
            fr = by_cells[row.cell_count]
            assert fr.i_peak_a == pytest.approx(row.i_peak_a, rel=1e-6)


# ===========================================================================
# 8c. c_margin is applied to the required c_min
# ===========================================================================


class TestCMarginApplied:
    def test_c_min_includes_margin(self, client_and_db):
        """Required c_min = (I_peak / (cap_mAh/1000)) × c_margin."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions(c_margin=1.25)
            result = compute_solution_space(db, plane, assumptions)

        for row in result.rows:
            raw_c = row.i_peak_a / (row.capacity_mah_min / 1000.0)
            assert row.c_min == pytest.approx(raw_c * 1.25, rel=1e-6), (
                f"S={row.cell_count}: c_min {row.c_min:.3f} should include 1.25× margin"
            )

    def test_c_margin_scales_c_min(self, client_and_db):
        """Increasing c_margin must increase the reported c_min proportionally."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            res_a = compute_solution_space(db, plane, _default_assumptions(c_margin=1.0))
            res_b = compute_solution_space(db, plane, _default_assumptions(c_margin=2.0))

        c_a = {r.cell_count: r.c_min for r in res_a.rows}
        c_b = {r.cell_count: r.c_min for r in res_b.rows}
        for s in c_a:
            assert c_b[s] == pytest.approx(c_a[s] * 2.0, rel=1e-6)

    def test_shopping_spec_c_includes_margin(self, client_and_db):
        """ShoppingSpec.battery_min_c must carry the margin too."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions(c_margin=1.25)
            result = compute_solution_space(db, plane, assumptions)

        by_cells = {r.cell_count: r for r in result.rows}
        for spec in result.shopping_specs:
            assert spec.battery_min_c == pytest.approx(by_cells[spec.cell_count].c_min, rel=1e-6)


# ===========================================================================
# 8d. motor_peak_w is shaft power (P_aero / eta_prop), not P_aero
# ===========================================================================


class TestMotorShaftPower:
    def test_motor_peak_is_shaft_power(self, client_and_db):
        """motor_peak_w = P_aero(V_top) / eta_prop_mid (required shaft power)."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        eta_mid = (assumptions.eta_prop_lo + assumptions.eta_prop_hi) / 2.0
        expected = result.p_aero_top_w / eta_mid
        for row in result.rows:
            assert row.motor_peak_w == pytest.approx(expected, rel=1e-6), (
                f"motor_peak_w {row.motor_peak_w:.2f} ≠ shaft power {expected:.2f}"
            )

    def test_motor_cont_is_shaft_power(self, client_and_db):
        """motor_cont_w = P_aero(V_cruise) / eta_prop_mid."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        eta_mid = (assumptions.eta_prop_lo + assumptions.eta_prop_hi) / 2.0
        expected = result.p_aero_cruise_w / eta_mid
        for row in result.rows:
            assert row.motor_cont_w == pytest.approx(expected, rel=1e-6)

    def test_shopping_spec_motor_is_shaft_power(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        eta_mid = (assumptions.eta_prop_lo + assumptions.eta_prop_hi) / 2.0
        expected = result.p_aero_top_w / eta_mid
        for spec in result.shopping_specs:
            assert spec.motor_min_peak_w == pytest.approx(expected, rel=1e-6)

    def test_motor_match_compares_against_shaft_power(self, client_and_db):
        """A motor that beats P_aero but NOT shaft power must NOT match."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            pre = compute_solution_space(db, plane, assumptions)
            eta_mid = (assumptions.eta_prop_lo + assumptions.eta_prop_hi) / 2.0
            p_aero_top = pre.p_aero_top_w
            shaft = p_aero_top / eta_mid
            # Motor between P_aero and shaft power → insufficient for shaft demand.
            mid_power = (p_aero_top + shaft) / 2.0
            _seed_brushless_motor(db, max_power_w=mid_power)
            db.commit()

        with SessionLocal() as db:
            plane2 = (
                db.query(AeroplaneModel)
                .filter(AeroplaneModel.name == "sol-space-test")
                .first()
            )
            result = compute_solution_space(db, plane2, assumptions)

        for row in result.rows:
            assert row.has_motor_match is False, (
                "Motor below shaft-power requirement must not match"
            )


# ===========================================================================
# 9. Shopping spec
# ===========================================================================


class TestShoppingSpec:
    def test_shopping_spec_count_matches(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions(cell_counts=[3, 4])
            result = compute_solution_space(db, plane, assumptions)

        assert len(result.shopping_specs) == 2

    def test_shopping_spec_fields_positive(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_rc_plane(db)
            assumptions = _default_assumptions()
            result = compute_solution_space(db, plane, assumptions)

        for spec in result.shopping_specs:
            assert spec.battery_min_mah > 0
            assert spec.battery_min_c > 0
            assert spec.esc_min_a > 0
            assert spec.motor_min_peak_w > 0


# ===========================================================================
# 10. Endpoint tests
# ===========================================================================


def _seed_assumption_db(session, aeroplane_id, param, value):
    row = DesignAssumptionModel(
        aeroplane_id=aeroplane_id,
        parameter_name=param,
        estimate_value=value,
        active_source="ESTIMATE",
    )
    session.add(row)
    session.flush()


class TestEndpoint:
    def _make_plane_for_endpoint(self, session: Session) -> AeroplaneModel:
        plane = make_aeroplane(session, name="ep-test-plane")
        _seed_assumption_db(session, plane.id, "mass", 1.5)
        _seed_assumption_db(session, plane.id, "cd0", 0.035)
        plane.assumption_computation_context = {
            "s_ref_m2": 0.40,
            "e_oswald": 0.78,
            "aspect_ratio": 8.0,
            "v_cruise_mps": 14.0,
        }
        session.flush()
        session.commit()
        return plane

    def test_returns_200_with_schema(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = self._make_plane_for_endpoint(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/powertrain/solution-space",
            params={"v_top_mps": 22.0, "t_target_min": 10.0},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        required_top = {
            "rows",
            "feasible_regions",
            "shopping_specs",
            "warnings",
            "p_aero_cruise_w",
            "p_aero_top_w",
            "energy_wh",
            "v_cruise_mps",
            "v_top_mps",
            "t_target_min",
            "assumptions_used",
        }
        missing = required_top - data.keys()
        assert not missing, f"Missing top-level keys: {missing}"

    def test_rows_count_matches_default_cell_counts(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = self._make_plane_for_endpoint(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/powertrain/solution-space",
            params={"v_top_mps": 22.0, "t_target_min": 10.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Default cell_counts = [2, 3, 4, 6] → 4 rows
        assert len(data["rows"]) == 4

    def test_override_cell_counts(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = self._make_plane_for_endpoint(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/powertrain/solution-space",
            params={"v_top_mps": 22.0, "t_target_min": 10.0, "cell_counts": [3, 6]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rows"]) == 2
        cell_counts_returned = [r["cell_count"] for r in data["rows"]]
        assert sorted(cell_counts_returned) == [3, 6]

    def test_404_missing_aeroplane(self, client_and_db):
        client, _ = client_and_db
        missing = str(uuid.uuid4())
        resp = client.get(
            f"/aeroplanes/{missing}/powertrain/solution-space",
            params={"v_top_mps": 22.0},
        )
        assert resp.status_code == 404

    def test_422_v_top_below_cruise(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = self._make_plane_for_endpoint(db)
            aeroplane_uuid = str(plane.uuid)

        # V_top = 5.0 < V_cruise = 14.0 → domain error
        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/powertrain/solution-space",
            params={"v_top_mps": 5.0, "t_target_min": 10.0},
        )
        assert resp.status_code == 422

    def test_override_t_target(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = self._make_plane_for_endpoint(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/powertrain/solution-space",
            params={"v_top_mps": 22.0, "t_target_min": 20.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["t_target_min"] == 20.0

    def test_warnings_present_for_missing_context(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db, name="ep-no-ctx")
            db.commit()
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/powertrain/solution-space",
            params={"v_top_mps": 25.0, "t_target_min": 10.0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["warnings"]) > 0

    def test_eta_prop_override(self, client_and_db):
        """Override eta_prop_lo/hi and verify the response reflects it."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = self._make_plane_for_endpoint(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/powertrain/solution-space",
            params={
                "v_top_mps": 22.0,
                "t_target_min": 10.0,
                "eta_prop_lo": 0.70,
                "eta_prop_hi": 0.80,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        used = data["assumptions_used"]
        assert used["eta_prop_lo"] == 0.70
        assert used["eta_prop_hi"] == 0.80
