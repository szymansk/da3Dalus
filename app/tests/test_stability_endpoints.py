"""Tests for the stability GET endpoint and extended POST endpoint."""

from __future__ import annotations

import uuid

import pytest

from app.models.stability_result import StabilityResultModel
from app.schemas.stability import StabilitySummaryResponse
from app.services.stability_service import persist_stability_result
from app.tests.conftest import make_aeroplane


def _make_summary(**overrides) -> StabilitySummaryResponse:
    defaults = {
        "static_margin": 0.16,
        "neutral_point_x": 0.12,
        "cg_x": 0.08,
        "Cma": -0.8,
        "Cnb": 0.05,
        "Clb": -0.03,
        "is_statically_stable": True,
        "is_directionally_stable": True,
        "is_laterally_stable": True,
        "analysis_method": "avl",
        "static_margin_pct": 16.0,
        "stability_class": "stable",
        "cg_range_forward": 0.0375,
        "cg_range_aft": 0.1075,
        "mac": 0.25,
        "trim_alpha_deg": 2.0,
        "trim_elevator_deg": -1.5,
    }
    defaults.update(overrides)
    return StabilitySummaryResponse(**defaults)


class TestGetCachedStabilityEndpoint:

    def test_404_when_no_cached_result(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, name="stability-test")
            aeroplane_uuid = str(aeroplane.uuid)
        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/stability")
        assert resp.status_code == 404

    def test_returns_cached_result(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, name="stability-test")
            aeroplane_uuid = str(aeroplane.uuid)
            persist_stability_result(db, aeroplane.id, "avl", _make_summary(), "h1")
            db.commit()
        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/stability")
        assert resp.status_code == 200
        data = resp.json()
        assert data["solver"] == "avl"
        assert data["neutral_point_x"] == pytest.approx(0.12)
        assert data["stability_class"] == "stable"
        assert data["status"] == "CURRENT"

    def test_returns_dirty_status(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db, name="stability-test")
            aeroplane_uuid = str(aeroplane.uuid)
            persist_stability_result(db, aeroplane.id, "avl", _make_summary(), "h1")
            db.commit()
            row = db.query(StabilityResultModel).first()
            row.status = "DIRTY"
            db.commit()
        resp = client.get(f"/aeroplanes/{aeroplane_uuid}/stability")
        assert resp.status_code == 200
        assert resp.json()["status"] == "DIRTY"

    def test_404_for_nonexistent_aeroplane(self, client_and_db):
        client, _ = client_and_db
        fake_uuid = uuid.uuid4()
        resp = client.get(f"/aeroplanes/{fake_uuid}/stability")
        assert resp.status_code == 404
