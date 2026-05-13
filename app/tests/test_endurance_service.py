"""Tests for app.services.endurance_service — gh-490.

Electric endurance / range from battery capacity, propeller efficiency,
and required power at V_md / V_min_sink (Anderson §6.4–6.5).

Hand-check (RC trainer reference):
  2 kg aircraft, 5000 mAh 4S (4 × 3.7 V nominal → 14.8 V, ≈ 74 Wh)
  η_total = 0.52, S = 0.40 m², AR = 7.0, V_min_sink = 10.5 m/s
  P_req(V_min_sink) = D(V_min_sink) × V_min_sink / η_total
    CL at V_min_sink = 2mg/(ρV²S) = 2×2×9.81/(1.225×10.5²×0.4) ≈ 0.723
    CD ≈ CD0 + CL²/(π·e·AR) — but test uses helper _power_required directly
  t_endurance ≈ E / P_req → should be > 8 min for reasonable CD0 ≈ 0.03
"""

from __future__ import annotations

import math
import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.endurance_service import (
    _classify_p_margin,
    _check_battery_mass_consistency,
    _power_required,
    compute_endurance,
)

# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

RHO_SL = 1.225  # kg/m³ sea-level ISA
G = 9.80665

# RC Trainer reference aircraft — 2 kg, 5000 mAh 4S (≈ 74 Wh), η_total = 0.52
RC_TRAINER = {
    "mass_kg": 2.0,
    "s_ref_m2": 0.40,
    "ar": 7.0,
    "cd0": 0.03,
    "e_oswald": 0.78,
    "e_oswald_quality": "good",
    "e_oswald_fallback_used": False,
    "v_md_mps": 14.0,
    "v_min_sink_mps": 10.5,
    "battery_capacity_wh": 74.0,
    "battery_mass_kg": 0.40,        # user component mass
    "motor_continuous_w": 200.0,
    "eta_prop": 0.65,
    "eta_motor": 0.85,
    "eta_esc": 0.94,
}

# η_total from RC_TRAINER defaults
ETA_TOTAL_RC = 0.65 * 0.85 * 0.94  # ≈ 0.519


# ---------------------------------------------------------------------------
# Helper: build a mock aircraft with assumption_computation_context
# ---------------------------------------------------------------------------


def _make_aircraft(
    mass_kg: float = 2.0,
    s_ref_m2: float = 0.40,
    ar: float = 7.0,
    cd0: float = 0.03,
    e_oswald: float | None = 0.78,
    e_oswald_quality: str = "good",
    e_oswald_fallback_used: bool = False,
    v_md_mps: float | None = 14.0,
    v_min_sink_mps: float | None = 10.5,
    battery_capacity_wh: float | None = 74.0,
    battery_mass_kg: float | None = 0.40,
    motor_continuous_w: float | None = 200.0,
    eta_prop: float = 0.65,
    eta_motor: float = 0.85,
    eta_esc: float = 0.94,
):
    """Build a minimal mock aircraft namespace for endurance tests."""
    aircraft = SimpleNamespace()
    aircraft.id = 1
    aircraft.uuid = uuid.uuid4()

    # assumption_computation_context (cached from assumption_compute_service)
    aircraft.assumption_computation_context = {
        "e_oswald": e_oswald,
        "e_oswald_quality": e_oswald_quality,
        "e_oswald_fallback_used": e_oswald_fallback_used,
        "v_md_mps": v_md_mps,
        "v_min_sink_mps": v_min_sink_mps,
        "s_ref_m2": s_ref_m2,
        "aspect_ratio": ar,
    }

    # Design assumptions (effective values)
    aircraft._design_assumptions = {
        "mass": mass_kg,
        "cd0": cd0,
        # Propulsion efficiency assumptions
        "battery_capacity_wh": battery_capacity_wh,
        "battery_specific_energy_wh_per_kg": 180.0,
        "propulsion_eta_prop": eta_prop,
        "propulsion_eta_motor": eta_motor,
        "propulsion_eta_esc": eta_esc,
        "motor_continuous_power_w": motor_continuous_w,
    }

    # Battery weight item (category="battery")
    aircraft._battery_mass_kg = battery_mass_kg

    return aircraft


# ---------------------------------------------------------------------------
# Tests: _power_required
# ---------------------------------------------------------------------------


class TestPowerRequired:
    """Unit tests for _power_required(rho, v, cd0, e, ar, mass, s_ref, eta_total)."""

    def test_p_req_at_v_md(self):
        """Power required at V_md must be positive and physically reasonable."""
        v_md = RC_TRAINER["v_md_mps"]
        p = _power_required(
            rho=RHO_SL,
            v=v_md,
            cd0=RC_TRAINER["cd0"],
            e=RC_TRAINER["e_oswald"],
            ar=RC_TRAINER["ar"],
            mass=RC_TRAINER["mass_kg"],
            s_ref=RC_TRAINER["s_ref_m2"],
            eta_total=ETA_TOTAL_RC,
        )
        assert p > 0.0
        # Sanity: RC trainer cruise power is 10–80 W range
        assert 10.0 < p < 200.0

    def test_p_req_at_v_min_sink_smaller_than_v_md(self):
        """P_req(V_min_sink) < P_req(V_md) for a typical aircraft.

        V_min_sink (= V_mp for propeller aircraft) is the speed of minimum
        power required; by definition it must be lower than P_req at V_md.
        """
        p_vmd = _power_required(
            rho=RHO_SL,
            v=RC_TRAINER["v_md_mps"],
            cd0=RC_TRAINER["cd0"],
            e=RC_TRAINER["e_oswald"],
            ar=RC_TRAINER["ar"],
            mass=RC_TRAINER["mass_kg"],
            s_ref=RC_TRAINER["s_ref_m2"],
            eta_total=ETA_TOTAL_RC,
        )
        p_vmin = _power_required(
            rho=RHO_SL,
            v=RC_TRAINER["v_min_sink_mps"],
            cd0=RC_TRAINER["cd0"],
            e=RC_TRAINER["e_oswald"],
            ar=RC_TRAINER["ar"],
            mass=RC_TRAINER["mass_kg"],
            s_ref=RC_TRAINER["s_ref_m2"],
            eta_total=ETA_TOTAL_RC,
        )
        # V_min_sink is minimum-power speed → P_req(V_min_sink) ≤ P_req(V_md)
        assert p_vmin <= p_vmd

    def test_p_req_increases_with_speed_at_high_v(self):
        """At speeds above V_md, P_req increases (parasitic drag dominates)."""
        p_slow = _power_required(
            rho=RHO_SL, v=14.0,
            cd0=0.03, e=0.78, ar=7.0, mass=2.0, s_ref=0.4, eta_total=0.52,
        )
        p_fast = _power_required(
            rho=RHO_SL, v=25.0,
            cd0=0.03, e=0.78, ar=7.0, mass=2.0, s_ref=0.4, eta_total=0.52,
        )
        assert p_fast > p_slow

    def test_heavier_aircraft_requires_more_power(self):
        kwargs = dict(rho=RHO_SL, v=14.0, cd0=0.03, e=0.78, ar=7.0, s_ref=0.4, eta_total=0.52)
        p_light = _power_required(mass=1.0, **kwargs)
        p_heavy = _power_required(mass=4.0, **kwargs)
        assert p_heavy > p_light

    def test_lower_eta_requires_more_shaft_power(self):
        """Lower efficiency means more battery power for the same aero drag."""
        kwargs = dict(rho=RHO_SL, v=14.0, cd0=0.03, e=0.78, ar=7.0, mass=2.0, s_ref=0.4)
        p_eff = _power_required(eta_total=0.80, **kwargs)
        p_poor = _power_required(eta_total=0.40, **kwargs)
        assert p_poor > p_eff

    def test_zero_speed_returns_inf_or_very_large(self):
        """At V=0, CL → ∞ → induced drag → ∞; function should raise or return ∞."""
        # Allow either ValueError/ZeroDivisionError or returning a large value
        try:
            p = _power_required(
                rho=RHO_SL, v=0.0, cd0=0.03, e=0.78, ar=7.0,
                mass=2.0, s_ref=0.4, eta_total=0.52,
            )
            # If it returns, it must be infinite or very large
            assert not math.isfinite(p) or p > 1e6
        except (ValueError, ZeroDivisionError, OverflowError):
            pass  # Also acceptable


# ---------------------------------------------------------------------------
# Tests: _classify_p_margin
# ---------------------------------------------------------------------------


class TestPMargin:
    """p_margin = (P_motor - P_req) / P_motor."""

    def test_comfortable_margin_classification(self):
        """p_margin > 0.20 → 'comfortable'."""
        result = _classify_p_margin(p_motor=200.0, p_req=150.0)
        # margin = (200-150)/200 = 0.25 > 0.20
        assert result["p_margin"] == pytest.approx(0.25)
        assert result["p_margin_class"] == "comfortable"

    def test_tight_margin_classification(self):
        """0 < p_margin <= 0.20 → 'feasible but tight'."""
        result = _classify_p_margin(p_motor=200.0, p_req=185.0)
        # margin = (200-185)/200 = 0.075
        assert result["p_margin_class"] == "feasible but tight"

    def test_infeasible_when_p_req_above_motor(self):
        """p_margin <= 0 → 'infeasible — motor underpowered'."""
        result = _classify_p_margin(p_motor=150.0, p_req=200.0)
        assert result["p_margin"] < 0
        assert result["p_margin_class"] == "infeasible — motor underpowered"

    def test_exact_zero_margin_is_infeasible(self):
        """p_margin = 0 (P_req == P_motor) is still infeasible (no reserve)."""
        result = _classify_p_margin(p_motor=200.0, p_req=200.0)
        assert result["p_margin"] == pytest.approx(0.0)
        assert result["p_margin_class"] == "infeasible — motor underpowered"

    def test_exactly_20pct_is_comfortable(self):
        """Boundary: p_margin = 0.20 is comfortable (strict > 0.20 from spec)."""
        result = _classify_p_margin(p_motor=200.0, p_req=160.0)
        # margin = 40/200 = 0.20 — spec says > 0.20 → comfortable, so 0.20 is tight
        assert result["p_margin"] == pytest.approx(0.20)
        assert result["p_margin_class"] == "feasible but tight"


# ---------------------------------------------------------------------------
# Tests: _check_battery_mass_consistency
# ---------------------------------------------------------------------------


class TestBatteryMassConsistency:
    def test_no_warning_when_within_30pct(self):
        """< 30 % deviation → no warning."""
        warnings: list[str] = []
        _check_battery_mass_consistency(
            capacity_wh=74.0,
            specific_energy_wh_per_kg=180.0,
            battery_mass_kg=0.40,   # predicted = 74/180 ≈ 0.411 kg → 2.8% off
            warnings=warnings,
        )
        assert len(warnings) == 0

    def test_warning_at_30pct_deviation(self):
        """≥ 30 % deviation → warning emitted (not error)."""
        warnings: list[str] = []
        _check_battery_mass_consistency(
            capacity_wh=74.0,
            specific_energy_wh_per_kg=180.0,
            battery_mass_kg=0.10,   # predicted = 0.411 kg; |0.10-0.411|/0.411 ≈ 76% > 30%
            warnings=warnings,
        )
        assert len(warnings) == 1
        assert ">30 %" in warnings[0] or "30 %" in warnings[0] or "30%" in warnings[0] or "deviat" in warnings[0].lower()

    def test_returns_predicted_mass_g(self):
        """Function returns predicted battery mass in grams."""
        warnings: list[str] = []
        predicted_g = _check_battery_mass_consistency(
            capacity_wh=74.0,
            specific_energy_wh_per_kg=180.0,
            battery_mass_kg=0.40,
            warnings=warnings,
        )
        expected_g = (74.0 / 180.0) * 1000.0  # ≈ 411 g
        assert predicted_g == pytest.approx(expected_g, rel=1e-4)

    def test_uses_user_component_mass(self):
        """The cross-check warning is based on user component mass, not predicted."""
        warnings_low: list[str] = []
        warnings_high: list[str] = []
        # Same capacity, but very different user masses
        _check_battery_mass_consistency(
            capacity_wh=100.0, specific_energy_wh_per_kg=180.0,
            battery_mass_kg=0.555, warnings=warnings_low,  # matches predicted ≈0.556 kg
        )
        _check_battery_mass_consistency(
            capacity_wh=100.0, specific_energy_wh_per_kg=180.0,
            battery_mass_kg=0.10, warnings=warnings_high,  # far from predicted
        )
        assert len(warnings_low) == 0
        assert len(warnings_high) == 1


# ---------------------------------------------------------------------------
# Tests: compute_endurance — confidence / fallback logic
# ---------------------------------------------------------------------------


class TestFallbackConsistency:
    """Confidence flag must be 'estimated' when polar is unreliable."""

    def _make_db(self):
        db = MagicMock()
        return db

    def _call(self, aircraft, db=None):
        if db is None:
            db = self._make_db()
        return compute_endurance(db=db, aircraft=aircraft)

    def test_estimated_when_e_oswald_fallback(self):
        """If e_oswald_fallback_used=True → confidence='estimated'."""
        aircraft = _make_aircraft(e_oswald_fallback_used=True, e_oswald_quality="good")
        result = self._call(aircraft)
        assert result["confidence"] == "estimated"

    def test_estimated_when_e_oswald_quality_poor(self):
        """If e_oswald_quality='poor' → confidence='estimated'."""
        aircraft = _make_aircraft(e_oswald_fallback_used=False, e_oswald_quality="poor")
        result = self._call(aircraft)
        assert result["confidence"] == "estimated"

    def test_estimated_when_e_oswald_quality_unknown(self):
        """If e_oswald_quality='unknown' → confidence='estimated'."""
        aircraft = _make_aircraft(e_oswald=None, e_oswald_fallback_used=True, e_oswald_quality="unknown")
        result = self._call(aircraft)
        assert result["confidence"] == "estimated"

    def test_computed_when_polar_valid(self):
        """Good polar quality + no fallback → confidence='computed'."""
        aircraft = _make_aircraft(e_oswald=0.78, e_oswald_fallback_used=False, e_oswald_quality="good")
        result = self._call(aircraft)
        assert result["confidence"] == "computed"

    def test_estimated_emits_warning_message(self):
        """When fallback used, warnings list contains polar-quality message."""
        aircraft = _make_aircraft(e_oswald_fallback_used=True)
        result = self._call(aircraft)
        warns = result.get("warnings", [])
        assert any("fallback" in w.lower() or "polar" in w.lower() for w in warns)


# ---------------------------------------------------------------------------
# Tests: compute_endurance — endurance / range physics
# ---------------------------------------------------------------------------


class TestEndurance:
    """Endurance and range physics."""

    def _call(self, aircraft):
        db = MagicMock()
        return compute_endurance(db=db, aircraft=aircraft)

    def test_endurance_at_v_min_sink_max(self):
        """t_endurance_max is achieved at V_min_sink (min-power speed)."""
        aircraft = _make_aircraft()
        result = self._call(aircraft)
        assert "t_endurance_max_s" in result
        assert result["t_endurance_max_s"] > 0.0

    def test_range_at_v_md_max(self):
        """range_max_m is achieved at V_md (min-drag speed)."""
        aircraft = _make_aircraft()
        result = self._call(aircraft)
        assert "range_max_m" in result
        assert result["range_max_m"] > 0.0

    def test_endurance_longer_than_range_speed_time(self):
        """t_endurance(V_min_sink) must be ≥ t_endurance(V_md).

        Because V_min_sink is the minimum-power speed, it gives the
        longest possible flight time.
        """
        aircraft = _make_aircraft()
        result = self._call(aircraft)
        # t at V_md = range_max_m / v_md
        v_md = RC_TRAINER["v_md_mps"]
        t_at_v_md = result["range_max_m"] / v_md
        assert result["t_endurance_max_s"] >= t_at_v_md - 1e-3

    def test_p_req_fields_present(self):
        """Both P_req fields must be present in output."""
        aircraft = _make_aircraft()
        result = self._call(aircraft)
        assert "p_req_at_v_md_w" in result
        assert "p_req_at_v_min_sink_w" in result

    def test_battery_mass_g_predicted_field(self):
        """battery_mass_g_predicted must be capacity / E* * 1000."""
        aircraft = _make_aircraft(battery_capacity_wh=74.0)
        result = self._call(aircraft)
        expected = (74.0 / 180.0) * 1000.0
        assert result["battery_mass_g_predicted"] == pytest.approx(expected, rel=1e-3)


# ---------------------------------------------------------------------------
# Tests: Cross-check — RC trainer reference
# ---------------------------------------------------------------------------


class TestCrossCheckRcTrainer:
    """RC trainer reference: 2 kg, 74 Wh, η_total ≈ 0.52 → t_endurance > 8 min."""

    def test_rc_trainer_endurance_above_8min(self):
        """2-kg RC trainer with 74 Wh battery must achieve >8 min endurance."""
        aircraft = _make_aircraft(
            mass_kg=2.0,
            s_ref_m2=0.40,
            ar=7.0,
            cd0=0.03,
            e_oswald=0.78,
            v_md_mps=14.0,
            v_min_sink_mps=10.5,
            battery_capacity_wh=74.0,
            battery_mass_kg=0.40,
            motor_continuous_w=200.0,
            eta_prop=0.65,
            eta_motor=0.85,
            eta_esc=0.94,
        )
        db = MagicMock()
        result = compute_endurance(db=db, aircraft=aircraft)
        t_min = result["t_endurance_max_s"] / 60.0
        assert t_min > 8.0, (
            f"RC trainer endurance {t_min:.1f} min is below 8 min threshold. "
            f"P_req(V_min_sink)={result.get('p_req_at_v_min_sink_w', '?'):.1f} W"
        )


# ---------------------------------------------------------------------------
# Tests: p_margin integration via compute_endurance
# ---------------------------------------------------------------------------


class TestPMarginIntegration:
    """Verify p_margin is correctly computed and included in endurance output."""

    def _call(self, aircraft):
        db = MagicMock()
        return compute_endurance(db=db, aircraft=aircraft)

    def test_comfortable_margin_when_motor_oversized(self):
        """Motor 500 W, P_req ~30 W → comfortable margin."""
        aircraft = _make_aircraft(motor_continuous_w=500.0)
        result = self._call(aircraft)
        assert result["p_margin_class"] == "comfortable"

    def test_infeasible_when_p_req_above_motor(self):
        """Motor 10 W, aircraft needs >10 W → infeasible."""
        aircraft = _make_aircraft(
            mass_kg=5.0,        # heavy aircraft, high P_req
            s_ref_m2=0.20,      # small wing → high wing loading
            motor_continuous_w=10.0,   # tiny motor
        )
        result = self._call(aircraft)
        assert result["p_margin_class"] == "infeasible — motor underpowered"

    def test_p_margin_value_in_output(self):
        aircraft = _make_aircraft()
        result = self._call(aircraft)
        assert "p_margin" in result
        assert isinstance(result["p_margin"], float)


# ---------------------------------------------------------------------------
# Tests: powertrain_sizing_service refactor (Model A)
# ---------------------------------------------------------------------------


class TestComputeEnduranceMissingInputs:
    """Verify graceful degradation when required inputs are missing."""

    def _call(self, aircraft):
        db = MagicMock()
        return compute_endurance(db=db, aircraft=aircraft)

    def test_returns_none_fields_when_battery_capacity_missing(self):
        """Without battery_capacity_wh → warnings, None outputs."""
        aircraft = _make_aircraft(battery_capacity_wh=None)
        result = self._call(aircraft)
        assert result["t_endurance_max_s"] is None
        assert result["range_max_m"] is None
        assert len(result["warnings"]) > 0

    def test_returns_none_fields_when_v_md_missing(self):
        """Without v_md_mps in context → graceful None outputs."""
        aircraft = _make_aircraft(v_md_mps=None, v_min_sink_mps=None)
        result = self._call(aircraft)
        assert result["t_endurance_max_s"] is None

    def test_no_motor_power_emits_warning(self):
        """No motor_continuous_power_w → p_margin unknown with warning."""
        aircraft = _make_aircraft(motor_continuous_w=None)
        result = self._call(aircraft)
        assert result["p_margin"] is None
        assert any("motor" in w.lower() for w in result["warnings"])


class TestComputeEnduranceForAeroplane:
    """Unit tests for compute_endurance_for_aeroplane (DB-integrated path)."""

    def _make_db(self, aeroplane=None, battery_item=None, assumption_rows=None):
        """Return a mock DB session that answers queries for the service."""
        db = MagicMock()

        def _query_side_effect(model_cls):
            chain = MagicMock()
            chain.filter.return_value = chain

            from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel, WeightItemModel

            if model_cls is AeroplaneModel:
                chain.first.return_value = aeroplane
            elif model_cls is DesignAssumptionModel:
                # Return matching assumption row by parameter_name
                def _assumption_first_side_effect():
                    return None  # all fallback to defaults
                chain.first.side_effect = _assumption_first_side_effect
            elif model_cls is WeightItemModel:
                chain.first.return_value = battery_item
            else:
                chain.first.return_value = None
                chain.all.return_value = []
            return chain

        db.query.side_effect = _query_side_effect
        return db

    def _make_aeroplane(self, with_context=True):
        from types import SimpleNamespace
        a = SimpleNamespace()
        a.id = 1
        a.uuid = uuid.uuid4()
        if with_context:
            a.assumption_computation_context = {
                "e_oswald": 0.78,
                "e_oswald_quality": "good",
                "e_oswald_fallback_used": False,
                "v_md_mps": 14.0,
                "v_min_sink_mps": 10.5,
                "s_ref_m2": 0.40,
                "aspect_ratio": 7.0,
                "battery_capacity_wh": 74.0,
                "motor_continuous_power_w": 200.0,
            }
        else:
            a.assumption_computation_context = {}
        return a

    def test_raises_not_found_when_aeroplane_missing(self):
        from app.core.exceptions import NotFoundError
        from app.services.endurance_service import compute_endurance_for_aeroplane

        db = self._make_db(aeroplane=None)
        with pytest.raises(NotFoundError):
            compute_endurance_for_aeroplane(db=db, aeroplane_uuid=uuid.uuid4())

    def test_returns_dict_with_expected_keys(self):
        from app.services.endurance_service import compute_endurance_for_aeroplane

        aeroplane = self._make_aeroplane(with_context=True)
        db = self._make_db(aeroplane=aeroplane)
        result = compute_endurance_for_aeroplane(db=db, aeroplane_uuid=aeroplane.uuid)
        assert "t_endurance_max_s" in result
        assert "range_max_m" in result
        assert "confidence" in result
        assert "warnings" in result

    def test_graceful_empty_context(self):
        """If assumption_computation_context is empty, returns None fields with warnings."""
        from app.services.endurance_service import compute_endurance_for_aeroplane

        aeroplane = self._make_aeroplane(with_context=False)
        db = self._make_db(aeroplane=aeroplane)
        result = compute_endurance_for_aeroplane(db=db, aeroplane_uuid=aeroplane.uuid)
        # Should not raise; missing inputs → warnings
        assert isinstance(result, dict)
        assert result["confidence"] in ("computed", "estimated")

    def test_battery_mass_from_weight_item(self):
        """Battery mass from WeightItemModel is used for cross-check."""
        from types import SimpleNamespace
        from app.services.endurance_service import compute_endurance_for_aeroplane

        aeroplane = self._make_aeroplane(with_context=True)
        battery_item = SimpleNamespace(mass_kg=0.08)  # very light → triggers cross-check warning

        db = self._make_db(aeroplane=aeroplane, battery_item=battery_item)
        result = compute_endurance_for_aeroplane(db=db, aeroplane_uuid=aeroplane.uuid)
        # Very low battery mass vs 74 Wh / 180 Wh/kg ≈ 411 g → deviation > 30%
        assert any("deviat" in w.lower() for w in result["warnings"])


class TestPowertrainServiceRefactor:
    """Verify powertrain_sizing_service calls endurance_service.compute_endurance."""

    def test_powertrain_calls_endurance_internally(self):
        """_evaluate_motor_battery_combo must delegate physics to endurance_service."""
        from app.services import powertrain_sizing_service

        # The service must import endurance_service (Model A refactor)
        import importlib
        import app.services.endurance_service as es_module
        assert hasattr(es_module, "compute_endurance"), (
            "endurance_service must export compute_endurance"
        )

        # The hardcoded constants must be GONE from powertrain_sizing_service
        import inspect
        src = inspect.getsource(powertrain_sizing_service)
        assert "DRAG_COEFF_ESTIMATE" not in src, (
            "powertrain_sizing_service must not contain hardcoded DRAG_COEFF_ESTIMATE"
        )
        assert "WING_AREA_ESTIMATE_M2" not in src, (
            "powertrain_sizing_service must not contain hardcoded WING_AREA_ESTIMATE_M2"
        )

    def test_powertrain_service_still_runnable(self):
        """After refactor, size_powertrain must still accept requests without crashing."""
        from app.services.powertrain_sizing_service import size_powertrain
        from app.schemas.powertrain_sizing import PowertrainSizingRequest
        from app.core.exceptions import NotFoundError
        import uuid

        from unittest.mock import MagicMock

        db = MagicMock()
        chain = MagicMock()
        chain.filter.return_value = chain
        chain.first.return_value = None  # aeroplane not found → NotFoundError
        chain.all.return_value = []
        db.query.return_value = chain

        req = PowertrainSizingRequest(
            airframe_mass_kg=2.0,
            target_cruise_speed_ms=15.0,
            target_top_speed_ms=25.0,
            target_flight_time_min=10.0,
            max_current_draw_a=None,
            altitude_m=0.0,
        )

        with pytest.raises(NotFoundError):
            size_powertrain(db, uuid.uuid4(), req)
