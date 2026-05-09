"""Integration tests for the Operating Point Simulation epic (#417).

Covers the full REST API surface for operating-point generation, trim
(AVL + AeroBuildup), stability, mass sweep, CG comparison, flight
envelope, analysis status, and deflection override roundtrip.
"""

from __future__ import annotations

import pytest

from app.tests.conftest import (
    make_operating_point,
    seed_design_assumptions,
    seed_integration_aeroplane,
)


# ---------------------------------------------------------------------------
# Test 1 — OP Generation Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_generate_default_operating_point_set(client_and_db):
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_integration_aeroplane(session)
        seed_design_assumptions(session, aeroplane.id)

        response = client.post(
            f"/aeroplanes/{aeroplane.uuid}/operating-pointsets/generate-default",
            json={"replace_existing": True},
        )
        assert response.status_code == 200, response.text
        data = response.json()

        ops = data["operating_points"]
        assert len(ops) >= 8

        for op in ops:
            assert "name" in op
            assert "status" in op
            assert op["velocity"] > 0

        op_names = {op["name"] for op in ops}
        assert "cruise" in op_names
        assert "stall_near_clean" in op_names
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 2 — AVL Trim E2E
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.requires_avl
def test_avl_trim_e2e(client_and_db):
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_integration_aeroplane(session)
        seed_design_assumptions(session, aeroplane.id)
        make_operating_point(
            session,
            aircraft_id=aeroplane.id,
            name="cruise",
            velocity=18.0,
            alpha=0.05,
            status="NOT_TRIMMED",
        )

        response = client.post(
            f"/aeroplanes/{aeroplane.uuid}/operating-points/avl-trim",
            json={
                "operating_point": {
                    "velocity": 18.0,
                    "alpha": 3.0,
                    "beta": 0.0,
                    "p": 0.0,
                    "q": 0.0,
                    "r": 0.0,
                    "xyz_ref": [0.15, 0.0, 0.0],
                    "altitude": 0.0,
                },
                "trim_constraints": [
                    {"variable": "alpha", "target": "PM", "value": 0.0},
                ],
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["converged"] is True
        assert "CL" in data["aero_coefficients"]
        assert "CD" in data["aero_coefficients"]
        assert "Cm" in data["aero_coefficients"]
        assert "alpha" in data["trimmed_state"]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 3 — AeroBuildup Trim E2E
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_aerobuildup_trim_e2e(client_and_db):
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_integration_aeroplane(session)
        seed_design_assumptions(session, aeroplane.id)

        response = client.post(
            f"/aeroplanes/{aeroplane.uuid}/operating-points/aerobuildup-trim",
            json={
                "operating_point": {
                    "velocity": 18.0,
                    "alpha": 3.0,
                    "beta": 0.0,
                    "p": 0.0,
                    "q": 0.0,
                    "r": 0.0,
                    "xyz_ref": [0.15, 0.0, 0.0],
                    "altitude": 0.0,
                },
                "trim_variable": "Elevator",
                "target_coefficient": "Cm",
                "target_value": 0.0,
                "deflection_bounds": [-25.0, 25.0],
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["converged"] is True
        assert -25.0 <= data["trimmed_deflection"] <= 25.0
        assert abs(data["achieved_value"]) < 0.01
        assert "CL" in data["aero_coefficients"]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 4 — Stability Analysis Pipeline
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_stability_analysis_pipeline(client_and_db):
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_integration_aeroplane(session)
        seed_design_assumptions(session, aeroplane.id)

        response = client.post(
            f"/aeroplanes/{aeroplane.uuid}/stability_summary/aerobuildup",
            json={
                "velocity": 18.0,
                "alpha": 3.0,
                "beta": 0.0,
                "p": 0.0,
                "q": 0.0,
                "r": 0.0,
                "xyz_ref": [0.15, 0.0, 0.0],
                "altitude": 0.0,
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["neutral_point_x"] is not None
        assert 0.05 <= data["neutral_point_x"] <= 0.5
        assert data["static_margin"] is not None
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 5 — Mass Sweep
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_mass_sweep(client_and_db):
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_integration_aeroplane(session)
        seed_design_assumptions(session, aeroplane.id)

        masses = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
        response = client.post(
            f"/aeroplanes/{aeroplane.uuid}/mass_sweep",
            json={
                "masses_kg": masses,
                "velocity": 15.0,
                "altitude": 0.0,
            },
        )
        assert response.status_code == 200, response.text
        data = response.json()

        points = data["points"]
        assert len(points) == 6

        stall_speeds = [p["stall_speed_ms"] for p in points]
        for i in range(1, len(stall_speeds)):
            assert stall_speeds[i] >= stall_speeds[i - 1]

        cl_margins = [p["cl_margin"] for p in points]
        for i in range(1, len(cl_margins)):
            assert cl_margins[i] <= cl_margins[i - 1]

        assert points[0]["cl_margin"] > 0
        assert points[0]["cl_margin"] > points[-1]["cl_margin"]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 6 — CG Comparison
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_cg_comparison(client_and_db):
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_integration_aeroplane(session)

        from datetime import datetime, timezone

        from app.models.aeroplanemodel import DesignAssumptionModel

        cg_assumption = DesignAssumptionModel(
            aeroplane_id=aeroplane.id,
            parameter_name="cg_x",
            estimate_value=0.25,
            active_source="ESTIMATE",
            updated_at=datetime.now(timezone.utc),
        )
        session.add(cg_assumption)
        session.commit()

        weight_items = [
            {"name": "motor", "mass_kg": 0.2, "x_m": 0.1, "y_m": 0.0, "z_m": 0.0},
            {"name": "battery", "mass_kg": 0.3, "x_m": 0.15, "y_m": 0.0, "z_m": 0.0},
            {"name": "servo", "mass_kg": 0.05, "x_m": 0.35, "y_m": 0.0, "z_m": 0.0},
        ]
        for item in weight_items:
            resp = client.post(
                f"/aeroplanes/{aeroplane.uuid}/weight-items",
                json=item,
            )
            assert resp.status_code == 201, resp.text

        response = client.get(f"/aeroplanes/{aeroplane.uuid}/cg_comparison")
        assert response.status_code == 200, response.text
        data = response.json()

        expected_cg_x = (0.1 * 0.2 + 0.15 * 0.3 + 0.35 * 0.05) / 0.55
        assert data["component_cg_x"] is not None
        assert abs(data["component_cg_x"] - expected_cg_x) < 0.001
        assert data["design_cg_x"] == 0.25
        assert data["delta_x"] is not None
        assert data["delta_x"] > 0
        assert data["within_tolerance"] is False
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 7 — Analysis Status
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_analysis_status(client_and_db):
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_integration_aeroplane(session)

        make_operating_point(
            session,
            aircraft_id=aeroplane.id,
            name="op_trimmed_1",
            status="TRIMMED",
            velocity=18.0,
        )
        make_operating_point(
            session,
            aircraft_id=aeroplane.id,
            name="op_trimmed_2",
            status="TRIMMED",
            velocity=12.0,
        )
        make_operating_point(
            session,
            aircraft_id=aeroplane.id,
            name="op_not_trimmed",
            status="NOT_TRIMMED",
            velocity=25.0,
        )

        response = client.get(f"/aeroplanes/{aeroplane.uuid}/analysis-status")
        assert response.status_code == 200, response.text
        data = response.json()

        assert data["op_counts"]["TRIMMED"] == 2
        assert data["op_counts"]["NOT_TRIMMED"] == 1
        assert data["total_ops"] == 3
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 8 — Flight Envelope
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_flight_envelope(client_and_db):
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_integration_aeroplane(session)
        seed_design_assumptions(session, aeroplane.id)

        make_operating_point(
            session,
            aircraft_id=aeroplane.id,
            name="cruise",
            status="TRIMMED",
            velocity=18.0,
            alpha=3.0,
        )
        make_operating_point(
            session,
            aircraft_id=aeroplane.id,
            name="max_speed",
            status="TRIMMED",
            velocity=28.0,
            alpha=1.0,
        )

        response = client.post(
            f"/aeroplanes/{aeroplane.uuid}/flight-envelope/compute",
        )
        assert response.status_code == 200, response.text
        data = response.json()

        vn = data["vn_curve"]
        assert len(vn["positive"]) >= 50
        assert len(vn["negative"]) >= 50

        assert vn["stall_speed_mps"] > 0
        assert 5.0 <= vn["stall_speed_mps"] <= 15.0
        assert vn["dive_speed_mps"] > vn["stall_speed_mps"]

        assert len(data["kpis"]) >= 6
        assert data["computed_at"] is not None

        cached = client.get(f"/aeroplanes/{aeroplane.uuid}/flight-envelope")
        assert cached.status_code == 200
        cached_data = cached.json()
        assert cached_data["vn_curve"]["stall_speed_mps"] == vn["stall_speed_mps"]
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Test 9 — Deflection Override Roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_deflection_override_roundtrip(client_and_db):
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_integration_aeroplane(session)

        op = make_operating_point(
            session,
            aircraft_id=aeroplane.id,
            name="cruise",
            status="TRIMMED",
            velocity=18.0,
        )

        response = client.patch(
            f"/operating_points/{op.id}/deflections",
            json={"control_deflections": {"elevator": 5.0}},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["control_deflections"] == {"elevator": 5.0}
        assert data["status"] == "NOT_TRIMMED"

        response2 = client.patch(
            f"/operating_points/{op.id}/deflections",
            json={"control_deflections": None},
        )
        assert response2.status_code == 200, response2.text
        data2 = response2.json()
        assert data2["control_deflections"] is None
        assert data2["status"] == "NOT_TRIMMED"
    finally:
        session.close()
