"""Expert View backend (gh-1282, ADR 0030): the canon endpoints with the kernel boundary stubbed."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from aero_kernel.schema import (
    AircraftInput,
    ComputeRequest,
    ComputeResult,
    Provenance,
    QuantityResult,
    QuantityStatus,
    TimeBounds,
    Timing,
)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app as application
from app.models.aeroplanemodel import (
    AeroplaneModel,
    BranchModel,
    DesignAssumptionModel,
    WingXSecModel,
)
from app.services import canon_service
from app.tests.conftest import make_aeroplane, make_wing, seed_integration_aeroplane


@pytest.fixture
def enveloped_db_client() -> Iterator[tuple[TestClient, sessionmaker]]:
    """The enveloped client, its database an in-memory one the test fills (never db/test.db)."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def in_memory_db() -> Iterator[Session]:
        with session_factory() as db:
            yield db
            db.commit()

    application.dependency_overrides[get_db] = in_memory_db
    try:
        yield TestClient(application), session_factory
    finally:
        application.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def enveloped_client(enveloped_db_client) -> TestClient:
    """A client of the real application, whose handlers turn errors into the one error envelope.

    Not entered as a context manager: the startup seeding of the database does not run.
    """
    client, _ = enveloped_db_client
    return client


async def stub_kernel(
    aircraft: AircraftInput, request: ComputeRequest, **_limits: int | None
) -> ComputeResult:
    quantity = QuantityResult(
        slug=request.quantities[0],
        unit="m/s",
        status=QuantityStatus.OK,
        value=7.5,
        tool="APP",
        application="a",
        timing=Timing.of(
            own=TimeBounds(lower=0.25, upper=0.75), before=TimeBounds(lower=1.0, upper=1.5)
        ),
    )
    return ComputeResult(quantities=(quantity,), provenance=Provenance(build_digest="test"))


class Facade:
    """Replaces the shared ``CachedKernel`` with the stub."""

    compute = staticmethod(stub_kernel)


def use_kernel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer the cached path (the default) with the stub."""
    monkeypatch.setattr(canon_service, "KERNEL", Facade())


# The first six and the 28 plan models of #1372, by their fleet ids.
FLEET_IDS = {
    "bryan",
    "jaguar",
    "rv-7",
    "chekker",
    "wiesel",
    "belemnitos",
    "a6m2_zero",
    "aeronca_champ",
    "albatros_4",
    "barracuda",
    "bf109_e",
    "d520_dewoitine",
    "dardo",
    "estrela",
    "extra_300_ep",
    "f3a_competicion",
    "force_5",
    "force_four",
    "fw190_a8",
    "gee_bee_r3",
    "kastaway",
    "miles_magister",
    "mini_funtana",
    "p36_hawk",
    "p39",
    "snoopy",
    "sonas_40",
    "spirit_100",
    "sprite",
    "super_trident",
    "ultra_mini_stick",
    "voodoo",
    "windfreak",
    "wristocrat",
    "avistar_elite",
    "ultra_stick_120",
}


@pytest.mark.integration
def test_the_fleet_is_listed(client_and_db):
    client, _ = client_and_db
    response = client.get("/canon/aircraft")
    assert response.status_code == 200
    fleet = response.json()["fleet"]
    ids = {entry["id"] for entry in fleet}
    assert ids == FLEET_IDS
    assert set(fleet[0]) == {"id", "name", "mass_kg", "flap_deflections"}


def add_branch(db: Session, plane: AeroplaneModel, name: str, *, main: bool) -> None:
    """Make ``plane`` the head of a new branch of its own lineage."""
    plane.root_id = plane.root_id or plane.id
    branch = BranchModel(
        root_id=plane.root_id, head_id=plane.id, name=name, is_main=main, created_by="human"
    )
    db.add(branch)
    db.flush()
    plane.branch_id = branch.id
    db.commit()


def stored(db: Session, name: str, *, mass: float | None = None) -> AeroplaneModel:
    plane = make_aeroplane(db, name=name)
    if mass is not None:
        db.add(
            DesignAssumptionModel(
                aeroplane_id=plane.id,
                parameter_name="mass",
                estimate_value=mass,
                active_source="ESTIMATE",
                updated_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    return plane


@pytest.mark.integration
def test_the_stored_aeroplanes_are_listed_in_their_current_state_only(client_and_db):
    client, session_factory = client_and_db
    with session_factory() as db:
        head = stored(db, "Bravo", mass=1.25)
        add_branch(db, head, "main", main=True)
        snapshot = stored(db, "Bravo")
        snapshot.root_id, snapshot.branch_id, snapshot.is_immutable = (
            head.id,
            head.branch_id,
            True,
        )
        head.predecessor_id = snapshot.id
        side = stored(db, "Bravo (experiment)")
        side.root_id = head.id
        add_branch(db, side, "experiment", main=False)
        legacy = stored(db, "Alpha")
        db.commit()
        expected = [(str(legacy.uuid), "Alpha", None), (str(head.uuid), "Bravo", 1.25)]
    response = client.get("/canon/aircraft")
    assert response.status_code == 200
    aeroplanes = response.json()["aeroplanes"]
    assert [(a["id"], a["name"], a["mass_kg"]) for a in aeroplanes] == expected


@pytest.mark.integration
def test_a_quantity_of_a_stored_aeroplane_is_computed(client_and_db, monkeypatch):
    received: list[AircraftInput] = []

    async def recording(aircraft: AircraftInput, request: ComputeRequest, **limits: int | None):
        received.append(aircraft)
        return await stub_kernel(aircraft, request, **limits)

    monkeypatch.setattr(
        canon_service, "KERNEL", type("F", (), {"compute": staticmethod(recording)})
    )
    client, session_factory = client_and_db
    with session_factory() as db:
        plane = seed_integration_aeroplane(db)
        aeroplane_id = str(plane.uuid)
        db.add(
            DesignAssumptionModel(
                aeroplane_id=plane.id,
                parameter_name="mass",
                estimate_value=1.1,
                active_source="ESTIMATE",
                updated_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
    response = client.post(
        "/canon/compute",
        json={
            "aircraft": {"aeroplane": aeroplane_id},
            "quantities": ["stall-speed"],
            "values": {"altitude": 500.0},
        },
    )
    assert response.status_code == 200
    assert response.json()["quantities"][0]["value"] == pytest.approx(7.5)
    (aircraft,) = received
    assert aircraft.airplane.name == "integration-test-plane"
    assert aircraft.values == {"aircraft-mass": 1.1, "altitude": 500.0}


@pytest.mark.integration
def test_an_unknown_aeroplane_answers_with_the_error_envelope(enveloped_db_client, monkeypatch):
    use_kernel(monkeypatch)
    client, _ = enveloped_db_client
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"aeroplane": str(uuid.uuid4())}, "quantities": ["stall-speed"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.integration
def test_an_aeroplane_that_does_not_convert_names_the_input_path(enveloped_db_client, monkeypatch):
    use_kernel(monkeypatch)
    client, session_factory = enveloped_db_client
    with session_factory() as db:
        plane = make_aeroplane(db, name="one rib")
        wing = make_wing(db, aeroplane_id=plane.id)
        db.add(
            WingXSecModel(
                wing_id=wing.id,
                xyz_le=[0, 0, 0],
                chord=0.2,
                twist=0,
                airfoil="naca2412",
                sort_index=0,
            )
        )
        db.commit()
        aeroplane_id = str(plane.uuid)
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"aeroplane": aeroplane_id}, "quantities": ["stall-speed"]},
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    (item,) = error["details"]["input_errors"]
    assert item["input_path"] == 'airplane.wings["main_wing"].x_secs'


@pytest.mark.integration
@pytest.mark.parametrize(
    "aircraft",
    [
        {"fleet": "bryan", "aeroplane": "6f1c1a52-8f3c-4a43-9d9a-2c7c4c3b5a10"},
        {"aeroplane": "not-a-uuid"},
        {},
    ],
)
def test_an_aircraft_reference_that_is_not_one_of_the_two_is_rejected(enveloped_client, aircraft):
    response = enveloped_client.post(
        "/canon/compute", json={"aircraft": aircraft, "quantities": ["stall-speed"]}
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_a_quantity_is_computed(client_and_db, monkeypatch):
    use_kernel(monkeypatch)
    client, _ = client_and_db
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"fleet": "bryan"}, "quantities": ["stall-speed"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "quantities",
        "input_errors",
        "provenance",
        "verdicts",
        "needs_confirmation",
        "logs",
    }
    assert body["quantities"][0]["slug"] == "stall-speed"
    assert body["quantities"][0]["value"] == pytest.approx(7.5)
    assert body["needs_confirmation"] == []
    timing = body["quantities"][0]["timing"]
    assert timing["own_s"] == {"lower": pytest.approx(0.25), "upper": pytest.approx(0.75)}
    assert timing["before_s"] == {"lower": pytest.approx(1.0), "upper": pytest.approx(1.5)}
    assert timing["total_s"] == {"lower": pytest.approx(1.25), "upper": pytest.approx(2.25)}


@pytest.mark.integration
def test_an_unknown_aircraft_answers_with_the_error_envelope(enveloped_client, monkeypatch):
    use_kernel(monkeypatch)
    client = enveloped_client
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"fleet": "nonexistent"}, "quantities": ["stall-speed"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.integration
def test_no_quantity_answers_with_the_error_envelope(enveloped_client):
    client = enveloped_client
    response = client.post(
        "/canon/compute", json={"aircraft": {"fleet": "bryan"}, "quantities": []}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.integration
def test_a_quantity_requested_twice_answers_with_the_error_envelope(enveloped_client):
    client = enveloped_client
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"fleet": "bryan"}, "quantities": ["stall-speed", "stall-speed"]},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.integration
def test_a_fresh_request_recomputes_without_the_cache(client_and_db, monkeypatch):
    monkeypatch.setattr(canon_service, "compute", stub_kernel)
    monkeypatch.setattr(canon_service, "KERNEL", None)  # the facade must not be touched
    client, _ = client_and_db
    response = client.post(
        "/canon/compute",
        json={"aircraft": {"fleet": "bryan"}, "quantities": ["stall-speed"], "fresh": True},
    )
    assert response.status_code == 200
    assert response.json()["quantities"][0]["from_cache"] is False


def test_the_compute_request_documents_the_fresh_flag(enveloped_client):
    schema = enveloped_client.get("/openapi.json").json()["components"]["schemas"]
    fresh = schema["CanonComputeRequest"]["properties"]["fresh"]
    assert fresh["default"] is False
    assert "cache" in fresh["description"]
