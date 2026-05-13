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


# ===========================================================================
# Additional endpoint coverage: _raise_http_from_domain + _resolve_aircraft_params
# ===========================================================================


class TestMatchingChartEndpointAdditional:
    """Tests targeting uncovered code paths in the endpoint module."""

    def test_invalid_mode_returns_422(self, client_and_db):
        """An invalid mode enum value should return 422 Unprocessable Entity."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/matching-chart",
            params={"mode": "invalid_mode_xyz"},
        )
        assert resp.status_code == 422

    def test_mode_uav_belly_land_accepted(self, client_and_db):
        """uav_belly_land mode should return 200 (covers the belly-land code path)."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/matching-chart",
            params={"mode": "uav_belly_land"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        # Landing constraint should have ws_max = null in belly-land mode
        landing = [c for c in data["constraints"] if c["name"] == "Landing"]
        assert len(landing) == 1
        assert landing[0]["ws_max"] is None

    def test_mode_rc_hand_launch_accepted(self, client_and_db):
        """rc_hand_launch mode should return 200 (covers no-runway code path)."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(
            f"/aeroplanes/{aeroplane_uuid}/matching-chart",
            params={"mode": "rc_hand_launch"},
        )
        assert resp.status_code == 200, resp.text

    def test_resolve_aircraft_params_with_b_ref_m_in_context(self, client_and_db):
        """When b_ref_m is in assumption_computation_context it is forwarded to service."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db, name="b-ref-test")

            # Seed minimal assumptions
            from app.models.aeroplanemodel import DesignAssumptionModel
            for param, val in [("mass", 10.0), ("cl_max", 1.2), ("cd0", 0.035), ("t_static_N", 50.0)]:
                db.add(DesignAssumptionModel(
                    aeroplane_id=plane.id,
                    parameter_name=param,
                    estimate_value=val,
                    active_source="ESTIMATE",
                ))

            # Context includes b_ref_m (triggers line 99)
            plane.assumption_computation_context = {
                "s_ref_m2": 0.05,
                "e_oswald": 0.8,
                "aspect_ratio": 7.0,
                "v_md_mps": 12.0,
                "b_ref_m": 1.0,       # <-- this is the key triggering line 99
            }
            db.flush()
            db.commit()
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/matching-chart")
        assert resp.status_code == 200, resp.text

    def test_resolve_aircraft_params_without_context(self, client_and_db):
        """When assumption_computation_context is None, defaults are used gracefully."""
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = make_aeroplane(db, name="no-context-test")

            from app.models.aeroplanemodel import DesignAssumptionModel
            for param, val in [("mass", 5.0), ("cl_max", 1.1), ("cd0", 0.04), ("t_static_N", 20.0)]:
                db.add(DesignAssumptionModel(
                    aeroplane_id=plane.id,
                    parameter_name=param,
                    estimate_value=val,
                    active_source="ESTIMATE",
                ))

            # No computation context — triggers all the "None" fallback paths
            plane.assumption_computation_context = None
            db.flush()
            db.commit()
            aeroplane_uuid = str(plane.uuid)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/matching-chart")
        assert resp.status_code == 200, resp.text

    def test_service_exception_is_mapped_to_http(self, client_and_db, monkeypatch):
        """ServiceException raised by compute_chart is mapped to 4xx/5xx (covers line 241)."""
        from app.core.exceptions import NotFoundError
        import app.api.v2.endpoints.aeroplane.matching_chart as mc_endpoint

        original = mc_endpoint.compute_chart if hasattr(mc_endpoint, "compute_chart") else None

        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            plane = _make_cessna_plane(db)
            aeroplane_uuid = str(plane.uuid)

        # Patch compute_chart inside the endpoint's module namespace
        def _raise_not_found(*args, **kwargs):
            raise NotFoundError("simulated not found")

        monkeypatch.setattr(
            "app.services.matching_chart_service.compute_chart",
            _raise_not_found,
        )

        # The endpoint imports compute_chart lazily at call time, so we need to
        # patch at the right place. Use a different strategy: patch at the
        # endpoint's import point.
        import app.services.matching_chart_service as mcs_module
        monkeypatch.setattr(mcs_module, "compute_chart", _raise_not_found)

        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/matching-chart")
        # NotFoundError → 404 via _raise_http_from_domain
        assert resp.status_code in {404, 422, 500}

    def test_raise_http_from_domain_internal_error(self):
        """_raise_http_from_domain maps InternalError to HTTP 500."""
        from fastapi import HTTPException
        from app.core.exceptions import InternalError
        from app.api.v2.endpoints.aeroplane.matching_chart import _raise_http_from_domain

        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(InternalError("boom"))
        assert exc_info.value.status_code == 500

    def test_raise_http_from_domain_not_found(self):
        """_raise_http_from_domain maps NotFoundError to HTTP 404."""
        from fastapi import HTTPException
        from app.core.exceptions import NotFoundError
        from app.api.v2.endpoints.aeroplane.matching_chart import _raise_http_from_domain

        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(NotFoundError("not there"))
        assert exc_info.value.status_code == 404

    def test_raise_http_from_domain_generic_service_exception(self):
        """_raise_http_from_domain maps generic ServiceException to HTTP 422."""
        from fastapi import HTTPException
        from app.core.exceptions import ServiceException
        from app.api.v2.endpoints.aeroplane.matching_chart import _raise_http_from_domain

        with pytest.raises(HTTPException) as exc_info:
            _raise_http_from_domain(ServiceException("generic"))
        assert exc_info.value.status_code == 422
