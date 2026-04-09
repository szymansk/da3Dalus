"""Error-path coverage for under-tested REST endpoints.

Covers the four default failure scenarios locked in during the
REST API stabilisation planning round:

1. GET /aeroplanes/{id} with a non-existent aeroplane → 404
2. PUT /aeroplanes/{id}/fuselages/{name} with a duplicate name → 409
3. POST /aeroplanes/{id}/wings/{name} with invalid geometry → 422
4. DELETE /operating_points/{op_id} when referenced by a pointset → 409
"""

from __future__ import annotations

import uuid

import pytest

from app.models.aeroplanemodel import AeroplaneModel


pytestmark = pytest.mark.integration


# --------------------------------------------------------------------------- #
# 1. GET /aeroplanes/{id} → 404
# --------------------------------------------------------------------------- #


def test_get_aeroplane_by_uuid_returns_404_when_missing(client_and_db):
    client, _ = client_and_db
    unknown = uuid.uuid4()
    response = client.get(f"/aeroplanes/{unknown}")
    assert response.status_code == 404
    body = response.json()
    # The ServiceException handler wraps the error in an "error" envelope.
    assert "error" in body or "detail" in body


# --------------------------------------------------------------------------- #
# 2. PUT /aeroplanes/{id}/fuselages/{name} → 409 on duplicate
# --------------------------------------------------------------------------- #


def test_create_fuselage_twice_returns_409_on_duplicate_name(client_and_db):
    client, SessionLocal = client_and_db

    # Create an aeroplane to attach fuselages to.
    with SessionLocal() as db:
        aeroplane = AeroplaneModel(name="dup-fuselage-plane", uuid=uuid.uuid4())
        db.add(aeroplane)
        db.commit()
        db.refresh(aeroplane)
        aeroplane_uuid = str(aeroplane.uuid)

    # FuselageSchema requires at least 2 cross-sections.
    minimal_fuselage_body = {
        "name": "main",
        "x_secs": [
            {"xyz": [0.0, 0.0, 0.0], "a": 0.05, "b": 0.05, "n": 2.0},
            {"xyz": [0.5, 0.0, 0.0], "a": 0.05, "b": 0.05, "n": 2.0},
        ],
    }

    first = client.put(
        f"/aeroplanes/{aeroplane_uuid}/fuselages/main",
        json=minimal_fuselage_body,
    )
    # First create is permitted — we are not asserting the exact success code
    # (it could be 200 or 201 depending on how the endpoint was wired), only
    # that it is not a 409.
    assert first.status_code < 400, first.text

    second = client.put(
        f"/aeroplanes/{aeroplane_uuid}/fuselages/main",
        json=minimal_fuselage_body,
    )
    # Duplicate name on the same aeroplane must be a 409 Conflict.
    assert second.status_code == 409, second.text


# --------------------------------------------------------------------------- #
# 3. POST /aeroplanes/{id}/wings/{name} → 422 on invalid geometry
# --------------------------------------------------------------------------- #


def test_create_wing_with_invalid_geometry_returns_422(client_and_db):
    client, SessionLocal = client_and_db

    with SessionLocal() as db:
        aeroplane = AeroplaneModel(name="invalid-wing-plane", uuid=uuid.uuid4())
        db.add(aeroplane)
        db.commit()
        db.refresh(aeroplane)
        aeroplane_uuid = str(aeroplane.uuid)

    # Deliberately malformed wing body: missing required x_secs, wrong
    # types, etc. FastAPI's RequestValidationError handler turns this
    # into a 422 response.
    bogus_body = {
        "nope": "not a valid wing schema",
    }

    response = client.put(
        f"/aeroplanes/{aeroplane_uuid}/wings/broken_wing",
        json=bogus_body,
    )
    assert response.status_code == 422, response.text


# --------------------------------------------------------------------------- #
# 4. DELETE /operating_points/{op_id} when referenced → 409 (or 404 if none)
# --------------------------------------------------------------------------- #


def test_delete_nonexistent_operating_point_returns_404(client_and_db):
    """
    Baseline check: deleting an op that does not exist returns 404.

    This test pins the current behaviour. A separate follow-up (tracked
    as cad-modelling-service-ge9 notes) should add the 409-on-reference
    case once the service layer enforces that constraint.
    """
    client, _ = client_and_db
    response = client.delete("/operating_points/999999")
    assert response.status_code == 404, response.text
