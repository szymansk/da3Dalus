"""Tests for app.services.mission_objective_service (gh-546)."""
from __future__ import annotations

from app.schemas.mission_objective import MissionObjective
from app.services.mission_objective_service import (
    get_mission_objective,
    list_mission_presets,
    upsert_mission_objective,
)
from app.tests.conftest import make_aeroplane


def _make_objective(**overrides):
    payload = dict(
        mission_type="trainer",
        target_cruise_mps=18.0, target_stall_safety=1.8,
        target_maneuver_n=3.0, target_glide_ld=12.0,
        target_climb_energy=22.0, target_wing_loading_n_m2=412.0,
        target_field_length_m=50.0, available_runway_m=50.0,
        runway_type="grass", t_static_N=18.0, takeoff_mode="runway",
    )
    payload.update(overrides)
    return MissionObjective(**payload)


def test_get_returns_default_when_none_persisted(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        aeroplane_id = aeroplane.id

    with SessionLocal() as db:
        obj = get_mission_objective(db, aeroplane_id)
        assert obj.mission_type == "trainer"
        assert obj.target_cruise_mps == 18.0


def test_upsert_creates_then_updates(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        aeroplane = make_aeroplane(db)
        db.commit()
        aircraft_id = aeroplane.id

    with SessionLocal() as db:
        upsert_mission_objective(db, aircraft_id, _make_objective(target_cruise_mps=22.0))
        db.commit()

    with SessionLocal() as db:
        obj = get_mission_objective(db, aircraft_id)
        assert obj.target_cruise_mps == 22.0

    with SessionLocal() as db:
        upsert_mission_objective(db, aircraft_id, _make_objective(target_cruise_mps=25.0))
        db.commit()

    with SessionLocal() as db:
        obj = get_mission_objective(db, aircraft_id)
        assert obj.target_cruise_mps == 25.0


def test_list_mission_presets_returns_six_seeded(client_and_db):
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        presets = list_mission_presets(db)
        ids = {p.id for p in presets}
    assert ids == {"trainer", "sport", "sailplane", "wing_racer", "acro_3d", "stol_bush"}
