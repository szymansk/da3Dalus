"""Endpoint tests for POST /aeroplanes/{id}/powertrain/performance (gh-615).

Uses the standard client_and_db fixture (in-memory SQLite, no external deps).
Propeller polar samples are seeded directly — no aerosandbox dependency.
"""

from __future__ import annotations

import uuid

import pytest

from app.models.aeroplanemodel import AeroplaneModel
from app.models.component import ComponentModel
from app.models.prop_polar import PropellerPolarModel, PropellerPolarSampleModel


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_aeroplane(session) -> AeroplaneModel:
    plane = AeroplaneModel(
        name="Test Plane",
        uuid=uuid.uuid4(),
    )
    session.add(plane)
    session.commit()
    session.refresh(plane)
    return plane


def _make_motor(session, **spec_overrides) -> ComponentModel:
    specs = {
        "kv_rpm_per_volt": 1000.0,
        "cells_lipo_max": 3,
        "max_current_a": 20.0,
        "continuous_current_a": 15.0,
        "efficiency_pct": None,
        "gear_ratio": None,
    }
    specs.update(spec_overrides)
    motor = ComponentModel(
        name="Test Motor 1000KV",
        component_type="brushless_motor",
        specs=specs,
    )
    session.add(motor)
    session.commit()
    session.refresh(motor)
    return motor


def _make_battery(session, cells=3, capacity_mah=2200.0, c_rate=30) -> ComponentModel:
    battery = ComponentModel(
        name="Test LiPo 3S 2200mAh",
        component_type="battery",
        specs={"cells": cells, "capacity_mah": capacity_mah, "c_rate": c_rate},
    )
    session.add(battery)
    session.commit()
    session.refresh(battery)
    return battery


def _make_prop_polar(session, diameter_in=10.0, pitch_in=5.0) -> PropellerPolarModel:
    """Seed a minimal APC 10x5-like propeller polar with a few RPM rows."""
    polar = PropellerPolarModel(
        manufacturer="APC",
        name=f"APC {diameter_in}x{pitch_in}",
        diameter_in=diameter_in,
        pitch_in=pitch_in,
        blades=2,
    )
    session.add(polar)
    session.flush()  # need polar.id for samples

    # Seed samples at two RPMs
    rpm_data = {
        6000: [
            (0.000, 0.1013, 0.0556, 0.0),
            (0.100, 0.0910, 0.0558, 0.163),
            (0.200, 0.0804, 0.0553, 0.291),
            (0.300, 0.0675, 0.0530, 0.382),
            (0.400, 0.0526, 0.0492, 0.428),
            (0.500, 0.0363, 0.0438, 0.414),
            (0.600, 0.0188, 0.0369, 0.306),
            (0.650, 0.0007, 0.0284, 0.016),
        ],
        8000: [
            (0.000, 0.1010, 0.0554, 0.0),
            (0.100, 0.0907, 0.0555, 0.163),
            (0.200, 0.0800, 0.0551, 0.290),
            (0.300, 0.0671, 0.0528, 0.381),
            (0.400, 0.0522, 0.0490, 0.426),
            (0.500, 0.0360, 0.0436, 0.413),
            (0.600, 0.0185, 0.0367, 0.302),
            (0.650, 0.0005, 0.0282, 0.012),
        ],
    }

    for rpm, rows in rpm_data.items():
        D_m = diameter_in * 0.0254
        n_rps = rpm / 60.0
        rho = 1.225
        for J, Ct, Cp, Pe in rows:
            pwr = Cp * rho * (n_rps**3) * (D_m**5)
            s = PropellerPolarSampleModel(
                propeller_id=polar.id,
                rpm=rpm,
                J=J,
                Ct=Ct,
                Cp=Cp,
                Pe=Pe,
                PWR_W=round(pwr, 4),
                Torque_Nm=None,
                Thrust_N=None,
            )
            session.add(s)

    session.commit()
    session.refresh(polar)
    return polar


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPowertrainPerformanceEndpoint:
    def _post(self, client, aeroplane_uuid, body: dict):
        return client.post(
            f"/aeroplanes/{aeroplane_uuid}/powertrain/performance",
            json=body,
        )

    def test_success_returns_200(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            motor = _make_motor(db)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        body = {
            "motor_component_id": motor.id,
            "battery_component_id": battery.id,
            "propeller_polar_id": polar.id,
            "v_min_ms": 0.0,
            "v_max_ms": 25.0,
            "n_points": 10,
        }
        resp = self._post(client, plane.uuid, body)
        assert resp.status_code == 200, resp.text

    def test_response_has_correct_n_samples(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            motor = _make_motor(db)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        body = {
            "motor_component_id": motor.id,
            "battery_component_id": battery.id,
            "propeller_polar_id": polar.id,
            "v_min_ms": 0.0,
            "v_max_ms": 20.0,
            "n_points": 15,
        }
        resp = self._post(client, plane.uuid, body)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["samples"]) == 15

    def test_thrust_monotone_from_response(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            motor = _make_motor(db)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        body = {
            "motor_component_id": motor.id,
            "battery_component_id": battery.id,
            "propeller_polar_id": polar.id,
            "v_min_ms": 0.0,
            "v_max_ms": 20.0,
            "n_points": 10,
        }
        resp = self._post(client, plane.uuid, body)
        assert resp.status_code == 200
        data = resp.json()
        thrusts = [s["thrust_n"] for s in data["samples"]]
        for i in range(len(thrusts) - 1):
            assert thrusts[i] >= thrusts[i + 1] - 1e-4, (
                f"Thrust not monotone at index {i + 1}: {thrusts}"
            )

    def test_eta_prop_in_range(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            motor = _make_motor(db)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        resp = self._post(
            client,
            plane.uuid,
            {
                "motor_component_id": motor.id,
                "battery_component_id": battery.id,
                "propeller_polar_id": polar.id,
                "v_min_ms": 0.0,
                "v_max_ms": 20.0,
                "n_points": 8,
            },
        )
        assert resp.status_code == 200
        for s in resp.json()["samples"]:
            assert 0.0 <= s["eta_prop"] <= 1.0

    def test_p_available_w_positive(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            motor = _make_motor(db)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        resp = self._post(
            client,
            plane.uuid,
            {
                "motor_component_id": motor.id,
                "battery_component_id": battery.id,
                "propeller_polar_id": polar.id,
                "v_min_ms": 0.0,
                "v_max_ms": 20.0,
                "n_points": 5,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["p_available_w"] > 0.0

    def test_geared_motor_uses_output_kv(self, client_and_db):
        """Geared motor and direct-drive with equivalent output_kv → similar RPM."""
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
            # Direct drive: KV=551
            motor_direct = _make_motor(db, kv_rpm_per_volt=551.0, gear_ratio=None, cells_lipo_max=3)
            # Geared: raw KV=2040, ratio=3.7 → output_kv≈551
            motor_geared = _make_motor(
                db, kv_rpm_per_volt=2040.0, gear_ratio=3.7, cells_lipo_max=3, efficiency_pct=80.0
            )
        finally:
            db.close()

        resp_d = self._post(
            client,
            plane.uuid,
            {
                "motor_component_id": motor_direct.id,
                "battery_component_id": battery.id,
                "propeller_polar_id": polar.id,
                "v_min_ms": 0.0,
                "v_max_ms": 5.0,
                "n_points": 2,
            },
        )
        resp_g = self._post(
            client,
            plane.uuid,
            {
                "motor_component_id": motor_geared.id,
                "battery_component_id": battery.id,
                "propeller_polar_id": polar.id,
                "v_min_ms": 0.0,
                "v_max_ms": 5.0,
                "n_points": 2,
            },
        )
        assert resp_d.status_code == 200
        assert resp_g.status_code == 200
        rpm_d = resp_d.json()["samples"][0]["rpm"]
        rpm_g = resp_g.json()["samples"][0]["rpm"]
        # Output RPMs should be within 2% of each other
        assert abs(rpm_d - rpm_g) < rpm_d * 0.02, f"RPM mismatch: {rpm_d} vs {rpm_g}"

    def test_404_for_unknown_aeroplane(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            motor = _make_motor(db)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        resp = self._post(
            client,
            uuid.uuid4(),
            {
                "motor_component_id": motor.id,
                "battery_component_id": battery.id,
                "propeller_polar_id": polar.id,
                "v_min_ms": 0.0,
                "v_max_ms": 20.0,
                "n_points": 5,
            },
        )
        assert resp.status_code == 404

    def test_404_for_unknown_motor(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        resp = self._post(
            client,
            plane.uuid,
            {
                "motor_component_id": 99999,
                "battery_component_id": battery.id,
                "propeller_polar_id": polar.id,
                "v_min_ms": 0.0,
                "v_max_ms": 20.0,
                "n_points": 5,
            },
        )
        assert resp.status_code == 404

    def test_404_for_unknown_propeller_polar(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            motor = _make_motor(db)
            battery = _make_battery(db)
        finally:
            db.close()

        resp = self._post(
            client,
            plane.uuid,
            {
                "motor_component_id": motor.id,
                "battery_component_id": battery.id,
                "propeller_polar_id": 99999,
                "v_min_ms": 0.0,
                "v_max_ms": 20.0,
                "n_points": 5,
            },
        )
        assert resp.status_code == 404

    def test_422_if_motor_missing_kv(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            # Motor with no KV in specs
            motor_bad = ComponentModel(
                name="Bad Motor",
                component_type="brushless_motor",
                specs={"cells_lipo_max": 3},  # no kv_rpm_per_volt
            )
            db.add(motor_bad)
            db.commit()
            db.refresh(motor_bad)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        resp = self._post(
            client,
            plane.uuid,
            {
                "motor_component_id": motor_bad.id,
                "battery_component_id": battery.id,
                "propeller_polar_id": polar.id,
                "v_min_ms": 0.0,
                "v_max_ms": 20.0,
                "n_points": 5,
            },
        )
        assert resp.status_code == 422

    def test_notes_field_present(self, client_and_db):
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            motor = _make_motor(db)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        resp = self._post(
            client,
            plane.uuid,
            {
                "motor_component_id": motor.id,
                "battery_component_id": battery.id,
                "propeller_polar_id": polar.id,
                "v_min_ms": 0.0,
                "v_max_ms": 20.0,
                "n_points": 5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "notes" in data
        assert data["notes"]  # non-empty — must mention the model simplification

    def test_estimated_flag_true_for_derived_power(self, client_and_db):
        """All samples must be flagged estimated=True (power from current×V)."""
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            motor = _make_motor(db)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        resp = self._post(
            client,
            plane.uuid,
            {
                "motor_component_id": motor.id,
                "battery_component_id": battery.id,
                "propeller_polar_id": polar.id,
                "v_min_ms": 0.0,
                "v_max_ms": 20.0,
                "n_points": 5,
            },
        )
        assert resp.status_code == 200
        for s in resp.json()["samples"]:
            assert s["estimated"] is True

    def test_qprop_path_when_rm_present(self, client_and_db):
        """gh-1006: motor with rm_ohm in specs → QPROP 3-param path.

        Samples are physics-solved (estimated=False), RPM is load-dependent
        (varies across the sweep), and the notes mention QPROP/Rm.
        """
        client, SessionLocal = client_and_db
        db = SessionLocal()
        try:
            plane = _make_aeroplane(db)
            motor = _make_motor(db, rm_ohm=0.1, io_no_load_a=0.8, max_current_a=40.0)
            battery = _make_battery(db)
            polar = _make_prop_polar(db)
        finally:
            db.close()

        resp = self._post(
            client,
            plane.uuid,
            {
                "motor_component_id": motor.id,
                "battery_component_id": battery.id,
                "propeller_polar_id": polar.id,
                "v_min_ms": 0.0,
                "v_max_ms": 20.0,
                "n_points": 8,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert all(s["estimated"] is False for s in data["samples"])
        rpms = {round(s["rpm"], 1) for s in data["samples"]}
        assert len(rpms) > 1  # load-dependent, not a single fixed RPM
        assert "qprop" in data["notes"].lower() or "rm" in data["notes"].lower()
