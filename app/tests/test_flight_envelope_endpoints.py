"""Tests for app/api/v2/endpoints/aeroplane/flight_envelope.py.

Covers the GET (cached) and POST (compute) flight envelope endpoints,
mocked at the service layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.core.exceptions import InternalError, NotFoundError, ServiceException
from app.core.platform import aerosandbox_available
from app.schemas.flight_envelope import (
    FlightEnvelopeRead,
    PerformanceKPI,
    VnCurve,
    VnMarker,
    VnPoint,
)
from app.tests.conftest import make_aeroplane

pytestmark = pytest.mark.skipif(
    not aerosandbox_available(),
    reason="flight_envelope router requires aerosandbox",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SERVICE_MODULE = "app.api.v2.endpoints.aeroplane.flight_envelope.flight_envelope_service"


def _make_aeroplane_detached(SessionLocal, name="fe-test-plane"):
    """Create an aeroplane and return (uuid_str, pk) without a live session."""
    db = SessionLocal()
    try:
        aeroplane = make_aeroplane(db, name=name)
        return str(aeroplane.uuid), aeroplane.id
    finally:
        db.close()


def _sample_envelope(aeroplane_pk: int = 1) -> FlightEnvelopeRead:
    """Return a realistic FlightEnvelopeRead for mocking."""
    return FlightEnvelopeRead(
        id=1,
        aeroplane_id=aeroplane_pk,
        vn_curve=VnCurve(
            positive=[
                VnPoint(velocity_mps=10.0, load_factor=1.0),
                VnPoint(velocity_mps=20.0, load_factor=2.5),
            ],
            negative=[
                VnPoint(velocity_mps=10.0, load_factor=-0.4),
                VnPoint(velocity_mps=20.0, load_factor=-1.0),
            ],
            dive_speed_mps=39.2,
            stall_speed_mps=10.0,
        ),
        kpis=[
            PerformanceKPI(
                label="stall_speed",
                display_name="Stall Speed",
                value=10.0,
                unit="m/s",
                source_op_id=None,
                confidence="limit",
            ),
        ],
        operating_points=[
            VnMarker(
                op_id=1,
                name="cruise",
                velocity_mps=20.0,
                load_factor=1.0,
                status="TRIMMED",
                label="cruise",
            ),
        ],
        assumptions_snapshot={"mass": 2.5, "cl_max": 1.4, "g_limit": 3.8},
        computed_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


# =========================================================================
# GET /aeroplanes/{aeroplane_id}/flight-envelope
# =========================================================================


class TestGetFlightEnvelope:
    def test_returns_cached_envelope(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, aircraft_pk = _make_aeroplane_detached(SessionLocal)

        envelope = _sample_envelope(aircraft_pk)
        with patch(
            f"{_SERVICE_MODULE}.get_flight_envelope",
            return_value=envelope,
        ) as mock_get:
            resp = client.get(f"/aeroplanes/{aircraft_uuid}/flight-envelope")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == 1
            assert data["aeroplane_id"] == aircraft_pk
            assert data["vn_curve"]["dive_speed_mps"] == 39.2
            assert len(data["kpis"]) == 1
            assert data["kpis"][0]["label"] == "stall_speed"
            assert len(data["operating_points"]) == 1
            mock_get.assert_called_once()

    def test_returns_404_when_no_cached_envelope(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "no-envelope")

        with patch(
            f"{_SERVICE_MODULE}.get_flight_envelope",
            return_value=None,
        ):
            resp = client.get(f"/aeroplanes/{aircraft_uuid}/flight-envelope")
            assert resp.status_code == 404

    def test_returns_404_when_aeroplane_not_found(self, client_and_db):
        client, _ = client_and_db
        fake_uuid = uuid.uuid4()

        with patch(
            f"{_SERVICE_MODULE}.get_flight_envelope",
            side_effect=NotFoundError("Aeroplane not found"),
        ):
            resp = client.get(f"/aeroplanes/{fake_uuid}/flight-envelope")
            assert resp.status_code == 404

    def test_invalid_uuid_returns_422(self, client_and_db):
        client, _ = client_and_db
        resp = client.get("/aeroplanes/not-a-uuid/flight-envelope")
        assert resp.status_code == 422


# =========================================================================
# POST /aeroplanes/{aeroplane_id}/flight-envelope/compute
# =========================================================================


class TestComputeFlightEnvelope:
    def test_returns_computed_envelope(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, aircraft_pk = _make_aeroplane_detached(SessionLocal, "compute-test")

        envelope = _sample_envelope(aircraft_pk)
        with patch(
            f"{_SERVICE_MODULE}.compute_flight_envelope",
            return_value=envelope,
        ) as mock_compute:
            resp = client.post(f"/aeroplanes/{aircraft_uuid}/flight-envelope/compute")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == 1
            assert data["vn_curve"]["stall_speed_mps"] == 10.0
            assert data["assumptions_snapshot"]["mass"] == 2.5
            mock_compute.assert_called_once()

    def test_not_found_error(self, client_and_db):
        client, _ = client_and_db
        fake_uuid = uuid.uuid4()

        with patch(
            f"{_SERVICE_MODULE}.compute_flight_envelope",
            side_effect=NotFoundError("Aeroplane not found"),
        ):
            resp = client.post(f"/aeroplanes/{fake_uuid}/flight-envelope/compute")
            assert resp.status_code == 404

    def test_internal_error(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "internal-err")

        with patch(
            f"{_SERVICE_MODULE}.compute_flight_envelope",
            side_effect=InternalError("Computation failed"),
        ):
            resp = client.post(f"/aeroplanes/{aircraft_uuid}/flight-envelope/compute")
            assert resp.status_code == 500

    def test_generic_service_exception_maps_to_500(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal, "generic-err")

        with patch(
            f"{_SERVICE_MODULE}.compute_flight_envelope",
            side_effect=ServiceException("generic failure"),
        ):
            resp = client.post(f"/aeroplanes/{aircraft_uuid}/flight-envelope/compute")
            assert resp.status_code == 500

    def test_invalid_uuid_returns_422(self, client_and_db):
        client, _ = client_and_db
        resp = client.post("/aeroplanes/not-a-uuid/flight-envelope/compute")
        assert resp.status_code == 422
