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


def test_upsert_changes_mission_type_writes_suggested_estimates(client_and_db):
    """gh-549: switching mission_type rewrites estimate_value per the preset."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        from app.tests.conftest import make_aeroplane
        from app.services.design_assumptions_service import seed_defaults
        from app.models.aeroplanemodel import DesignAssumptionModel

        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aircraft_id = aeroplane.id

    with SessionLocal() as db:
        upsert_mission_objective(db, aircraft_id, _make_objective(mission_type="sailplane"))
        db.commit()

    with SessionLocal() as db:
        rows = {
            r.parameter_name: r
            for r in db.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aircraft_id).all()
        }
        # Sailplane preset values from app/services/mission_preset_seed.py
        assert rows["g_limit"].estimate_value == 5.3
        assert rows["target_static_margin"].estimate_value == 0.10
        assert rows["cl_max"].estimate_value == 1.3
        assert rows["power_to_weight"].estimate_value == 0.0
        assert rows["prop_efficiency"].estimate_value == 0.0


def test_upsert_does_not_touch_calculated_value_when_changing_mission(client_and_db):
    """gh-549 safety: auto-apply must never touch calculated_value or active_source."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        from app.tests.conftest import make_aeroplane
        from app.services.design_assumptions_service import (
            seed_defaults,
            update_calculated_value,
        )
        from app.models.aeroplanemodel import DesignAssumptionModel

        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        # Set a calculated_value via the canonical path (simulate AeroBuildup output)
        update_calculated_value(
            db,
            str(aeroplane.uuid),
            "cl_max",
            1.62,
            "aerobuildup",
            auto_switch_source=True,
        )
        db.commit()
        aircraft_id = aeroplane.id

    with SessionLocal() as db:
        upsert_mission_objective(db, aircraft_id, _make_objective(mission_type="sailplane"))
        db.commit()

    with SessionLocal() as db:
        cl_max_row = (
            db.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aircraft_id, parameter_name="cl_max")
            .one()
        )
        # estimate_value was overwritten by the preset
        assert cl_max_row.estimate_value == 1.3   # sailplane preset
        # calculated_value preserved
        assert cl_max_row.calculated_value == 1.62
        # active_source preserved (CALCULATED takes precedence per existing convention)
        assert cl_max_row.active_source == "CALCULATED"


def test_upsert_no_change_in_mission_type_does_not_rewrite_estimates(client_and_db):
    """Idempotent: re-saving the same mission_type must not rewrite estimates
    (avoids unnecessary writes; matters if user manually tweaked an estimate)."""
    _, SessionLocal = client_and_db
    with SessionLocal() as db:
        from app.tests.conftest import make_aeroplane
        from app.services.design_assumptions_service import seed_defaults
        from app.models.aeroplanemodel import DesignAssumptionModel

        aeroplane = make_aeroplane(db)
        seed_defaults(db, str(aeroplane.uuid))
        db.commit()
        aircraft_id = aeroplane.id

    # First upsert applies trainer defaults
    with SessionLocal() as db:
        upsert_mission_objective(db, aircraft_id, _make_objective(mission_type="trainer"))
        db.commit()

    # User manually overrides g_limit
    with SessionLocal() as db:
        row = (
            db.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aircraft_id, parameter_name="g_limit")
            .one()
        )
        row.estimate_value = 4.5
        db.commit()

    # Re-upsert with SAME mission_type — should NOT rewrite g_limit
    with SessionLocal() as db:
        upsert_mission_objective(db, aircraft_id, _make_objective(mission_type="trainer"))
        db.commit()

    with SessionLocal() as db:
        row = (
            db.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aircraft_id, parameter_name="g_limit")
            .one()
        )
        assert row.estimate_value == 4.5   # user override preserved
