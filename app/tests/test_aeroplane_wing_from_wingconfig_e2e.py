import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.aeroplanemodel import AeroplaneModel


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "wingconfig_from_prompt.json"


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


def test_create_wing_from_wingconfig_endpoint_persists_full_details(client_and_db):
    client, SessionLocal = client_and_db
    aeroplane_uuid = uuid.uuid4()
    wing_name = "e2e-wing-from-config"

    with FIXTURE_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    with SessionLocal() as db:
        db.add(AeroplaneModel(name="e2e-plane", uuid=aeroplane_uuid))
        db.commit()

    response = client.post(
        f"/aeroplanes/{aeroplane_uuid}/wings/{wing_name}/from-wingconfig",
        json=payload,
    )

    assert response.status_code == 201, response.text
    assert response.json() == {
        "status": "created",
        "operation": "create_aeroplane_wing_from_wingconfig",
    }

    # Verify the new AirplaneConfiguration endpoint returns the serialized configuration.
    with SessionLocal() as db:
        plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
        assert plane is not None
        plane.total_mass_kg = 2.5
        db.commit()

    config_response = client.get(f"/aeroplanes/{aeroplane_uuid}/airplane_configuration")
    assert config_response.status_code == 200, config_response.text
    config_payload = config_response.json()
    assert config_payload["name"] == "e2e-plane"
    assert config_payload["total_mass_kg"] == pytest.approx(2.5)
    assert len(config_payload["wings"]) == 1
    assert config_payload["wings"][0]["symmetric"] is True

    with SessionLocal() as db:
        plane = db.query(AeroplaneModel).filter(AeroplaneModel.uuid == aeroplane_uuid).first()
        assert plane is not None
        assert len(plane.wings) == 1

        wing = plane.wings[0]
        assert wing.name == wing_name
        assert wing.symmetric is True

        # One x-sec per segment root plus one terminal x-sec.
        assert len(wing.x_secs) == len(payload["segments"]) + 1
        assert wing.x_secs[-1].detail is None

        # Segment-anchored detail data from payload should be persisted.
        assert len(wing.x_secs[0].detail.spares) == 3
        assert len(wing.x_secs[1].detail.spares) == 3

        ted_count = 0
        spare_count = 0
        for index, x_sec in enumerate(wing.x_secs[:-1]):
            assert x_sec.detail is not None
            assert x_sec.detail.x_sec_type in {"root", "segment", "tip"}
            assert x_sec.detail.number_interpolation_points == 201

            spare_count += len(x_sec.detail.spares)

            ted = x_sec.detail.trailing_edge_device
            if ted is not None:
                ted_count += 1
                assert ted.name == "aileron"
                assert ted.rel_chord_root == pytest.approx(0.8)
                assert x_sec.control_surface is not None
                assert x_sec.control_surface.hinge_point == pytest.approx(ted.rel_chord_root)

            # Tip segments (last 5 segment anchors) keep tip_type=flat.
            if index >= 7:
                assert x_sec.detail.tip_type == "flat"

        # One additional minimal TED is canonicalized from an ASB control surface.
        assert ted_count == 5
        assert spare_count == 11

        # First TED from payload has asymmetric behavior and should be preserved.
        first_ted_xsec = wing.x_secs[2]
        assert first_ted_xsec.detail.trailing_edge_device is not None
        assert first_ted_xsec.detail.trailing_edge_device.symmetric is False
        assert first_ted_xsec.control_surface is not None
        assert first_ted_xsec.control_surface.symmetric is False
