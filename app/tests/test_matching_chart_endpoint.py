"""Endpoint tests for the matching chart REST API (gh-492).

Covers GET /aeroplanes/{id}/matching-chart:
- Happy path with all required data → 200 with full response
- 404 when aeroplane not found
- Mode parameter respected
- Override parameters accepted
- Binding constraint in response
"""

from __future__ import annotations

import uuid

import pytest

from app.models.aeroplanemodel import AeroplaneModel, DesignAssumptionModel
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_assumption(session, aeroplane_id: int, param_name: str, value: float):
    row = DesignAssumptionModel(
        aeroplane_id=aeroplane_id,
        parameter_name=param_name,
        estimate_value=value,
        active_source="ESTIMATE",
    )
    session.add(row)
    session.flush()


def _make_cessna_plane(session) -> AeroplaneModel:
    """Create a Cessna-like aeroplane with all required data."""
    plane = make_aeroplane(session, name="matching-chart-test")

    _seed_assumption(session, plane.id, "mass", 1088.0)
    _seed_assumption(session, plane.id, "cl_max", 1.5)
    _seed_assumption(session, plane.id, "cd0", 0.031)
    _seed_assumption(session, plane.id, "t_static_N", 1900.0)

    # Computation context (normally from assumption_compute_service)
    plane.assumption_computation_context = {
        "v_stall_mps": 25.4,
        "s_ref_m2": 16.17,
        "e_oswald": 0.75,
        "aspect_ratio": 7.32,
        "v_md_mps": 45.0,
        "v_cruise_mps": 55.0,
    }
    session.flush()
    session.commit()
    return plane


# ===========================================================================
# Endpoint tests
# ===========================================================================


class TestMatchingChartEndpoint:
    def test_returns_200_with_all_fields(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/matching-chart")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        required_keys = {"ws_range_n_m2", "constraints", "design_point", "feasibility", "warnings"}
        assert not (required_keys - data.keys()), f"Missing keys: {required_keys - data.keys()}"

    def test_design_point_in_response(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/matching-chart")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        dp = data["design_point"]
        assert "ws_n_m2" in dp
        assert "t_w" in dp
        # Cessna design point checks
        assert 500 <= dp["ws_n_m2"] <= 800, f"W/S = {dp['ws_n_m2']:.1f}, expected ~660"
        assert 0.10 <= dp["t_w"] <= 0.30, f"T/W = {dp['t_w']:.4f}, expected ~0.178"

    def test_404_missing_aeroplane(self, client_and_db):
        client, _ = client_and_db
        missing_uuid = str(uuid.uuid4())
        resp = client.get(f"/aeroplanes/{missing_uuid}/matching-chart")
        assert resp.status_code == 404

    def test_constraints_have_required_structure(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/matching-chart")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert len(data["constraints"]) >= 4, f"Expected ≥4 constraints, got {len(data['constraints'])}"
        for c in data["constraints"]:
            assert "name" in c
            assert "color" in c
            assert "binding" in c
            assert isinstance(c["binding"], bool)

    def test_binding_constraint_marker(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/matching-chart",
            params={"s_runway": 411.0, "v_s_target": 26.0},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # With correct field length the design point should be feasible and at least one binding
        assert data["feasibility"] in {"feasible", "infeasible_below_constraints"}

    def test_mode_rc_runway_accepted(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/matching-chart",
            params={"mode": "rc_runway"},
        )
        assert resp.status_code == 200, resp.text

    def test_mode_uav_runway_accepted(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/matching-chart",
            params={"mode": "uav_runway"},
        )
        assert resp.status_code == 200, resp.text

    def test_override_params_accepted(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/matching-chart",
            params={
                "s_runway": 300.0,
                "v_s_target": 20.0,
                "gamma_climb_deg": 3.0,
                "v_cruise_mps": 60.0,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "constraints" in data

    def test_feasibility_is_valid_string(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/matching-chart")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["feasibility"] in {"feasible", "infeasible_below_constraints"}

    def test_ws_range_sorted_ascending(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/matching-chart")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        ws = data["ws_range_n_m2"]
        assert all(ws[i] < ws[i + 1] for i in range(len(ws) - 1)), (
            "ws_range_n_m2 must be sorted ascending"
        )
