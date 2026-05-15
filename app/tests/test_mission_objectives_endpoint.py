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


def test_get_mission_kpis_returns_seven_axes(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db, total_mass_kg=2.0)
        uuid = str(aeroplane.uuid)
        a_id = aeroplane.id

    # Seed a context so the KPIs aren't all "missing"
    from app.models.aeroplanemodel import AeroplaneModel

    with SessionLocal() as db:
        a = db.query(AeroplaneModel).filter_by(id=a_id).one()
        a.assumption_computation_context = {
            "v_cruise_mps": 18.0,
            "v_s1_mps": 12.0,
            "aspect_ratio": 8.0,
            "s_ref_m2": 0.3,
            "polar_by_config": {
                "clean": {"cd0": 0.025, "e_oswald": 0.8, "cl_max": 1.4},
            },
            "flight_envelope_n_max": 3.0,
        }
        db.commit()

    r = client.get(f"/aeroplanes/{uuid}/mission-kpis")
    assert r.status_code == 200
    body = r.json()
    assert set(body["ist_polygon"].keys()) == {
        "stall_safety",
        "glide",
        "climb",
        "cruise",
        "maneuver",
        "wing_loading",
        "field_friendliness",
    }
    # Default mission is "trainer" (from default MissionObjective)
    assert body["active_mission_id"] == "trainer"
    assert {p["mission_id"] for p in body["target_polygons"]} == {"trainer"}


def test_get_mission_kpis_multi_mission_param(client_and_db):
    client, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        uuid = str(aeroplane.uuid)

    r = client.get(
        f"/aeroplanes/{uuid}/mission-kpis?missions=trainer&missions=sailplane"
    )
    assert r.status_code == 200
    body = r.json()
    assert {p["mission_id"] for p in body["target_polygons"]} == {
        "trainer",
        "sailplane",
    }
    # First query arg drives active_mission_id
    assert body["active_mission_id"] == "trainer"


def test_get_mission_kpis_404_for_unknown_aeroplane(client_and_db):
    client, _ = client_and_db
    # Well-formed but unknown UUID4 (version digit "4" at position 14)
    unknown_uuid = "11111111-1111-4111-8111-111111111111"
    r = client.get(f"/aeroplanes/{unknown_uuid}/mission-kpis")
    assert r.status_code == 404
