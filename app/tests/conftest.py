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
from datetime import datetime, timezone
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models.aeroplanemodel import (
    AeroplaneModel,
    DesignAssumptionModel,
    FuselageModel,
    WeightItemModel,
    WingModel,
    WingXSecDetailModel,
    WingXSecModel,
    WingXSecTrailingEdgeDeviceModel,
)
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
        expire_on_commit=False,
        class_=Session,
    )
    Base.metadata.create_all(bind=engine)

    # gh#83: seed the default component types so tests see the same registry
    # shape that a migrated prod DB would have.
    _seed_session = TestingSessionLocal()
    try:
        seed_default_types(_seed_session)
        _seed_session.commit()
    finally:
        _seed_session.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
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
    description: str = "",
    velocity: float = 20.0,
    alpha: float = 0.05,
    beta: float = 0.0,
    p: float = 0.0,
    q: float = 0.0,
    r: float = 0.0,
    xyz_ref: list[float] | None = None,
    altitude: float = 0.0,
    status: str = "TRIMMED",
    control_deflections: dict[str, float] | None = None,
) -> OperatingPointModel:
    """Create and commit a minimal OperatingPointModel tied to an aircraft."""
    op = OperatingPointModel(
        name=name,
        description=description,
        aircraft_id=aircraft_id,
        velocity=velocity,
        alpha=alpha,
        beta=beta,
        p=p,
        q=q,
        r=r,
        xyz_ref=xyz_ref or [0.0, 0.0, 0.0],
        altitude=altitude,
        status=status,
        control_deflections=control_deflections,
    )
    session.add(op)
    session.commit()
    session.refresh(op)
    return op


def _add_xsec(
    session: Session,
    wing: WingModel,
    *,
    xyz_le: list[float],
    chord: float,
    twist: float,
    airfoil: str,
    sort_index: int,
    x_sec_type: str | None = None,
    ted_kwargs: dict | None = None,
) -> WingXSecModel:
    """Create a WingXSecModel with optional detail and trailing edge device."""
    xsec = WingXSecModel(
        wing_id=wing.id,
        xyz_le=xyz_le,
        chord=chord,
        twist=twist,
        airfoil=airfoil,
        sort_index=sort_index,
    )
    session.add(xsec)
    session.flush()

    if x_sec_type or ted_kwargs:
        detail = WingXSecDetailModel(
            wing_xsec_id=xsec.id,
            x_sec_type=x_sec_type,
        )
        session.add(detail)
        session.flush()
        if ted_kwargs:
            ted = WingXSecTrailingEdgeDeviceModel(
                wing_xsec_detail_id=detail.id,
                **ted_kwargs,
            )
            session.add(ted)
            session.flush()

    return xsec


def seed_integration_aeroplane(session: Session) -> AeroplaneModel:
    """Create a complete aeroplane with main wing, htail, and vtail for integration tests.

    All geometry uses metres (DB convention). The plane has control surfaces
    on each wing root segment: aileron, elevator, and rudder.
    """
    aeroplane = AeroplaneModel(
        name="integration-test-plane",
        uuid=uuid.uuid4(),
        total_mass_kg=1.5,
        xyz_ref=[0.15, 0.0, 0.0],
    )
    session.add(aeroplane)
    session.flush()

    # --- main wing ---
    main_wing = WingModel(name="main_wing", symmetric=True, aeroplane_id=aeroplane.id)
    session.add(main_wing)
    session.flush()
    _add_xsec(
        session,
        main_wing,
        xyz_le=[0, 0, 0],
        chord=0.2,
        twist=2.0,
        airfoil="naca2412",
        sort_index=0,
        x_sec_type="segment",
        ted_kwargs={
            "name": "MainAileron",
            "role": "aileron",
            "rel_chord_root": 0.75,
            "rel_chord_tip": 0.75,
            "positive_deflection_deg": 25.0,
            "negative_deflection_deg": 25.0,
            "deflection_deg": 0.0,
            "symmetric": False,
        },
    )
    _add_xsec(
        session,
        main_wing,
        xyz_le=[0.0, 0.5, 0.0],
        chord=0.15,
        twist=0.0,
        airfoil="naca2412",
        sort_index=1,
    )

    # --- horizontal tail ---
    htail = WingModel(name="horizontal_tail", symmetric=True, aeroplane_id=aeroplane.id)
    session.add(htail)
    session.flush()
    _add_xsec(
        session,
        htail,
        xyz_le=[0.5, 0.0, 0.0],
        chord=0.1,
        twist=0.0,
        airfoil="naca0012",
        sort_index=0,
        x_sec_type="segment",
        ted_kwargs={
            "name": "Elevator",
            "role": "elevator",
            "rel_chord_root": 0.5,
            "rel_chord_tip": 0.5,
            "positive_deflection_deg": 25.0,
            "negative_deflection_deg": 25.0,
            "deflection_deg": 0.0,
            "symmetric": True,
        },
    )
    _add_xsec(
        session,
        htail,
        xyz_le=[0.5, 0.2, 0.0],
        chord=0.08,
        twist=0.0,
        airfoil="naca0012",
        sort_index=1,
    )

    # --- vertical tail ---
    vtail = WingModel(name="vertical_tail", symmetric=False, aeroplane_id=aeroplane.id)
    session.add(vtail)
    session.flush()
    _add_xsec(
        session,
        vtail,
        xyz_le=[0.5, 0.0, 0.0],
        chord=0.1,
        twist=0.0,
        airfoil="naca0009",
        sort_index=0,
        x_sec_type="segment",
        ted_kwargs={
            "name": "Rudder",
            "role": "rudder",
            "rel_chord_root": 0.5,
            "rel_chord_tip": 0.5,
            "positive_deflection_deg": 25.0,
            "negative_deflection_deg": 25.0,
            "deflection_deg": 0.0,
            "symmetric": True,
        },
    )
    _add_xsec(
        session,
        vtail,
        xyz_le=[0.5, 0.0, 0.15],
        chord=0.07,
        twist=0.0,
        airfoil="naca0009",
        sort_index=1,
    )

    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_design_assumptions(session: Session, aeroplane_id: int) -> list[DesignAssumptionModel]:
    """Seed the minimal set of design assumptions needed for analysis endpoints."""
    params = {
        "mass": 1.5,
        "cg_x": 0.15,
        "cl_max": 1.4,
        "g_limit": 3.0,
        "cd0": 0.03,
        "target_static_margin": 0.12,
    }
    rows = []
    for name, value in params.items():
        row = DesignAssumptionModel(
            aeroplane_id=aeroplane_id,
            parameter_name=name,
            estimate_value=value,
            active_source="ESTIMATE",
            updated_at=datetime.now(timezone.utc),
        )
        session.add(row)
        rows.append(row)
    session.commit()
    for r in rows:
        session.refresh(r)
    return rows
