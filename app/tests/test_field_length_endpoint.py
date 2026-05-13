"""Endpoint tests for the field-length REST API (gh-489).

Covers the GET /aeroplanes/{id}/field-lengths endpoint:
- Happy path (runway/runway with seeded assumptions + context)
- 404 when aeroplane not found
- 422 when stall speed or s_ref not in context
- 422 when t_static_N is absent for runway mode
- Query parameters: landing_mode=belly_land, takeoff_mode=hand_launch
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


def _make_plane_with_context(session, *, t_static_N: float | None = 1900.0) -> AeroplaneModel:
    """Create an aeroplane with all required data for field-length computation."""
    plane = make_aeroplane(session, name="field-len-test")

    # Seed design assumptions
    _seed_assumption(session, plane.id, "mass", 1088.0)
    _seed_assumption(session, plane.id, "cl_max", 1.5)
    if t_static_N is not None:
        _seed_assumption(session, plane.id, "t_static_N", t_static_N)

    # Seed computation context (normally written by assumption_compute_service)
    plane.assumption_computation_context = {
        "v_stall_mps": 25.4,
        "s_ref_m2": 16.17,
        "v_cruise_mps": 55.0,
    }
    session.flush()
    session.commit()
    return plane


# ===========================================================================
# Endpoint tests
# ===========================================================================


class TestFieldLengthEndpoint:
    def test_runway_returns_200_with_all_fields(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_with_context(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/field-lengths",
            params={"takeoff_mode": "runway", "landing_mode": "runway"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        required = {
            "s_to_ground_m", "s_to_50ft_m",
            "s_ldg_ground_m", "s_ldg_50ft_m",
            "vto_obstacle_mps", "vapp_mps",
            "mode_takeoff", "mode_landing",
            "warnings",
        }
        assert not (required - data.keys())
        assert data["mode_takeoff"] == "runway"
        assert data["mode_landing"] == "runway"
        assert data["s_to_ground_m"] > 0
        assert data["s_ldg_ground_m"] > 0

    def test_404_when_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        missing_uuid = str(uuid.uuid4())
        resp = client.get(f"/aeroplanes/{missing_uuid}/field-lengths")
        assert resp.status_code == 404

    def test_422_when_t_static_missing_for_runway(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            # No t_static_N seeded
            plane = _make_plane_with_context(db, t_static_N=None)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/field-lengths",
            params={"takeoff_mode": "runway"},
        )
        assert resp.status_code == 422

    def test_422_when_stall_speed_missing_from_context(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db, name="no-context")
            _seed_assumption(db, plane.id, "mass", 1088.0)
            _seed_assumption(db, plane.id, "cl_max", 1.5)
            _seed_assumption(db, plane.id, "t_static_N", 1900.0)
            # No assumption_computation_context
            plane.assumption_computation_context = None
            db.flush()
            db.commit()
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/field-lengths")
        assert resp.status_code == 422

    def test_belly_land_returns_shorter_distance(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_with_context(db)
            aeroplane_uuid = str(plane.uuid)

        r_runway = client.get(
            f"/aeroplanes/{aeroplane_uuid}/field-lengths",
            params={"landing_mode": "runway"},
        )
        r_belly = client.get(
            f"/aeroplanes/{aeroplane_uuid}/field-lengths",
            params={"landing_mode": "belly_land"},
        )
        assert r_runway.status_code == 200
        assert r_belly.status_code == 200
        assert r_belly.json()["s_ldg_ground_m"] < r_runway.json()["s_ldg_ground_m"]

    def test_hand_launch_returns_zero_ground_roll(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_with_context(db)
            aeroplane_uuid = str(plane.uuid)

        v_stall = 25.4
        v_throw = 1.25 * v_stall  # above both 1.10 and 1.20 floors
        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/field-lengths",
            params={"takeoff_mode": "hand_launch", "v_throw_mps": v_throw},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["s_to_ground_m"] == pytest.approx(0.0)
        assert data["s_to_50ft_m"] == pytest.approx(0.0)

    def test_default_mode_is_runway(self, client_and_db):
        """Calling without mode params defaults to runway/runway."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_plane_with_context(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/field-lengths")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode_takeoff"] == "runway"
        assert data["mode_landing"] == "runway"
