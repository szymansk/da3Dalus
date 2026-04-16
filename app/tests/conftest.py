"""Shared pytest fixtures for the cad-modelling-service test suite.

Everything that more than one test file needs lives here. New tests should
prefer these fixtures over reinventing the pattern.

Scope choices:
- `client_and_db` is function-scoped: each test gets a fresh in-memory SQLite
  and a fresh FastAPI TestClient. Max isolation, cheapest to reason about.
- `clean_cad_task_state` is function-scoped and autouse: every test starts
  with an empty cad_service.tasks dict so the global state stops leaking
  between tests.

Factory helpers return ORM instances that are already committed to the
session, so tests can rely on `.id` being populated.
"""

from __future__ import annotations

import uuid
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.aeroplanemodel import AeroplaneModel, FuselageModel, WingModel
from app.models.analysismodels import OperatingPointModel
from app.services import cad_service
from app.services.component_type_service import seed_default_types


# --------------------------------------------------------------------------- #
# Core fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture()
def client_and_db() -> Tuple[TestClient, sessionmaker]:
    """Fresh FastAPI TestClient + in-memory SQLite session factory per test.

    Yields a tuple of (TestClient, SessionLocal). SessionLocal is a
    sessionmaker that test code can use to create extra sessions outside
    of the FastAPI dependency chain (e.g. for direct setup via factory
    helpers).
    """
    app = create_app()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    # gh#83: seed the default component types so tests see the same registry
    # shape that a migrated prod DB would have.
    _seed_session = TestingSessionLocal()
    try:
        seed_default_types(_seed_session)
    finally:
        _seed_session.close()

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


@pytest.fixture(autouse=True)
def clean_cad_task_state():
    """Clear cad_service task state + process pool around every test.

    cad_service keeps task state in a module-level dict guarded by a Lock.
    Without this fixture, tasks from one test leak into the next and
    polling-based assertions become flaky.

    We also shut down the ProcessPoolExecutor both before and after each
    test so that no worker process outlives its test. The executor is
    lazily re-created by ``_get_executor`` when the next test actually
    submits CAD work, so tests that never touch the CAD path pay no
    spawn cost.
    """
    with cad_service.tasks_lock:
        cad_service.tasks.clear()
    cad_service.shutdown_executor()
    yield
    with cad_service.tasks_lock:
        cad_service.tasks.clear()
    cad_service.shutdown_executor()


# --------------------------------------------------------------------------- #
# Factory helpers
# --------------------------------------------------------------------------- #
# Direct-ORM style: the helpers talk to the session, not the REST API.
# The REST API itself is exercised in the test bodies, not in the setup.


def make_aeroplane(
    session: Session,
    *,
    name: str = "test-aeroplane",
    total_mass_kg: float | None = None,
) -> AeroplaneModel:
    """Create and commit a minimal AeroplaneModel."""
    aeroplane = AeroplaneModel(
        name=name,
        uuid=uuid.uuid4(),
        total_mass_kg=total_mass_kg,
    )
    session.add(aeroplane)
    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def make_wing(
    session: Session,
    *,
    aeroplane_id: int,
    name: str = "main_wing",
    symmetric: bool = True,
) -> WingModel:
    """Create and commit a minimal WingModel tied to an existing aeroplane."""
    wing = WingModel(
        name=name,
        symmetric=symmetric,
        aeroplane_id=aeroplane_id,
    )
    session.add(wing)
    session.commit()
    session.refresh(wing)
    return wing


def make_fuselage(
    session: Session,
    *,
    aeroplane_id: int,
    name: str = "main_fuselage",
) -> FuselageModel:
    """Create and commit a minimal FuselageModel tied to an existing aeroplane."""
    fuselage = FuselageModel(
        name=name,
        aeroplane_id=aeroplane_id,
    )
    session.add(fuselage)
    session.commit()
    session.refresh(fuselage)
    return fuselage


def make_operating_point(
    session: Session,
    *,
    aircraft_id: int,
    name: str = "op_test",
    velocity: float = 20.0,
    alpha: float = 0.05,
    beta: float = 0.0,
    status: str = "TRIMMED",
) -> OperatingPointModel:
    """Create and commit a minimal OperatingPointModel tied to an aircraft."""
    op = OperatingPointModel(
        name=name,
        aircraft_id=aircraft_id,
        velocity=velocity,
        alpha=alpha,
        beta=beta,
        status=status,
    )
    session.add(op)
    session.commit()
    session.refresh(op)
    return op
