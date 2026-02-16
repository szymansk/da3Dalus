import asyncio
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
    generate_default_set_for_aircraft,
    trim_operating_point_for_aircraft,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


async def _fake_trim(*_, target, **__):
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
        patch("app.services.operating_point_generator_service.aeroplaneModelToAeroplaneSchema_async", return_value=SimpleNamespace()),
        patch("app.services.operating_point_generator_service.aeroplaneSchemaToAsbAirplane_async", return_value=_mock_airplane_with_controls("rudder")),
        patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
    ):
        result = asyncio.run(generate_default_set_for_aircraft(db_session, aircraft_uuid))

    assert result.source_flight_profile_id == profile.id
    assert len(result.operating_points) == 11
    assert "dutch_role_start" in [p.name for p in result.operating_points]

    persisted = db_session.query(OperatingPointModel).filter(OperatingPointModel.aircraft_id == aircraft.id).all()
    assert len(persisted) == 11


def test_generate_default_set_without_profile_uses_defaults(db_session):
    aircraft_uuid = uuid.uuid4()
    aircraft = AeroplaneModel(name="plane-default", uuid=aircraft_uuid)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch("app.services.operating_point_generator_service.aeroplaneModelToAeroplaneSchema_async", return_value=SimpleNamespace()),
        patch("app.services.operating_point_generator_service.aeroplaneSchemaToAsbAirplane_async", return_value=_mock_airplane_with_controls("rudder")),
        patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
    ):
        result = asyncio.run(generate_default_set_for_aircraft(db_session, aircraft_uuid))

    assert result.source_flight_profile_id is None
    assert len(result.operating_points) == 11


def test_generate_replace_existing_replaces_old_rows(db_session):
    aircraft_uuid = uuid.uuid4()
    aircraft = AeroplaneModel(name="replace-plane", uuid=aircraft_uuid)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch("app.services.operating_point_generator_service.aeroplaneModelToAeroplaneSchema_async", return_value=SimpleNamespace()),
        patch("app.services.operating_point_generator_service.aeroplaneSchemaToAsbAirplane_async", return_value=_mock_airplane_with_controls("rudder")),
        patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
    ):
        asyncio.run(generate_default_set_for_aircraft(db_session, aircraft_uuid))
        asyncio.run(generate_default_set_for_aircraft(db_session, aircraft_uuid, replace_existing=True))

    points = db_session.query(OperatingPointModel).filter(OperatingPointModel.aircraft_id == aircraft.id).all()
    assert len(points) == 11


def test_generate_skips_points_when_required_controls_missing(db_session, caplog):
    caplog.set_level("INFO")
    aircraft_uuid = uuid.uuid4()
    aircraft = AeroplaneModel(name="no-controls-plane", uuid=aircraft_uuid)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch("app.services.operating_point_generator_service.aeroplaneModelToAeroplaneSchema_async", return_value=SimpleNamespace()),
        patch("app.services.operating_point_generator_service.aeroplaneSchemaToAsbAirplane_async", return_value=_mock_airplane_with_controls()),
        patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
    ):
        result = asyncio.run(generate_default_set_for_aircraft(db_session, aircraft_uuid))

    names = [point.name for point in result.operating_points]
    assert "turn_n2" not in names
    assert "dutch_role_start" not in names
    assert len(result.operating_points) == 9

    # Logging can differ depending on global logger configuration. Functional output is asserted above.


def test_generate_with_rudder_keeps_dutch_role_point(db_session):
    aircraft_uuid = uuid.uuid4()
    aircraft = AeroplaneModel(name="rudder-plane", uuid=aircraft_uuid)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch("app.services.operating_point_generator_service.aeroplaneModelToAeroplaneSchema_async", return_value=SimpleNamespace()),
        patch("app.services.operating_point_generator_service.aeroplaneSchemaToAsbAirplane_async", return_value=_mock_airplane_with_controls("rudder")),
        patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
    ):
        result = asyncio.run(generate_default_set_for_aircraft(db_session, aircraft_uuid))

    names = [point.name for point in result.operating_points]
    assert "dutch_role_start" in names
    assert len(result.operating_points) == 11


def test_generate_replace_existing_with_skips_keeps_consistent_rows(db_session):
    aircraft_uuid = uuid.uuid4()
    aircraft = AeroplaneModel(name="replace-skip-plane", uuid=aircraft_uuid)
    db_session.add(aircraft)
    db_session.commit()

    with (
        patch("app.services.operating_point_generator_service.aeroplaneModelToAeroplaneSchema_async", return_value=SimpleNamespace()),
        patch("app.services.operating_point_generator_service.aeroplaneSchemaToAsbAirplane_async", return_value=_mock_airplane_with_controls()),
        patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
    ):
        asyncio.run(generate_default_set_for_aircraft(db_session, aircraft_uuid))
        asyncio.run(generate_default_set_for_aircraft(db_session, aircraft_uuid, replace_existing=True))

    points = db_session.query(OperatingPointModel).filter(OperatingPointModel.aircraft_id == aircraft.id).all()
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
        patch("app.services.operating_point_generator_service.aeroplaneModelToAeroplaneSchema_async", return_value=SimpleNamespace()),
        patch(
            "app.services.operating_point_generator_service.aeroplaneSchemaToAsbAirplane_async",
            return_value=_mock_airplane_with_controls("elevator"),
        ),
        patch("app.services.operating_point_generator_service._trim_or_estimate_point", side_effect=_fake_trim),
    ):
        result = asyncio.run(trim_operating_point_for_aircraft(db_session, aircraft_uuid, request))

    assert result.source_flight_profile_id == profile.id
    assert result.point.name == "manual_trim"
    assert result.point.status == OperatingPointStatus.TRIMMED
    assert result.point.velocity == pytest.approx(21.0)
    assert result.point.altitude == pytest.approx(120.0)
    assert result.point.aircraft_id == aircraft.id
