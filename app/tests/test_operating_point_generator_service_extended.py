"""Extended tests for operating_point_generator_service.

Covers the pure/utility functions and internal helpers that the existing
test module does not exercise (lines 49-56, 60-63, 86, 93, 103-104,
247-259, 289, 323-541, 551-609, 755-762, 794, 832-837).
"""

import math
import uuid
from types import SimpleNamespace
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.exceptions import InternalError, NotFoundError, ValidationError
from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel
from app.models.flightprofilemodel import RCFlightProfileModel
from app.schemas.aeroanalysisschema import (
    OperatingPointStatus,
    TrimOperatingPointRequest,
)
from app.services.operating_point_generator_service import (
    TrimmedPoint,
    _apply_limit_warnings,
    _build_target_definitions,
    _cl_target_for_velocity,
    _compute_trim_score,
    _default_profile,
    _detect_control_capabilities,
    _estimate_reference_speeds,
    _evaluate_trim_candidate,
    _fallback_speeds,
    _get_aircraft_or_raise,
    _get_profile_or_raise,
    _grid_search_trim,
    _load_effective_flight_profile,
    _pick_control_name,
    _required_capabilities_for_target,
    _safe_coeff,
    _solve_trim_candidate_with_opti,
    _trim_or_estimate_point,
    _validate_target_capability,
    generate_default_set_for_aircraft,
    trim_operating_point_for_aircraft,
)


# ------------------------------------------------------------------ #
# Fixtures
# ------------------------------------------------------------------ #

@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine, autocommit=False, autoflush=False, class_=Session
    )
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _make_profile(db: Session, **overrides) -> RCFlightProfileModel:
    defaults = dict(
        name="test_profile",
        type="trainer",
        environment={"altitude_m": 0, "wind_mps": 0},
        goals={
            "cruise_speed_mps": 18,
            "max_level_speed_mps": 28,
            "min_speed_margin_vs_clean": 1.20,
            "takeoff_speed_margin_vs_to": 1.25,
            "approach_speed_margin_vs_ldg": 1.30,
            "target_turn_n": 2.0,
            "loiter_s": 600,
        },
        handling={},
        constraints={"max_alpha_deg": 25, "max_beta_deg": 30},
    )
    defaults.update(overrides)
    profile = RCFlightProfileModel(**defaults)
    db.add(profile)
    db.flush()
    return profile


def _make_aircraft(
    db: Session,
    *,
    flight_profile_id: Optional[int] = None,
    total_mass_kg: Optional[float] = None,
) -> AeroplaneModel:
    aircraft = AeroplaneModel(
        name="test-plane",
        uuid=uuid.uuid4(),
        flight_profile_id=flight_profile_id,
        total_mass_kg=total_mass_kg,
    )
    db.add(aircraft)
    db.commit()
    return aircraft


def _mock_airplane_with_controls(*control_names: str) -> SimpleNamespace:
    control_surfaces = [SimpleNamespace(name=n) for n in control_names]
    return SimpleNamespace(
        xyz_ref=[0, 0, 0],
        s_ref=1.0,
        wings=[SimpleNamespace(xsecs=[SimpleNamespace(control_surfaces=control_surfaces)])],
    )


def _fake_trim(*_, target, **__):
    return TrimmedPoint(
        name=target["name"],
        description=f"mocked {target['name']}",
        config=target["config"],
        velocity=float(target["velocity"]),
        altitude=float(target["altitude"]),
        alpha_rad=0.05,
        beta_rad=0.0,
        p=0.0,
        q=0.0,
        r=0.0,
        status=OperatingPointStatus.TRIMMED,
        warnings=[],
        controls={},
    )


# ================================================================== #
# _safe_coeff  (lines 49-56)
# ================================================================== #


class TestSafeCoeff:
    def test_none_value_returns_default(self):
        assert _safe_coeff({"x": None}, "x") == 0.0
        assert _safe_coeff({"x": None}, "x", default=5.0) == 5.0

    def test_missing_key_returns_default(self):
        assert _safe_coeff({}, "x") == 0.0
        assert _safe_coeff({}, "x", default=-1.0) == -1.0

    def test_scalar_float(self):
        assert _safe_coeff({"CL": 1.23}, "CL") == pytest.approx(1.23)

    def test_scalar_int(self):
        assert _safe_coeff({"CL": 3}, "CL") == pytest.approx(3.0)

    def test_numpy_scalar(self):
        assert _safe_coeff({"CL": np.float64(2.5)}, "CL") == pytest.approx(2.5)

    def test_numpy_1d_array(self):
        assert _safe_coeff({"CL": np.array([4.2, 5.0])}, "CL") == pytest.approx(4.2)

    def test_numpy_empty_array_returns_default(self):
        assert _safe_coeff({"CL": np.array([])}, "CL") == 0.0
        assert _safe_coeff({"CL": np.array([])}, "CL", default=9.9) == pytest.approx(9.9)

    def test_numpy_2d_array_ravel(self):
        arr = np.array([[7.7, 8.8]])
        assert _safe_coeff({"x": arr}, "x") == pytest.approx(7.7)


# ================================================================== #
# _compute_trim_score  (lines 60-63)
# ================================================================== #


class TestComputeTrimScore:
    def test_no_cl_target(self):
        score = _compute_trim_score(cm=0.1, cy=0.2, cl=0.5, cl_target=None)
        assert score == pytest.approx(abs(0.1) + 0.5 * abs(0.2))

    def test_with_cl_target(self):
        score = _compute_trim_score(cm=0.0, cy=0.0, cl=1.0, cl_target=0.8)
        assert score == pytest.approx(0.3 * abs(1.0 - 0.8))

    def test_all_zero(self):
        assert _compute_trim_score(0, 0, 0, 0) == pytest.approx(0.0)


# ================================================================== #
# _get_aircraft_or_raise / _get_profile_or_raise  (lines 83-94)
# ================================================================== #


class TestGetOrRaise:
    def test_aircraft_found(self, db_session):
        aircraft = _make_aircraft(db_session)
        result = _get_aircraft_or_raise(db_session, aircraft.uuid)
        assert result.id == aircraft.id

    def test_aircraft_not_found_raises(self, db_session):
        with pytest.raises(NotFoundError):
            _get_aircraft_or_raise(db_session, uuid.uuid4())

    def test_profile_found(self, db_session):
        profile = _make_profile(db_session)
        result = _get_profile_or_raise(db_session, profile.id)
        assert result.id == profile.id

    def test_profile_not_found_raises(self, db_session):
        with pytest.raises(NotFoundError):
            _get_profile_or_raise(db_session, 99999)


# ================================================================== #
# _load_effective_flight_profile  (lines 97-120)
# ================================================================== #


class TestLoadEffectiveFlightProfile:
    def test_profile_override(self, db_session):
        profile = _make_profile(db_session, name="override_profile")
        aircraft = _make_aircraft(db_session)
        data, pid = _load_effective_flight_profile(db_session, aircraft, profile.id)
        assert pid == profile.id
        assert data["name"] == "override_profile"

    def test_aircraft_assigned_profile(self, db_session):
        profile = _make_profile(db_session, name="assigned")
        aircraft = _make_aircraft(db_session, flight_profile_id=profile.id)
        data, pid = _load_effective_flight_profile(db_session, aircraft)
        assert pid == profile.id
        assert data["name"] == "assigned"

    def test_default_profile_fallback(self, db_session):
        aircraft = _make_aircraft(db_session)
        data, pid = _load_effective_flight_profile(db_session, aircraft)
        assert pid is None
        assert data["name"] == "default_profile"


# ================================================================== #
# _fallback_speeds  (lines 247-251)
# ================================================================== #


class TestFallbackSpeeds:
    def test_max_level_speed_decreasing_factors(self):
        speeds = _fallback_speeds("max_level_speed", 20.0)
        assert len(speeds) == 4
        assert speeds[0] == pytest.approx(20.0)
        assert speeds[1] == pytest.approx(19.0)
        assert speeds[2] == pytest.approx(18.0)
        assert speeds[3] == pytest.approx(17.0)

    def test_other_name_increasing_factors(self):
        speeds = _fallback_speeds("cruise", 10.0)
        assert len(speeds) == 4
        assert speeds[0] == pytest.approx(10.0)
        assert speeds[1] == pytest.approx(10.5)
        assert speeds[2] == pytest.approx(11.0)
        assert speeds[3] == pytest.approx(11.5)

    def test_minimum_speed_clamp(self):
        speeds = _fallback_speeds("stall_near_clean", 1.0)
        # All should be >= 2.0
        for s in speeds:
            assert s >= 2.0


# ================================================================== #
# _pick_control_name  (lines 255-259)
# ================================================================== #


class TestPickControlName:
    def test_finds_matching_control(self):
        assert _pick_control_name(["Elevator_Main"], {"elevator"}) == "Elevator_Main"

    def test_returns_none_when_no_match(self):
        assert _pick_control_name(["Flap_Left"], {"elevator"}) is None

    def test_case_insensitive(self):
        assert _pick_control_name(["RUDDER_1"], {"rudder"}) == "RUDDER_1"

    def test_empty_list(self):
        assert _pick_control_name([], {"elevator"}) is None

    def test_first_match_wins(self):
        result = _pick_control_name(["elevon_left", "elevator_right"], {"elevon", "elevator"})
        assert result == "elevon_left"


# ================================================================== #
# _detect_control_capabilities  (lines 262-284)
# ================================================================== #


class TestDetectControlCapabilities:
    def test_with_elevator(self):
        airplane = _mock_airplane_with_controls("elevator")
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is True
        assert caps["has_roll_control"] is False
        assert caps["has_yaw_control"] is False
        assert "elevator" in caps["available_controls"]

    def test_with_aileron_and_rudder(self):
        airplane = _mock_airplane_with_controls("aileron", "rudder")
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is False
        assert caps["has_roll_control"] is True
        assert caps["has_yaw_control"] is True

    def test_with_elevon(self):
        airplane = _mock_airplane_with_controls("elevon_left")
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is True
        assert caps["has_roll_control"] is True

    def test_no_controls(self):
        airplane = _mock_airplane_with_controls()
        caps = _detect_control_capabilities(airplane)
        assert caps["has_pitch_control"] is False
        assert caps["has_roll_control"] is False
        assert caps["has_yaw_control"] is False
        assert caps["available_controls"] == []

    def test_no_wings(self):
        airplane = SimpleNamespace(wings=[])
        caps = _detect_control_capabilities(airplane)
        assert caps["available_controls"] == []

    def test_no_xsecs(self):
        airplane = SimpleNamespace(wings=[SimpleNamespace(xsecs=[])])
        caps = _detect_control_capabilities(airplane)
        assert caps["available_controls"] == []

    def test_empty_name_skipped(self):
        airplane = SimpleNamespace(
            wings=[SimpleNamespace(xsecs=[SimpleNamespace(control_surfaces=[SimpleNamespace(name="")])])]
        )
        caps = _detect_control_capabilities(airplane)
        assert caps["available_controls"] == []

    def test_wings_attr_none(self):
        airplane = SimpleNamespace(wings=None)
        caps = _detect_control_capabilities(airplane)
        assert caps["available_controls"] == []


# ================================================================== #
# _required_capabilities_for_target  (line 289)
# ================================================================== #


class TestRequiredCapabilitiesForTarget:
    def test_turn_n2(self):
        assert _required_capabilities_for_target("turn_n2") == {"has_roll_control|has_yaw_control"}

    def test_dutch_role_start(self):
        assert _required_capabilities_for_target("dutch_role_start") == {"has_yaw_control"}

    def test_cruise_empty(self):
        assert _required_capabilities_for_target("cruise") == set()

    def test_unknown_empty(self):
        assert _required_capabilities_for_target("something_else") == set()


# ================================================================== #
# _validate_target_capability  (lines 295-310)
# ================================================================== #


class TestValidateTargetCapability:
    def test_turn_n2_with_roll_control(self):
        ok, missing = _validate_target_capability(
            {"name": "turn_n2"},
            {"has_roll_control": True, "has_yaw_control": False},
        )
        assert ok is True
        assert missing == ""

    def test_turn_n2_with_yaw_control(self):
        ok, missing = _validate_target_capability(
            {"name": "turn_n2"},
            {"has_roll_control": False, "has_yaw_control": True},
        )
        assert ok is True

    def test_turn_n2_without_controls(self):
        ok, missing = _validate_target_capability(
            {"name": "turn_n2"},
            {"has_roll_control": False, "has_yaw_control": False},
        )
        assert ok is False
        assert "has_roll_control|has_yaw_control" in missing

    def test_dutch_role_without_yaw(self):
        ok, missing = _validate_target_capability(
            {"name": "dutch_role_start"},
            {"has_yaw_control": False},
        )
        assert ok is False
        assert "has_yaw_control" in missing

    def test_dutch_role_with_yaw(self):
        ok, _ = _validate_target_capability(
            {"name": "dutch_role_start"},
            {"has_yaw_control": True},
        )
        assert ok is True

    def test_cruise_always_valid(self):
        ok, _ = _validate_target_capability({"name": "cruise"}, {})
        assert ok is True


# ================================================================== #
# _cl_target_for_velocity  (lines 464-469)
# ================================================================== #


class TestClTargetForVelocity:
    def test_valid_computation(self):
        result = _cl_target_for_velocity(
            candidate_velocity_mps=20.0,
            total_mass_kg=5.0,
            s_ref=0.5,
            rho=1.225,
            n_target=1.0,
        )
        q_dyn = 0.5 * 1.225 * 20.0**2
        expected = (5.0 * 9.81 * 1.0) / (q_dyn * 0.5)
        assert result == pytest.approx(expected)

    def test_no_mass_returns_none(self):
        assert _cl_target_for_velocity(20.0, None, 0.5, 1.225, 1.0) is None
        assert _cl_target_for_velocity(20.0, 0.0, 0.5, 1.225, 1.0) is None

    def test_zero_s_ref_returns_none(self):
        assert _cl_target_for_velocity(20.0, 5.0, 0.0, 1.225, 1.0) is None
        assert _cl_target_for_velocity(20.0, 5.0, -1.0, 1.225, 1.0) is None

    def test_n_target_scaling(self):
        r1 = _cl_target_for_velocity(20.0, 5.0, 0.5, 1.225, 1.0)
        r2 = _cl_target_for_velocity(20.0, 5.0, 0.5, 1.225, 2.0)
        assert r2 == pytest.approx(2.0 * r1)


# ================================================================== #
# _apply_limit_warnings  (lines 525-541)
# ================================================================== #


class TestApplyLimitWarnings:
    def test_trimmed(self):
        warnings: list[str] = []
        status = _apply_limit_warnings(5.0, 0.0, 0.1, {"max_alpha_deg": 25}, warnings)
        assert status == OperatingPointStatus.TRIMMED
        assert warnings == []

    def test_not_trimmed(self):
        warnings: list[str] = []
        status = _apply_limit_warnings(5.0, 0.0, 0.5, {}, warnings)
        assert status == OperatingPointStatus.NOT_TRIMMED
        assert "NOT_TRIMMED" in warnings

    def test_alpha_limit_reached(self):
        warnings: list[str] = []
        status = _apply_limit_warnings(30.0, 0.0, 0.1, {"max_alpha_deg": 25}, warnings)
        assert status == OperatingPointStatus.LIMIT_REACHED
        assert "ALPHA_LIMIT_REACHED" in warnings

    def test_beta_limit_reached(self):
        warnings: list[str] = []
        status = _apply_limit_warnings(5.0, 35.0, 0.1, {"max_beta_deg": 30}, warnings)
        assert status == OperatingPointStatus.LIMIT_REACHED
        assert "BETA_LIMIT_REACHED" in warnings

    def test_both_limits_reached(self):
        warnings: list[str] = []
        status = _apply_limit_warnings(
            30.0, 35.0, 0.5,
            {"max_alpha_deg": 25, "max_beta_deg": 30},
            warnings,
        )
        assert status == OperatingPointStatus.LIMIT_REACHED
        assert "NOT_TRIMMED" in warnings
        assert "ALPHA_LIMIT_REACHED" in warnings
        assert "BETA_LIMIT_REACHED" in warnings

    def test_no_constraint_keys(self):
        warnings: list[str] = []
        status = _apply_limit_warnings(30.0, 35.0, 0.1, {}, warnings)
        assert status == OperatingPointStatus.TRIMMED


# ================================================================== #
# _estimate_reference_speeds
# ================================================================== #


class TestEstimateReferenceSpeeds:
    def test_default_profile(self):
        profile = _default_profile()
        refs = _estimate_reference_speeds(profile)
        assert refs["vs_clean"] >= 3.0
        assert refs["vs_to"] >= 2.5
        assert refs["vs_ldg"] >= 2.0

    def test_low_margin_clamped(self):
        profile = _default_profile()
        profile["goals"]["min_speed_margin_vs_clean"] = 0.5  # below 1.05
        refs = _estimate_reference_speeds(profile)
        # min_margin_clean should be clamped to 1.05
        cruise = 18.0
        assert refs["vs_clean"] == pytest.approx(max(3.0, cruise / 1.05))


# ================================================================== #
# _build_target_definitions
# ================================================================== #


class TestBuildTargetDefinitions:
    def test_returns_12_targets(self):
        profile = _default_profile()
        refs = _estimate_reference_speeds(profile)
        targets = _build_target_definitions(profile, refs)
        assert len(targets) == 12
        names = [t["name"] for t in targets]
        assert "cruise" in names
        assert "dutch_role_start" in names
        assert "turn_n2" in names
        assert "stall_with_flaps" in names

    def test_altitude_propagated(self):
        profile = _default_profile()
        profile["environment"]["altitude_m"] = 500.0
        refs = _estimate_reference_speeds(profile)
        targets = _build_target_definitions(profile, refs)
        for t in targets:
            assert t["altitude"] == 500.0

    def test_max_level_speed_fallback(self):
        profile = _default_profile()
        profile["goals"]["max_level_speed_mps"] = None
        refs = _estimate_reference_speeds(profile)
        targets = _build_target_definitions(profile, refs)
        mls = next(t for t in targets if t["name"] == "max_level_speed")
        cruise = 18.0
        expected = max(1.35 * cruise, cruise + 8.0)
        assert mls["velocity"] == pytest.approx(expected)


# ================================================================== #
# generate_default_set_for_aircraft — error paths (lines 755-762)
# ================================================================== #


class TestGenerateDefaultSetErrors:
    def test_aircraft_not_found_raises(self, db_session):
        with pytest.raises(NotFoundError):
            generate_default_set_for_aircraft(db_session, uuid.uuid4())

    def test_sqlalchemy_error_raises_internal(self, db_session):
        aircraft = _make_aircraft(db_session)
        with (
            patch(
                "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
                side_effect=SQLAlchemyError("db boom"),
            ),
        ):
            with pytest.raises(InternalError, match="Database error"):
                generate_default_set_for_aircraft(db_session, aircraft.uuid)

    def test_generic_exception_raises_internal(self, db_session):
        aircraft = _make_aircraft(db_session)
        with (
            patch(
                "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
                side_effect=RuntimeError("unexpected"),
            ),
        ):
            with pytest.raises(InternalError, match="Operating-point generation error"):
                generate_default_set_for_aircraft(db_session, aircraft.uuid)

    def test_profile_override_not_found_raises(self, db_session):
        aircraft = _make_aircraft(db_session)
        with pytest.raises(NotFoundError):
            generate_default_set_for_aircraft(
                db_session, aircraft.uuid, profile_id_override=99999
            )


# ================================================================== #
# trim_operating_point_for_aircraft — error paths (lines 794, 832-837)
# ================================================================== #


class TestTrimOperatingPointErrors:
    def _make_request(self, **overrides) -> TrimOperatingPointRequest:
        defaults = dict(
            name="test_trim",
            config="clean",
            velocity=20.0,
            altitude=0.0,
            beta_target_deg=0.0,
            n_target=1.0,
        )
        defaults.update(overrides)
        return TrimOperatingPointRequest(**defaults)

    def test_aircraft_not_found(self, db_session):
        request = self._make_request()
        with pytest.raises(NotFoundError):
            trim_operating_point_for_aircraft(db_session, uuid.uuid4(), request)

    def test_missing_controls_raises_validation_error(self, db_session):
        aircraft = _make_aircraft(db_session)
        request = self._make_request(name="turn_n2")
        with (
            patch(
                "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
                return_value=SimpleNamespace(),
            ),
            patch(
                "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
                return_value=_mock_airplane_with_controls(),  # no controls
            ),
        ):
            with pytest.raises(ValidationError, match="cannot be trimmed"):
                trim_operating_point_for_aircraft(db_session, aircraft.uuid, request)

    def test_sqlalchemy_error(self, db_session):
        aircraft = _make_aircraft(db_session)
        request = self._make_request()
        with (
            patch(
                "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
                side_effect=SQLAlchemyError("db error"),
            ),
        ):
            with pytest.raises(InternalError, match="Database error"):
                trim_operating_point_for_aircraft(db_session, aircraft.uuid, request)

    def test_generic_exception(self, db_session):
        aircraft = _make_aircraft(db_session)
        request = self._make_request()
        with (
            patch(
                "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
                side_effect=RuntimeError("boom"),
            ),
        ):
            with pytest.raises(InternalError, match="Operating-point trim error"):
                trim_operating_point_for_aircraft(db_session, aircraft.uuid, request)

    def test_successful_trim_returns_result(self, db_session):
        profile = _make_profile(db_session)
        aircraft = _make_aircraft(db_session, flight_profile_id=profile.id)
        request = self._make_request()
        with (
            patch(
                "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
                return_value=SimpleNamespace(),
            ),
            patch(
                "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
                return_value=_mock_airplane_with_controls("elevator"),
            ),
            patch(
                "app.services.operating_point_generator_service._trim_or_estimate_point",
                side_effect=_fake_trim,
            ),
        ):
            result = trim_operating_point_for_aircraft(db_session, aircraft.uuid, request)

        assert result.source_flight_profile_id == profile.id
        assert result.point.name == "test_trim"
        assert result.point.velocity == pytest.approx(20.0)


# ================================================================== #
# _default_profile
# ================================================================== #


class TestDefaultProfile:
    def test_structure(self):
        p = _default_profile()
        assert p["name"] == "default_profile"
        assert "environment" in p
        assert "goals" in p
        assert "constraints" in p
        assert p["goals"]["cruise_speed_mps"] == 18.0


# ================================================================== #
# TrimmedPoint dataclass
# ================================================================== #


class TestTrimmedPoint:
    def test_construction(self):
        tp = TrimmedPoint(
            name="test",
            description="desc",
            config="clean",
            velocity=20.0,
            altitude=0.0,
            alpha_rad=0.1,
            beta_rad=0.0,
            p=0.0,
            q=0.0,
            r=0.0,
            status=OperatingPointStatus.TRIMMED,
            warnings=[],
            controls={"elevator": 2.5},
        )
        assert tp.name == "test"
        assert tp.controls == {"elevator": 2.5}


# ================================================================== #
# _solve_trim_candidate_with_opti  (lines 323-415)
# ================================================================== #


class TestSolveTrimCandidateWithOpti:
    """Tests for the Opti-based trim solver.

    These mock the aerosandbox Opti/AeroBuildup internals to test
    the function's logic without running real aero computations.
    """

    def _make_target(self, name: str = "cruise") -> dict[str, Any]:
        return {
            "name": name,
            "config": "clean",
            "velocity": 20.0,
            "altitude": 0.0,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
        }

    def test_returns_none_on_exception(self):
        """When anything inside raises, should return None (catch-all)."""
        mock_airplane = MagicMock()
        # Make with_control_deflections raise to trigger the except branch
        mock_airplane.with_control_deflections.side_effect = RuntimeError("boom")

        result = _solve_trim_candidate_with_opti(
            asb_airplane=mock_airplane,
            target=self._make_target(),
            velocity_mps=20.0,
            altitude_m=0.0,
            beta_target_deg=0.0,
            cl_target=0.5,
            constraints={"max_alpha_deg": 25},
            capabilities={"available_controls": ["elevator"]},
        )
        assert result is None

    def test_returns_none_no_controls_and_aero_fails(self):
        """With no controls, if AeroBuildup fails, returns None."""
        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0, 0, 0]

        with patch("app.services.operating_point_generator_service.asb") as mock_asb:
            mock_asb.Opti.return_value = MagicMock()
            mock_asb.Atmosphere.return_value = MagicMock()
            mock_asb.OperatingPoint.return_value = MagicMock()
            mock_asb.AeroBuildup.return_value.run_with_stability_derivatives.side_effect = (
                RuntimeError("aero failure")
            )
            result = _solve_trim_candidate_with_opti(
                asb_airplane=mock_airplane,
                target=self._make_target(),
                velocity_mps=20.0,
                altitude_m=0.0,
                beta_target_deg=0.0,
                cl_target=None,
                constraints={},
                capabilities={"available_controls": []},
            )
        assert result is None


# ================================================================== #
# _evaluate_trim_candidate  (lines 427-453)
# ================================================================== #


class TestEvaluateTrimCandidate:
    """Tests for the trim evaluation function using mocked ASB."""

    def test_basic_evaluation(self):
        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0, 0, 0]

        with patch("app.services.operating_point_generator_service.asb") as mock_asb:
            mock_asb.Atmosphere.return_value = MagicMock()
            mock_asb.OperatingPoint.return_value = MagicMock()
            mock_buildup = MagicMock()
            mock_buildup.run_with_stability_derivatives.return_value = {
                "Cm": 0.01,
                "CL": 0.5,
                "CY": 0.02,
            }
            mock_asb.AeroBuildup.return_value = mock_buildup

            score, metrics = _evaluate_trim_candidate(
                asb_airplane=mock_airplane,
                altitude_m=0.0,
                velocity_mps=20.0,
                alpha_deg=5.0,
                beta_deg=0.0,
                cl_target=0.5,
            )

        assert isinstance(score, float)
        assert metrics["cm"] == pytest.approx(0.01)
        assert metrics["cl"] == pytest.approx(0.5)
        assert metrics["cy"] == pytest.approx(0.02)

    def test_with_controls(self):
        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0, 0, 0]
        mock_deflected = MagicMock()
        mock_deflected.xyz_ref = [0, 0, 0]
        mock_airplane.with_control_deflections.return_value = mock_deflected

        with patch("app.services.operating_point_generator_service.asb") as mock_asb:
            mock_asb.Atmosphere.return_value = MagicMock()
            mock_asb.OperatingPoint.return_value = MagicMock()
            mock_buildup = MagicMock()
            mock_buildup.run_with_stability_derivatives.return_value = {
                "Cm": 0.0,
                "CL": 0.4,
                "CY": 0.0,
            }
            mock_asb.AeroBuildup.return_value = mock_buildup

            score, metrics = _evaluate_trim_candidate(
                asb_airplane=mock_airplane,
                altitude_m=100.0,
                velocity_mps=25.0,
                alpha_deg=3.0,
                beta_deg=1.0,
                cl_target=0.4,
                controls={"elevator": 2.0},
            )

        mock_airplane.with_control_deflections.assert_called_once_with({"elevator": 2.0})
        assert score == pytest.approx(0.0)

    def test_no_cl_target(self):
        mock_airplane = MagicMock()
        mock_airplane.xyz_ref = [0, 0, 0]

        with patch("app.services.operating_point_generator_service.asb") as mock_asb:
            mock_asb.Atmosphere.return_value = MagicMock()
            mock_asb.OperatingPoint.return_value = MagicMock()
            mock_buildup = MagicMock()
            mock_buildup.run_with_stability_derivatives.return_value = {
                "Cm": 0.1,
                "CL": 0.5,
                "CY": 0.2,
            }
            mock_asb.AeroBuildup.return_value = mock_buildup

            score, _ = _evaluate_trim_candidate(
                asb_airplane=mock_airplane,
                altitude_m=0.0,
                velocity_mps=20.0,
                alpha_deg=5.0,
                beta_deg=0.0,
                cl_target=None,
            )

        # score = abs(cm) + 0.5*abs(cy) = 0.1 + 0.1 = 0.2
        assert score == pytest.approx(0.2)


# ================================================================== #
# _grid_search_trim  (lines 484-514)
# ================================================================== #


class TestGridSearchTrim:
    def test_finds_best_score(self):
        """Grid search should call _evaluate_trim_candidate and track the best."""
        call_count = {"n": 0}

        def mock_evaluate(*, asb_airplane, altitude_m, velocity_mps, alpha_deg, beta_deg, cl_target):
            call_count["n"] += 1
            # Return a low score for alpha near 4.0
            score = abs(alpha_deg - 4.0) * 0.1 + 0.01
            return score, {"cm": 0.01, "cl": 0.5, "cy": 0.0}

        mock_airplane = MagicMock()
        target = {"name": "cruise", "velocity": 20.0, "altitude": 0.0}

        with patch(
            "app.services.operating_point_generator_service._evaluate_trim_candidate",
            side_effect=lambda **kw: mock_evaluate(**kw),
        ):
            best_score, best_alpha, best_beta, best_vel, best_controls = _grid_search_trim(
                asb_airplane=mock_airplane,
                target=target,
                velocity=20.0,
                altitude=0.0,
                beta_candidates=[0.0],
                cl_target_fn=lambda v: 0.5,
            )

        assert best_score < float("inf")
        assert call_count["n"] > 0
        assert best_controls == {}

    def test_handles_exception_in_evaluate(self):
        """If _evaluate_trim_candidate raises, grid search should skip."""
        mock_airplane = MagicMock()
        target = {"name": "cruise", "velocity": 20.0, "altitude": 0.0}

        with patch(
            "app.services.operating_point_generator_service._evaluate_trim_candidate",
            side_effect=RuntimeError("eval failed"),
        ):
            best_score, best_alpha, best_beta, best_vel, best_controls = _grid_search_trim(
                asb_airplane=mock_airplane,
                target=target,
                velocity=20.0,
                altitude=0.0,
                beta_candidates=[0.0],
                cl_target_fn=lambda v: None,
            )

        assert best_score == float("inf")


# ================================================================== #
# _trim_or_estimate_point  (lines 551-609)
# ================================================================== #


class TestTrimOrEstimatePoint:
    def _make_target(self, name: str = "cruise") -> dict[str, Any]:
        return {
            "name": name,
            "config": "clean",
            "velocity": 20.0,
            "altitude": 0.0,
            "beta_target_deg": 0.0,
            "n_target": 1.0,
        }

    def test_opti_converges_well(self):
        """When opti returns a good score (<0.35), grid search is skipped."""
        mock_airplane = MagicMock()
        mock_airplane.s_ref = 0.5
        aircraft = MagicMock()
        aircraft.total_mass_kg = 5.0

        opti_result = {
            "alpha_deg": 3.0,
            "beta_deg": 0.0,
            "score": 0.05,
            "controls": {"elevator": 1.5},
            "metrics": {"cm": 0.001, "cy": 0.0, "cl": 0.5},
        }

        with (
            patch("app.services.operating_point_generator_service.asb") as mock_asb,
            patch(
                "app.services.operating_point_generator_service._solve_trim_candidate_with_opti",
                return_value=opti_result,
            ),
            patch(
                "app.services.operating_point_generator_service._grid_search_trim",
            ) as mock_grid,
        ):
            mock_asb.Atmosphere.return_value.density.return_value = 1.225

            result = _trim_or_estimate_point(
                asb_airplane=mock_airplane,
                aircraft=aircraft,
                target=self._make_target(),
                constraints={"max_alpha_deg": 25},
                capabilities={"available_controls": ["elevator"]},
            )

        mock_grid.assert_not_called()
        assert result.name == "cruise"
        assert result.alpha_rad == pytest.approx(math.radians(3.0))
        assert result.controls == {"elevator": 1.5}
        assert result.status == OperatingPointStatus.TRIMMED

    def test_opti_fails_falls_back_to_grid(self):
        """When opti returns None, grid search is used."""
        mock_airplane = MagicMock()
        mock_airplane.s_ref = 0.5
        aircraft = MagicMock()
        aircraft.total_mass_kg = 5.0

        with (
            patch("app.services.operating_point_generator_service.asb") as mock_asb,
            patch(
                "app.services.operating_point_generator_service._solve_trim_candidate_with_opti",
                return_value=None,
            ),
            patch(
                "app.services.operating_point_generator_service._grid_search_trim",
                return_value=(0.1, 5.0, 0.0, 20.0, {}),
            ) as mock_grid,
        ):
            mock_asb.Atmosphere.return_value.density.return_value = 1.225

            result = _trim_or_estimate_point(
                asb_airplane=mock_airplane,
                aircraft=aircraft,
                target=self._make_target(),
                constraints={"max_alpha_deg": 25},
                capabilities={"available_controls": []},
            )

        mock_grid.assert_called_once()
        assert result.alpha_rad == pytest.approx(math.radians(5.0))
        assert result.status == OperatingPointStatus.TRIMMED

    def test_opti_poor_score_triggers_grid(self):
        """When opti score > 0.35, grid search is attempted."""
        mock_airplane = MagicMock()
        mock_airplane.s_ref = 0.5
        aircraft = MagicMock()
        aircraft.total_mass_kg = 5.0

        opti_result = {
            "alpha_deg": 10.0,
            "beta_deg": 0.0,
            "score": 0.5,
            "controls": {},
            "metrics": {"cm": 0.3, "cy": 0.0, "cl": 0.5},
        }

        with (
            patch("app.services.operating_point_generator_service.asb") as mock_asb,
            patch(
                "app.services.operating_point_generator_service._solve_trim_candidate_with_opti",
                return_value=opti_result,
            ),
            patch(
                "app.services.operating_point_generator_service._grid_search_trim",
                return_value=(0.2, 4.0, 0.0, 20.0, {}),
            ),
        ):
            mock_asb.Atmosphere.return_value.density.return_value = 1.225

            result = _trim_or_estimate_point(
                asb_airplane=mock_airplane,
                aircraft=aircraft,
                target=self._make_target(),
                constraints={"max_alpha_deg": 25},
                capabilities={"available_controls": []},
            )

        # Grid search found better score (0.2 < 0.5), so grid result is used
        assert result.alpha_rad == pytest.approx(math.radians(4.0))
        assert result.status == OperatingPointStatus.TRIMMED

    def test_dutch_role_extra_beta_candidates(self):
        """dutch_role_start target should produce 3 beta candidates."""
        mock_airplane = MagicMock()
        mock_airplane.s_ref = 0.5
        aircraft = MagicMock()
        aircraft.total_mass_kg = 5.0

        target = self._make_target("dutch_role_start")
        target["beta_target_deg"] = 2.0
        target["warnings"] = ["NO_CONTROL_TRIM_MVP"]

        with (
            patch("app.services.operating_point_generator_service.asb") as mock_asb,
            patch(
                "app.services.operating_point_generator_service._solve_trim_candidate_with_opti",
                return_value=None,
            ),
            patch(
                "app.services.operating_point_generator_service._grid_search_trim",
                return_value=(0.1, 3.0, 2.0, 20.0, {}),
            ) as mock_grid,
        ):
            mock_asb.Atmosphere.return_value.density.return_value = 1.225

            result = _trim_or_estimate_point(
                asb_airplane=mock_airplane,
                aircraft=aircraft,
                target=target,
                constraints={},
                capabilities={"available_controls": []},
            )

        # Verify beta_candidates passed to grid_search_trim includes [2.0, 0.0, -2.0]
        call_args = mock_grid.call_args
        beta_candidates = call_args.kwargs.get("beta_candidates") or call_args[0][4]
        assert 2.0 in beta_candidates
        assert 0.0 in beta_candidates
        assert -2.0 in beta_candidates
        # Warnings should include the original warning
        assert "NO_CONTROL_TRIM_MVP" in result.warnings

    def test_warnings_from_target_propagated(self):
        """Pre-existing warnings on the target are carried through."""
        mock_airplane = MagicMock()
        mock_airplane.s_ref = 0.5
        aircraft = MagicMock()
        aircraft.total_mass_kg = None

        target = self._make_target()
        target["warnings"] = ["CUSTOM_WARNING"]

        with (
            patch("app.services.operating_point_generator_service.asb") as mock_asb,
            patch(
                "app.services.operating_point_generator_service._solve_trim_candidate_with_opti",
                return_value=None,
            ),
            patch(
                "app.services.operating_point_generator_service._grid_search_trim",
                return_value=(0.5, 8.0, 0.0, 20.0, {}),
            ),
        ):
            mock_asb.Atmosphere.return_value.density.return_value = 1.225

            result = _trim_or_estimate_point(
                asb_airplane=mock_airplane,
                aircraft=aircraft,
                target=target,
                constraints={},
                capabilities={"available_controls": []},
            )

        assert "CUSTOM_WARNING" in result.warnings
        assert result.status == OperatingPointStatus.NOT_TRIMMED
