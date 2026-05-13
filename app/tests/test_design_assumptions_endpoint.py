"""Tests for design assumptions API endpoints."""

from __future__ import annotations

import uuid

import pytest

from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# POST /aeroplanes/{id}/assumptions (seed defaults)
# ---------------------------------------------------------------------------


class TestSeedAssumptions:
    def test_seed_returns_201(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        resp = client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        assert resp.status_code == 201
        body = resp.json()
        # 8 original + 5 electric-endurance params added in gh-491
        assert len(body["assumptions"]) == 13: takeoff and landing field length (Roskam ground-roll + RC modes))
        assert body["warnings_count"] == 0

    def test_seed_idempotent(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        resp = client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        assert resp.status_code == 201
        assert len(resp.json()["assumptions"]) == 14: takeoff and landing field length (Roskam ground-roll + RC modes))

    def test_seed_404_for_missing_aeroplane(self, client_and_db):
        client, _ = client_and_db
        resp = client.post(f"/aeroplanes/{uuid.uuid4()}/assumptions")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /aeroplanes/{id}/assumptions
# ---------------------------------------------------------------------------


class TestListAssumptions:
    def test_list_returns_200(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        # Seed first
        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        resp = client.get(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        assert resp.status_code == 200
        body = resp.json()
        # 8 original + 5 electric-endurance params added in gh-491
        assert len(body["assumptions"]) == 13: takeoff and landing field length (Roskam ground-roll + RC modes))

    def test_list_empty_before_seed(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        resp = client.get(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        assert resp.status_code == 200
        assert len(resp.json()["assumptions"]) == 0

    def test_list_404_for_missing_aeroplane(self, client_and_db):
        client, _ = client_and_db
        resp = client.get(f"/aeroplanes/{uuid.uuid4()}/assumptions")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /aeroplanes/{id}/assumptions/{param_name}
# ---------------------------------------------------------------------------


class TestUpdateAssumption:
    def test_update_returns_200(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        resp = client.put(
            f"/aeroplanes/{aeroplane.uuid}/assumptions/mass",
            json={"estimate_value": 2.5},
        )
        assert resp.status_code == 200
        assert resp.json()["estimate_value"] == 2.5

    def test_update_404_for_missing_aeroplane(self, client_and_db):
        client, _ = client_and_db
        resp = client.put(
            f"/aeroplanes/{uuid.uuid4()}/assumptions/mass",
            json={"estimate_value": 2.0},
        )
        assert resp.status_code == 404

    def test_update_422_for_invalid_param(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        resp = client.put(
            f"/aeroplanes/{aeroplane.uuid}/assumptions/invalid_param",
            json={"estimate_value": 2.0},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /aeroplanes/{id}/assumptions/{param_name}/source
# ---------------------------------------------------------------------------


class TestSwitchSource:
    def test_switch_returns_200(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        client.post(f"/aeroplanes/{aeroplane.uuid}/assumptions")
        # Switching to ESTIMATE (always valid)
        resp = client.patch(
            f"/aeroplanes/{aeroplane.uuid}/assumptions/mass/source",
            json={"active_source": "ESTIMATE"},
        )
        assert resp.status_code == 200
        assert resp.json()["active_source"] == "ESTIMATE"

    def test_switch_404_for_missing_aeroplane(self, client_and_db):
        client, _ = client_and_db
        resp = client.patch(
            f"/aeroplanes/{uuid.uuid4()}/assumptions/mass/source",
            json={"active_source": "ESTIMATE"},
        )
        assert resp.status_code == 404

    def test_switch_422_for_invalid_param(self, client_and_db):
        client, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)

        resp = client.patch(
            f"/aeroplanes/{aeroplane.uuid}/assumptions/invalid_param/source",
            json={"active_source": "ESTIMATE"},
        )
        assert resp.status_code == 422
