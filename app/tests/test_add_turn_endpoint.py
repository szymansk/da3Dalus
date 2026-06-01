"""gh-806: POST add-turn endpoint creates and returns a turn OP."""

import pytest


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_add_turn_endpoint(client_and_db):
    from app.tests.conftest import seed_smoke_conventional_ttail

    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        uuid = aeroplane.uuid
    finally:
        session.close()

    resp = client.post(
        f"/aeroplanes/{uuid}/operating-points/add-turn",
        json={"bank_angle_deg": 30.0},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "turn_30"


def test_add_turn_rejects_bad_bank(client_and_db):
    from app.tests.conftest import seed_smoke_conventional_ttail

    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        uuid = seed_smoke_conventional_ttail(session).uuid
    finally:
        session.close()
    resp = client.post(f"/aeroplanes/{uuid}/operating-points/add-turn", json={"bank_angle_deg": 95.0})
    assert resp.status_code == 422
