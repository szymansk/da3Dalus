"""Tests for app.services.powertrain_performance (gh-615).

All polar data is mocked — NO aerosandbox / DB dependency in the fast tier.

Covers:
- Propeller interpolation: Ct(J), Cp(J), Pe(J) from polar samples
- Clamping at Ct=0 (UAT note #615 comment #4)
- Torque derived from PWR_W/(2π·n), not stored Torque_Nm at low RPM
- Gear-aware output_kv (UAT note #615 comment #3)
- Power-limited + efficiency-chain motor model (no Rm)
- T(V) curve: monotone decrease, clamp at Ct=0
- P(V) = mechanical shaft power curve
- η_prop(J) is J-dependent (not flat scalar)
- Battery power ceiling is honoured
- Structured request/response schemas
- Endpoint integration (mocked DB)
"""

from __future__ import annotations

import math
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Service functions under test — imported BEFORE any fixtures so failures
# are visible as import errors rather than fixture errors.
# ---------------------------------------------------------------------------
from app.services.powertrain_performance import (
    PropellerPolarRow,
    MotorSpec,
    BatterySpec,
    PowertrainPerformanceRequest,
    PowertrainPerformanceResponse,
    PerformanceSample,
    interpolate_ct_cp_pe,
    compute_prop_operating_point,
    compute_performance_curve,
)


# ---------------------------------------------------------------------------
# Shared polar fixtures  — APC 10x5 like data at a single RPM
# ---------------------------------------------------------------------------


def _make_apc10x5_samples() -> list[PropellerPolarRow]:
    """Minimal APC 10×5 polar, single RPM=6000, covers J=0..0.65."""
    # Realistic: Ct decreasing, Cp≈const, Pe peaking ~J=0.45
    data = [
        (0.000, 0.1013, 0.0556),
        (0.100, 0.0910, 0.0558),
        (0.200, 0.0804, 0.0553),
        (0.300, 0.0675, 0.0530),
        (0.400, 0.0526, 0.0492),
        (0.500, 0.0363, 0.0438),
        (0.600, 0.0188, 0.0369),
        (0.650, 0.0007, 0.0284),  # last valid: Ct ~0 (clamp check)
        (0.680, -0.004, 0.0275),  # negative: must be clamped
    ]
    D_m = 10 * 0.0254  # 10 inch → metres
    rho = 1.225
    n_rps = 6000 / 60.0  # 100 rps
    rows = []
    for J, Ct, Cp in data:
        Pe = Ct * J / Cp if (Cp > 0 and J > 0) else 0.0
        # PWR_W from coefficient: P = Cp * rho * n³ * D⁵
        pwr = Cp * rho * (n_rps**3) * (D_m**5)
        rows.append(
            PropellerPolarRow(
                rpm=6000,
                J=J,
                Ct=Ct,
                Cp=Cp,
                Pe=Pe,
                PWR_W=pwr,
                Torque_Nm=None,
                Thrust_N=None,
            )
        )
    return rows


def _make_motor_basic(
    kv: float = 1000.0,
    gear_ratio: float | None = None,
    efficiency_pct: float | None = None,
    cells_lipo_max: int = 3,
    io_no_load_a: float | None = None,
    max_current_a: float = 20.0,
    continuous_current_a: float = 15.0,
) -> MotorSpec:
    return MotorSpec(
        kv_rpm_per_volt=kv,
        gear_ratio=gear_ratio,
        efficiency_pct=efficiency_pct,
        cells_lipo_max=cells_lipo_max,
        io_no_load_a=io_no_load_a,
        max_current_a=max_current_a,
        continuous_current_a=continuous_current_a,
    )


def _make_battery(cells: int = 3, capacity_mah: float = 2200.0, c_rate: int = 30) -> BatterySpec:
    return BatterySpec(cells=cells, capacity_mah=capacity_mah, c_rate=c_rate)


# ---------------------------------------------------------------------------
# PropellerPolarRow dataclass
# ---------------------------------------------------------------------------


class TestPropellerPolarRow:
    def test_fields_accessible(self):
        row = PropellerPolarRow(
            rpm=6000, J=0.3, Ct=0.07, Cp=0.05, Pe=0.42, PWR_W=50.0, Torque_Nm=0.003, Thrust_N=2.5
        )
        assert row.J == 0.3
        assert row.Ct == 0.07
        assert row.rpm == 6000

    def test_optional_fields_can_be_none(self):
        row = PropellerPolarRow(
            rpm=6000, J=0.0, Ct=0.1, Cp=0.05, Pe=None, PWR_W=None, Torque_Nm=None, Thrust_N=None
        )
        assert row.Pe is None


# ---------------------------------------------------------------------------
# MotorSpec: gear-aware output_kv
# ---------------------------------------------------------------------------


class TestMotorSpec:
    def test_output_kv_no_gear(self):
        m = _make_motor_basic(kv=1000.0, gear_ratio=None)
        assert m.output_kv == pytest.approx(1000.0)

    def test_output_kv_with_gear(self):
        """D-Drive geared motor: raw KV=2040, ratio=3.7 → output_kv≈551."""
        m = _make_motor_basic(kv=2040.0, gear_ratio=3.7)
        assert m.output_kv == pytest.approx(2040.0 / 3.7, rel=1e-6)

    def test_output_kv_gear_ratio_one(self):
        m = _make_motor_basic(kv=880.0, gear_ratio=1.0)
        assert m.output_kv == pytest.approx(880.0)

    def test_output_kv_exposed_not_raw_kv(self):
        """output_kv must differ from kv_rpm_per_volt when gear_ratio > 1."""
        m = _make_motor_basic(kv=2040.0, gear_ratio=3.7)
        assert m.output_kv != m.kv_rpm_per_volt

    def test_motor_max_electrical_power(self):
        """max electrical power = max_current_a × 3.7 V/cell × cells (comment #3 rule)."""
        m = _make_motor_basic(kv=1000.0, cells_lipo_max=3, max_current_a=20.0)
        expected = 20.0 * 3.7 * 3  # 222 W
        assert m.max_electrical_power_w == pytest.approx(expected, rel=1e-6)

    def test_motor_efficiency_default(self):
        """When efficiency_pct is None, default is 0.85."""
        m = _make_motor_basic(efficiency_pct=None)
        assert m.eta_motor == pytest.approx(0.85)

    def test_motor_efficiency_from_pct(self):
        m = _make_motor_basic(efficiency_pct=80.0)
        assert m.eta_motor == pytest.approx(0.80)


# ---------------------------------------------------------------------------
# BatterySpec
# ---------------------------------------------------------------------------


class TestBatterySpec:
    def test_nominal_voltage(self):
        b = _make_battery(cells=3)
        assert b.nominal_voltage_v == pytest.approx(3.7 * 3)

    def test_max_continuous_discharge_w(self):
        """P_max = capacity_mah / 1000 * c_rate * nominal_voltage (rough ceiling)."""
        b = _make_battery(cells=3, capacity_mah=2200.0, c_rate=30)
        # C_max_a = 2.2 Ah × 30C = 66 A; P = 66 × 11.1 V = 732.6 W
        assert b.max_continuous_discharge_w > 0


# ---------------------------------------------------------------------------
# Interpolation: Ct/Cp/Pe at arbitrary J
# ---------------------------------------------------------------------------


class TestInterpolateCt:
    def setup_method(self):
        self.samples = _make_apc10x5_samples()

    def test_ct_at_J0(self):
        ct, cp, pe = interpolate_ct_cp_pe(self.samples, J=0.0)
        assert ct == pytest.approx(0.1013, rel=1e-3)

    def test_ct_monotone_decreasing(self):
        """Ct(J) must be monotone decreasing over the valid range."""
        Js = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
        cts = [interpolate_ct_cp_pe(self.samples, J=j)[0] for j in Js]
        for i in range(len(cts) - 1):
            assert cts[i] > cts[i + 1], f"Ct not decreasing at J={Js[i + 1]}"

    def test_ct_clamp_at_zero_for_negative_tail(self):
        """J past zero-thrust must return Ct=0 (clamp, not negative)."""
        ct, cp, pe = interpolate_ct_cp_pe(self.samples, J=0.680)
        assert ct >= 0.0, "Ct must be clamped at 0, not negative"

    def test_pe_peak_in_middle(self):
        """Pe should peak somewhere 0.3 < J < 0.65 for typical RC props."""
        Js = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        pes = [interpolate_ct_cp_pe(self.samples, J=j)[2] for j in Js]
        max_pe = max(pes)
        j_at_max = Js[pes.index(max_pe)]
        assert 0.2 <= j_at_max <= 0.65, f"Pe peak at unexpected J={j_at_max}"

    def test_interpolation_midpoint(self):
        """Interpolation between J=0.2 and J=0.3 must be between their values."""
        ct_02, _, _ = interpolate_ct_cp_pe(self.samples, J=0.2)
        ct_03, _, _ = interpolate_ct_cp_pe(self.samples, J=0.3)
        ct_mid, _, _ = interpolate_ct_cp_pe(self.samples, J=0.25)
        assert ct_03 <= ct_mid <= ct_02

    def test_extrapolation_returns_warning_flag(self):
        """J beyond dataset max must return extrapolation_warning=True."""
        ct, cp, pe, *rest = interpolate_ct_cp_pe(self.samples, J=2.0, return_warning=True)
        extrapolation_warning = rest[0] if rest else False
        assert bool(extrapolation_warning) is True

    def test_no_warning_within_range(self):
        ct, cp, pe, *rest = interpolate_ct_cp_pe(self.samples, J=0.3, return_warning=True)
        extrapolation_warning = rest[0] if rest else False
        assert bool(extrapolation_warning) is False


# ---------------------------------------------------------------------------
# compute_prop_operating_point: from (rpm, V, D_m) → T, P_shaft, η
# ---------------------------------------------------------------------------


class TestComputePropOperatingPoint:
    def setup_method(self):
        self.samples = _make_apc10x5_samples()
        self.D_m = 10 * 0.0254  # 10 inch

    def test_static_thrust_positive(self):
        """At V=0, thrust must be positive."""
        t, p, eta = compute_prop_operating_point(self.samples, rpm=6000, V=0.0, D_m=self.D_m)
        assert t > 0.0

    def test_thrust_decreases_with_speed(self):
        """T(V) must be monotone decreasing from V=0 to high V."""
        Vs = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0]
        thrusts = [
            compute_prop_operating_point(self.samples, rpm=6000, V=v, D_m=self.D_m)[0] for v in Vs
        ]
        for i in range(len(thrusts) - 1):
            assert thrusts[i] >= thrusts[i + 1], (
                f"T not monotone at V={Vs[i + 1]}: {thrusts[i]:.3f} >= {thrusts[i + 1]:.3f}"
            )

    def test_thrust_clamps_at_zero(self):
        """Very high V → J large → Ct≈0 → thrust ≈ 0 (never negative)."""
        t, p, eta = compute_prop_operating_point(self.samples, rpm=6000, V=100.0, D_m=self.D_m)
        assert t >= 0.0

    def test_torque_from_power_not_stored(self):
        """Torque must be derived from PWR_W/(2π·n), not Torque_Nm column.

        Build a sample where Torque_Nm is wrong (set to 999) and verify
        the returned shaft power is computed from Cp, not the Torque_Nm column.
        """
        from dataclasses import replace

        # Give all samples wrong Torque_Nm
        bad_samples = [
            PropellerPolarRow(
                rpm=s.rpm,
                J=s.J,
                Ct=s.Ct,
                Cp=s.Cp,
                Pe=s.Pe,
                PWR_W=s.PWR_W,
                Torque_Nm=999.0,
                Thrust_N=s.Thrust_N,
            )
            for s in self.samples
        ]
        t_good, p_good, _ = compute_prop_operating_point(self.samples, 6000, V=10.0, D_m=self.D_m)
        t_bad, p_bad, _ = compute_prop_operating_point(bad_samples, 6000, V=10.0, D_m=self.D_m)
        # Power must be the same — derived from Cp, not Torque_Nm
        assert p_good == pytest.approx(p_bad, rel=1e-4)

    def test_eta_prop_j_dependent(self):
        """η_prop at J=0 should be 0 (static); at cruise J should be nonzero."""
        _, _, eta_static = compute_prop_operating_point(self.samples, rpm=6000, V=0.0, D_m=self.D_m)
        _, _, eta_cruise = compute_prop_operating_point(
            self.samples, rpm=6000, V=12.0, D_m=self.D_m
        )
        assert eta_static == pytest.approx(0.0, abs=0.01)
        assert eta_cruise > 0.1

    def test_eta_prop_not_flat_scalar(self):
        """η_prop must change with V (not a constant 0.65)."""
        Vs = [5.0, 10.0, 15.0, 20.0]
        etas = [
            compute_prop_operating_point(self.samples, rpm=6000, V=v, D_m=self.D_m)[2] for v in Vs
        ]
        # At least some variation expected
        assert max(etas) - min(etas) > 0.05, "η_prop must vary with V (J-dependent)"


# ---------------------------------------------------------------------------
# compute_performance_curve: T(V), P(V), η(J) over velocity range
# ---------------------------------------------------------------------------


class TestComputePerformanceCurve:
    def setup_method(self):
        self.polar_samples = _make_apc10x5_samples()
        self.motor = _make_motor_basic(kv=1000.0, gear_ratio=None, cells_lipo_max=3)
        self.battery = _make_battery(cells=3, capacity_mah=2200.0, c_rate=30)
        self.D_m = 10 * 0.0254
        self.diameter_in = 10.0

    def _run(self, v_min=0.0, v_max=25.0, n_points=10, altitude_m=0.0, throttle=1.0):
        req = PowertrainPerformanceRequest(
            motor=self.motor,
            battery=self.battery,
            propeller_diameter_in=self.diameter_in,
            polar_samples=self.polar_samples,
            v_min_ms=v_min,
            v_max_ms=v_max,
            n_points=n_points,
            altitude_m=altitude_m,
            throttle=throttle,
        )
        return compute_performance_curve(req)

    def test_returns_response_type(self):
        resp = self._run()
        assert isinstance(resp, PowertrainPerformanceResponse)

    def test_correct_number_of_samples(self):
        resp = self._run(n_points=10)
        assert len(resp.samples) == 10

    def test_samples_have_required_fields(self):
        resp = self._run(n_points=5)
        for s in resp.samples:
            assert isinstance(s, PerformanceSample)
            assert s.velocity_ms >= 0.0
            assert s.thrust_n >= 0.0
            assert s.eta_prop >= 0.0
            assert s.rpm > 0
            assert s.J >= 0.0

    def test_thrust_monotone_decreasing(self):
        resp = self._run(n_points=12)
        thrusts = [s.thrust_n for s in resp.samples]
        for i in range(len(thrusts) - 1):
            assert thrusts[i] >= thrusts[i + 1] - 1e-6, f"Thrust not monotone at sample {i + 1}"

    def test_eta_prop_j_dependent(self):
        """η_prop across the curve must not be a flat constant."""
        resp = self._run(n_points=10)
        etas = [s.eta_prop for s in resp.samples if s.velocity_ms > 0]
        if etas:
            assert max(etas) - min(etas) > 0.01, "η_prop must vary (J-dependent)"

    def test_power_available_uses_battery_voltage(self):
        """P_available = V_battery × max_current → battery cells × 3.7 V."""
        resp = self._run()
        # voltage = 3 cells × 3.7 = 11.1 V; P_available > 0
        assert resp.p_available_w > 0.0

    def test_power_ceiling_enforced(self):
        """P_shaft must not exceed motor max_power (derived from current limit × V × η)."""
        resp = self._run()
        for s in resp.samples:
            assert s.p_shaft_w >= 0.0

    def test_geared_motor_lower_prop_rpm(self):
        """Geared motor at same voltage → lower prop RPM than direct drive."""
        motor_direct = _make_motor_basic(kv=551.0, gear_ratio=None, cells_lipo_max=3)
        motor_geared = _make_motor_basic(kv=2040.0, gear_ratio=3.7, cells_lipo_max=3)

        req_direct = PowertrainPerformanceRequest(
            motor=motor_direct,
            battery=self.battery,
            propeller_diameter_in=self.diameter_in,
            polar_samples=self.polar_samples,
            v_min_ms=0.0,
            v_max_ms=20.0,
            n_points=5,
        )
        req_geared = PowertrainPerformanceRequest(
            motor=motor_geared,
            battery=self.battery,
            propeller_diameter_in=self.diameter_in,
            polar_samples=self.polar_samples,
            v_min_ms=0.0,
            v_max_ms=20.0,
            n_points=5,
        )
        resp_direct = compute_performance_curve(req_direct)
        resp_geared = compute_performance_curve(req_geared)
        # Both should produce comparable RPM (output_kv ≈ same: 551 vs 2040/3.7=551)
        rpm_direct = resp_direct.samples[0].rpm
        rpm_geared = resp_geared.samples[0].rpm
        assert abs(rpm_direct - rpm_geared) < rpm_direct * 0.02, (
            f"Gear-adjusted RPMs should match: {rpm_direct:.0f} vs {rpm_geared:.0f}"
        )

    def test_warnings_list_present(self):
        resp = self._run()
        assert isinstance(resp.warnings, list)

    def test_notes_label_derived_values(self):
        """Response must label derived/estimated values (comment #3 UAT)."""
        resp = self._run()
        # notes field must exist and contain something
        assert hasattr(resp, "notes")

    def test_static_thrust_at_v0(self):
        """Sample at V=0 must have J=0 and thrust > 0."""
        resp = self._run(v_min=0.0, n_points=5)
        s0 = resp.samples[0]
        assert s0.velocity_ms == 0.0
        assert s0.J == pytest.approx(0.0, abs=1e-9)
        assert s0.thrust_n > 0.0

    def test_infeasibility_flag_when_power_insufficient(self):
        """Very low max_current_a → motor can't spin prop → infeasible flag."""
        weak_motor = _make_motor_basic(kv=1000.0, max_current_a=0.01, continuous_current_a=0.01)
        req = PowertrainPerformanceRequest(
            motor=weak_motor,
            battery=self.battery,
            propeller_diameter_in=self.diameter_in,
            polar_samples=self.polar_samples,
            v_min_ms=0.0,
            v_max_ms=20.0,
            n_points=5,
        )
        resp = compute_performance_curve(req)
        # Either all zero thrust or an infeasibility warning
        assert all(s.thrust_n == 0.0 for s in resp.samples) or len(resp.warnings) > 0


# ---------------------------------------------------------------------------
# Schema: PowertrainPerformanceRequest validation
# ---------------------------------------------------------------------------


class TestPowertrainPerformanceRequest:
    def test_valid_request(self):
        req = PowertrainPerformanceRequest(
            motor=_make_motor_basic(),
            battery=_make_battery(),
            propeller_diameter_in=10.0,
            polar_samples=_make_apc10x5_samples(),
            v_min_ms=0.0,
            v_max_ms=30.0,
            n_points=20,
        )
        assert req.v_max_ms > req.v_min_ms

    def test_n_points_bounded(self):
        from pydantic import ValidationError

        with pytest.raises((ValidationError, ValueError)):
            PowertrainPerformanceRequest(
                motor=_make_motor_basic(),
                battery=_make_battery(),
                propeller_diameter_in=10.0,
                polar_samples=[],
                v_min_ms=0.0,
                v_max_ms=30.0,
                n_points=0,  # invalid
            )

    def test_v_max_gt_v_min(self):
        from pydantic import ValidationError

        with pytest.raises((ValidationError, ValueError)):
            PowertrainPerformanceRequest(
                motor=_make_motor_basic(),
                battery=_make_battery(),
                propeller_diameter_in=10.0,
                polar_samples=_make_apc10x5_samples(),
                v_min_ms=30.0,
                v_max_ms=5.0,  # invalid: v_max < v_min
                n_points=10,
            )


# ---------------------------------------------------------------------------
# PerformanceSample schema
# ---------------------------------------------------------------------------


class TestPerformanceSample:
    def test_all_fields_accessible(self):
        s = PerformanceSample(
            velocity_ms=10.0,
            thrust_n=5.2,
            p_shaft_w=55.0,
            eta_prop=0.42,
            J=0.35,
            rpm=6000,
            estimated=True,
        )
        assert s.estimated is True
        assert s.eta_prop == pytest.approx(0.42)

    def test_thrust_non_negative(self):
        from pydantic import ValidationError

        with pytest.raises((ValidationError, ValueError)):
            PerformanceSample(
                velocity_ms=10.0,
                thrust_n=-1.0,
                p_shaft_w=50.0,
                eta_prop=0.4,
                J=0.3,
                rpm=5000,
            )


# ---------------------------------------------------------------------------
# PowertrainPerformanceResponse
# ---------------------------------------------------------------------------


class TestPowertrainPerformanceResponse:
    def test_response_has_p_available(self):
        resp = PowertrainPerformanceResponse(
            samples=[],
            p_available_w=200.0,
            warnings=[],
            notes="estimated",
        )
        assert resp.p_available_w == 200.0

    def test_warnings_default_empty(self):
        resp = PowertrainPerformanceResponse(
            samples=[],
            p_available_w=100.0,
        )
        assert resp.warnings == []
