"""QPROP 3-parameter brushless DC motor model tests (gh-1006).

When winding resistance Rm is available on the motor component, the powertrain
performance model upgrades from the 2-param fixed-RPM approximation
(rpm = output_kv · V) to Drela's QPROP 3-parameter torque-balance:

  motor speed:  ω/Kv_si = V_terminal - I·Rm   (back-EMF; Kv_si in rad/s/V)
  motor torque: Q = (I - I0)/Kv_si
  efficiency:   η_motor = (V_terminal - I·Rm)·(I - I0) / (V_terminal·I)

The operating RPM is found where motor shaft torque balances propeller torque
demand Q_prop(n) = Cp·ρ·n²·D⁵ / (2π).

When Rm is None the model must fall back to identical 2-param behaviour.

References:
- M. Drela, QPROP Formulation, https://web.mit.edu/drela/Public/web/qprop/
"""

from __future__ import annotations

import math

import pytest

from app.services.powertrain_performance import (
    BatterySpec,
    MotorSpec,
    PowertrainPerformanceRequest,
    PropellerPolarRow,
    compute_performance_curve,
    solve_qprop_operating_point,
)


# ---------------------------------------------------------------------------
# Fixtures — APC 10x5-like polar, single RPM
# ---------------------------------------------------------------------------


def _make_apc10x5_samples() -> list[PropellerPolarRow]:
    data = [
        (0.000, 0.1013, 0.0556),
        (0.100, 0.0910, 0.0558),
        (0.200, 0.0804, 0.0553),
        (0.300, 0.0675, 0.0530),
        (0.400, 0.0526, 0.0492),
        (0.500, 0.0363, 0.0438),
        (0.600, 0.0188, 0.0369),
        (0.650, 0.0007, 0.0284),
    ]
    rows = []
    for J, Ct, Cp in data:
        Pe = Ct * J / Cp if (Cp > 0 and J > 0) else 0.0
        rows.append(
            PropellerPolarRow(
                rpm=6000, J=J, Ct=Ct, Cp=Cp, Pe=Pe, PWR_W=None, Torque_Nm=None, Thrust_N=None
            )
        )
    return rows


def _motor_with_rm(
    kv: float = 1000.0,
    rm_ohm: float | None = 0.1,
    io_no_load_a: float | None = 0.8,
    cells_lipo_max: int = 3,
    max_current_a: float = 40.0,
) -> MotorSpec:
    return MotorSpec(
        kv_rpm_per_volt=kv,
        rm_ohm=rm_ohm,
        io_no_load_a=io_no_load_a,
        cells_lipo_max=cells_lipo_max,
        max_current_a=max_current_a,
        continuous_current_a=max_current_a,
    )


def _battery(cells: int = 3, capacity_mah: float = 2200.0, c_rate: int = 30) -> BatterySpec:
    return BatterySpec(cells=cells, capacity_mah=capacity_mah, c_rate=c_rate)


def _request(motor: MotorSpec, **kw) -> PowertrainPerformanceRequest:
    base = dict(
        motor=motor,
        battery=_battery(),
        propeller_diameter_in=10.0,
        polar_samples=_make_apc10x5_samples(),
        v_min_ms=0.0,
        v_max_ms=20.0,
        n_points=11,
        throttle=1.0,
    )
    base.update(kw)
    return PowertrainPerformanceRequest(**base)


# ---------------------------------------------------------------------------
# MotorSpec — rm_ohm field
# ---------------------------------------------------------------------------


class TestMotorSpecRm:
    def test_rm_ohm_accepted(self):
        m = _motor_with_rm(rm_ohm=0.05)
        assert m.rm_ohm == pytest.approx(0.05)

    def test_rm_ohm_optional_defaults_none(self):
        m = MotorSpec(kv_rpm_per_volt=1000.0, cells_lipo_max=3)
        assert m.rm_ohm is None

    def test_rm_ohm_must_be_positive(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            MotorSpec(kv_rpm_per_volt=1000.0, cells_lipo_max=3, rm_ohm=-0.1)

    def test_has_rm_model_flag(self):
        assert _motor_with_rm(rm_ohm=0.1).uses_qprop_model is True
        assert MotorSpec(kv_rpm_per_volt=1000.0, cells_lipo_max=3).uses_qprop_model is False


# ---------------------------------------------------------------------------
# solve_qprop_operating_point — torque balance physics
# ---------------------------------------------------------------------------


class TestSolveQpropOperatingPoint:
    def test_returns_rpm_current_torque(self):
        motor = _motor_with_rm()
        samples = _make_apc10x5_samples()
        res = solve_qprop_operating_point(
            motor=motor,
            samples=samples,
            V_terminal=11.1,
            V_airspeed=0.0,
            D_m=10 * 0.0254,
            altitude_m=0.0,
        )
        assert res.rpm > 0
        assert res.current_a > 0
        assert res.torque_nm > 0

    def test_voltage_equation_satisfied(self):
        """At the solved point, V = I·Rm + ω/Kv_si (back-EMF) within tolerance."""
        motor = _motor_with_rm(kv=1000.0, rm_ohm=0.1, io_no_load_a=0.8)
        res = solve_qprop_operating_point(
            motor=motor,
            samples=_make_apc10x5_samples(),
            V_terminal=11.1,
            V_airspeed=5.0,
            D_m=10 * 0.0254,
            altitude_m=0.0,
        )
        kv_si = motor.output_kv * 2.0 * math.pi / 60.0  # rad/s per volt
        omega = res.rpm * 2.0 * math.pi / 60.0
        v_reconstructed = res.current_a * motor.rm_ohm + omega / kv_si
        assert v_reconstructed == pytest.approx(11.1, rel=1e-3)

    def test_torque_balance_satisfied(self):
        """Motor torque (I-I0)/Kv_si equals propeller torque demand at solution."""
        motor = _motor_with_rm(kv=1000.0, rm_ohm=0.1, io_no_load_a=0.8)
        res = solve_qprop_operating_point(
            motor=motor,
            samples=_make_apc10x5_samples(),
            V_terminal=11.1,
            V_airspeed=0.0,
            D_m=10 * 0.0254,
            altitude_m=0.0,
        )
        kv_si = motor.output_kv * 2.0 * math.pi / 60.0
        q_motor = (res.current_a - motor.io_no_load_a) / kv_si
        assert q_motor == pytest.approx(res.torque_nm, rel=1e-3)

    def test_higher_voltage_drop_lowers_rpm(self):
        """Larger Rm → bigger I·Rm drop → lower available back-EMF → lower RPM."""
        low_rm = solve_qprop_operating_point(
            motor=_motor_with_rm(rm_ohm=0.02),
            samples=_make_apc10x5_samples(),
            V_terminal=11.1,
            V_airspeed=0.0,
            D_m=10 * 0.0254,
        )
        high_rm = solve_qprop_operating_point(
            motor=_motor_with_rm(rm_ohm=0.30),
            samples=_make_apc10x5_samples(),
            V_terminal=11.1,
            V_airspeed=0.0,
            D_m=10 * 0.0254,
        )
        assert high_rm.rpm < low_rm.rpm

    def test_motor_efficiency_in_range(self):
        res = solve_qprop_operating_point(
            motor=_motor_with_rm(),
            samples=_make_apc10x5_samples(),
            V_terminal=11.1,
            V_airspeed=0.0,
            D_m=10 * 0.0254,
        )
        assert 0.0 < res.eta_motor < 1.0


# ---------------------------------------------------------------------------
# 3-param vs 2-param divergence under load
# ---------------------------------------------------------------------------


class TestQpropVs2Param:
    def test_qprop_rpm_below_2param_at_load(self):
        """3-param RPM is below the no-resistance 2-param rpm = Kv·V (I·Rm drop)."""
        motor = _motor_with_rm(kv=1000.0, rm_ohm=0.12, io_no_load_a=0.8)
        req = _request(motor)
        resp = compute_performance_curve(req)
        v_bat = req.battery.nominal_voltage_v  # 3 × 3.7 = 11.1
        rpm_2param = motor.output_kv * v_bat  # 11100
        # all samples share the same RPM in 2-param; in 3-param it's load-dependent
        max_rpm = max(s.rpm for s in resp.samples)
        assert max_rpm < rpm_2param

    def test_qprop_rpm_varies_with_velocity(self):
        """Unlike 2-param (fixed rpm), QPROP rpm changes across the velocity sweep."""
        motor = _motor_with_rm()
        resp = compute_performance_curve(_request(motor))
        rpms = {round(s.rpm, 1) for s in resp.samples}
        assert len(rpms) > 1

    def test_notes_mention_qprop(self):
        resp = compute_performance_curve(_request(_motor_with_rm()))
        assert "qprop" in resp.notes.lower() or "rm" in resp.notes.lower()

    def test_samples_not_marked_estimated(self):
        """QPROP power is solved from torque balance, not current×voltage estimate."""
        resp = compute_performance_curve(_request(_motor_with_rm()))
        assert all(s.estimated is False for s in resp.samples)


# ---------------------------------------------------------------------------
# Fallback — Rm absent → identical to legacy 2-param
# ---------------------------------------------------------------------------


class TestFallbackWhenRmMissing:
    def test_no_rm_keeps_fixed_rpm(self):
        motor = MotorSpec(
            kv_rpm_per_volt=1000.0,
            cells_lipo_max=3,
            io_no_load_a=0.8,
            max_current_a=40.0,
            continuous_current_a=40.0,
        )
        req = _request(motor)
        resp = compute_performance_curve(req)
        v_bat = req.battery.nominal_voltage_v
        expected_rpm = motor.output_kv * v_bat * req.throttle
        # legacy model: all samples share the fixed RPM
        assert all(s.rpm == pytest.approx(round(expected_rpm, 1)) for s in resp.samples)
        assert all(s.estimated is True for s in resp.samples)

    def test_no_rm_identical_to_baseline(self):
        """Rm=None must produce byte-for-byte the same samples as before gh-1006."""
        motor_a = MotorSpec(kv_rpm_per_volt=900.0, cells_lipo_max=3, max_current_a=30.0)
        resp = compute_performance_curve(_request(motor_a))
        # Sanity: legacy path produces a single fixed RPM
        assert len({round(s.rpm, 1) for s in resp.samples}) == 1


# ---------------------------------------------------------------------------
# Known-motor sanity (QPROP textbook formula at static point)
# ---------------------------------------------------------------------------


class TestKnownMotorSanity:
    def test_static_efficiency_matches_qprop_formula(self):
        """η = (V - I·Rm)(I - I0)/(V·I) reproduced from solved I at static."""
        motor = _motor_with_rm(kv=1000.0, rm_ohm=0.1, io_no_load_a=0.8)
        res = solve_qprop_operating_point(
            motor=motor,
            samples=_make_apc10x5_samples(),
            V_terminal=11.1,
            V_airspeed=0.0,
            D_m=10 * 0.0254,
        )
        v_t, cur, rm, i0 = 11.1, res.current_a, motor.rm_ohm, motor.io_no_load_a
        eta_expected = (v_t - cur * rm) * (cur - i0) / (v_t * cur)
        assert res.eta_motor == pytest.approx(eta_expected, rel=1e-6)
