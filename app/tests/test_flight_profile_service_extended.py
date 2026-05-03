"""Extended tests for app.services.flight_profile_service — CRUD, assignment, edge cases."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import patch

from app.core.exceptions import ConflictError, InternalError, NotFoundError
from app.schemas.flight_profile import (
    FlightProfileType,
    RCFlightProfileCreate,
    RCFlightProfileUpdate,
)
from app.services import flight_profile_service as svc
from app.tests.conftest import make_aeroplane


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile_payload(
    name: str = "test_trainer",
    profile_type: FlightProfileType = FlightProfileType.trainer,
    cruise_speed_mps: float = 18.0,
) -> RCFlightProfileCreate:
    return RCFlightProfileCreate(
        name=name,
        type=profile_type,
        goals={"cruise_speed_mps": cruise_speed_mps},
    )


def _make_update_payload(**kwargs) -> RCFlightProfileUpdate:
    return RCFlightProfileUpdate(**kwargs)


# ---------------------------------------------------------------------------
# _merge_dict
# ---------------------------------------------------------------------------

class TestMergeDict:
    def test_base_only_when_update_none(self):
        base = {"a": 1, "b": 2}
        result = svc._merge_dict(base, None)
        assert result == {"a": 1, "b": 2}
        # Must be a copy, not the same object
        assert result is not base

    def test_base_only_when_update_empty(self):
        base = {"a": 1}
        result = svc._merge_dict(base, {})
        assert result == {"a": 1}

    def test_update_overrides_base(self):
        base = {"a": 1, "b": 2}
        result = svc._merge_dict(base, {"b": 99})
        assert result == {"a": 1, "b": 99}

    def test_update_adds_new_keys(self):
        base = {"a": 1}
        result = svc._merge_dict(base, {"c": 3})
        assert result == {"a": 1, "c": 3}


# ---------------------------------------------------------------------------
# _get_profile_or_raise / _get_aircraft_or_raise
# ---------------------------------------------------------------------------

class TestGetHelpers:
    def test_profile_not_found(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc._get_profile_or_raise(db, 99999)

    def test_aircraft_not_found(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc._get_aircraft_or_raise(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# create_profile
# ---------------------------------------------------------------------------

class TestCreateProfile:
    def test_create_basic_profile(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            profile = svc.create_profile(db, _make_profile_payload())
            assert profile.id is not None
            assert profile.name == "test_trainer"
            assert profile.type == FlightProfileType.trainer
            assert profile.goals.cruise_speed_mps == 18.0
            assert profile.created_at is not None
            assert profile.updated_at is not None

    def test_create_with_all_sections(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            payload = RCFlightProfileCreate(
                name="full_profile",
                type=FlightProfileType.warbird,
                environment={"altitude_m": 500, "wind_mps": 5},
                goals={"cruise_speed_mps": 25.0, "max_level_speed_mps": 35.0},
                handling={"stability_preference": "agile", "pitch_response": "snappy"},
                constraints={"max_bank_deg": 70, "max_alpha_deg": 15},
            )
            profile = svc.create_profile(db, payload)
            assert profile.environment.altitude_m == 500
            assert profile.environment.wind_mps == 5
            assert profile.goals.max_level_speed_mps == 35.0
            assert profile.handling.stability_preference.value == "agile"
            assert profile.constraints.max_bank_deg == 70

    def test_duplicate_name_raises_conflict(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            svc.create_profile(db, _make_profile_payload(name="unique_name"))
            with pytest.raises(ConflictError):
                svc.create_profile(db, _make_profile_payload(name="unique_name"))

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with patch.object(db, "flush", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.create_profile(db, _make_profile_payload(name="db_fail"))


# ---------------------------------------------------------------------------
# list_profiles
# ---------------------------------------------------------------------------

class TestListProfiles:
    def test_empty_list(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            result = svc.list_profiles(db)
            assert result == []

    def test_returns_all_profiles(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            svc.create_profile(db, _make_profile_payload(name="alpha"))
            svc.create_profile(db, _make_profile_payload(name="beta"))
            result = svc.list_profiles(db)
            assert len(result) == 2

    def test_filter_by_type(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            svc.create_profile(db, _make_profile_payload(name="trainer_one", profile_type=FlightProfileType.trainer))
            svc.create_profile(db, _make_profile_payload(name="glider_one", profile_type=FlightProfileType.glider))

            trainers = svc.list_profiles(db, profile_type=FlightProfileType.trainer)
            assert len(trainers) == 1
            assert trainers[0].name == "trainer_one"

    def test_skip_and_limit(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            for i in range(5):
                svc.create_profile(db, _make_profile_payload(name=f"profile_{i:02d}"))
            result = svc.list_profiles(db, skip=2, limit=2)
            assert len(result) == 2

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with patch.object(db, "query", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.list_profiles(db)


# ---------------------------------------------------------------------------
# get_profile
# ---------------------------------------------------------------------------

class TestGetProfile:
    def test_get_existing(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            created = svc.create_profile(db, _make_profile_payload())
            fetched = svc.get_profile(db, created.id)
            assert fetched.id == created.id
            assert fetched.name == created.name

    def test_raises_not_found(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.get_profile(db, 99999)


# ---------------------------------------------------------------------------
# update_profile
# ---------------------------------------------------------------------------

class TestUpdateProfile:
    def test_update_name(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            created = svc.create_profile(db, _make_profile_payload(name="original"))
            updated = svc.update_profile(db, created.id, _make_update_payload(name="renamed"))
            assert updated.name == "renamed"

    def test_update_type(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            created = svc.create_profile(db, _make_profile_payload())
            updated = svc.update_profile(
                db, created.id,
                _make_update_payload(type=FlightProfileType.glider),
            )
            assert updated.type == FlightProfileType.glider

    def test_partial_update_preserves_other_fields(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            created = svc.create_profile(db, _make_profile_payload(name="keep_goals"))
            updated = svc.update_profile(
                db, created.id,
                _make_update_payload(name="new_name"),
            )
            # Goals should be preserved
            assert updated.goals.cruise_speed_mps == created.goals.cruise_speed_mps

    def test_duplicate_name_raises_conflict(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            svc.create_profile(db, _make_profile_payload(name="existing"))
            p2 = svc.create_profile(db, _make_profile_payload(name="to_rename"))
            with pytest.raises(ConflictError):
                svc.update_profile(db, p2.id, _make_update_payload(name="existing"))

    def test_same_name_no_conflict(self, client_and_db):
        """Updating a profile with its own current name should not conflict."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            created = svc.create_profile(db, _make_profile_payload(name="keep_me"))
            # Update with same name but change type
            updated = svc.update_profile(
                db, created.id,
                _make_update_payload(name="keep_me", type=FlightProfileType.warbird),
            )
            assert updated.name == "keep_me"
            assert updated.type == FlightProfileType.warbird

    def test_raises_not_found(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.update_profile(db, 99999, _make_update_payload(name="nope"))

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            created = svc.create_profile(db, _make_profile_payload(name="db_fail_upd"))
            with patch.object(db, "flush", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.update_profile(db, created.id, _make_update_payload(name="new_name_fail"))

    def test_merge_environment_partial(self, client_and_db):
        """Partial environment update merges with existing values."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            payload = RCFlightProfileCreate(
                name="env_merge",
                type=FlightProfileType.trainer,
                environment={"altitude_m": 200, "wind_mps": 3},
                goals={"cruise_speed_mps": 18.0},
            )
            created = svc.create_profile(db, payload)
            updated = svc.update_profile(
                db, created.id,
                _make_update_payload(environment={"altitude_m": 500}),
            )
            # altitude changed, wind preserved
            assert updated.environment.altitude_m == 500
            assert updated.environment.wind_mps == 3


# ---------------------------------------------------------------------------
# delete_profile
# ---------------------------------------------------------------------------

class TestDeleteProfile:
    def test_delete_existing(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            created = svc.create_profile(db, _make_profile_payload(name="delete_me"))
            svc.delete_profile(db, created.id)
            with pytest.raises(NotFoundError):
                svc.get_profile(db, created.id)

    def test_raises_not_found(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.delete_profile(db, 99999)

    def test_raises_conflict_when_assigned_to_aircraft(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            profile = svc.create_profile(db, _make_profile_payload(name="assigned_prof"))
            aeroplane = make_aeroplane(db)
            svc.assign_profile_to_aircraft(db, aeroplane.uuid, profile.id)

            with pytest.raises(ConflictError):
                svc.delete_profile(db, profile.id)

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            created = svc.create_profile(db, _make_profile_payload(name="db_del_fail"))
            with patch.object(db, "delete", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.delete_profile(db, created.id)


# ---------------------------------------------------------------------------
# assign_profile_to_aircraft
# ---------------------------------------------------------------------------

class TestAssignProfileToAircraft:
    def test_assign_success(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            profile = svc.create_profile(db, _make_profile_payload(name="assign_p"))
            result = svc.assign_profile_to_aircraft(db, aeroplane.uuid, profile.id)
            assert result.aircraft_id == str(aeroplane.uuid)
            assert result.flight_profile_id == profile.id

    def test_reassign_to_different_profile(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            p1 = svc.create_profile(db, _make_profile_payload(name="profile_one"))
            p2 = svc.create_profile(db, _make_profile_payload(name="profile_two"))
            svc.assign_profile_to_aircraft(db, aeroplane.uuid, p1.id)
            result = svc.assign_profile_to_aircraft(db, aeroplane.uuid, p2.id)
            assert result.flight_profile_id == p2.id

    def test_raises_not_found_for_missing_aircraft(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            profile = svc.create_profile(db, _make_profile_payload(name="no_aircraft"))
            with pytest.raises(NotFoundError):
                svc.assign_profile_to_aircraft(db, uuid.uuid4(), profile.id)

    def test_raises_not_found_for_missing_profile(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            with pytest.raises(NotFoundError):
                svc.assign_profile_to_aircraft(db, aeroplane.uuid, 99999)

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            profile = svc.create_profile(db, _make_profile_payload(name="assign_db_fail"))
            with patch.object(db, "flush", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.assign_profile_to_aircraft(db, aeroplane.uuid, profile.id)


# ---------------------------------------------------------------------------
# detach_profile_from_aircraft
# ---------------------------------------------------------------------------

class TestDetachProfileFromAircraft:
    def test_detach_success(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            profile = svc.create_profile(db, _make_profile_payload(name="detach_p"))
            svc.assign_profile_to_aircraft(db, aeroplane.uuid, profile.id)

            result = svc.detach_profile_from_aircraft(db, aeroplane.uuid)
            assert result.aircraft_id == str(aeroplane.uuid)
            assert result.flight_profile_id is None

    def test_detach_already_unassigned(self, client_and_db):
        """Detaching when no profile is assigned should still succeed."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            result = svc.detach_profile_from_aircraft(db, aeroplane.uuid)
            assert result.flight_profile_id is None

    def test_raises_not_found_for_missing_aircraft(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            with pytest.raises(NotFoundError):
                svc.detach_profile_from_aircraft(db, uuid.uuid4())

    def test_db_error_raises_internal_error(self, client_and_db):
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            with patch.object(db, "flush", side_effect=SQLAlchemyError("boom")):
                with pytest.raises(InternalError):
                    svc.detach_profile_from_aircraft(db, aeroplane.uuid)

    def test_delete_profile_after_detach(self, client_and_db):
        """After detaching, the profile should be deletable."""
        _, SessionLocal = client_and_db
        with SessionLocal() as db:
            aeroplane = make_aeroplane(db)
            profile = svc.create_profile(db, _make_profile_payload(name="detach_then_del"))
            svc.assign_profile_to_aircraft(db, aeroplane.uuid, profile.id)
            svc.detach_profile_from_aircraft(db, aeroplane.uuid)
            svc.delete_profile(db, profile.id)  # should not raise
            with pytest.raises(NotFoundError):
                svc.get_profile(db, profile.id)
