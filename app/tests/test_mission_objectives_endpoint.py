"""Endpoint tests for Mission Objectives + Mission Presets (gh-546)."""
from __future__ import annotations

from app.tests.conftest import make_aeroplane


def test_get_mission_objectives_default(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        uuid = str(aeroplane.uuid)

    r = client.get(f"/aeroplanes/{uuid}/mission-objectives")
    assert r.status_code == 200
    body = r.json()
    assert body["mission_type"] == "trainer"
    assert body["target_cruise_mps"] == 18.0


def test_put_mission_objectives_persists(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        uuid = str(aeroplane.uuid)

    payload = {
        "mission_type": "sailplane",
        "target_cruise_mps": 14.0, "target_stall_safety": 1.6,
        "target_maneuver_n": 4.0, "target_glide_ld": 25.0,
        "target_climb_energy": 45.0, "target_wing_loading_n_m2": 200.0,
        "target_field_length_m": 60.0, "available_runway_m": 80.0,
        "runway_type": "grass", "t_static_N": 0.0, "takeoff_mode": "bungee",
    }
    r = client.put(f"/aeroplanes/{uuid}/mission-objectives", json=payload)
    assert r.status_code == 200

    r2 = client.get(f"/aeroplanes/{uuid}/mission-objectives")
    assert r2.json()["mission_type"] == "sailplane"
    assert r2.json()["target_glide_ld"] == 25.0


def test_get_mission_presets_returns_six(client_and_db):
    client, _ = client_and_db
    r = client.get("/mission-presets")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()}
    assert ids == {"trainer", "sport", "sailplane", "wing_racer", "acro_3d", "stol_bush"}
