import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel
from app.models.flightprofilemodel import RCFlightProfileModel
from app.schemas.aeroanalysisschema import OperatingPointStatus, TrimOperatingPointRequest
from app.services.operating_point_generator_service import (
    TrimmedPoint,
    _estimate_reference_speeds,
    generate_default_set_for_aircraft,
    trim_operating_point_for_aircraft,
)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
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


def _mock_airplane_with_controls(*control_names: str) -> SimpleNamespace:
    control_surfaces = [SimpleNamespace(name=name) for name in control_names]
    return SimpleNamespace(
        xyz_ref=[0, 0, 0],
        s_ref=1.0,
        wings=[SimpleNamespace(xsecs=[SimpleNamespace(control_surfaces=control_surfaces)])],
    )


def test_generate_default_set_with_profile_assignment(db_session):
    aircraft_uuid = uuid.uuid4()
    profile = RCFlightProfileModel(
        name="profile_a",
        type="trainer",
        environment={"altitude_m": 100, "wind_mps": 0},
        goals={
            "cruise_speed_mps": 20,
            "max_level_speed_mps": 30,
            "min_speed_margin_vs_clean": 1.2,
            "takeoff_speed_margin_vs_to": 1.25,
            "approach_speed_margin_vs_ldg": 1.3,
            "target_turn_n": 2.0,
            "loiter_s": 600,
        },
        handling={
            "stability_preference": "stable",
            "roll_rate_target_dps": 120,
            "pitch_response": "smooth",
            "yaw_coupling_tolerance": "low",
        },
        constraints={"max_bank_deg": 60, "max_alpha_deg": 18, "max_beta_deg": 12},
    )
    db_session.add(profile)
    db_session.flush()

    aircraft = AeroplaneModel(name="plane", uuid=aircraft_uuid, flight_profile_id=profile.id)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch(
            "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
            return_value=SimpleNamespace(),
        ),
        patch(
            "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
            return_value=_mock_airplane_with_controls("[rudder]Rudder"),
        ),
        patch(
            "app.services.operating_point_generator_service._trim_or_estimate_point",
            side_effect=_fake_trim,
        ),
    ):
        result = generate_default_set_for_aircraft(db_session, aircraft_uuid)

    assert result.source_flight_profile_id == profile.id
    assert len(result.operating_points) == 11
    assert "dutch_role_start" in [p.name for p in result.operating_points]

    persisted = (
        db_session.query(OperatingPointModel)
        .filter(OperatingPointModel.aircraft_id == aircraft.id)
        .all()
    )
    assert len(persisted) == 11


def test_generate_default_set_without_profile_uses_defaults(db_session):
    aircraft_uuid = uuid.uuid4()
    aircraft = AeroplaneModel(name="plane-default", uuid=aircraft_uuid)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch(
            "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
            return_value=SimpleNamespace(),
        ),
        patch(
            "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
            return_value=_mock_airplane_with_controls("[rudder]Rudder"),
        ),
        patch(
            "app.services.operating_point_generator_service._trim_or_estimate_point",
            side_effect=_fake_trim,
        ),
    ):
        result = generate_default_set_for_aircraft(db_session, aircraft_uuid)

    assert result.source_flight_profile_id is None
    assert len(result.operating_points) == 11


def test_generate_replace_existing_replaces_old_rows(db_session):
    aircraft_uuid = uuid.uuid4()
    aircraft = AeroplaneModel(name="replace-plane", uuid=aircraft_uuid)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch(
            "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
            return_value=SimpleNamespace(),
        ),
        patch(
            "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
            return_value=_mock_airplane_with_controls("[rudder]Rudder"),
        ),
        patch(
            "app.services.operating_point_generator_service._trim_or_estimate_point",
            side_effect=_fake_trim,
        ),
    ):
        generate_default_set_for_aircraft(db_session, aircraft_uuid)
        generate_default_set_for_aircraft(db_session, aircraft_uuid, replace_existing=True)

    points = (
        db_session.query(OperatingPointModel)
        .filter(OperatingPointModel.aircraft_id == aircraft.id)
        .all()
    )
    assert len(points) == 11


def test_generate_skips_points_when_required_controls_missing(db_session, caplog):
    caplog.set_level("INFO")
    aircraft_uuid = uuid.uuid4()
    aircraft = AeroplaneModel(name="no-controls-plane", uuid=aircraft_uuid)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch(
            "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
            return_value=SimpleNamespace(),
        ),
        patch(
            "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
            return_value=_mock_airplane_with_controls(),
        ),
        patch(
            "app.services.operating_point_generator_service._trim_or_estimate_point",
            side_effect=_fake_trim,
        ),
    ):
        result = generate_default_set_for_aircraft(db_session, aircraft_uuid)

    names = [point.name for point in result.operating_points]
    assert "turn_n2" not in names
    assert "dutch_role_start" not in names
    assert "stall_with_flaps" not in names
    assert len(result.operating_points) == 9

    # Logging can differ depending on global logger configuration. Functional output is asserted above.


def test_generate_with_rudder_keeps_dutch_role_point(db_session):
    aircraft_uuid = uuid.uuid4()
    aircraft = AeroplaneModel(name="rudder-plane", uuid=aircraft_uuid)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch(
            "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
            return_value=SimpleNamespace(),
        ),
        patch(
            "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
            return_value=_mock_airplane_with_controls("[rudder]Rudder"),
        ),
        patch(
            "app.services.operating_point_generator_service._trim_or_estimate_point",
            side_effect=_fake_trim,
        ),
    ):
        result = generate_default_set_for_aircraft(db_session, aircraft_uuid)

    names = [point.name for point in result.operating_points]
    assert "dutch_role_start" in names
    assert len(result.operating_points) == 11


def test_generate_replace_existing_with_skips_keeps_consistent_rows(db_session):
    aircraft_uuid = uuid.uuid4()
    aircraft = AeroplaneModel(name="replace-skip-plane", uuid=aircraft_uuid)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch(
            "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
            return_value=SimpleNamespace(),
        ),
        patch(
            "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
            return_value=_mock_airplane_with_controls(),
        ),
        patch(
            "app.services.operating_point_generator_service._trim_or_estimate_point",
            side_effect=_fake_trim,
        ),
    ):
        generate_default_set_for_aircraft(db_session, aircraft_uuid)
        generate_default_set_for_aircraft(db_session, aircraft_uuid, replace_existing=True)

    points = (
        db_session.query(OperatingPointModel)
        .filter(OperatingPointModel.aircraft_id == aircraft.id)
        .all()
    )
    assert len(points) == 9


def test_trim_single_operating_point_for_aircraft(db_session):
    aircraft_uuid = uuid.uuid4()
    profile = RCFlightProfileModel(
        name="trim_profile",
        type="trainer",
        environment={"altitude_m": 150, "wind_mps": 0},
        goals={
            "cruise_speed_mps": 22,
            "max_level_speed_mps": 30,
            "min_speed_margin_vs_clean": 1.2,
            "takeoff_speed_margin_vs_to": 1.25,
            "approach_speed_margin_vs_ldg": 1.3,
            "target_turn_n": 2.0,
            "loiter_s": 600,
        },
        handling={
            "stability_preference": "stable",
            "roll_rate_target_dps": 120,
            "pitch_response": "smooth",
            "yaw_coupling_tolerance": "low",
        },
        constraints={"max_bank_deg": 60, "max_alpha_deg": 18, "max_beta_deg": 12},
    )
    db_session.add(profile)
    db_session.flush()

    aircraft = AeroplaneModel(name="trim-plane", uuid=aircraft_uuid, flight_profile_id=profile.id)
    db_session.add(aircraft)
    db_session.commit()

    request = TrimOperatingPointRequest(
        name="manual_trim",
        config="clean",
        velocity=21.0,
        altitude=120.0,
        beta_target_deg=1.0,
        n_target=1.1,
    )

    with (
        patch(
            "app.services.operating_point_generator_service.aeroplane_model_to_aeroplane_schema_async",
            return_value=SimpleNamespace(),
        ),
        patch(
            "app.services.operating_point_generator_service.aeroplane_schema_to_asb_airplane_async",
            return_value=_mock_airplane_with_controls("[elevator]Elevator"),
        ),
        patch(
            "app.services.operating_point_generator_service._trim_or_estimate_point",
            side_effect=_fake_trim,
        ),
    ):
        result = trim_operating_point_for_aircraft(db_session, aircraft_uuid, request)

    assert result.source_flight_profile_id == profile.id
    assert result.point.name == "manual_trim"
    assert result.point.status == OperatingPointStatus.TRIMMED
    assert result.point.velocity == pytest.approx(21.0)
    assert result.point.altitude == pytest.approx(120.0)
    assert result.point.aircraft_id == aircraft.id


# ============================================================================
# gh-526 / epic gh-525 finding C1 — physics-based reference speeds from polar
# ============================================================================


def _profile_with_cruise(cruise_mps: float = 22.0) -> dict:
    return {
        "goals": {
            "cruise_speed_mps": cruise_mps,
            "min_speed_margin_vs_clean": 1.20,
        },
        "environment": {},
        "constraints": {},
    }


def test_reference_speeds_use_per_config_v_s_from_context():
    """gh-526: when v_s1_mps / v_s_to_mps / v_s0_mps are in context, use them
    directly instead of applying 0.95 / 0.90 scalars to a single V_s."""
    cached_context = {
        "v_stall_mps": 14.0,  # legacy alias
        "v_s1_mps": 14.0,  # clean
        "v_s_to_mps": 12.5,  # takeoff (with flap)
        "v_s0_mps": 10.5,  # landing (full flap)
    }
    refs = _estimate_reference_speeds(_profile_with_cruise(), cached_context)
    assert refs["vs_clean"] == pytest.approx(14.0)
    assert refs["vs_to"] == pytest.approx(12.5)
    assert refs["vs_ldg"] == pytest.approx(10.5)


def test_reference_speeds_legacy_context_uses_v_stall_for_all_configs():
    """gh-526: older contexts without v_s_to / v_s0 fall back to v_stall_mps
    for both takeoff and landing (no 0.95 / 0.90 scalar applied)."""
    cached_context = {"v_stall_mps": 14.0}  # legacy / pre-526 context
    refs = _estimate_reference_speeds(_profile_with_cruise(), cached_context)
    assert refs["vs_clean"] == pytest.approx(14.0)
    # Without polar_by_config we have no flap-config info — same V_s everywhere
    assert refs["vs_to"] == pytest.approx(14.0)
    assert refs["vs_ldg"] == pytest.approx(14.0)


def test_reference_speeds_cold_start_uses_cruise_over_margin():
    """gh-526: no context at all → cruise / min_margin_clean for all three,
    with no 0.95 / 0.90 multipliers (those scalars are physically meaningless)."""
    refs = _estimate_reference_speeds(_profile_with_cruise(cruise_mps=24.0), None)
    # 24 / 1.20 = 20.0
    assert refs["vs_clean"] == pytest.approx(20.0)
    assert refs["vs_to"] == pytest.approx(20.0)
    assert refs["vs_ldg"] == pytest.approx(20.0)


# ============================================================================
# gh-528 / epic gh-525 finding C3 — grid-search fallback velocity update
# ============================================================================


def test_grid_search_returns_trim_method_grid_fallback():
    """gh-528: when Opti fails to converge well, the trim fallback path
    must set ``trim_method = 'grid_fallback'`` (not 'grid_search') so
    downstream consumers can distinguish a confident Opti convergence
    from an estimated grid result.
    """
    from app.services.operating_point_generator_service import _trim_or_estimate_point

    airplane = _mock_airplane_with_controls("[elevator]Elevator")

    target = {
        "name": "best_angle_climb_vx",
        "config": "clean",
        "velocity": 18.0,
        "altitude": 0.0,
        "beta_target_deg": 0.0,
        "n_target": 1.0,
    }

    # Force Opti to "fail" (return None) so we enter the grid fallback.
    # Force the grid to return a sensible (alpha, beta, V, controls).
    with (
        patch(
            "app.services.operating_point_generator_service._solve_trim_candidate_with_opti",
            return_value=None,
        ),
        patch(
            "app.services.operating_point_generator_service._grid_search_trim",
            return_value=(0.20, 6.0, 0.0, 17.5, {"[elevator]Elevator": -2.5}),
        ),
        patch(
            "app.services.operating_point_generator_service._cl_target_for_velocity",
            return_value=0.65,
        ),
    ):
        point = _trim_or_estimate_point(
            asb_airplane=airplane,
            aircraft=SimpleNamespace(id=1, total_mass_kg=1.5),
            target=target,
            constraints={"max_alpha_deg": 18.0, "max_beta_deg": 12.0},
            capabilities={"available_controls": ["[elevator]Elevator"]},
            effective_mass_kg=1.5,
        )

    assert point.trim_method == "grid_fallback", (
        f"Expected trim_method='grid_fallback' on Opti failure, got '{point.trim_method}'"
    )


def test_grid_search_updates_velocity_from_grid_result():
    """gh-528: after the grid fallback, the OP must record the grid's
    chosen velocity, not the target heuristic.

    Reproduces the regression: target velocity was 18.0 but the grid
    converged at 17.5 — the OP must surface 17.5.
    """
    from app.services.operating_point_generator_service import _trim_or_estimate_point

    airplane = _mock_airplane_with_controls("[elevator]Elevator")

    target = {
        "name": "best_angle_climb_vx",
        "config": "clean",
        "velocity": 18.0,  # target heuristic
        "altitude": 0.0,
        "beta_target_deg": 0.0,
        "n_target": 1.0,
    }

    with (
        patch(
            "app.services.operating_point_generator_service._solve_trim_candidate_with_opti",
            return_value=None,
        ),
        patch(
            "app.services.operating_point_generator_service._grid_search_trim",
            return_value=(0.20, 6.0, 0.0, 17.5, {"[elevator]Elevator": -2.5}),
        ),
        patch(
            "app.services.operating_point_generator_service._cl_target_for_velocity",
            return_value=0.65,
        ),
    ):
        point = _trim_or_estimate_point(
            asb_airplane=airplane,
            aircraft=SimpleNamespace(id=1, total_mass_kg=1.5),
            target=target,
            constraints={"max_alpha_deg": 18.0, "max_beta_deg": 12.0},
            capabilities={"available_controls": ["[elevator]Elevator"]},
            effective_mass_kg=1.5,
        )

    assert point.velocity == pytest.approx(17.5), (
        f"Expected velocity=17.5 from grid result, got {point.velocity}"
    )


def test_grid_fallback_records_solver_path_in_trim_enrichment():
    """gh-528 AC: trim_residuals / trim_enrichment must surface
    a ``solver_path`` field so downstream consumers can audit which
    branch produced each OP."""
    from app.services.operating_point_generator_service import _trim_or_estimate_point

    airplane = _mock_airplane_with_controls("[elevator]Elevator")
    target = {
        "name": "approach_landing",
        "config": "landing",
        "velocity": 14.0,
        "altitude": 0.0,
        "beta_target_deg": 0.0,
        "n_target": 1.0,
        "flap_deflection_deg": 30.0,
    }

    with (
        patch(
            "app.services.operating_point_generator_service._solve_trim_candidate_with_opti",
            return_value=None,
        ),
        patch(
            "app.services.operating_point_generator_service._grid_search_trim",
            return_value=(0.30, 8.0, 0.0, 13.8, {"[elevator]Elevator": -4.0}),
        ),
        patch(
            "app.services.operating_point_generator_service._cl_target_for_velocity",
            return_value=1.05,
        ),
    ):
        point = _trim_or_estimate_point(
            asb_airplane=airplane,
            aircraft=SimpleNamespace(id=1, total_mass_kg=1.5),
            target=target,
            constraints={"max_alpha_deg": 18.0, "max_beta_deg": 12.0},
            capabilities={"available_controls": ["[elevator]Elevator"]},
            effective_mass_kg=1.5,
        )

    # trim_residuals receives the structured fallback metadata so
    # downstream tools (UI, AVL replay) can branch on solver_path.
    assert point.trim_residuals is not None
    assert point.trim_residuals.get("solver_path") == "grid_fallback"


def test_opti_success_keeps_trim_method_opti_and_target_velocity():
    """Regression: when Opti converges, trim_method stays 'opti' and
    the OP records the target velocity (Opti fixes V, solves for α)."""
    from app.services.operating_point_generator_service import _trim_or_estimate_point

    airplane = _mock_airplane_with_controls("[elevator]Elevator")

    target = {
        "name": "cruise",
        "config": "clean",
        "velocity": 22.0,
        "altitude": 0.0,
        "beta_target_deg": 0.0,
        "n_target": 1.0,
    }

    # Opti succeeds with low residual → no fallback.
    with (
        patch(
            "app.services.operating_point_generator_service._solve_trim_candidate_with_opti",
            return_value={
                "score": 0.10,
                "alpha_deg": 3.5,
                "beta_deg": 0.0,
                "controls": {"[elevator]Elevator": -1.2},
                "metrics": {"cm": 0.001, "cl": 0.42, "cy": 0.0},
            },
        ),
        patch(
            "app.services.operating_point_generator_service._cl_target_for_velocity",
            return_value=0.42,
        ),
    ):
        point = _trim_or_estimate_point(
            asb_airplane=airplane,
            aircraft=SimpleNamespace(id=1, total_mass_kg=1.5),
            target=target,
            constraints={"max_alpha_deg": 18.0, "max_beta_deg": 12.0},
            capabilities={"available_controls": ["[elevator]Elevator"]},
            effective_mass_kg=1.5,
        )

    import math as _m

    assert point.trim_method == "opti"
    assert point.velocity == pytest.approx(22.0)
    assert point.alpha_rad == pytest.approx(_m.radians(3.5))


# ============================================================================
# gh-527 / epic gh-525 finding C2 — flap deflection bounded by TED limits
# ============================================================================


def test_clip_flap_to_ted_limit_clips_excessive_deflection():
    """gh-527: when a target's flap_deflection_deg exceeds the TED's
    positive_deflection_deg, the OPG clips it to the limit before the
    trim solver sees the value."""
    from app.services.operating_point_generator_service import _clip_flap_to_ted_limit

    target = {
        "name": "approach_landing",
        "config": "landing",
        "flap_deflection_deg": 30.0,
    }
    # TED only goes to 20°
    deflection_limits = {"[flap]Flap": (20.0, 20.0)}
    clipped = _clip_flap_to_ted_limit(target, deflection_limits)
    assert clipped["flap_deflection_deg"] == 20.0
    assert "FLAP_DEFLECTION_CLIPPED" in clipped.get("warnings", [])


def test_clip_flap_within_limit_is_unchanged():
    """A 15° target on a 25°-rated flap is passed through unchanged with
    no clip warning."""
    from app.services.operating_point_generator_service import _clip_flap_to_ted_limit

    target = {
        "name": "takeoff_climb",
        "config": "takeoff",
        "flap_deflection_deg": 15.0,
    }
    deflection_limits = {"[flap]Flap": (25.0, 25.0)}
    clipped = _clip_flap_to_ted_limit(target, deflection_limits)
    assert clipped["flap_deflection_deg"] == 15.0
    assert "FLAP_DEFLECTION_CLIPPED" not in clipped.get("warnings", [])


def test_clip_flap_no_target_deflection_is_a_noop():
    """Targets without flap_deflection_deg (clean configs) pass through."""
    from app.services.operating_point_generator_service import _clip_flap_to_ted_limit

    target = {"name": "cruise", "config": "clean"}
    deflection_limits = {"[flap]Flap": (25.0, 25.0)}
    clipped = _clip_flap_to_ted_limit(target, deflection_limits)
    assert "flap_deflection_deg" not in clipped


def test_clip_flap_no_flap_in_limits_is_a_noop():
    """Aircraft without a flap-role TED → no clipping, no warning."""
    from app.services.operating_point_generator_service import _clip_flap_to_ted_limit

    target = {
        "name": "approach_landing",
        "config": "landing",
        "flap_deflection_deg": 30.0,
    }
    deflection_limits = {"[elevator]Elevator": (25.0, 25.0)}
    clipped = _clip_flap_to_ted_limit(target, deflection_limits)
    # No flap geometry → leave the target alone (no spurious clip)
    assert clipped["flap_deflection_deg"] == 30.0
    assert "FLAP_DEFLECTION_CLIPPED" not in clipped.get("warnings", [])


def test_trimmed_point_controls_include_flap_deflection():
    """gh-527: when the target has a flap_deflection_deg, the resulting
    TrimmedPoint must include the flap in its `controls` dict so the
    enrichment pipeline can compute its authority ratio."""
    from app.services.operating_point_generator_service import _trim_or_estimate_point

    airplane = _mock_airplane_with_controls("[elevator]Elevator", "[flap]Flap")

    target = {
        "name": "approach_landing",
        "config": "landing",
        "velocity": 14.0,
        "altitude": 0.0,
        "beta_target_deg": 0.0,
        "n_target": 1.0,
        "flap_deflection_deg": 22.0,
    }

    with (
        patch(
            "app.services.operating_point_generator_service._solve_trim_candidate_with_opti",
            return_value={
                "score": 0.15,
                "alpha_deg": 7.5,
                "beta_deg": 0.0,
                "controls": {"[elevator]Elevator": -3.0},
                "metrics": {"cm": 0.001, "cl": 1.0, "cy": 0.0},
            },
        ),
        patch(
            "app.services.operating_point_generator_service._cl_target_for_velocity",
            return_value=1.0,
        ),
    ):
        point = _trim_or_estimate_point(
            asb_airplane=airplane,
            aircraft=SimpleNamespace(id=1, total_mass_kg=1.5),
            target=target,
            constraints={"max_alpha_deg": 18.0, "max_beta_deg": 12.0},
            capabilities={"available_controls": ["[elevator]Elevator", "[flap]Flap"]},
            effective_mass_kg=1.5,
        )

    assert "[flap]Flap" in point.controls, (
        f"flap deflection must be in OP controls; got {list(point.controls.keys())}"
    )
    assert point.controls["[flap]Flap"] == pytest.approx(22.0)


# ============================================================================
# gh-535 — STALE_NO_POLAR warning on cold-start (epic gh-525 follow-up)
# ============================================================================


def test_estimate_reference_speeds_reports_polar_provenance_when_context_present():
    """gh-535: when v_s1_mps is in context, provenance is 'polar'."""
    cached_context = {
        "v_stall_mps": 14.0,
        "v_s1_mps": 14.0,
        "v_s_to_mps": 12.5,
        "v_s0_mps": 10.5,
    }
    refs = _estimate_reference_speeds(_profile_with_cruise(), cached_context)
    assert refs.get("provenance") == "polar"


def test_estimate_reference_speeds_reports_cold_start_when_context_missing():
    """gh-535: with no context, provenance is 'cold_start' so callers
    can stamp the STALE_NO_POLAR warning."""
    refs = _estimate_reference_speeds(_profile_with_cruise(cruise_mps=24.0), None)
    assert refs.get("provenance") == "cold_start"


def test_stamp_stale_no_polar_appends_warning_on_cold_start_only():
    """gh-535: targets coming through `_stamp_stale_no_polar` carry
    'STALE_NO_POLAR' in `warnings` only when refs.provenance == 'cold_start'."""
    from app.services.operating_point_generator_service import _stamp_stale_no_polar

    targets = [
        {"name": "cruise", "config": "clean", "velocity": 20.0},
        {"name": "approach_landing", "config": "landing", "velocity": 14.0},
    ]
    stamped_cold = _stamp_stale_no_polar(targets, {"provenance": "cold_start"})
    for t in stamped_cold:
        assert "STALE_NO_POLAR" in t["warnings"]

    stamped_polar = _stamp_stale_no_polar(targets, {"provenance": "polar"})
    for t in stamped_polar:
        assert "STALE_NO_POLAR" not in t.get("warnings", [])


def test_stamp_stale_no_polar_does_not_duplicate_existing_warning():
    """Idempotent: re-stamping a target that already has the warning
    must not produce duplicates."""
    from app.services.operating_point_generator_service import _stamp_stale_no_polar

    targets = [{"name": "cruise", "warnings": ["STALE_NO_POLAR"]}]
    stamped = _stamp_stale_no_polar(targets, {"provenance": "cold_start"})
    assert stamped[0]["warnings"].count("STALE_NO_POLAR") == 1
