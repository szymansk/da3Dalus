"""Tests for the GET /aeroplanes/{aeroplane_id}/analysis-status endpoint."""

from __future__ import annotations

import uuid

import pytest

from app.core.platform import aerosandbox_available
from app.models.analysismodels import OperatingPointModel
from app.tests.conftest import make_aeroplane

# The operating_points router is only registered when aerosandbox is available.
pytestmark = pytest.mark.skipif(
    not aerosandbox_available(),
    reason="operating_points router requires aerosandbox",
)


def _make_aeroplane_detached(SessionLocal, name="test-plane"):
    """Create an aeroplane and return (uuid_str, pk) without a live session."""
    db = SessionLocal()
    try:
        aeroplane = make_aeroplane(db, name=name)
        return str(aeroplane.uuid), aeroplane.id
    finally:
        db.close()


def _make_op(session, aircraft_id: int, status: str = "TRIMMED", name: str = "op"):
    op = OperatingPointModel(
        name=name,
        description="test op",
        aircraft_id=aircraft_id,
        velocity=20.0,
        alpha=0.05,
        beta=0.0,
        p=0.0,
        q=0.0,
        r=0.0,
        altitude=100.0,
        config="clean",
        status=status,
        warnings=[],
        controls={},
        xyz_ref=[0.0, 0.0, 0.0],
    )
    session.add(op)
    session.commit()
    session.refresh(op)
    return op


class TestGetAnalysisStatus:
    """Test GET /aeroplanes/{aeroplane_id}/analysis-status."""

    @pytest.fixture(autouse=True)
    def _clear_job_tracker(self):
        """Reset the global job_tracker between tests to avoid state leaks."""
        from app.core.background_jobs import job_tracker

        job_tracker._jobs.clear()
        job_tracker._debounce_tasks.clear()
        yield
        job_tracker._jobs.clear()
        job_tracker._debounce_tasks.clear()

    def test_returns_empty_for_unknown_aeroplane(self, client_and_db):
        client, _ = client_and_db
        fake_uuid = str(uuid.uuid4())
        resp = client.get(f"/aeroplanes/{fake_uuid}/analysis-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_ops"] == 0
        assert data["op_counts"] == {}
        assert data["retrim_active"] is False
        assert data["retrim_debouncing"] is False

    def test_returns_correct_op_counts(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, aircraft_pk = _make_aeroplane_detached(SessionLocal)

        db = SessionLocal()
        try:
            _make_op(db, aircraft_pk, status="TRIMMED", name="op1")
            _make_op(db, aircraft_pk, status="TRIMMED", name="op2")
            _make_op(db, aircraft_pk, status="NOT_TRIMMED", name="op3")
            _make_op(db, aircraft_pk, status="DIRTY", name="op4")
        finally:
            db.close()

        resp = client.get(f"/aeroplanes/{aircraft_uuid}/analysis-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_ops"] == 4
        assert data["op_counts"]["TRIMMED"] == 2
        assert data["op_counts"]["NOT_TRIMMED"] == 1
        assert data["op_counts"]["DIRTY"] == 1

    def test_retrim_flags_default_false(self, client_and_db):
        client, SessionLocal = client_and_db
        aircraft_uuid, _ = _make_aeroplane_detached(SessionLocal)

        resp = client.get(f"/aeroplanes/{aircraft_uuid}/analysis-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["retrim_active"] is False
        assert data["retrim_debouncing"] is False
        assert data["last_computation"] is None

    def test_invalid_uuid_returns_422(self, client_and_db):
        client, _ = client_and_db
        resp = client.get("/aeroplanes/not-a-uuid/analysis-status")
        assert resp.status_code == 422
