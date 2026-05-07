"""Tests for mass/CG API endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.schemas.design_assumption import PARAMETER_DEFAULTS
from app.tests.conftest import make_aeroplane


MOCK_S_REF = 0.30


# ---------------------------------------------------------------------------
# POST /aeroplanes/{id}/design_metrics
# ---------------------------------------------------------------------------


class TestDesignMetricsEndpoint:
    def test_returns_200(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        with patch(
            "app.services.mass_cg_service.get_s_ref_for_aeroplane",
            return_value=MOCK_S_REF,
        ):
            resp = client.post(
                f"/aeroplanes/{aeroplane.uuid}/design_metrics",
                json={"velocity": 15.0, "altitude": 0.0},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "stall_speed_ms" in body
        assert "wing_loading_pa" in body
        assert "required_cl" in body
        assert "cl_margin" in body
        assert body["mass_kg"] == PARAMETER_DEFAULTS["mass"]
        assert body["s_ref"] == MOCK_S_REF

    def test_404_for_missing_aeroplane(self, client_and_db):
        client, _ = client_and_db
        resp = client.post(
            f"/aeroplanes/{uuid.uuid4()}/design_metrics",
            json={"velocity": 15.0, "altitude": 0.0},
        )
        assert resp.status_code == 404

    def test_422_for_zero_velocity(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        resp = client.post(
            f"/aeroplanes/{aeroplane.uuid}/design_metrics",
            json={"velocity": 0.0, "altitude": 0.0},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /aeroplanes/{id}/mass_sweep
# ---------------------------------------------------------------------------


class TestMassSweepEndpoint:
    def test_returns_200(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        with patch(
            "app.services.mass_cg_service.get_s_ref_for_aeroplane",
            return_value=MOCK_S_REF,
        ):
            resp = client.post(
                f"/aeroplanes/{aeroplane.uuid}/mass_sweep",
                json={"masses_kg": [1.0, 1.5, 2.0], "velocity": 15.0, "altitude": 0.0},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["points"]) == 3
        assert body["velocity"] == 15.0
        assert body["s_ref"] == MOCK_S_REF

    def test_404_for_missing_aeroplane(self, client_and_db):
        client, _ = client_and_db
        resp = client.post(
            f"/aeroplanes/{uuid.uuid4()}/mass_sweep",
            json={"masses_kg": [1.0], "velocity": 15.0, "altitude": 0.0},
        )
        assert resp.status_code == 404

    def test_422_for_empty_masses(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        resp = client.post(
            f"/aeroplanes/{aeroplane.uuid}/mass_sweep",
            json={"masses_kg": [], "velocity": 15.0, "altitude": 0.0},
        )
        assert resp.status_code == 422

    def test_422_for_negative_mass(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        resp = client.post(
            f"/aeroplanes/{aeroplane.uuid}/mass_sweep",
            json={"masses_kg": [1.0, -0.5], "velocity": 15.0, "altitude": 0.0},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /aeroplanes/{id}/cg_comparison
# ---------------------------------------------------------------------------


class TestCGComparisonEndpoint:
    def test_returns_200(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        resp = client.get(f"/aeroplanes/{aeroplane.uuid}/cg_comparison")
        assert resp.status_code == 200
        body = resp.json()
        assert "design_cg_x" in body
        assert body["design_cg_x"] == PARAMETER_DEFAULTS["cg_x"]
        assert body["component_cg_x"] is None
        assert body["within_tolerance"] is None

    def test_with_weight_items(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        client.post(
            f"/aeroplanes/{aeroplane.uuid}/weight-items",
            json={
                "name": "motor",
                "mass_kg": 1.0,
                "x_m": 0.15,
                "y_m": 0.0,
                "z_m": 0.0,
            },
        )

        resp = client.get(f"/aeroplanes/{aeroplane.uuid}/cg_comparison")
        assert resp.status_code == 200
        body = resp.json()
        assert body["component_cg_x"] == pytest.approx(0.15)
        assert body["component_total_mass_kg"] == pytest.approx(1.0)
        assert body["delta_x"] is not None

    def test_404_for_missing_aeroplane(self, client_and_db):
        client, _ = client_and_db
        resp = client.get(f"/aeroplanes/{uuid.uuid4()}/cg_comparison")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Weight item CRUD triggers assumption sync
# ---------------------------------------------------------------------------


class TestWeightItemsSyncAssumptions:
    def test_create_syncs_mass_assumption(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        client.post(
            f"/aeroplanes/{aeroplane.uuid}/weight-items",
            json={"name": "battery", "mass_kg": 0.5, "x_m": 0.1},
        )

        resp = client.get(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        by_name = {a["parameter_name"]: a for a in resp.json()["assumptions"]}
        assert by_name["mass"]["calculated_value"] == pytest.approx(0.5)
        assert by_name["mass"]["calculated_source"] == "weight_items"

    def test_delete_clears_when_last_item(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        resp = client.post(
            f"/aeroplanes/{aeroplane.uuid}/weight-items",
            json={"name": "battery", "mass_kg": 0.5, "x_m": 0.1},
        )
        item_id = resp.json()["id"]

        client.delete(f"/aeroplanes/{aeroplane.uuid}/weight-items/{item_id}")

        resp = client.get(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        by_name = {a["parameter_name"]: a for a in resp.json()["assumptions"]}
        assert by_name["mass"]["calculated_value"] is None

    def test_update_resyncs_assumptions(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        resp = client.post(
            f"/aeroplanes/{aeroplane.uuid}/weight-items",
            json={"name": "battery", "mass_kg": 0.5, "x_m": 0.1},
        )
        item_id = resp.json()["id"]

        client.put(
            f"/aeroplanes/{aeroplane.uuid}/weight-items/{item_id}",
            json={"name": "battery", "mass_kg": 1.0, "x_m": 0.2},
        )

        resp = client.get(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        by_name = {a["parameter_name"]: a for a in resp.json()["assumptions"]}
        assert by_name["mass"]["calculated_value"] == pytest.approx(1.0)
        assert by_name["cg_x"]["calculated_value"] == pytest.approx(0.2)
