import uuid

from app.models.aeroplanemodel import AeroplaneModel

# The `client_and_db` fixture is provided by app/tests/conftest.py.


def valid_profile_payload(name: str = "rc_trainer_balanced") -> dict:
    return {
        "name": name,
        "type": "trainer",
        "environment": {"altitude_m": 0, "wind_mps": 0},
        "goals": {
            "cruise_speed_mps": 18,
            "max_level_speed_mps": 28,
            "min_speed_margin_vs_clean": 1.2,
            "takeoff_speed_margin_vs_to": 1.25,
            "approach_speed_margin_vs_ldg": 1.3,
            "target_turn_n": 2.0,
            "loiter_s": 480,
        },
        "handling": {
            "stability_preference": "stable",
            "roll_rate_target_dps": 120,
            "pitch_response": "smooth",
            "yaw_coupling_tolerance": "low",
        },
        "constraints": {"max_bank_deg": 60, "max_alpha_deg": 14, "max_beta_deg": 8},
    }


def test_create_profile_returns_201(client_and_db):
    client, _ = client_and_db
    response = client.post("/flight-profiles", json=valid_profile_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "rc_trainer_balanced"
    assert body["type"] == "trainer"
    assert "id" in body


def test_create_duplicate_name_returns_409(client_and_db):
    client, _ = client_and_db
    payload = valid_profile_payload()
    client.post("/flight-profiles", json=payload)
    response = client.post("/flight-profiles", json=payload)
    assert response.status_code == 409
    assert "existiert" in response.json()["detail"]


def test_list_profiles_returns_200(client_and_db):
    client, _ = client_and_db
    client.post("/flight-profiles", json=valid_profile_payload("profile_one"))
    response = client.get("/flight-profiles")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_patch_rename_to_existing_name_returns_409(client_and_db):
    client, _ = client_and_db
    first = client.post("/flight-profiles", json=valid_profile_payload("profile_one")).json()
    client.post("/flight-profiles", json=valid_profile_payload("profile_two"))
    response = client.patch(f"/flight-profiles/{first['id']}", json={"name": "profile_two"})
    assert response.status_code == 409
    assert "existiert" in response.json()["detail"]


def test_delete_profile_with_assignment_returns_409(client_and_db):
    client, SessionLocal = client_and_db
    profile = client.post("/flight-profiles", json=valid_profile_payload("assigned_profile")).json()

    aircraft_uuid = uuid.uuid4()
    with SessionLocal() as db:
        db.add(AeroplaneModel(name="test aircraft", uuid=aircraft_uuid))
        db.commit()

    assign = client.put(f"/aircraft/{aircraft_uuid}/flight-profile/{profile['id']}")
    assert assign.status_code == 200

    response = client.delete(f"/flight-profiles/{profile['id']}")
    assert response.status_code == 409


def test_delete_profile_returns_json_payload(client_and_db):
    client, _ = client_and_db
    profile = client.post("/flight-profiles", json=valid_profile_payload("delete_me_profile")).json()

    response = client.delete(f"/flight-profiles/{profile['id']}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok", "operation": "delete_flight_profile"}


def test_assign_and_detach_profile_updates_aircraft(client_and_db):
    client, SessionLocal = client_and_db
    profile = client.post("/flight-profiles", json=valid_profile_payload("linked_profile")).json()

    aircraft_uuid = uuid.uuid4()
    with SessionLocal() as db:
        db.add(AeroplaneModel(name="linked aircraft", uuid=aircraft_uuid))
        db.commit()

    assign = client.put(f"/aircraft/{aircraft_uuid}/flight-profile/{profile['id']}")
    assert assign.status_code == 200
    assert assign.json()["flight_profile_id"] == profile["id"]

    with SessionLocal() as db:
        aircraft = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aircraft_uuid).first()
        assert aircraft.flight_profile_id == profile["id"]

    detach = client.delete(f"/aircraft/{aircraft_uuid}/flight-profile")
    assert detach.status_code == 200
    assert detach.json()["flight_profile_id"] is None

    with SessionLocal() as db:
        aircraft = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aircraft_uuid).first()
        assert aircraft.flight_profile_id is None
