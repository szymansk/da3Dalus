import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.aeroplanemodel import AeroplaneModel
from app.models.analysismodels import OperatingPointModel


@pytest.fixture()
def client_and_db():
    app = create_app()
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, TestingSessionLocal

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_generate_default_endpoint_returns_generated_set(client_and_db):
    client, SessionLocal = client_and_db
    aircraft_uuid = uuid.uuid4()

    with SessionLocal() as db:
        db.add(AeroplaneModel(name="api-plane", uuid=aircraft_uuid))
        db.commit()

    mocked_response = {
        "id": 1,
        "name": "default_operating_point_set",
        "description": "generated",
        "aircraft_id": 1,
        "source_flight_profile_id": None,
        "operating_points": [
            {
                "id": 10,
                "name": "dutch_role_start",
                "description": "mock",
                "aircraft_id": 1,
                "config": "clean",
                "status": "TRIMMED",
                "warnings": [],
                "controls": {},
                "velocity": 20.0,
                "alpha": 0.05,
                "beta": 0.0,
                "p": 0.0,
                "q": 0.0,
                "r": 0.0,
                "xyz_ref": [0.0, 0.0, 0.0],
                "altitude": 0.0,
            }
        ],
    }

    with patch(
        "app.api.v2.endpoints.operating_points.operating_point_generator_service.generate_default_set_for_aircraft",
        new=AsyncMock(return_value=mocked_response),
    ):
        response = client.post(
            f"/aircraft/{aircraft_uuid}/operating-pointsets/generate-default",
            json={"replace_existing": False},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "default_operating_point_set"
    assert body["operating_points"][0]["name"] == "dutch_role_start"


def test_generate_default_endpoint_handles_skipped_points_response(client_and_db):
    client, SessionLocal = client_and_db
    aircraft_uuid = uuid.uuid4()

    with SessionLocal() as db:
        db.add(AeroplaneModel(name="api-skip-plane", uuid=aircraft_uuid))
        db.commit()

    mocked_response = {
        "id": 2,
        "name": "default_operating_point_set",
        "description": "generated-with-skips",
        "aircraft_id": 1,
        "source_flight_profile_id": None,
        "operating_points": [],
    }

    with patch(
        "app.api.v2.endpoints.operating_points.operating_point_generator_service.generate_default_set_for_aircraft",
        new=AsyncMock(return_value=mocked_response),
    ):
        response = client.post(
            f"/aircraft/{aircraft_uuid}/operating-pointsets/generate-default",
            json={"replace_existing": False},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "default_operating_point_set"
    assert body["operating_points"] == []


def test_trim_operating_point_endpoint_returns_trimmed_point(client_and_db):
    client, SessionLocal = client_and_db
    aircraft_uuid = uuid.uuid4()

    with SessionLocal() as db:
        db.add(AeroplaneModel(name="trim-plane", uuid=aircraft_uuid))
        db.commit()

    mocked_response = {
        "source_flight_profile_id": None,
        "point": {
            "name": "custom_trim_point",
            "description": "config=clean, target_n=1.00, V=20.00mps, altitude=0.0m",
            "aircraft_id": 1,
            "config": "clean",
            "status": "TRIMMED",
            "warnings": [],
            "controls": {"elevator": -1.2},
            "velocity": 20.0,
            "alpha": 0.03,
            "beta": 0.0,
            "p": 0.0,
            "q": 0.0,
            "r": 0.0,
            "xyz_ref": [0.0, 0.0, 0.0],
            "altitude": 0.0,
        },
    }

    with patch(
        "app.api.v2.endpoints.operating_points.operating_point_generator_service.trim_operating_point_for_aircraft",
        new=AsyncMock(return_value=mocked_response),
    ):
        response = client.post(
            f"/aircraft/{aircraft_uuid}/operating-points/trim",
            json={
                "name": "custom_trim_point",
                "config": "clean",
                "velocity": 20.0,
                "altitude": 0.0,
                "beta_target_deg": 0.0,
                "n_target": 1.0,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["point"]["name"] == "custom_trim_point"
    assert body["point"]["status"] == "TRIMMED"
    assert body["point"]["controls"]["elevator"] == -1.2


def test_operating_points_filter_by_aircraft_id(client_and_db):
    client, SessionLocal = client_and_db
    aircraft_uuid = uuid.uuid4()

    with SessionLocal() as db:
        aircraft = AeroplaneModel(name="filter-plane", uuid=aircraft_uuid)
        db.add(aircraft)
        db.flush()

        db.add(
            OperatingPointModel(
                aircraft_id=aircraft.id,
                name="cruise",
                description="test",
                config="clean",
                status="TRIMMED",
                warnings=[],
                controls={},
                velocity=18.0,
                alpha=0.04,
                beta=0.0,
                p=0.0,
                q=0.0,
                r=0.0,
                xyz_ref=[0.0, 0.0, 0.0],
                altitude=0.0,
            )
        )
        db.commit()

    response = client.get(f"/operating_points?aircraft_id={aircraft_uuid}")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "cruise"
