"""Tests for the computation-context and computation-config endpoints.

Covers:
- GET /aeroplanes/{id}/assumptions/computation-context
- GET /aeroplanes/{id}/computation-config
- PUT /aeroplanes/{id}/computation-config
"""

from __future__ import annotations

import uuid

from app.models.aeroplanemodel import AeroplaneModel
from app.models.computation_config import (
    COMPUTATION_CONFIG_DEFAULTS,
    AircraftComputationConfigModel,
)
from app.tests.conftest import make_aeroplane


def test_get_computation_context_returns_null_when_never_computed(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        aeroplane_uuid = str(aeroplane.uuid)

    resp = client.get(f"/aeroplanes/{aeroplane_uuid}/assumptions/computation-context")
    assert resp.status_code == 200
    assert resp.json() is None


def test_get_computation_context_returns_cached(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        aeroplane.assumption_computation_context = {
            "v_cruise_mps": 18.0,
            "reynolds": 230000,
            "mac_m": 0.21,
        }
        db.commit()
        aeroplane_uuid = str(aeroplane.uuid)

    resp = client.get(f"/aeroplanes/{aeroplane_uuid}/assumptions/computation-context")
    assert resp.status_code == 200
    body = resp.json()
    assert body["v_cruise_mps"] == 18.0
    assert body["reynolds"] == 230000


def test_get_computation_config_creates_default_when_missing(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        aeroplane_uuid = str(aeroplane.uuid)
        aeroplane_id = aeroplane.id

    resp = client.get(f"/aeroplanes/{aeroplane_uuid}/computation-config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["coarse_alpha_step_deg"] == COMPUTATION_CONFIG_DEFAULTS["coarse_alpha_step_deg"]

    with SessionLocal() as db:
        rows = (
            db.query(AircraftComputationConfigModel)
            .filter(AircraftComputationConfigModel.aeroplane_id == aeroplane_id)
            .all()
        )
        assert len(rows) == 1


def test_put_computation_config_updates_fields(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        aeroplane_uuid = str(aeroplane.uuid)

    resp = client.put(
        f"/aeroplanes/{aeroplane_uuid}/computation-config",
        json={"coarse_alpha_step_deg": 0.5, "fine_velocity_count": 12},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["coarse_alpha_step_deg"] == 0.5
    assert body["fine_velocity_count"] == 12
    # Untouched fields keep defaults
    assert body["debounce_seconds"] == COMPUTATION_CONFIG_DEFAULTS["debounce_seconds"]


def test_get_computation_context_404_for_missing_aeroplane(client_and_db):
    client, _ = client_and_db
    resp = client.get(
        f"/aeroplanes/{uuid.uuid4()}/assumptions/computation-context"
    )
    assert resp.status_code == 404
